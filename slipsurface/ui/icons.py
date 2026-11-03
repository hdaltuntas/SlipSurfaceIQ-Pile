"""Simple vector toolbar icons for SlipSurfaceIQ Pile (LE-style, no external files)."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

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
    else:
        p.setPen(_pen(INK, 4))
        p.drawRect(QRectF(16, 16, 32, 32))

    p.end()
    return pm


def icon(name: str) -> QIcon:
    ic = QIcon()
    for s in (16, 24, 32, 48):
        ic.addPixmap(_pixmap(name, s))
    return ic
