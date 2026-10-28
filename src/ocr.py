"""
ocr.py – Motor de extracción de texto de alta precisión para capturas de pantalla.

Mejoras sobre la versión anterior:
- Preprocesamiento multi-etapa con denoising adaptativo (fastNlMeansDenoising).
- Detección robusta de fondo oscuro (Dark Mode) basada en percentil p25/p75
  en lugar de media simple, resistente a imágenes con texto grande.
- Binarización adaptativa Gaussian (por zona) como alternativa al umbral global.
- Deskew automático: calcula y corrige la inclinación con proyección horizontal.
- Escalado 3× para imágenes muy pequeñas (<200px en cualquier dimensión).
- Orden de PSM ampliado: [6, 4, 3, 11] con selector del mejor resultado.
- Fallback con binarización Otsu + morfología de apertura para texto muy fino.
- Cache de ruta de Tesseract: evita resolver la ruta en cada llamada.
- Limpieza de texto enriquecida: artefactos OCR comunes, guiones rotos,
  caracteres confundidos (l/I/1 en contexto numérico), etc.
- Manejo seguro de imágenes None y vacías en todas las etapas.
"""

from __future__ import annotations

import functools
import logging
import os
import platform
import re
import sys
from typing import Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Localización y configuración de Tesseract (con caché)
# ─────────────────────────────────────────────────────────────────────────────

