"""
region_selector.py – Overlay interactivo de selección de región ("Screen Freeze").

Captura y congela la pantalla en el momento de activación para que el usuario
pueda dibujar un rectángulo de selección sin parpadeos, sin problemas de
escalado DPI y sin capturar elementos del propio overlay.

Características:
- Soporte completo para pantallas High DPI (escalado 125%, 150%, 200%).
- Pantalla congelada (Freeze Screen) estilo herramienta Recortes de Windows / Lightshot.
- Oscurecimiento elegante del fondo con área de selección iluminada y nítida.
- Etiqueta flotante con dimensiones del recorte (Ancho × Alto).
- Cancelación con tecla ESC.
- Retorno directo de la imagen recortada (PIL.Image) a resolución nativa.
"""

import sys
import logging
from typing import Optional, Tuple

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QRect, QPoint, QSize
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QPen,
    QBrush,
    QCursor,
    QPixmap,
    QImage,
    QFont,
)
from PIL import Image

logger = logging.getLogger(__name__)


def pil_to_qpixmap(pil_img: Image.Image) -> QPixmap:
    """Convierte una imagen de PIL en formato RGB/RGBA a un QPixmap de Qt."""
    img_rgb = pil_img.convert("RGBA")
    data = img_rgb.tobytes("raw", "RGBA")
    qimg = QImage(
        data,
        img_rgb.width,
        img_rgb.height,
        QImage.Format.Format_RGBA8888,
    )
    return QPixmap.fromImage(qimg)


