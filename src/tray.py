"""
tray.py – Icono de la bandeja del sistema (System Tray).
Permite acceder a las capturas y salir de la aplicación desde el tray.
"""
import sys
from typing import Callable, Dict
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QPen
from PyQt6.QtCore import Qt, QSize


def _create_default_icon() -> QIcon:
    """
    Crea un ícono de bandeja minimalista: fondo oscuro + acento índigo + letra T.
    Diseño plano, nítido a 16×16 (escala del tray).
    """
    SIZE = 64
    pixmap = QPixmap(QSize(SIZE, SIZE))
    pixmap.fill(QColor(0, 0, 0, 0))  # fondo completamente transparente

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Fondo cuadrado redondeado (estilo macOS/Win11 icon)
    painter.setBrush(QColor(13, 13, 18))       # casi negro
    painter.setPen(QPen(QColor(99, 102, 241, 120), 2))  # borde índigo sutil
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)

    # Letra T con degradado índigo
    painter.setPen(QColor(129, 140, 248))      # índigo claro
    font = QFont("Segoe UI", 30, QFont.Weight.Bold)
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, -1)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "T")

    # Punto de acento (indicador activo) – esquina inferior derecha
    painter.setBrush(QColor(99, 102, 241))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(44, 44, 12, 12)

    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    """
    Icono de bandeja con menú contextual para las opciones de captura.
    """

    def __init__(self, callbacks: Dict[str, Callable], parent=None):
        """
        Args:
            callbacks: Dict con claves:
                - 'capture_full'
                - 'capture_window'
                - 'capture_region'
                - 'quit'
        """
        icon = _create_default_icon()
        super().__init__(icon, parent)
        self._callbacks = callbacks
        self._setup_menu()
        self.setToolTip("Text IMG Extractor\nCapturador de pantalla + OCR")

    def _setup_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #0d0d0f;
                color: #d4d4e0;
                border: 1px solid #1e1e2a;
                border-radius: 10px;
                padding: 6px 4px;
                font-size: 13px;
            }
            QMenu::item {
                padding: 7px 22px 7px 14px;
                border-radius: 6px;
                margin: 1px 4px;
            }
            QMenu::item:selected {
                background-color: #18181f;
                color: #e2e2f0;
            }
            QMenu::item:disabled {
                color: #3a3a52;
                background: transparent;
            }
            QMenu::separator {
                height: 1px;
                background-color: #16161e;
                margin: 4px 10px;
            }
        """)

        # ── Título (no clickeable) ──
        title_action = menu.addAction("  Text IMG Extractor")
        title_action.setEnabled(False)
        menu.addSeparator()

        # ── Opciones de captura ──
        full_action = menu.addAction("  Capturar pantalla completa   Ctrl+Shift+F")
        full_action.triggered.connect(lambda: self._safe_call("capture_full"))

        window_action = menu.addAction("  Ventana activa   Ctrl+Shift+W")
        window_action.triggered.connect(lambda: self._safe_call("capture_window"))

        region_action = menu.addAction("  Seleccionar región   Ctrl+Shift+S")
        region_action.triggered.connect(lambda: self._safe_call("capture_region"))

        menu.addSeparator()

        # ── Salir ──
        quit_action = menu.addAction("  Salir")
        quit_action.triggered.connect(lambda: self._safe_call("quit"))

        self.setContextMenu(menu)
        # Doble clic -> captura de región
        self.activated.connect(self._on_activated)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._safe_call("capture_region")

    def _safe_call(self, action: str):
        cb = self._callbacks.get(action)
        if cb:
            try:
                cb()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error en tray callback {action}: {e}")

    def show_notification(self, title: str, message: str):
        """Muestra una notificación emergente del sistema."""
        self.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 2000)