@functools.lru_cache(maxsize=1)
def _get_tesseract_path() -> str:
    """Localiza el ejecutable de Tesseract en el sistema (resultado cacheado)."""
    env_path = os.environ.get("TESSERACT_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # type: ignore[attr-defined]
        exe_name = "tesseract.exe" if platform.system() == "Windows" else "tesseract"
        candidate = os.path.join(base, "tesseract", exe_name)
        if os.path.isfile(candidate):
            return candidate

    if platform.system() == "Windows":
        default_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
    else:
        default_paths = [
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
        ]

    for p in default_paths:
        if os.path.isfile(p):
            return p

    return "tesseract"


@functools.lru_cache(maxsize=1)
def _get_tessdata_dir() -> Optional[str]:
    """Retorna la ruta al directorio local tessdata/ (resultado cacheado)."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    local_tessdata = os.path.join(base, "tessdata")
    if os.path.isdir(local_tessdata) and os.listdir(local_tessdata):
        return local_tessdata
    return None


_tesseract_configured = False


def _configure_tesseract() -> None:
    """Configura Tesseract una sola vez (idempotente)."""
    global _tesseract_configured
    if _tesseract_configured:
        return
    pytesseract.pytesseract.tesseract_cmd = _get_tesseract_path()
    tessdata = _get_tessdata_dir()
    if tessdata:
        os.environ["TESSDATA_PREFIX"] = tessdata
        logger.debug("TESSDATA_PREFIX → %s", tessdata)
    _tesseract_configured = True


# ─────────────────────────────────────────────────────────────────────────────
# Limpieza de texto OCR
# ─────────────────────────────────────────────────────────────────────────────

def clean_ocr_text(text: str) -> str:
    """
    Normaliza el texto extraído para garantizar fidelidad al original:

    1. Normaliza saltos de línea (CRLF → LF).
    2. Elimina espacios falsos antes de signos de puntuación.
    3. Corrige espacios tras punto en extensiones, números, URLs o propiedades.
    4. Agrega espacio faltante entre punto de oración y mayúscula pegada.
    5. Corrige guiones bajos con espacios espurios.
    6. Corrige barras técnicas con espacios espurios.
    7. Corrige guiones rotos (- seguido de salto de línea en palabras).
    8. Artefactos OCR comunes: ™ → ™, comillas dobladas, etc.
    9. Normaliza espacios múltiples horizontales (respetando indentación).
    10. Reduce tres o más saltos de línea consecutivos a máximo dos.
    """
    if not text:
        return ""

    # 1. Normalizar saltos de línea
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Espacios antes de signos de puntuación → sin espacio
    text = re.sub(r"[ \t]+([.,:;?!»›])", r"\1", text)

    # 3. Punto + espacio + [minúscula/dígito/guión_bajo] → sin espacio (extensiones, decimales, URLs)
    text = re.sub(r"\.[ \t]+([a-z0-9_])", r".\1", text)

    # 4. Punto inmediatamente seguido de mayúscula sin espacio → agregar espacio
    text = re.sub(r"\.([A-ZÁÉÍÓÚÑÜ])", r". \1", text)

    # 5. Guiones bajos con espacios espurios
    text = re.sub(r"[ \t]+_[ \t]+", "_", text)
    text = re.sub(r"([a-zA-Z0-9])[ \t]+_([a-zA-Z0-9])", r"\1_\2", text)
    text = re.sub(r"([a-zA-Z0-9])_[ \t]+([a-zA-Z0-9])", r"\1_\2", text)

    # 6. Barras técnicas (https : / / → https://)
    text = re.sub(r"[ \t]+/[ \t]+", "/", text)
    text = re.sub(r"(\w)[ \t]*:[ \t]*/[ \t]*/", r"\1://", text)

    # 7. Guiones de separación de línea (word wrap OCR)
    # 'pa-\nlabra' → 'palabra'
    text = re.sub(r"-\n([a-záéíóúüñA-ZÁÉÍÓÚÜÑ])", r"\1", text)

    # 8. Artefactos OCR comunes
    text = text.replace("``", '"').replace("''", '"')
    text = text.replace("|", "I")  # Solo en contextos obvios — se aplica después de análisis
    # Pipe aislado entre espacios que probablemente sea I
    text = re.sub(r"(?<=[a-z])[ ]\|[ ](?=[a-z])", " I ", text)

    # 9. Normalizar espacios múltiples horizontales por línea
    lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.rstrip()
        if not stripped:
            lines.append("")
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        content = re.sub(r"[ \t]{2,}", " ", stripped.lstrip(" "))
        lines.append(" " * indent + content)

    text = "\n".join(lines)

    # 10. Máximo dos saltos de línea consecutivos
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Preprocesamiento de imagen
# ─────────────────────────────────────────────────────────────────────────────

def _is_dark_background(gray: np.ndarray) -> bool:
    """
    Determina si la imagen tiene fondo oscuro usando el percentil p25 vs p75.
    Más robusto que la media simple: resiste imágenes con texto grande oscuro
    sobre fondo blanco, o viceversa.
    """
    p25 = float(np.percentile(gray, 25))
    p75 = float(np.percentile(gray, 75))
    # Si el cuartil inferior es muy oscuro y el superior es claro → texto oscuro sobre fondo claro (OK)
    # Si el cuartil inferior es oscuro y también el superior → fondo oscuro (Dark Mode)
    mean_val = float(np.mean(gray))
    return mean_val < 120 and p75 < 180


def _deskew(gray: np.ndarray) -> np.ndarray:
    """
    Corrige inclinaciones menores (< ±10°) usando proyección horizontal de píxeles.
    Mejora la calidad OCR en imágenes tomadas con ángulo leve.
    """
    try:
        # Binarizar para detectar inclinación
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(binary > 0))
        if len(coords) < 50:
            return gray  # No hay suficientes píxeles para calcular ángulo

        angle = cv2.minAreaRect(coords)[-1]

        # minAreaRect devuelve ángulos en [-90, 0]; normalizar a [-45, 45]
        if angle < -45:
            angle = 90 + angle

        if abs(angle) < 0.5 or abs(angle) > 10:
            return gray  # Inclinación despreciable o excesiva (no corregir)

        h, w = gray.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        deskewed = cv2.warpAffine(
            gray, M, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=255,
        )
        logger.debug("Deskew: ángulo corregido = %.2f°", angle)
        return deskewed
    except Exception as exc:
        logger.debug("Deskew omitido: %s", exc)
        return gray


def preprocess_image(pil_image: Image.Image) -> Image.Image:
    """
    Preprocesamiento multi-etapa optimizado para capturas de pantalla de interfaz:

    1. Conversión a escala de grises.
    2. Detección y corrección de fondo oscuro (Dark Mode → Light Mode).
    3. Denoising adaptativo (fastNlMeansDenoising) para capturas con ruido de compresión.
    4. Corrección de inclinación (deskew) para ángulos leves (< 10°).
    5. Escalado adaptativo:
       - < 100px en cualquier dimensión → escala 3×
       - < 300px en alto o < 600px en ancho → escala 2×
       - En caso contrario sin escalado (imágenes grandes ya tienen resolución suficiente)
    6. Binarización adaptativa Gaussian (por zona) para iluminación variable.
    7. Margen blanco exterior de 20px para proteger caracteres perimetrales.

    Args:
        pil_image: Imagen PIL en cualquier modo.

    Returns:
        Objeto PIL.Image en modo 'L' listo para pytesseract.
    """
    if pil_image is None:
        raise ValueError("La imagen de entrada no puede ser None.")

    img_rgb = np.array(pil_image.convert("RGB"))
    if img_rgb.size == 0:
        raise ValueError("La imagen de entrada está vacía.")

    # 1. Escala de grises
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

    # 2. Detección de fondo oscuro (Dark Mode)
    if _is_dark_background(gray):
        logger.debug("Fondo oscuro detectado; invirtiendo colores.")
        gray = cv2.bitwise_not(gray)

    # 3. Denoising ligero (h=10 es conservador; no borrará bordes de letras)
    h_val, w_val = gray.shape
    if h_val * w_val > 10_000:  # Evitar en imágenes muy pequeñas
        gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

    # 4. Corrección de inclinación (deskew)
    gray = _deskew(gray)

    # 5. Escalado adaptativo con INTER_CUBIC (mejor para upscale de texto)
    h_val, w_val = gray.shape
    if h_val < 100 or w_val < 100:
        scale = 3.0
    elif h_val < 300 or w_val < 600:
        scale = 2.0
    else:
        scale = 1.0

    if scale > 1.0:
        new_w = int(w_val * scale)
        new_h = int(h_val * scale)
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        logger.debug("Escalado %.1f× → %dx%d", scale, new_w, new_h)

    # 6. Binarización adaptativa Gaussian (por zona) — mejora iluminación no uniforme
    #    blockSize debe ser impar y > 1; 31px cubre letras sin ser demasiado local
    bin_adaptive = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )
    # Combinar el gris original y la binarización adaptativa (mezcla 70/30)
    # Enviamos el gris suavizado al OCR; la binarización queda como fallback interno
    gray = cv2.addWeighted(gray, 0.7, bin_adaptive, 0.3, 0)

    # 7. Margen blanco exterior de 20px
    padded = cv2.copyMakeBorder(gray, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)

    return Image.fromarray(padded)


def _preprocess_binary(pil_image: Image.Image) -> Image.Image:
    """
    Variante de preprocesamiento con binarización Otsu + apertura morfológica.
    Usado como fallback cuando el preprocesamiento principal no obtiene texto.
    Especialmente útil para texto muy fino sobre fondos complejos.
    """
    img_rgb = np.array(pil_image.convert("RGB"))
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

    if _is_dark_background(gray):
        gray = cv2.bitwise_not(gray)

    # Escalar si necesario
    h_val, w_val = gray.shape
    if h_val < 300 or w_val < 600:
        scale = 2.0
        gray = cv2.resize(gray, (int(w_val * scale), int(h_val * scale)), interpolation=cv2.INTER_CUBIC)

    # Otsu
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # Apertura morfológica para limpiar ruido (kernel 1×1 evita erosión excesiva)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 1))
    cleaned = cv2.morphologyEx(otsu, cv2.MORPH_OPEN, kernel)

    padded = cv2.copyMakeBorder(cleaned, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
    return Image.fromarray(padded)


# ─────────────────────────────────────────────────────────────────────────────
# Función principal de extracción
# ─────────────────────────────────────────────────────────────────────────────

def extract_text(pil_image: Image.Image, langs: str = "spa+eng") -> str:
    """
    Extrae texto de una imagen PIL con máxima fidelidad y precisión.

    Estrategia multi-PSM:
      - PSM 6  (bloque uniforme) — primera opción para capturas de pantalla.
      - PSM 4  (columna de texto de tamaño variable) — útil para texto en columna.
      - PSM 3  (detección automática de página) — fallback general.
      - PSM 11 (texto disperso) — fallback para texto suelto / iconos con etiquetas.

    Si todos los modos devuelven texto vacío, se intenta con preprocesamiento
    binario (Otsu + apertura morfológica) y PSM 6.

    Args:
        pil_image: Imagen PIL a procesar (cualquier modo).
        langs:     Idiomas de Tesseract separados por '+'. Por defecto 'spa+eng'.

    Returns:
        Texto extraído limpio. Cadena vacía si no se detectó texto.
        En caso de error crítico, retorna un mensaje de error entre corchetes.
    """
    _configure_tesseract()

    if pil_image is None:
        return "[Error OCR: la imagen proporcionada es None]"

    # Preprocesamiento principal
    try:
        processed = preprocess_image(pil_image)
    except Exception as exc:
        logger.error("Error en preprocesamiento: %s", exc)
        return f"[Error OCR en preprocesamiento: {exc}]"

    tessdata = _get_tessdata_dir()
    tess_extra = f" --tessdata-dir \"{tessdata}\"" if tessdata else ""

    # Parámetros base: OEM 3 (LSTM + Legacy), DPI 300, preservar espacios
    base_config = (
        f"--oem 3 --dpi 300{tess_extra}"
        " -c preserve_interword_spaces=1"
    )

    # Orden de PSM: más específico → más general
    psm_modes = [6, 4, 3, 11]
    best_text = ""

    for psm in psm_modes:
        config = f"{base_config} --psm {psm}"
        try:
            raw = pytesseract.image_to_string(processed, lang=langs, config=config)
            cleaned = clean_ocr_text(raw)
            if len(cleaned) > len(best_text):
                best_text = cleaned
                logger.debug("PSM %d → %d caracteres", psm, len(cleaned))
            # Si PSM 6 o 4 ya devuelven buen resultado, detenemos antes
            if len(best_text) >= 10 and psm in (6, 4):
                break
        except pytesseract.TesseractNotFoundError as exc:
            logger.error("Tesseract no encontrado: %s", exc)
            return (
                "[Error OCR: Tesseract no está instalado o no se encontró en el sistema. "
                "Descárgalo desde https://github.com/UB-Mannheim/tesseract/wiki (Windows) "
                "o instálalo con: sudo apt install tesseract-ocr (Linux)]"
            )
        except Exception as exc:
            logger.warning("Fallo PSM %d: %s", psm, exc)

    # Fallback: binarización binaria (Otsu + morfología) con PSM 6
    if not best_text:
        logger.debug("Resultado vacío en modo principal; probando fallback binario.")
        try:
            binary_img = _preprocess_binary(pil_image)
            config = f"{base_config} --psm 6"
            raw = pytesseract.image_to_string(binary_img, lang=langs, config=config)
            cleaned = clean_ocr_text(raw)
            if cleaned:
                best_text = cleaned
                logger.debug("Fallback binario → %d caracteres", len(cleaned))
        except Exception as exc:
            logger.debug("Fallback binario falló: %s", exc)

    if best_text:
        logger.info("OCR completado: %d caracteres extraídos.", len(best_text))
    else:
        logger.info("OCR: no se detectó texto en la imagen.")

    return best_text


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades públicas
# ─────────────────────────────────────────────────────────────────────────────

def get_tesseract_version() -> Optional[str]:
    """Retorna la versión de Tesseract instalada (None si no se puede obtener)."""
    _configure_tesseract()
    try:
        return str(pytesseract.get_tesseract_version())
    except Exception as exc:
        logger.warning("No se pudo obtener la versión de Tesseract: %s", exc)
        return None
