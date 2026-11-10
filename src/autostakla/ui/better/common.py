"""Zajednički delovi Better ekrana: dugmad, polje za iznos, datum, tabele, otvaranje PDF-a."""
from __future__ import annotations

import logging
import os
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from autostakla.core import paths

log = logging.getLogger(__name__)


def dugmad(dialog: QDialog, ok_text: str, cancel_text: str = "Otkaži") -> QDialogButtonBox:
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    bb.button(QDialogButtonBox.StandardButton.Ok).setText(ok_text)
    bb.button(QDialogButtonBox.StandardButton.Cancel).setText(cancel_text)
    bb.rejected.connect(dialog.reject)
    return bb


def iznos_edit(placeholder: str = "npr. 12.500") -> QLineEdit:
    e = QLineEdit()
    e.setPlaceholderText(placeholder)
    e.setMaximumWidth(160)
    return e


def datum_edit(d: date) -> QDateEdit:
    e = QDateEdit(QDate(d.year, d.month, d.day))
    e.setCalendarPopup(True)
    e.setDisplayFormat("dd.MM.yyyy")
    return e


def iso(e: QDateEdit) -> str:
    return e.date().toString("yyyy-MM-dd")


def tabela(headers: list[str], stretch: int | None = None) -> QTableWidget:
    t = QTableWidget(0, len(headers))
    t.setHorizontalHeaderLabels(headers)
    t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    t.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    t.setAlternatingRowColors(True)
    t.verticalHeader().setVisible(False)
    if stretch is not None:
        t.horizontalHeader().setSectionResizeMode(stretch, QHeaderView.ResizeMode.Stretch)
    return t


def popuni(t: QTableWidget, rows: list[list], data: list | None = None, desno: tuple[int, ...] = (),
           bold: set[int] | None = None) -> None:
    """Redovi tabele; 'data' ide uz kolonu 0 (UserRole), 'desno' = kolone poravnate desno (iznosi)."""
    t.setRowCount(len(rows))
    for r, red in enumerate(rows):
        for c, v in enumerate(red):
            it = QTableWidgetItem("" if v is None else str(v))
            if c in desno:
                it.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if bold and r in bold:
                f = QFont()
                f.setBold(True)
                it.setFont(f)
            if c == 0 and data is not None:
                it.setData(Qt.ItemDataRole.UserRole, data[r])
            t.setItem(r, c, it)
    t.resizeColumnsToContents()


def izabrano(t: QTableWidget):
    rows = t.selectionModel().selectedRows()
    return t.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole) if rows else None


def combo_pretraga(combo: QComboBox, items: list[tuple[str, object]], select=None, prazno: str | None = None) -> None:
    """Combo sa pretragom po delu teksta (kao izbor stakla kod ulaza)."""
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
    combo.clear()
    if prazno is not None:
        combo.addItem(prazno, None)
    for text, value in items:
        combo.addItem(text, value)
    comp = QCompleter([combo.itemText(i) for i in range(combo.count())], combo)
    comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    comp.setFilterMode(Qt.MatchFlag.MatchContains)
    combo.setCompleter(comp)
    idx = combo.findData(select) if select is not None else (0 if prazno is not None else -1)
    combo.setCurrentIndex(idx)


def combo_vrednost(combo: QComboBox):
    idx = combo.findText(combo.currentText(), Qt.MatchFlag.MatchFixedString)
    return combo.itemData(idx) if idx >= 0 else None


def stampa_folder() -> Path:
    folder = paths.root_dir() / "stampa"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def stampa_fajl(naziv: str, ekstenzija: str = "pdf") -> Path:
    return stampa_folder() / f"{naziv}_{datetime.now():%Y-%m-%d_%H%M%S}.{ekstenzija}"


def otvori(parent: QWidget, path: Path) -> None:
    try:
        os.startfile(path)  # type: ignore[attr-defined]
    except OSError:
        log.exception("Fajl ne može da se otvori")
        QMessageBox.information(parent, "Otvaranje", f"Fajl je napravljen, ali Windows ne zna čime da ga otvori:\n\n{path}")
