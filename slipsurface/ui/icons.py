"""Toolbar icons for SlipSurfaceIQ Pile.

Prefers SVG files in the icons/ folder when available;
falls back to vector-drawn QIcons.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

_ICONS_DIR = Path(__file__).parent / "icons"

INK = QColor("#2d3a4a")
BLUE = QColor("#2f6fd6")
GREEN = QColor("#2e9d4f")
ORANGE = QColor("#f08a24")


def _pen(c=INK, w=4.0):
    p = QPen(c, w)
    p.setCapStyle(Qt.RoundCap)
    p.setJoinStyle(Qt.RoundJoin)
    return p


def _pixmap(name: str, size: int = 32) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    scale = size / 64.0
    p.scale(scale, scale)

    if name == "open":
        p.setPen(_pen(INK, 4))
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawRoundedRect(QRectF(12, 18, 40, 28), 4, 4)
        p.drawLine(QPointF(12, 26), QPointF(28, 26))
        p.drawLine(QPointF(28, 18), QPointF(28, 26))
    elif name == "save":
        p.setPen(_pen(INK, 4))
        p.setBrush(BLUE)
        p.drawRoundedRect(QRectF(16, 12, 32, 40), 3, 3)
        p.setBrush(QColor("white"))
        p.drawRect(QRectF(22, 12, 16, 12))
        p.drawRect(QRectF(20, 32, 24, 14))
    elif name == "analyse":
        p.setPen(_pen(GREEN, 5))
        p.drawLine(QPointF(16, 40), QPointF(28, 28))
        p.drawLine(QPointF(28, 28), QPointF(40, 36))
        p.drawLine(QPointF(40, 36), QPointF(52, 16))
        p.setBrush(GREEN)
        p.drawEllipse(QPointF(52, 16), 5, 5)
    elif name == "optimize":
        p.setPen(_pen(ORANGE, 4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(32, 32), 16, 16)
        p.drawLine(QPointF(32, 16), QPointF(32, 24))
        p.drawLine(QPointF(32, 40), QPointF(32, 48))
        p.drawLine(QPointF(16, 32), QPointF(24, 32))
        p.drawLine(QPointF(40, 32), QPointF(48, 32))
    elif name == "interpret":
        p.setPen(_pen(BLUE, 4))
        p.setBrush(QColor(255, 255, 255, 180))
        p.drawRoundedRect(QRectF(14, 14, 36, 28), 4, 4)
        p.drawLine(QPointF(20, 24), QPointF(40, 24))
        p.drawLine(QPointF(20, 32), QPointF(34, 32))
        p.setBrush(BLUE)
        p.drawEllipse(QPointF(44, 44), 6, 6)
    elif name == "new":
        p.setPen(_pen(INK, 4))
        p.setBrush(QColor(255, 255, 255, 220))
        p.drawRoundedRect(QRectF(16, 14, 32, 36), 3, 3)
        p.setPen(_pen(BLUE, 3))
        p.drawLine(QPointF(22, 24), QPointF(42, 24))
        p.drawLine(QPointF(22, 32), QPointF(38, 32))
        p.drawLine(QPointF(22, 40), QPointF(34, 40))
    elif name == "report":
        p.setPen(_pen(INK, 4))
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawRoundedRect(QRectF(18, 10, 28, 40), 3, 3)
        p.setPen(_pen(BLUE, 3))
        p.drawLine(QPointF(24, 20), QPointF(40, 20))
        p.drawLine(QPointF(24, 28), QPointF(40, 28))
        p.drawLine(QPointF(24, 36), QPointF(36, 36))
        p.setBrush(GREEN)
        p.drawEllipse(QPointF(42, 42), 7, 7)
        p.setPen(_pen(QColor("white"), 2))
        p.drawLine(QPointF(39, 42), QPointF(42, 45))
        p.drawLine(QPointF(42, 45), QPointF(46, 39))
    elif name == "settings":
        p.setPen(_pen(INK, 4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(32, 32), 10, 10)
        for ang in range(0, 360, 45):
            import math
            rad = math.radians(ang)
            x1 = 32 + 14 * math.cos(rad)
            y1 = 32 + 14 * math.sin(rad)
            x2 = 32 + 20 * math.cos(rad)
            y2 = 32 + 20 * math.sin(rad)
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    elif name == "help":
        p.setPen(_pen(BLUE, 5))
        p.setBrush(BLUE)
        p.drawEllipse(QPointF(32, 32), 18, 18)
        p.setPen(_pen(QColor("white"), 4))
        p.drawLine(QPointF(32, 22), QPointF(32, 28))
        p.drawEllipse(QPointF(32, 40), 2.5, 2.5)
    elif name == "quit":
        p.setPen(_pen(QColor("#d23b2f"), 5))
        p.drawLine(QPointF(18, 18), QPointF(46, 46))
        p.drawLine(QPointF(46, 18), QPointF(18, 46))
    elif name == "language":
        p.setPen(_pen(BLUE, 4))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(32, 32), 16, 16)
        p.drawLine(QPointF(16, 32), QPointF(48, 32))
        p.drawArc(QRectF(20, 16, 24, 32), 0, 180 * 16)
        p.drawArc(QRectF(20, 16, 24, 32), 180 * 16, 180 * 16)
    elif name == "refresh":
        p.setPen(_pen(GREEN, 4))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(16, 16, 32, 32), 45 * 16, 270 * 16)
        p.setBrush(GREEN)
        path = QPainterPath()
        path.moveTo(44, 20)
        path.lineTo(52, 28)
        path.lineTo(36, 28)
        path.closeSubpath()
        p.drawPath(path)
    elif name == "export":
        p.setPen(_pen(INK, 4))
        p.setBrush(QColor(255, 255, 255, 200))
        p.drawRoundedRect(QRectF(14, 18, 28, 28), 3, 3)
        p.setPen(_pen(BLUE, 4))
        p.drawLine(QPointF(32, 14), QPointF(32, 36))
        p.drawLine(QPointF(24, 28), QPointF(32, 36))
        p.drawLine(QPointF(40, 28), QPointF(32, 36))
    else:
        p.setPen(_pen(INK, 4))
        p.drawRect(QRectF(16, 16, 32, 32))

    p.end()
    return pm


def icon(name: str) -> QIcon:
    """Return a QIcon, preferring an SVG file if present."""
    svg = _ICONS_DIR / f"{name}.svg"
    if svg.is_file():
        return QIcon(str(svg))
    # Fallback to vector drawing
    ic = QIcon()
    for s in (16, 24, 32, 48):
        ic.addPixmap(_pixmap(name, s))
    return ic
