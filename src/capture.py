"""
capture.py – Módulo de captura de pantalla de alta velocidad.
Soporta: pantalla completa, ventana activa, región (rect).

Mejoras sobre la versión anterior:
- DPI Awareness en Windows (SetProcessDpiAwarenessContext) para capturas
  a resolución nativa en pantallas HiDPI/4K sin escalado del sistema.
- Conversión BGRA → RGB robusta usando numpy (evita artefactos de color).
- Logging de tiempos de captura en DEBUG para diagnóstico de rendimiento.
- Fallback mejorado a PIL.ImageGrab con bbox correcto en todos los casos.

Dependencias:
    - mss
    - Pillow (PIL)
    - numpy
    - pywin32 (solo Windows, para captura de ventana activa)
    - xdotool (solo Linux, para captura de ventana activa)
"""

from __future__ import annotations

import platform
import logging
import time
from typing import Optional, Tuple

import mss
import mss.tools
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

def _get_mss():
    """Retorna una instancia de MSS compatible sin advertencias de deprecación."""
    return mss.MSS() if hasattr(mss, "MSS") else mss.mss()


# ─────────────────────────────────────────────────────────────────────────────
# DPI Awareness (Windows)
# ─────────────────────────────────────────────────────────────────────────────

_dpi_awareness_set = False


def _ensure_dpi_awareness() -> None:
    """
    Configura DPI awareness en Windows para obtener capturas a resolución
    nativa en pantallas HiDPI (125%, 150%, 200%, etc.).
    Se llama una sola vez; posteriores invocaciones son no-op.
    """
    global _dpi_awareness_set
    if _dpi_awareness_set or platform.system() != "Windows":
        return
    try:
        import ctypes
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4 (Windows 10 1703+)
        ctypes.windll.shcore.SetProcessDpiAwarenessContext(-4)
        logger.debug("DPI Awareness configurado: Per-Monitor V2")
    except AttributeError:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
            logger.debug("DPI Awareness configurado: System DPI Aware (fallback)")
        except Exception as exc:
            logger.debug("No se pudo configurar DPI Awareness: %s", exc)
    finally:
        _dpi_awareness_set = True


# ─────────────────────────────────────────────────────────────────────────────
# Conversión de imagen
# ─────────────────────────────────────────────────────────────────────────────

def _sct_to_pil(sct_img) -> Image.Image:
    """
    Convierte una imagen mss.ScreenShot a PIL.Image en modo RGB.
    Usa numpy para la conversión BGRA → RGB sin artefactos.
    """
    # mss devuelve datos en formato BGRA
    arr = np.frombuffer(sct_img.bgra, dtype=np.uint8)
    arr = arr.reshape((sct_img.height, sct_img.width, 4))
    # BGRA → RGB (descartar canal A, reordenar B y R)
    rgb = arr[:, :, [2, 1, 0]]
    return Image.fromarray(rgb, mode="RGB")


# ─────────────────────────────────────────────────────────────────────────────
# Capturas
# ─────────────────────────────────────────────────────────────────────────────

def capture_full() -> Image.Image:
    """
    Captura toda la pantalla primaria y retorna un objeto PIL.Image en modo RGB.

    Intenta primero con ``mss`` (máxima velocidad) y, si falla, usa
    ``PIL.ImageGrab`` como fallback (más compatible en entornos Windows).

    Returns:
        PIL.Image.Image: Imagen capturada del monitor primario.

    Raises:
        RuntimeError: Si ambos métodos fallan.
    """
    _ensure_dpi_awareness()
    t0 = time.perf_counter()

    # Intento 1: mss (más rápido, nativo)
    try:
        with _get_mss() as sct:
            monitor = sct.monitors[1]  # monitor primario
            sct_img = sct.grab(monitor)
            img = _sct_to_pil(sct_img)
            logger.debug("capture_full (mss) en %.1f ms", (time.perf_counter() - t0) * 1000)
            return img
    except Exception as exc:
        logger.warning("mss falló para capture_full (%s), usando PIL.ImageGrab.", exc)

    # Fallback: PIL.ImageGrab (solo Windows/macOS)
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab(all_screens=False)
        img = img.convert("RGB")
        logger.debug("capture_full (ImageGrab) en %.1f ms", (time.perf_counter() - t0) * 1000)
        return img
    except Exception as exc2:
        logger.error("PIL.ImageGrab también falló: %s", exc2)
        raise RuntimeError(f"No se pudo capturar la pantalla completa: {exc2}") from exc2


def capture_active_window() -> Image.Image:
    """
    Captura la ventana activa del sistema operativo.

    En Windows utiliza win32gui para obtener las coordenadas de la ventana
    en primer plano. En Linux utiliza xdotool + xwininfo para obtener la
    geometría de la ventana activa. Si ocurre cualquier error, se realiza
    un fallback a la captura de pantalla completa.

    Returns:
        PIL.Image.Image: Imagen capturada de la ventana activa, o de la
        pantalla completa si la captura de ventana falla.
    """
    _ensure_dpi_awareness()
    try:
        if platform.system() == "Windows":
            return _capture_active_window_win()
        else:
            return _capture_active_window_linux()
    except Exception as exc:
        logger.warning(
            "No se pudo capturar la ventana activa (%s). "
            "Realizando fallback a pantalla completa.", exc
        )
        return capture_full()


