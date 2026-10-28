"""
generate_icon.py – Genera el icono assets/icon.ico para Text IMG Extractor.
Ejecutar una sola vez desde la raíz del proyecto:
    python assets/generate_icon.py
"""
import os
import sys

# Asegurar que PyQt6 esté disponible
try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont, QPen
    from PyQt6.QtCore import Qt, QSize
except ImportError:
    print("ERROR: PyQt6 no está instalado. Instálalo con: pip install PyQt6")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow no está instalado. Instálalo con: pip install Pillow")
    sys.exit(1)

import io

def generate_icon():
    app = QApplication.instance() or QApplication(sys.argv)

    sizes = [256, 128, 64, 48, 32, 16]
    pil_images = []

    for SIZE in sizes:
        pixmap = QPixmap(QSize(SIZE, SIZE))
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fondo redondeado oscuro
        radius = SIZE * 0.22
        painter.setBrush(QColor(13, 13, 18))
        painter.setPen(QPen(QColor(99, 102, 241, 150), max(1, SIZE // 32)))
        painter.drawRoundedRect(
            SIZE // 16, SIZE // 16,
            SIZE - SIZE // 8, SIZE - SIZE // 8,
            radius, radius
        )

        # Letra T
        font_size = int(SIZE * 0.48)
        painter.setPen(QColor(129, 140, 248))
        font = QFont("Segoe UI", font_size, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "T")

        # Punto de acento (esquina inferior derecha)
        dot_size = max(4, SIZE // 6)
        dot_x = SIZE - dot_size - SIZE // 8
        dot_y = SIZE - dot_size - SIZE // 8
        painter.setBrush(QColor(99, 102, 241))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(dot_x, dot_y, dot_size, dot_size)

        painter.end()

        # Convertir QPixmap → PIL Image via PNG bytes
        import io as _io
        ba2 = pixmap.toImage()
        buf = _io.BytesIO()
        # Guardar como PNG en buffer
        import ctypes
        # Usar save() de QImage a bytes via buffer trick
        from PyQt6.QtCore import QBuffer, QIODevice
        qbuf = QBuffer()
        qbuf.open(QIODevice.OpenModeFlag.ReadWrite)
        ba2.save(qbuf, "PNG")
        qbuf.seek(0)
        png_bytes = bytes(qbuf.readAll())
        qbuf.close()
        pil_img = Image.open(_io.BytesIO(png_bytes)).convert("RGBA")
        pil_images.append(pil_img)

    # Guardar ICO
    out_path = os.path.join(os.path.dirname(__file__), "icon.ico")
    pil_images[0].save(
        out_path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=pil_images[1:],
    )
    print(f"Icono generado: {out_path}")

if __name__ == "__main__":
    generate_icon()
