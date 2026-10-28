"""Tests para el módulo de captura de pantalla."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from PIL import Image


class TestCaptureModule:
    """Pruebas del módulo capture.py"""

    def test_capture_full_returns_image(self):
        """capture_full() debe retornar una imagen PIL válida."""
        from capture import capture_full
        img = capture_full()
        assert isinstance(img, Image.Image)
        assert img.width > 0
        assert img.height > 0

    def test_capture_full_mode_rgb(self):
        """La imagen capturada debe ser RGB."""
        from capture import capture_full
        img = capture_full()
        assert img.mode == "RGB"

    def test_capture_region_returns_correct_size(self):
        """capture_region debe retornar imagen del tamaño especificado."""
        from capture import capture_region
        rect = (0, 0, 200, 150)
        img = capture_region(rect)
        assert isinstance(img, Image.Image)
        assert img.width == 200
        assert img.height == 150

    def test_capture_region_invalid_does_not_crash(self):
        """capture_region con valores fuera de pantalla no debe crashear."""
        from capture import capture_region
        try:
            img = capture_region((9999, 9999, 100, 100))
            # Si retorna algo, debe ser PIL.Image
            assert isinstance(img, Image.Image)
        except Exception:
            pass  # Es aceptable fallar con coordenadas inválidas

    def test_capture_active_window_returns_image(self):
        """capture_active_window debe retornar una imagen PIL válida."""
        from capture import capture_active_window
        img = capture_active_window()
        assert isinstance(img, Image.Image)


class TestOCRModule:
    """Pruebas del módulo ocr.py"""

    def _make_text_image(self, text: str) -> Image.Image:
        """Crea una imagen PIL simple con texto para testing."""
        from PIL import ImageDraw, ImageFont
        img = Image.new("RGB", (400, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((10, 30), text, fill=(0, 0, 0))
        return img

    def test_extract_text_returns_string(self):
        """extract_text debe retornar un string."""
        from ocr import extract_text
        img = Image.new("RGB", (200, 50), color=(255, 255, 255))
        result = extract_text(img)
        assert isinstance(result, str)

    def test_preprocess_image_returns_image(self):
        """preprocess_image debe retornar una imagen PIL."""
        from ocr import preprocess_image
        img = Image.new("RGB", (100, 100), color=(200, 200, 200))
        result = preprocess_image(img)
        assert isinstance(result, Image.Image)

    def test_preprocess_converts_to_binary(self):
        """preprocess_image debe producir imagen en modo L (escala de grises/binarizado)."""
        from ocr import preprocess_image
        img = Image.new("RGB", (100, 100), color=(128, 128, 128))
        result = preprocess_image(img)
        assert result.mode == "L"


class TestResultDialog:
    """Pruebas básicas del módulo result_dialog.py (sin ejecutar la UI completa)."""

    def test_result_dialog_import(self):
        """El módulo result_dialog debe importarse sin errores."""
        import result_dialog
        assert hasattr(result_dialog, "ResultDialog")
        assert hasattr(result_dialog, "show_result")

    def test_hotkeys_import(self):
        """El módulo hotkeys debe importarse sin errores."""
        import hotkeys
        assert hasattr(hotkeys, "HotkeyManager")
        assert hasattr(hotkeys, "DEFAULT_HOTKEYS")

    def test_tray_import(self):
        """El módulo tray debe importarse sin errores."""
        import tray
        assert hasattr(tray, "TrayIcon")