def _capture_active_window_win() -> Image.Image:
    """
    Captura la ventana activa en Windows usando la API win32gui.

    Returns:
        PIL.Image.Image: Imagen de la ventana en primer plano.

    Raises:
        ImportError: Si pywin32 no está instalado.
        RuntimeError: Si no se puede obtener la geometría de la ventana.
    """
    try:
        import win32gui
    except ImportError as exc:
        raise ImportError(
            "pywin32 es necesario para capturar la ventana activa en Windows. "
            "Instálalo con: pip install pywin32"
        ) from exc

    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        raise RuntimeError("No se encontró ninguna ventana en primer plano.")

    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    width = right - left
    height = bottom - top

    if width <= 0 or height <= 0:
        raise RuntimeError(
            f"Geometría de ventana inválida: left={left}, top={top}, "
            f"right={right}, bottom={bottom}"
        )

    rect = {"left": left, "top": top, "width": width, "height": height}
    t0 = time.perf_counter()
    try:
        with _get_mss() as sct:
            sct_img = sct.grab(rect)
            img = _sct_to_pil(sct_img)
            logger.debug("capture_window_win (mss) en %.1f ms", (time.perf_counter() - t0) * 1000)
            return img
    except Exception as exc:
        logger.warning("mss falló para ventana activa (%s), usando PIL.ImageGrab.", exc)
        from PIL import ImageGrab
        img = ImageGrab.grab(bbox=(left, top, right, bottom))
        return img.convert("RGB")


def _capture_active_window_linux() -> Image.Image:
    """
    Captura la ventana activa en Linux usando xdotool.

    Requiere que xdotool esté instalado en el sistema
    (``sudo apt install xdotool`` en Debian/Ubuntu).

    Returns:
        PIL.Image.Image: Imagen de la ventana activa.

    Raises:
        RuntimeError: Si xdotool no está disponible o la geometría es inválida.
    """
    import subprocess

    try:
        result = subprocess.run(
            ["xdotool", "getactivewindow", "getwindowgeometry", "--shell"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "xdotool no está instalado. Instálalo con: sudo apt install xdotool"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("xdotool tardó demasiado en responder.") from exc

    if result.returncode != 0:
        raise RuntimeError(
            f"xdotool falló con código {result.returncode}: {result.stderr.strip()}"
        )

    geom: dict = {}
    for line in result.stdout.splitlines():
        k, _, v = line.partition("=")
        geom[k.strip()] = v.strip()

    try:
        x = int(geom.get("X", 0))
        y = int(geom.get("Y", 0))
        w = int(geom.get("WIDTH", 800))
        h = int(geom.get("HEIGHT", 600))
    except ValueError as exc:
        raise RuntimeError(f"No se pudo parsear la geometría de la ventana: {geom}") from exc

    if w <= 0 or h <= 0:
        raise RuntimeError(f"Geometría de ventana inválida: width={w}, height={h}")

    rect = {"left": x, "top": y, "width": w, "height": h}
    with mss.mss() as sct:
        sct_img = sct.grab(rect)
        return _sct_to_pil(sct_img)


def capture_region(rect: Tuple[int, int, int, int]) -> Image.Image:
    """
    Captura una región específica de la pantalla.

    Args:
        rect: Tupla con las coordenadas (left, top, width, height) en píxeles.

    Returns:
        PIL.Image.Image: Imagen de la región capturada en modo RGB.

    Raises:
        ValueError: Si las dimensiones de la región son inválidas (≤ 0).
        RuntimeError: Si mss no puede capturar la región.
    """
    _ensure_dpi_awareness()
    left, top, width, height = rect

    if width <= 0 or height <= 0:
        raise ValueError(
            f"Las dimensiones de la región deben ser positivas. "
            f"Recibido: width={width}, height={height}"
        )

    monitor = {"left": left, "top": top, "width": width, "height": height}
    t0 = time.perf_counter()
    try:
        with _get_mss() as sct:
            sct_img = sct.grab(monitor)
            img = _sct_to_pil(sct_img)
            logger.debug("capture_region (mss) en %.1f ms", (time.perf_counter() - t0) * 1000)
            return img
    except Exception as exc:
        logger.warning("mss falló para capture_region (%s), usando PIL.ImageGrab.", exc)
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(bbox=(left, top, left + width, top + height))
            return img.convert("RGB")
        except Exception as exc2:
            logger.error("PIL.ImageGrab también falló: %s", exc2)
            raise RuntimeError(f"No se pudo capturar la región {rect}: {exc2}") from exc2
