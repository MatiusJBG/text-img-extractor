"""
ocr.py – Motor de extracción de texto optimizado para capturas de pantalla.

Diseñado específicamente para screenshots de escritorio:
- Inversión automática para modo oscuro (Dark Mode).
- Padding perimetral blanco para evitar corte de caracteres en los bordes.
- Escalado adaptativo con interpolación Lanczos4 (sin halos ni distorsión en puntos).
- Parámetros calibrados: --dpi 300 y preserve_interword_spaces=1.
- Limpieza y fidelidad de espaciado (elimina espacios espurios antes o después de puntos).
- Soporte para modelos de lenguaje en tessdata/ (español + inglés).
"""

import os
import sys
import platform
import logging
import re
from typing import Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image

logger = logging.getLogger(__name__)


def _get_tesseract_path() -> str:
    """Localiza el ejecutable de Tesseract en el sistema."""
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


def _get_tessdata_dir() -> Optional[str]:
    """Retorna la ruta al directorio local tessdata/ si contiene modelos entrenados."""
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    local_tessdata = os.path.join(base, "tessdata")
    if os.path.isdir(local_tessdata):
        return local_tessdata
    return None


def _configure_tesseract() -> None:
    """Configura la ruta de Tesseract y el prefijo de tessdata."""
    pytesseract.pytesseract.tesseract_cmd = _get_tesseract_path()
    tessdata = _get_tessdata_dir()
    if tessdata:
        os.environ["TESSDATA_PREFIX"] = tessdata


def clean_ocr_text(text: str) -> str:
    """
    Normaliza el texto extraído para garantizar fidelidad al original:
    1. Elimina espacios falsos antes de signos de puntuación (ej: 'hola . mundo' -> 'hola. mundo').
    2. Elimina espacios falsos después de puntos en extensiones, números, URLs o métodos
       (ej: 'archivo. py' -> 'archivo.py', '1. 0. 4' -> '1.0.4', 'app. exe' -> 'app.exe').
    3. Asegura espaciado natural tras punto que finaliza oración (seguido de mayúscula).
    4. Corrige espacios espurios alrededor de guiones bajos o barras técnicas (ej: 'user _ id' -> 'user_id').
    5. Reduce espacios dobles horizontales respetando la estructura de párrafos.
    """
    if not text:
        return ""

    # Normalizar saltos de línea
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 1. Quitar espacios antes de signos de puntuación: 'palabra .' -> 'palabra.'
    text = re.sub(r"[ \t]+([.,:;?!])", r"\1", text)

    # 2. Corregir espacios tras punto en extensiones, números, URLs o propiedades:
    # Si después del punto hay espacios y luego una minúscula, dígito o guion bajo:
    # 'archivo. py' -> 'archivo.py', '1. 0' -> '1.0', 'com. ar' -> 'com.ar'
    text = re.sub(r"\.[ \t]+([a-z0-9_])", r".\1", text)

    # 3. Tras punto de oración seguido inmediatamente de letra mayúscula sin espacio:
    # 'final.Siguiente' -> 'final. Siguiente'
    text = re.sub(r"\.([A-ZÁÉÍÓÚÑ])", r". \1", text)

    # 4. Símbolos técnicos: guiones bajos con espacios espurios
    text = re.sub(r"[ \t]+_[ \t]+", "_", text)
    text = re.sub(r"([a-zA-Z0-9])[ \t]+_([a-zA-Z0-9])", r"\1_\2", text)
    text = re.sub(r"([a-zA-Z0-9])_[ \t]+([a-zA-Z0-9])", r"\1_\2", text)

    # 5. Barras técnicas: 'https : / /' -> 'https://'
    text = re.sub(r"[ \t]+/[ \t]+", "/", text)

    # 6. Normalizar espacios múltiples horizontales por línea
    lines = []
    for line in text.split("\n"):
        stripped = line.rstrip()
        if not stripped:
            lines.append("")
            continue
        indent = len(stripped) - len(stripped.lstrip(" "))
        content = re.sub(r"[ \t]{2,}", " ", stripped.lstrip(" "))
        lines.append(" " * indent + content)

    text = "\n".join(lines)
    # Máximo dos saltos de línea consecutivos
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def preprocess_image(pil_image: Image.Image) -> np.ndarray:
    """
    Preprocesamiento especializado para capturas de pantalla de interfaz:
    1. Conversión a escala de grises.
    2. Detección y corrección de fondo oscuro (Dark Mode -> Light Mode).
    3. Escalado adaptativo con Lanczos4 para preservar puntos nítidos sin artefactos de halo.
    4. Margen blanco exterior (padding) de 20px para proteger caracteres perimetrales.
    """
    if pil_image is None:
        raise ValueError("La imagen de entrada no puede ser None.")

    img_rgb = np.array(pil_image.convert("RGB"))
    if img_rgb.size == 0:
        raise ValueError("La imagen de entrada está vacía.")

    # 1. Escala de grises
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)

    # 2. Detección de fondo oscuro (Dark Mode)
    mean_val = np.mean(gray)
    if mean_val < 128:
        logger.debug("Fondo oscuro detectado (media=%.1f); invirtiendo colores.", mean_val)
        gray = cv2.bitwise_not(gray)

    # 3. Escalado adaptativo con INTER_LANCZOS4
    # Si la imagen tiene poca altura, escalamos a 2x para alcanzar la resolución óptima
    h, w = gray.shape
    if h < 200 or w < 400:
        scale = 2.0
        new_w = int(w * scale)
        new_h = int(h * scale)
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)

    # 4. Margen blanco exterior de 20px
    padded = cv2.copyMakeBorder(
        gray, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255
    )

    return padded


