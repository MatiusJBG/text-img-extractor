"""
main.py – Punto de entrada principal de Text IMG Extractor.

Lanza el servicio en segundo plano con:
- Icono de bandeja del sistema (tray)
- Atajos de teclado globales
- Coordina captura, OCR y diálogo de resultados
"""
import sys
import os
import platform
import logging
import threading
from typing import Optional

# ── Configuración de logging ──────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("text_img_extractor")

# ── Qt: debe crearse antes de importar módulos que usan Qt ───────────────────
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt

# ── Módulos internos ──────────────────────────────────────────────────────────
# Ajustar path si se ejecuta como módulo o desde el directorio raíz
if getattr(sys, "frozen", False):
    # Modo PyInstaller: los módulos están en sys._MEIPASS/src
    sys.path.insert(0, os.path.join(sys._MEIPASS, "src"))
else:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from capture import capture_full, capture_active_window, capture_region
from region_selector import RegionSelector
from ocr import extract_text
from result_dialog import ResultDialog
from hotkeys import HotkeyManager
from tray import TrayIcon


# ─────────────────────────────────────────────────────────────────────────────
class CaptureWorker(QObject):
    """
    Worker que ejecuta captura + OCR en un hilo separado para no bloquear la UI.
    Emite la señal `finished` con el texto extraído cuando termina.
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, mode: str, region=None, preloaded_image=None):
        super().__init__()
        self._mode = mode
        self._region = region
        self._preloaded_image = preloaded_image

    def run(self):
        try:
            logger.info(f"Iniciando procesamiento de imagen: modo={self._mode}")
            if self._preloaded_image is not None:
                image = self._preloaded_image
            elif self._mode == "full":
                image = capture_full()
            elif self._mode == "window":
                image = capture_active_window()
            elif self._mode == "region" and self._region:
                image = capture_region(self._region)
            else:
                self.error.emit("Modo de captura inválido o región no especificada.")
                return

            logger.info("Imagen lista, iniciando OCR de alta precisión...")
            text = extract_text(image)
            logger.info(f"OCR completado: {len(text)} caracteres extraídos.")
            self.finished.emit(text)
        except Exception as e:
            logger.error(f"Error en CaptureWorker: {e}")
            self.error.emit(str(e))


# ─────────────────────────────────────────────────────────────────────────────
class App(QObject):
    """
    Aplicación principal. Orquesta tray, hotkeys y flujo de captura.
    """
    # Señales para despachar trabajo al hilo principal de Qt
    _trigger_full = pyqtSignal()
    _trigger_window = pyqtSignal()
    _trigger_region = pyqtSignal()

    def __init__(self, qapp: QApplication):
        super().__init__()
        self._qapp = qapp
        self._worker_thread: Optional[QThread] = None
        self._is_capturing = False  # Evita capturas simultáneas

        # ── Conectar señales al hilo principal ──
        self._trigger_full.connect(self._do_capture_full)
        self._trigger_window.connect(self._do_capture_window)
        self._trigger_region.connect(self._do_capture_region)

        # ── Tray ──
        callbacks = {
            "capture_full":   lambda: self._trigger_full.emit(),
            "capture_window": lambda: self._trigger_window.emit(),
            "capture_region": lambda: self._trigger_region.emit(),
            "quit":           self._quit,
        }
        self._tray = TrayIcon(callbacks)
        self._tray.show()

        # ── Hotkeys (en hilo daemon) ──
        self._hotkeys = HotkeyManager({
            "capture_full":   lambda: self._trigger_full.emit(),
            "capture_window": lambda: self._trigger_window.emit(),
            "capture_region": lambda: self._trigger_region.emit(),
        })
        self._hotkeys.start()

        logger.info("Text IMG Extractor iniciado en segundo plano.")
        self._tray.show_notification(
            "Text IMG Extractor",
            "Activo en segundo plano.\n"
            "Ctrl+Shift+S → seleccionar región\n"
            "Ctrl+Shift+F → pantalla completa\n"
            "Ctrl+Shift+W → ventana activa"
        )

    # ── Métodos de captura (ejecutan en el hilo principal Qt) ─────────────────

    def _do_capture_full(self):
        self._start_capture("full")

    def _do_capture_window(self):
        self._start_capture("window")

    def _do_capture_region(self):
        if self._is_capturing:
            return

        # 1. Congelar la pantalla previa (evita capturar el propio overlay y desfases de DPI)
        try:
            frozen_screen = capture_full()
        except Exception as exc:
            logger.warning("No se pudo capturar pantalla congelada previa: %s", exc)
            frozen_screen = None

        # 2. Mostrar overlay interactivo con la pantalla congelada
        selector = RegionSelector(background_image=frozen_screen)
        selector.show()

        # Procesar eventos hasta que el usuario termine la selección
        while selector.isVisible():
            self._qapp.processEvents()

        # 3. Obtener el recorte a resolución nativa
        cropped = selector.get_cropped_image()
        if cropped is not None:
            self._start_capture("region", preloaded_image=cropped)
        else:
            region = selector.get_result()
            if region:
                self._start_capture("region", region=region)

    def _start_capture(self, mode: str, region=None, preloaded_image=None):
        if self._is_capturing:
            logger.warning("Captura en progreso, ignorando solicitud.")
            return
        self._is_capturing = True

        # Crear worker + hilo
        self._worker_thread = QThread()
        self._worker = CaptureWorker(mode, region=region, preloaded_image=preloaded_image)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_capture_done)
        self._worker.error.connect(self._on_capture_error)
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.error.connect(self._worker_thread.quit)
        self._worker_thread.finished.connect(self._reset_capturing)

        self._worker_thread.start()

    def _on_capture_done(self, text: str):
        logger.info("Mostrando diálogo de resultado.")
        dialog = ResultDialog(text)
        dialog.exec()

    def _on_capture_error(self, error: str):
        logger.error(f"Error de captura: {error}")
        self._tray.show_notification("Error", f"Error en la captura: {error}")

    def _reset_capturing(self):
        self._is_capturing = False

    def _quit(self):
        logger.info("Cerrando Text IMG Extractor.")
        self._hotkeys.stop()
        self._tray.hide()
        self._qapp.quit()


# ─────────────────────────────────────────────────────────────────────────────
def main():
    # Necesario para el tray en Linux con algunos gestores de ventanas
    if platform.system() != "Windows":
        os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)  # No cerrar al cerrar diálogos
    qapp.setApplicationName("Text IMG Extractor")
    qapp.setApplicationVersion("1.0.0")

    if not QApplication.primaryScreen():
        logger.error("No se encontró pantalla. Abortando.")
        sys.exit(1)

    app = App(qapp)
    sys.exit(qapp.exec())


if __name__ == "__main__":
    main()