class RegionSelector(QWidget):
    """
    Overlay a pantalla completa para selección de área con técnica Screen Freeze.
    """

    MIN_SELECTION_PX: int = 8

    def __init__(self, background_image: Optional[Image.Image] = None) -> None:
        super().__init__()
        self._bg_pil: Optional[Image.Image] = background_image
        self._bg_pixmap: Optional[QPixmap] = (
            pil_to_qpixmap(background_image) if background_image is not None else None
        )
        self._start: Optional[QPoint] = None
        self._end: Optional[QPoint] = None
        self._cropped_image: Optional[Image.Image] = None
        self._result: Optional[Tuple[int, int, int, int]] = None

        self._setup_window()

    def _setup_window(self) -> None:
        """Configura la ventana overlay en modo pantalla completa sin bordes."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        # Cubrir la geometría virtual de todas las pantallas
        screen = QApplication.primaryScreen()
        if screen is not None:
            self.setGeometry(screen.virtualGeometry())
        else:
            self.setGeometry(0, 0, 1920, 1080)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """Dibuja el fondo congelado, la máscara oscura y el marco de selección."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        widget_rect = self.rect()

        # 1. Si tenemos imagen de fondo congelada, la dibujamos escalada al widget
        if self._bg_pixmap is not None and not self._bg_pixmap.isNull():
            painter.drawPixmap(widget_rect, self._bg_pixmap)

        # 2. Dibujar capa oscura sobre toda la pantalla
        # Si no hay selección, pantalla oscurecida al 40%
        if self._start is None or self._end is None:
            painter.fillRect(widget_rect, QColor(0, 0, 0, 110))
            # Mensaje de ayuda en el centro
            self._draw_hint(painter, widget_rect)
            return

        sel_rect = QRect(self._start, self._end).normalized()

        # 3. Dibujar 4 rectángulos oscuros alrededor del área seleccionada
        # (Top, Bottom, Left, Right) para dejar la selección 100% nítida y brillante
        dark_color = QColor(0, 0, 0, 130)

        # Arriba de la selección
        painter.fillRect(0, 0, widget_rect.width(), sel_rect.top(), dark_color)
        # Abajo de la selección
        painter.fillRect(
            0,
            sel_rect.bottom() + 1,
            widget_rect.width(),
            widget_rect.height() - sel_rect.bottom(),
            dark_color,
        )
        # Izquierda
        painter.fillRect(
            0,
            sel_rect.top(),
            sel_rect.left(),
            sel_rect.height(),
            dark_color,
        )
        # Derecha
        painter.fillRect(
            sel_rect.right() + 1,
            sel_rect.top(),
            widget_rect.width() - sel_rect.right(),
            sel_rect.height(),
            dark_color,
        )

        # 4. Borde punteado fino del área de selección
        border_pen = QPen(QColor(99, 102, 241, 180), 1, Qt.PenStyle.DotLine)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(sel_rect)

        # 4b. Esquinas angulares del marco (acento índigo brillante)
        self._draw_corner_handles(painter, sel_rect)

        # 5. Etiqueta flotante con el tamaño (Ancho × Alto px)
        self._draw_dimension_tag(painter, sel_rect)

    def _draw_hint(self, painter: QPainter, rect: QRect) -> None:
        """Muestra una pequeña guía visual al abrir el selector."""
        hint_text = "Arrastra para seleccionar el texto a extraer  ·  ESC para cancelar"
        painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        text_rect = painter.fontMetrics().boundingRect(hint_text)

        padding_x, padding_y = 18, 9
        badge_w = text_rect.width() + padding_x * 2
        badge_h = text_rect.height() + padding_y * 2
        badge_x = (rect.width() - badge_w) // 2
        badge_y = 36  # Cerca de la parte superior

        badge_rect = QRect(badge_x, badge_y, badge_w, badge_h)
        # Fondo semitransparente oscuro
        painter.setBrush(QBrush(QColor(10, 10, 15, 210)))
        painter.setPen(QPen(QColor(99, 102, 241, 140), 1))
        painter.drawRoundedRect(badge_rect, 8, 8)

        painter.setPen(QColor(200, 200, 215))
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, hint_text)

    def _draw_corner_handles(self, painter: QPainter, sel_rect: QRect) -> None:
        """Dibuja esquinas angulares en los 4 vértices del área de selección."""
        corner_len = 12
        corner_color = QColor(99, 102, 241)   # índigo acento
        pen = QPen(corner_color, 2, Qt.PenStyle.SolidLine)
        pen.setCapStyle(Qt.PenCapStyle.SquareCap)
        painter.setPen(pen)

        x1, y1 = sel_rect.left(), sel_rect.top()
        x2, y2 = sel_rect.right(), sel_rect.bottom()

        # Esquina superior-izquierda
        painter.drawLine(x1, y1, x1 + corner_len, y1)
        painter.drawLine(x1, y1, x1, y1 + corner_len)
        # Esquina superior-derecha
        painter.drawLine(x2, y1, x2 - corner_len, y1)
        painter.drawLine(x2, y1, x2, y1 + corner_len)
        # Esquina inferior-izquierda
        painter.drawLine(x1, y2, x1 + corner_len, y2)
        painter.drawLine(x1, y2, x1, y2 - corner_len)
        # Esquina inferior-derecha
        painter.drawLine(x2, y2, x2 - corner_len, y2)
        painter.drawLine(x2, y2, x2, y2 - corner_len)

    def _draw_dimension_tag(self, painter: QPainter, sel_rect: QRect) -> None:
        """Dibuja una pequeña etiqueta con las dimensiones en píxeles reales."""
        scale_x = (
            self._bg_pil.width / self.width() if self._bg_pil is not None else 1.0
        )
        scale_y = (
            self._bg_pil.height / self.height() if self._bg_pil is not None else 1.0
        )
        real_w = int(sel_rect.width() * scale_x)
        real_h = int(sel_rect.height() * scale_y)

        tag_text = f"{real_w} × {real_h} px"
        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
        metrics = painter.fontMetrics()
        tag_w = metrics.horizontalAdvance(tag_text) + 12
        tag_h = metrics.height() + 6

        # Posicionar la etiqueta abajo a la derecha de la selección
        tag_x = sel_rect.right() - tag_w
        tag_y = sel_rect.bottom() + 6

        # Si se sale de la pantalla por abajo, ponerla arriba del rectángulo
        if tag_y + tag_h > self.height():
            tag_y = sel_rect.top() - tag_h - 6

        tag_rect = QRect(max(0, tag_x), max(0, tag_y), tag_w, tag_h)
        painter.setBrush(QBrush(QColor(15, 23, 42, 210)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(tag_rect, 4, 4)

        painter.setPen(QColor(226, 232, 240))
        painter.drawText(tag_rect, Qt.AlignmentFlag.AlignCenter, tag_text)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self._start = event.position().toPoint()
            self._end = self._start
            self.update()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._start is not None:
            self._end = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and self._start is not None:
            self._end = event.position().toPoint()
            sel_rect = QRect(self._start, self._end).normalized()

            if (
                sel_rect.width() >= self.MIN_SELECTION_PX
                and sel_rect.height() >= self.MIN_SELECTION_PX
            ):
                self._compute_results(sel_rect)
            else:
                logger.debug(
                    "Selección demasiado pequeña (%dx%d), cancelando.",
                    sel_rect.width(),
                    sel_rect.height(),
                )
                self._cropped_image = None
                self._result = None

            self.close()

    def _compute_results(self, sel_rect: QRect) -> None:
        """Calcula el recorte exacto en píxeles reales sobre la imagen congelada."""
        if self._bg_pil is not None:
            # Factores de escala para compensar High-DPI
            scale_x = self._bg_pil.width / self.width()
            scale_y = self._bg_pil.height / self.height()

            real_x1 = max(0, int(sel_rect.left() * scale_x))
            real_y1 = max(0, int(sel_rect.top() * scale_y))
            real_x2 = min(self._bg_pil.width, int(sel_rect.right() * scale_x))
            real_y2 = min(self._bg_pil.height, int(sel_rect.bottom() * scale_y))

            if real_x2 > real_x1 and real_y2 > real_y1:
                self._cropped_image = self._bg_pil.crop(
                    (real_x1, real_y1, real_x2, real_y2)
                )
                self._result = (
                    real_x1,
                    real_y1,
                    real_x2 - real_x1,
                    real_y2 - real_y1,
                )
                logger.info(
                    "Región recortada con éxito: %dx%d (escala X: %.2f, Y: %.2f)",
                    real_x2 - real_x1,
                    real_y2 - real_y1,
                    scale_x,
                    scale_y,
                )
        else:
            # Fallback si no había imagen congelada previa
            global_pos = self.mapToGlobal(sel_rect.topLeft())
            self._result = (
                global_pos.x(),
                global_pos.y(),
                sel_rect.width(),
                sel_rect.height(),
            )

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        if event.key() == Qt.Key.Key_Escape:
            logger.debug("Selección cancelada con ESC.")
            self._cropped_image = None
            self._result = None
            self.close()

    def get_cropped_image(self) -> Optional[Image.Image]:
        """Retorna directamente la imagen PIL recortada a resolución real nativa."""
        return self._cropped_image

    def get_result(self) -> Optional[Tuple[int, int, int, int]]:
        """Retorna las coordenadas de la región (left, top, width, height)."""
        return self._result
