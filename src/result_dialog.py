"""
result_dialog.py – Diálogo que muestra el texto extraído por OCR.

Diseño: dark glass / translúcido, minimalista, elegante.
- Ventana frameless con efecto de fondo semitransparente (glassmorphism oscuro)
- Animación fade-in al aparecer
- Texto monoespacio con syntax-highlight de espaciado
- Botón Copiar principal (Ctrl+C) con feedback animado
- Cierre con ESC / clic fuera / botón ✕
- Contador de caracteres discreto
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QFrame, QApplication, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (
    QFont, QIcon, QKeySequence, QShortcut, QColor,
    QPainter, QPainterPath, QBrush, QPen
)


# ── Paleta de colores ──────────────────────────────────────────────────────────
_BG_WINDOW     = "#0d0d0f"       # fondo de ventana (casi negro)
_BG_CARD       = "#111116"       # superficie de la tarjeta
_BG_TEXT_AREA  = "#0a0a0c"       # fondo del área de texto
_BORDER        = "#1e1e28"       # borde sutil
_BORDER_GLOW   = "#2a2a3a"       # borde con un leve brillo
_TEXT_PRIMARY  = "#e2e2e6"       # texto principal
_TEXT_MUTED    = "#5a5a72"       # texto secundario / contador
_TEXT_EMPTY    = "#3a3a50"       # texto de estado vacío
_ACCENT        = "#6366f1"       # índigo vibrante (acento principal)
_ACCENT_HOVER  = "#818cf8"       # hover del acento
_ACCENT_FG     = "#ffffff"       # texto sobre el acento
_BTN_SECONDARY = "#1a1a22"       # botón secundario
_BTN_SEC_HOVER = "#23232e"       # hover secundario
_SEPARATOR     = "#17171f"       # línea separadora
_SCROLLBAR     = "#1e1e28"       # scrollbar track
_SCROLLBAR_TH  = "#2e2e40"       # scrollbar thumb
_SUCCESS       = "#22c55e"       # verde éxito (icono copiado)
_HEADER_ICON   = "#6366f1"       # color del icono del header


_STYLE = f"""
QDialog {{
    background-color: {_BG_WINDOW};
    border: 1px solid {_BORDER_GLOW};
    border-radius: 12px;
}}
QLabel#header_label {{
    color: {_TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.3px;
}}
QLabel#char_label {{
    color: {_TEXT_MUTED};
    font-size: 11px;
}}
QTextEdit {{
    background-color: {_BG_TEXT_AREA};
    color: {_TEXT_PRIMARY};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 12px 14px;
    selection-background-color: #3f3f6a;
    selection-color: {_TEXT_PRIMARY};
    line-height: 1.5;
}}
QTextEdit:focus {{
    border: 1px solid {_BORDER_GLOW};
}}
/* Scrollbar */
QTextEdit QScrollBar:vertical {{
    background: {_SCROLLBAR};
    width: 6px;
    border-radius: 3px;
    margin: 0;
}}
QTextEdit QScrollBar::handle:vertical {{
    background: {_SCROLLBAR_TH};
    border-radius: 3px;
    min-height: 20px;
}}
QTextEdit QScrollBar::handle:vertical:hover {{
    background: #3e3e56;
}}
QTextEdit QScrollBar::add-line:vertical,
QTextEdit QScrollBar::sub-line:vertical {{
    height: 0;
}}
/* Botón primario */
QPushButton#copy_btn {{
    background-color: {_ACCENT};
    color: {_ACCENT_FG};
    border: none;
    border-radius: 8px;
    padding: 8px 22px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.2px;
}}
QPushButton#copy_btn:hover {{
    background-color: {_ACCENT_HOVER};
}}
QPushButton#copy_btn:pressed {{
    background-color: #4f52d4;
}}
QPushButton#copy_btn:disabled {{
    background-color: #1e2040;
    color: #4a4a7a;
}}
/* Botón cerrar */
QPushButton#close_btn {{
    background-color: {_BTN_SECONDARY};
    color: {_TEXT_MUTED};
    border: 1px solid {_BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
}}
QPushButton#close_btn:hover {{
    background-color: {_BTN_SEC_HOVER};
    color: {_TEXT_PRIMARY};
    border-color: {_BORDER_GLOW};
}}
QPushButton#close_btn:pressed {{
    background-color: #111118;
}}
/* Separador */
QFrame#separator {{
    color: {_SEPARATOR};
    background-color: {_SEPARATOR};
    border: none;
    max-height: 1px;
}}
"""


class ResultDialog(QDialog):
    """
    Diálogo oscuro minimalista para mostrar texto extraído por OCR.

    Características visuales:
    - Ventana frameless con fondo oscuro casi opaco
    - Drop-shadow externa para profundidad
    - Fade-in animado al aparecer
    - Texto en fuente monoespaciada ligera
    - Botón 'Copiar' con feedback animado (✓ Copiado)
    - Atajos: Ctrl+C → copiar, ESC → cerrar
    """

    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = text
        self._setup_window()
        self._setup_ui()
        self._setup_animations()

    # ── Configuración de ventana ──────────────────────────────────────────────

    def _setup_window(self):
        self.setWindowTitle("Text IMG Extractor")
        self.setMinimumSize(540, 380)
        self.resize(580, 420)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Sombra externa
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.setGraphicsEffect(shadow)

    # ── Construcción de UI ────────────────────────────────────────────────────

    def _setup_ui(self):
        # Contenedor raíz (para el fondo redondeado)
        self._card = QFrame(self)
        self._card.setObjectName("card")
        self._card.setStyleSheet(f"""
            QFrame#card {{
                background-color: {_BG_WINDOW};
                border: 1px solid {_BORDER_GLOW};
                border-radius: 12px;
            }}
        """)

        # Layout raíz del diálogo (solo posiciona la tarjeta)
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.addWidget(self._card)

        # Layout interno de la tarjeta
        layout = QVBoxLayout(self._card)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_separator())
        layout.addLayout(self._build_body())
        layout.addWidget(self._build_separator())
        layout.addLayout(self._build_footer())

        # Atajos
        QShortcut(QKeySequence("Ctrl+C"), self, self._copy_text)
        QShortcut(QKeySequence("Escape"), self, self.close)

        self.setStyleSheet(_STYLE)

    def _build_header(self) -> QHBoxLayout:
        """Barra de título compacta con icono y título."""
        layout = QHBoxLayout()
        layout.setContentsMargins(20, 16, 16, 14)
        layout.setSpacing(10)

        # Icono decorativo (punto de color)
        dot = QLabel("◈")
        dot.setStyleSheet(f"color: {_ACCENT}; font-size: 16px;")
        dot.setFixedWidth(18)

        title = QLabel("Texto extraído")
        title.setObjectName("header_label")

        layout.addWidget(dot)
        layout.addWidget(title)
        layout.addStretch()

        # Botón X discreto
        x_btn = QPushButton("✕")
        x_btn.setFixedSize(24, 24)
        x_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        x_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {_TEXT_MUTED};
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                padding: 0;
            }}
            QPushButton:hover {{
                background: #1e1e2a;
                color: {_TEXT_PRIMARY};
            }}
        """)
        x_btn.clicked.connect(self.close)
        layout.addWidget(x_btn)

        return layout

    def _build_separator(self) -> QFrame:
        sep = QFrame()
        sep.setObjectName("separator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        return sep

    def _build_body(self) -> QVBoxLayout:
        """Área de texto principal."""
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 10)
        layout.setSpacing(8)

        self._text_edit = QTextEdit()
        self._text_edit.setReadOnly(True)

        # Contenido
        if self._text:
            self._text_edit.setPlainText(self._text)
        else:
            self._text_edit.setPlaceholderText("No se detectó texto en la captura.")

        # Fuente monoespaciada ligera
        font = QFont("Cascadia Code", 10)
        font.setStyleHint(QFont.StyleHint.Monospace)
        if not font.exactMatch():
            font = QFont("Consolas", 10)
        self._text_edit.setFont(font)
        self._text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

        layout.addWidget(self._text_edit)
        return layout

    def _build_footer(self) -> QVBoxLayout:
        """Footer con contador + botones."""
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 10, 16, 16)
        layout.setSpacing(10)

        # Contador de caracteres
        char_count = len(self._text)
        plural = "es" if char_count != 1 else ""
        self._count_label = QLabel(f"{char_count} carácter{plural}")
        self._count_label.setObjectName("char_label")

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self._copy_btn = QPushButton("Copiar texto")
        self._copy_btn.setObjectName("copy_btn")
        self._copy_btn.setMinimumHeight(38)
        self._copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._copy_btn.clicked.connect(self._copy_text)

        self._close_btn = QPushButton("Cerrar")
        self._close_btn.setObjectName("close_btn")
        self._close_btn.setMinimumHeight(38)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self.close)

        btn_layout.addWidget(self._count_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        btn_layout.addStretch()
        btn_layout.addWidget(self._close_btn)
        btn_layout.addWidget(self._copy_btn)

        layout.addLayout(btn_layout)
        return layout

    # ── Animaciones ───────────────────────────────────────────────────────────

    def _setup_animations(self):
        """Configura la animación fade-in al mostrar la ventana."""
        self.setWindowOpacity(0.0)
        self._fade_in = QPropertyAnimation(self, b"windowOpacity")
        self._fade_in.setDuration(180)
        self._fade_in.setStartValue(0.0)
        self._fade_in.setEndValue(0.97)
        self._fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)

    def showEvent(self, event):
        super().showEvent(event)
        # Centrar en pantalla al mostrar
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.center().x() - self.width() // 2,
                geo.center().y() - self.height() // 2,
            )
        self._fade_in.start()

    # ── Arrastrar ventana frameless ───────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag_pos"):
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    # ── Lógica ────────────────────────────────────────────────────────────────

    def _copy_text(self):
        """Copia el texto al portapapeles y muestra feedback visual."""
        if not self._text:
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(self._text)

        # Feedback animado en el botón
        self._copy_btn.setText("✓  Copiado")
        self._copy_btn.setEnabled(False)
        self._copy_btn.setStyleSheet(f"""
            QPushButton#copy_btn {{
                background-color: {_SUCCESS};
                color: #fff;
                border: none;
                border-radius: 8px;
                padding: 8px 22px;
                font-size: 13px;
                font-weight: 600;
            }}
        """)
        QTimer.singleShot(1600, self._reset_copy_btn)

    def _reset_copy_btn(self):
        self._copy_btn.setText("Copiar texto")
        self._copy_btn.setEnabled(True)
        self._copy_btn.setStyleSheet("")  # restaura desde _STYLE global


# ── API pública ───────────────────────────────────────────────────────────────

def show_result(text: str) -> None:
    """
    Muestra el diálogo de resultado con el texto extraído.
    Crea QApplication si no existe.
    """
    app = QApplication.instance()
    if app is None:
        import sys
        app = QApplication(sys.argv)

    dialog = ResultDialog(text)
    dialog.exec()
