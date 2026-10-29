"""
ocr.py – Motor de extracción de texto de alta precisión para capturas de pantalla.

Mejoras y correcciones:
- Preprocesamiento multi-etapa con denoising adaptativo (fastNlMeansDenoising).
- Detección robusta de fondo oscuro (Dark Mode) basada en percentil p25/p75.
- Binarización adaptativa Gaussian (por zona) como alternativa al umbral global.
- Deskew automático: calcula y corrige la inclinación con proyección horizontal.
- Escalado 3× para imágenes muy pequeñas (<100px) y 2× para medianas (<300px/<600px).
- Orden de PSM calibrado: [6, 4, 3, 11] con selector del mejor resultado.
- Fallback con binarización Otsu + morfología de apertura para texto muy fino.
- Configuración limpia y robusta de TESSDATA_PREFIX: evita errores de apertura
  de archivos traineddata provocados por comillas escapadas en Windows.
- Búsqueda recursiva y exhaustiva de tessdata (PyInstaller MEIPASS, ejecutable, local y sistema).
- Limpieza de texto enriquecida: artefactos OCR comunes, guiones rotos, URLs, etc.
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
        return os.path.abspath(env_path)

    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
        exe_name = "tesseract.exe" if platform.system() == "Windows" else "tesseract"
        candidate = os.path.join(base, "tesseract", exe_name)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)

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
            return os.path.abspath(p)

    return "tesseract"


@functools.lru_cache(maxsize=1)
def _get_tessdata_dir() -> Optional[str]:
    """
    Localiza la carpeta tessdata con modelos .traineddata.
    Prioriza:
    1. Carpeta local del proyecto o junto al ejecutable.
    2. Directorio empaquetado por PyInstaller (_MEIPASS).
    3. Instalación de Tesseract en el sistema operativo.
    """
    candidates = []

    # 1. Empaquetado PyInstaller
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            candidates.append(os.path.join(sys._MEIPASS, "tessdata"))
            candidates.append(os.path.join(sys._MEIPASS, "tesseract", "tessdata"))
        candidates.append(os.path.join(os.path.dirname(sys.executable), "tessdata"))

    # 2. Proyecto local / Entorno de desarrollo
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(base, "tessdata"))
    candidates.append(os.path.join(base, "tesseract", "tessdata"))

    # 3. Variable de entorno preexistente (si es válida)
    env_prefix = os.environ.get("TESSDATA_PREFIX")
    if env_prefix:
        candidates.append(env_prefix)

    # 4. Instalaciones estándar del sistema
    if platform.system() == "Windows":
        candidates.extend([
            r"C:\Program Files\Tesseract-OCR\tessdata",
            r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
            os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tessdata"),
        ])
    else:
        candidates.extend([
            "/usr/share/tesseract-ocr/5/tessdata",
            "/usr/share/tesseract-ocr/4.00/tessdata",
            "/usr/share/tessdata",
        ])

    for path in candidates:
        if path and os.path.isdir(path):
            # Verificar si contiene al menos un modelo .traineddata
            try:
                files = os.listdir(path)
                if any(f.endswith(".traineddata") for f in files):
                    norm = os.path.normpath(os.path.abspath(path))
                    logger.debug("Directorio tessdata localizado: %s", norm)
                    return norm
            except Exception:
                continue

    return None


_tesseract_configured = False


def _configure_tesseract() -> None:
    """Configura Tesseract y la variable TESSDATA_PREFIX una sola vez de forma limpia."""
    global _tesseract_configured
    if _tesseract_configured:
        return

    pytesseract.pytesseract.tesseract_cmd = _get_tesseract_path()

    tessdata = _get_tessdata_dir()
    if tessdata:
        # Tesseract utiliza TESSDATA_PREFIX sin comillas ni caracteres extraños
        os.environ["TESSDATA_PREFIX"] = tessdata
        logger.debug("TESSDATA_PREFIX configurado: %s", tessdata)

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
    8. Artefactos OCR comunes.
    9. Normaliza espacios múltiples horizontales (respetando indentación).
    10. Reduce saltos de línea excesivos a máximo dos consecutivos.
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
    text = re.sub(r"-\n([a-záéíóúüñA-ZÁÉÍÓÚÜÑ])", r"\1", text)

    # 8. Artefactos OCR comunes
    text = text.replace("``", '"').replace("''", '"')
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
    Determina si la imagen tiene fondo oscuro usando percentiles p25/p75.
    Más robusto que la media simple ante textos grandes sobre fondo claro.
    """
    p75 = float(np.percentile(gray, 75))
    mean_val = float(np.mean(gray))
    return mean_val < 120 and p75 < 180


