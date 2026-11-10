"""Jednostavan stubičasti grafikon (QPainter, bez dodatne biblioteke); boje iz teme."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtWidgets import QWidget


class Stubici(QWidget):
    def __init__(self, naslov: str = ""):
        super().__init__()
        self.naslov = naslov
        self.podaci: list[tuple[str, int]] = []
        self.format = str
        self.setMinimumHeight(240)

    def postavi(self, podaci: list[tuple[str, int]], format_vrednosti=str) -> None:
        self.podaci, self.format = podaci, format_vrednosti
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        tekst, boja = pal.color(QPalette.ColorRole.WindowText), pal.color(QPalette.ColorRole.Highlight)
        p.setPen(tekst)
        w, h = self.width(), self.height()
        p.drawText(QRectF(0, 0, w, 20), Qt.AlignmentFlag.AlignLeft, self.naslov)
        if not self.podaci:
            p.drawText(QRectF(0, 0, w, h), Qt.AlignmentFlag.AlignCenter, "Nema podataka za izabrani period.")
            return
        top, bottom, left = 40, 36, 8
        maks = max(v for _, v in self.podaci) or 1
        korak = (w - 2 * left) / len(self.podaci)
        sirina = max(4.0, korak * 0.6)
        for i, (oznaka, v) in enumerate(self.podaci):
            visina = (h - top - bottom) * v / maks
            x = left + i * korak + (korak - sirina) / 2
            p.fillRect(QRectF(x, h - bottom - visina, sirina, visina), boja)
            p.drawText(QRectF(left + i * korak, h - bottom - visina - 18, korak, 16),
                       Qt.AlignmentFlag.AlignCenter, self.format(v))
            p.drawText(QRectF(left + i * korak, h - bottom + 4, korak, 30),
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, oznaka)