def extract_text(pil_image: Image.Image, langs: str = "spa+eng") -> str:
    """
    Extrae texto de una captura garantizando fidelidad de espaciado y caracteres.
    Usa --dpi 300 y preserve_interword_spaces=1 con limpieza posterior de artefactos.
    """
    _configure_tesseract()

    if pil_image is None:
        return "[Error OCR: la imagen proporcionada es None]"

    try:
        processed = preprocess_image(pil_image)
    except Exception as exc:
        logger.error("Error en preprocesamiento: %s", exc)
        return f"[Error OCR en preprocesamiento: {exc}]"

    tessdata = _get_tessdata_dir()
    tess_extra = f" --tessdata-dir {tessdata}" if tessdata else ""

    # Parámetros calibrados para fidelidad de espaciado y resolución
    base_config = f"--oem 3 --dpi 300{tess_extra} -c preserve_interword_spaces=1"

    # Estrategia de segmentación:
    # PSM 6: Asume bloque uniforme de texto (el más preciso para recortes de pantalla)
    # PSM 3: Fallback si PSM 6 devuelve vacío
    psm_modes = [6, 3, 11]
    best_text = ""

    for psm in psm_modes:
        config = f"{base_config} --psm {psm}"
        try:
            raw_text = pytesseract.image_to_string(processed, lang=langs, config=config)
            cleaned = clean_ocr_text(raw_text)
            if len(cleaned) > len(best_text):
                best_text = cleaned
            # Si obtuvimos un texto válido con PSM 6, terminamos inmediatamente
            if len(best_text) >= 2 and psm == 6:
                break
        except pytesseract.TesseractNotFoundError as exc:
            logger.error("Tesseract no encontrado: %s", exc)
            return (
                "[Error OCR: Tesseract no está instalado o no se encontró en el sistema. "
                "Instálalo desde https://github.com/UB-Mannheim/tesseract/wiki (Windows)]"
            )
        except Exception as exc:
            logger.warning("Fallo intento con PSM %d: %s", psm, exc)

    # Fallback con binarización Otsu si los modos estándar no detectaron nada
    if not best_text:
        try:
            _, otsu = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            config = f"{base_config} --psm 6"
            otsu_text = pytesseract.image_to_string(otsu, lang=langs, config=config)
            cleaned_otsu = clean_ocr_text(otsu_text)
            if cleaned_otsu:
                best_text = cleaned_otsu
        except Exception as exc:
            logger.debug("Fallback Otsu no obtuvo resultado: %s", exc)

    return best_text


def get_tesseract_version() -> Optional[str]:
    """Retorna la versión de Tesseract instalada."""
    _configure_tesseract()
    try:
        return str(pytesseract.get_tesseract_version())
    except Exception as exc:
        logger.warning("No se pudo obtener la versión de Tesseract: %s", exc)
        return None