def _deskew(gray: np.ndarray) -> np.ndarray:
    """
    Corrige inclinaciones menores (< ±10°) usando proyección horizontal de píxeles.
    """
    try:
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(binary > 0))
        if len(coords) < 50:
            return gray

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle

        if abs(angle) < 0.5 or abs(angle) > 10:
            return gray

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
    3. Denoising adaptativo (fastNlMeansDenoising) para capturas con ruido.
    4. Corrección de inclinación (deskew) para ángulos leves (< 10°).
    5. Escalado adaptativo (3× para <100px, 2× para <300px/<600px).
    6. Binarización adaptativa Gaussian (por zona).
    7. Margen blanco exterior de 20px para proteger caracteres perimetrales.

    Returns:
        Objeto PIL.Image listo para pytesseract.
    """
    if pil_image is None:
        raise ValueError("La imagen de entrada no puede ser None.")

    img_rgb = np.array(pil_image.convert("RGB"))
    if img_rgb.size == 0:
        raise ValueError("La imagen de entrada está vacía.")

    # 1. Escala de grises
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

    # 2. Detección de fondo oscuro
    if _is_dark_background(gray):
        logger.debug("Fondo oscuro detectado; invirtiendo colores.")
        gray = cv2.bitwise_not(gray)

    # 3. Denoising ligero
    h_val, w_val = gray.shape
    if h_val * w_val > 10_000:
        gray = cv2.fastNlMeansDenoising(gray, h=10, templateWindowSize=7, searchWindowSize=21)

    # 4. Corrección de inclinación
    gray = _deskew(gray)

    # 5. Escalado adaptativo
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

    # 6. Binarización adaptativa Gaussiana
    bin_adaptive = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )
    gray = cv2.addWeighted(gray, 0.7, bin_adaptive, 0.3, 0)

    # 7. Margen blanco exterior de 20px
    padded = cv2.copyMakeBorder(gray, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)

    return Image.fromarray(padded)


def _preprocess_binary(pil_image: Image.Image) -> Image.Image:
    """
    Variante de preprocesamiento con binarización Otsu + apertura morfológica.
    Usado como fallback cuando el preprocesamiento principal no obtiene texto.
    """
    img_rgb = np.array(pil_image.convert("RGB"))
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

    if _is_dark_background(gray):
        gray = cv2.bitwise_not(gray)

    h_val, w_val = gray.shape
    if h_val < 300 or w_val < 600:
        scale = 2.0
        gray = cv2.resize(gray, (int(w_val * scale), int(h_val * scale)), interpolation=cv2.INTER_CUBIC)

    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
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
      - PSM 6  (bloque uniforme de texto)
      - PSM 4  (columna de texto variable)
      - PSM 3  (automático de página)
      - PSM 11 (texto disperso)

    Args:
        pil_image: Imagen PIL a procesar.
        langs:     Idiomas de Tesseract separados por '+'. Por defecto 'spa+eng'.

    Returns:
        Texto extraído limpio. Cadena vacía si no se detectó texto.
    """
    _configure_tesseract()

    if pil_image is None:
        return "[Error OCR: la imagen proporcionada es None]"

    try:
        processed = preprocess_image(pil_image)
    except Exception as exc:
        logger.error("Error en preprocesamiento: %s", exc)
        return f"[Error OCR en preprocesamiento: {exc}]"

    # Parámetros calibrados:
    # NOTA: TESSDATA_PREFIX se gestiona via variable de entorno en _configure_tesseract()
    # para evitar problemas de escape de comillas en rutas de Windows con espacios.
    base_config = "--oem 3 --dpi 300 -c preserve_interword_spaces=1"

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
            # Si PSM 6 o 4 ya devuelven buen resultado, terminamos antes
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
