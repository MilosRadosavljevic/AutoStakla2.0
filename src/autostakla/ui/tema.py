"""Svetla / tamna tema. Izbor se pamti u bazi (podesavanja.tema) i važi pri sledećem pokretanju."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from autostakla.core import settings

log = logging.getLogger(__name__)

_SCHEME = {"svetla": Qt.ColorScheme.Light, "tamna": Qt.ColorScheme.Dark}


def trenutna(conn) -> str:
    """Sačuvana tema; ako je nema – kakva je trenutno u Windows-u."""
    t = settings.get(conn, settings.KEY_TEMA)
    if t in settings.TEME:
        return t
    return "tamna" if QApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark else "svetla"


def primeni(tema: str) -> None:
    QApplication.styleHints().setColorScheme(_SCHEME.get(tema, Qt.ColorScheme.Unknown))


def ucitaj(conn) -> None:
    """Pri startu: primeni sačuvanu temu (ako nije sačuvana – ostaje kao Windows)."""
    t = settings.get(conn, settings.KEY_TEMA)
    if t in settings.TEME:
        primeni(t)


def promeni(conn, tema: str) -> None:
    primeni(tema)
    settings.set(conn, settings.KEY_TEMA, tema)
    log.info("Tema: %s", tema)
