"""Zajednički delovi UI-ja."""
from __future__ import annotations

import logging
from contextlib import contextmanager

from PySide6.QtWidgets import QComboBox, QMessageBox, QWidget

from autostakla.lager.repo import LagerError

log = logging.getLogger(__name__)


@contextmanager
def user_errors(parent: QWidget, title: str = "Pažnja"):
    """LagerError -> poruka korisniku (bez gašenja programa). Ostale greške idu u globalni handler."""
    try:
        yield
    except LagerError as e:
        log.info("Poruka korisniku: %s", e)
        QMessageBox.warning(parent, title, str(e))


def confirm(parent: QWidget, title: str, text: str) -> bool:
    return QMessageBox.question(parent, title, text) == QMessageBox.StandardButton.Yes


def fill_combo(combo: QComboBox, items: list[tuple[str, object]], keep=True, first: tuple[str, object] | None = None):
    """Popuni combo (tekst, vrednost); zadrži izabranu vrednost ako i dalje postoji."""
    current = combo.currentData() if keep else None
    combo.blockSignals(True)
    combo.clear()
    if first:
        combo.addItem(first[0], first[1])
    for text, value in items:
        combo.addItem(text, value)
    idx = combo.findData(current) if current is not None else -1
    combo.setCurrentIndex(idx if idx >= 0 else 0)
    combo.blockSignals(False)
