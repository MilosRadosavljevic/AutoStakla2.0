"""Kupac: unos/izmena i izbor (combo sa pretragom + „Novi kupac…“)."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QFormLayout, QHBoxLayout, QLineEdit, QPushButton, QWidget

from autostakla.better import prodaja
from autostakla.ui.better.common import combo_pretraga, combo_vrednost, dugmad
from autostakla.ui.common import user_errors


class KupacDialog(QDialog):
    def __init__(self, parent, conn, kupac_id: int | None = None, ime: str = ""):
        super().__init__(parent)
        self.conn, self.kupac_id = conn, kupac_id
        self.setWindowTitle("Izmena kupca" if kupac_id else "Novi kupac")
        k = prodaja.get_kupac(conn, kupac_id) if kupac_id else {"ime": ime, "telefon": "", "napomena": ""}
        self.ime = QLineEdit(k["ime"] or "")
        self.telefon = QLineEdit(k["telefon"] or "")
        self.napomena = QLineEdit(k["napomena"] or "")
        form = QFormLayout(self)
        form.addRow("Ime i prezime / firma:", self.ime)
        form.addRow("Telefon:", self.telefon)
        form.addRow("Napomena:", self.napomena)
        bb = dugmad(self, "Sačuvaj")
        bb.accepted.connect(self._save)
        form.addRow(bb)
        self.resize(420, 160)

    def _save(self) -> None:
        with user_errors(self):
            if self.kupac_id:
                prodaja.update_kupac(self.conn, self.kupac_id, self.ime.text(), self.telefon.text(),
                                     self.napomena.text())
            else:
                self.kupac_id = prodaja.add_kupac(self.conn, self.ime.text(), self.telefon.text(),
                                                  self.napomena.text())
            self.accept()


class KupacPicker(QWidget):
    def __init__(self, conn, kupac_id: int | None = None):
        super().__init__()
        self.conn = conn
        self.combo = QComboBox()
        novi = QPushButton("Novi kupac…")
        novi.clicked.connect(self._novi)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.combo, 1)
        lay.addWidget(novi)
        self._load(kupac_id)

    def _load(self, select=None) -> None:
        items = [(f"{k['ime']}" + (f" ({k['telefon']})" if k["telefon"] else ""), k["id"])
                 for k in prodaja.list_kupci(self.conn)]
        combo_pretraga(self.combo, items, select, prazno="(bez kupca)")

    def _novi(self) -> None:
        tekst = self.combo.currentText() if combo_vrednost(self.combo) is None else ""
        d = KupacDialog(self, self.conn, ime="" if tekst == "(bez kupca)" else tekst)
        if d.exec():
            self._load(d.kupac_id)

    def value(self) -> int | None:
        return combo_vrednost(self.combo)
