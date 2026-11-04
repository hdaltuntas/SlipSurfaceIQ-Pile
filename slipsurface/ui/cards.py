"""The headline results as a row of cards — capacity, checks, length.

Fed by `summary.cards()` / `summary.socket_cards()`; a card's `state`
("ok", "bad", "na" or "") colours its value, so the checks read at a glance.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

STATE_COLOURS = {"ok": "#16a34a", "bad": "#dc2626", "na": "#9ca3af"}


class CardStrip(QWidget):
    """A wrapping grid of small result cards."""

    def __init__(self, parent=None, columns: int = 5):
        super().__init__(parent)
        self.columns = columns
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(10)
        self.setVisible(False)

    def clear(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.setVisible(False)

    def set_cards(self, cards: list):
        self.clear()
        for index, card in enumerate(cards):
            self.grid.addWidget(self._card(card), index // self.columns, index % self.columns)
        self.setVisible(bool(cards))

    @staticmethod
    def _card(card: dict) -> QFrame:
        frame = QFrame()
        frame.setObjectName("card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)
        title = QLabel(card.get("title", ""))
        title.setObjectName("cardTitle")
        value = QLabel(card.get("value", ""))
        value.setObjectName("cardValue")
        colour = STATE_COLOURS.get(card.get("state", ""))
        if colour:
            value.setStyleSheet(f"color: {colour};")
        lay.addWidget(title)
        lay.addWidget(value)
        if card.get("sub"):
            sub = QLabel(card["sub"])
            sub.setObjectName("cardSub")
            sub.setWordWrap(True)
            lay.addWidget(sub)
        frame.setToolTip(f"{card.get('title', '')}: {card.get('value', '')}\n"
                         f"{card.get('sub', '')}")
        return frame
