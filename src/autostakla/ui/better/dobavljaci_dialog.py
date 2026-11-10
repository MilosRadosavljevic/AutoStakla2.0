"""Dobavljači (šifarnik) i cene stakla po dobavljačima."""
from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from autostakla.better import nabavka, novac
from autostakla.lager import repo
from autostakla.ui.better.common import datum_edit, dugmad, iso, iznos_edit, izabrano, popuni, tabela
from autostakla.ui.common import fill_combo, user_errors


class DobavljacDialog(QDialog):
    def __init__(self, parent, conn, dobavljac_id: int | None = None):
        super().__init__(parent)
        self.conn, self.dobavljac_id = conn, dobavljac_id
        self.setWindowTitle("Izmena dobavljača" if dobavljac_id else "Novi dobavljač")
        d = nabavka.get_dobavljac(conn, dobavljac_id) if dobavljac_id else {}
        self.naziv = QLineEdit(d.get("naziv") or "")
        self.telefon = QLineEdit(d.get("telefon") or "")
        self.email = QLineEdit(d.get("email") or "")
        self.napomena = QLineEdit(d.get("napomena") or "")
        form = QFormLayout(self)
        form.addRow("Naziv:", self.naziv)
        form.addRow("Telefon:", self.telefon)
        form.addRow("E-mail:", self.email)
        form.addRow("Napomena:", self.napomena)
        bb = dugmad(self, "Sačuvaj")
        bb.accepted.connect(self._save)
        form.addRow(bb)
        self.resize(440, 180)

    def _save(self) -> None:
        with user_errors(self):
            args = (self.naziv.text(), self.telefon.text(), self.email.text(), self.napomena.text())
            if self.dobavljac_id:
                nabavka.update_dobavljac(self.conn, self.dobavljac_id, *args)
            else:
                self.dobavljac_id = nabavka.add_dobavljac(self.conn, *args)
            self.accept()


class DobavljaciDialog(QDialog):
    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("Dobavljači")
        self.svi = QCheckBox("prikaži i neaktivne")
        self.svi.toggled.connect(self.refresh)
        self.t = tabela(["Naziv", "Telefon", "E-mail", "Napomena", "Aktivan"], stretch=3)
        self.t.doubleClicked.connect(self.izmeni)
        dugm = QHBoxLayout()
        dugm.addWidget(self.svi, 1)
        for text, slot in (("Dodaj…", self.dodaj), ("Izmeni…", self.izmeni),
                           ("Aktiviraj / deaktiviraj", self.aktivan), ("Zatvori", self.accept)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            dugm.addWidget(b)
        lay = QVBoxLayout(self)
        lay.addWidget(self.t)
        lay.addLayout(dugm)
        self.resize(820, 440)
        self.refresh()

    def refresh(self, *_args) -> None:
        rows = nabavka.list_dobavljaci(self.conn, not self.svi.isChecked())
        popuni(self.t, [[d["naziv"], d["telefon"], d["email"], d["napomena"], "da" if d["aktivno"] else "ne"]
                        for d in rows], [d["id"] for d in rows])

    def dodaj(self) -> None:
        if DobavljacDialog(self, self.conn).exec():
            self.refresh()

    def izmeni(self, *_args) -> None:
        did = izabrano(self.t)
        if did is not None and DobavljacDialog(self, self.conn, did).exec():
            self.refresh()

    def aktivan(self) -> None:
        did = izabrano(self.t)
        if did is not None:
            with user_errors(self):
                nabavka.set_aktivan(self.conn, did, not nabavka.get_dobavljac(self.conn, did)["aktivno"])
                self.refresh()


class CeneDialog(QDialog):
    """Nabavne cene jednog stakla kod svih dobavljača (važeće + istorija)."""

    def __init__(self, parent, conn, staklo_id: int):
        super().__init__(parent)
        self.conn, self.staklo_id = conn, staklo_id
        self.setWindowTitle("Cene po dobavljačima")
        self.vazece = tabela(["Dobavljač", "Cena bez PDV", "Važi od", "Napomena"], stretch=3)
        self.istorija = tabela(["Dobavljač", "Cena bez PDV", "Važi od", "Napomena"], stretch=3)
        nova = QPushButton("Nova cena…")
        nova.clicked.connect(self.nova)
        zatvori = QPushButton("Zatvori")
        zatvori.clicked.connect(self.accept)
        dole = QHBoxLayout()
        dole.addStretch(1)
        dole.addWidget(nova)
        dole.addWidget(zatvori)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"<b>{repo.get_staklo(conn, staklo_id).naziv}</b> – važeće cene (najjeftinija prva):"))
        lay.addWidget(self.vazece)
        lay.addWidget(QLabel("Istorija cena:"))
        lay.addWidget(self.istorija)
        lay.addLayout(dole)
        self.resize(700, 520)
        self.refresh()

    def refresh(self) -> None:
        v = nabavka.cene_za_staklo(self.conn, self.staklo_id)
        popuni(self.vazece, [[c["dobavljac"] + ("" if c["aktivno"] else " (neaktivan)"), novac.fmt(c["cena"]),
                              c["vazi_od"], c["napomena"]] for c in v], desno=(1,), bold={0} if v else None)
        popuni(self.istorija, [[c["dobavljac"], novac.fmt(c["cena"]), c["vazi_od"], c["napomena"]]
                               for c in nabavka.istorija_cena(self.conn, self.staklo_id)], desno=(1,))

    def nova(self) -> None:
        if not nabavka.list_dobavljaci(self.conn):
            QMessageBox.information(self, "Cene", "Prvo dodajte dobavljača (Poslovanje → Dobavljači).")
            return
        if NovaCenaDialog(self, self.conn, self.staklo_id).exec():
            self.refresh()


class NovaCenaDialog(QDialog):
    def __init__(self, parent, conn, staklo_id: int):
        super().__init__(parent)
        self.conn, self.staklo_id = conn, staklo_id
        self.setWindowTitle("Nova cena")
        self.dobavljac = QComboBox()
        fill_combo(self.dobavljac, [(d["naziv"], d["id"]) for d in nabavka.list_dobavljaci(conn)], keep=False)
        self.cena = iznos_edit()
        self.vazi_od = datum_edit(date.today())
        self.napomena = QLineEdit()
        form = QFormLayout(self)
        form.addRow("Dobavljač:", self.dobavljac)
        form.addRow("Nabavna cena (bez PDV-a):", self.cena)
        form.addRow("Važi od:", self.vazi_od)
        form.addRow("Napomena:", self.napomena)
        bb = dugmad(self, "Sačuvaj")
        bb.accepted.connect(self._save)
        form.addRow(bb)
        self.resize(420, 180)

    def _save(self) -> None:
        with user_errors(self):
            nabavka.postavi_cenu(self.conn, self.staklo_id, self.dobavljac.currentData(),
                                 novac.parse(self.cena.text()), iso(self.vazi_od), self.napomena.text())
            self.accept()
