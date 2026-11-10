"""Predračun i otpremnice, vozila iz naziva stakla, podaci o firmi i PDV."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidgetItem,
    QVBoxLayout,
)

from autostakla.better import dokumenti, novac, vozila
from autostakla.lager import repo
from autostakla.ui.better.common import (
    combo_pretraga,
    combo_vrednost,
    dugmad,
    iznos_edit,
    izabrano,
    otvori,
    popuni,
    stampa_folder,
    tabela,
)
from autostakla.ui.better.kupac_dialog import KupacPicker
from autostakla.ui.common import user_errors


class DokumentiDialog(QDialog):
    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("Predračuni i otpremnice")
        self.t = tabela(["Broj", "Datum", "Kupac", "Ukupno", "Napomena"], stretch=4)
        self.t.doubleClicked.connect(self.pdf)
        dole = QHBoxLayout()
        dole.addWidget(QLabel("<i>Nisu fiskalni računi. Otpremnica se pravi iz prozora Prodaja.</i>"), 1)
        for text, slot in (("Novi predračun…", self.predracun), ("Otvori PDF", self.pdf), ("Zatvori", self.accept)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            dole.addWidget(b)
        lay = QVBoxLayout(self)
        lay.addWidget(self.t)
        lay.addLayout(dole)
        self.resize(900, 480)
        self.refresh()

    def refresh(self) -> None:
        rows = dokumenti.list_dokumenti(self.conn)
        popuni(self.t, [[r["broj"], r["datum"], r["kupac"], novac.fmt(r["ukupno"] or 0), r["napomena"]] for r in rows],
               [r["id"] for r in rows], desno=(3,))

    def predracun(self) -> None:
        d = PredracunDialog(self, self.conn)
        if d.exec():
            self.refresh()
            otvori(self, dokumenti.pdf(self.conn, d.dokument_id, stampa_folder()))

    def pdf(self, *_args) -> None:
        did = izabrano(self.t)
        if did is not None:
            otvori(self, dokumenti.pdf(self.conn, did, stampa_folder()))


class PredracunDialog(QDialog):
    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self.dokument_id: int | None = None
        self.stavke: list[dokumenti.Stavka] = []
        self.setWindowTitle("Novi predračun")
        self.kupac = KupacPicker(conn)
        self.staklo = QComboBox()
        combo_pretraga(self.staklo, [(s["naziv"], s["id"]) for s in repo.list_stakla(conn)])
        self.staklo.lineEdit().setPlaceholderText("staklo sa liste ili slobodan tekst (npr. ugradnja)")
        self.kom = QSpinBox()
        self.kom.setRange(1, 99)
        self.cena = iznos_edit()
        dodaj = QPushButton("Dodaj stavku")
        dodaj.clicked.connect(self._dodaj)
        unos = QHBoxLayout()
        unos.addWidget(self.staklo, 1)
        unos.addWidget(QLabel("kom:"))
        unos.addWidget(self.kom)
        unos.addWidget(QLabel("cena sa PDV:"))
        unos.addWidget(self.cena)
        unos.addWidget(dodaj)
        self.t = tabela(["Naziv", "Kom", "Cena", "Ukupno"], stretch=0)
        ukloni = QPushButton("Ukloni stavku")
        ukloni.clicked.connect(self._ukloni)
        self.ukupno = QLabel()
        self.napomena = QLineEdit()
        form = QFormLayout()
        form.addRow("Kupac:", self.kupac)
        form.addRow("Napomena:", self.napomena)
        bb = dugmad(self, "Napravi predračun")
        bb.accepted.connect(self._save)
        sredina = QHBoxLayout()
        sredina.addWidget(self.ukupno, 1)
        sredina.addWidget(ukloni)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addLayout(unos)
        lay.addWidget(self.t)
        lay.addLayout(sredina)
        lay.addWidget(bb)
        self.resize(820, 460)
        self._prikazi()

    def _dodaj(self) -> None:
        with user_errors(self):
            naziv = self.staklo.currentText().strip()
            if not naziv:
                raise repo.LagerError("Izaberite staklo ili upišite naziv stavke.")
            self.stavke.append(dokumenti.Stavka(naziv, self.kom.value(), novac.parse(self.cena.text()),
                                                combo_vrednost(self.staklo)))
            self.cena.clear()
            self._prikazi()

    def _ukloni(self) -> None:
        rows = self.t.selectionModel().selectedRows()
        if rows:
            del self.stavke[rows[0].row()]
            self._prikazi()

    def _prikazi(self) -> None:
        popuni(self.t, [[s.naziv, s.kolicina, novac.fmt(s.cena), novac.fmt(s.kolicina * s.cena)] for s in self.stavke],
               desno=(1, 2, 3))
        self.ukupno.setText(f"Ukupno sa PDV-om: <b>{novac.fmt(sum(s.kolicina * s.cena for s in self.stavke))}</b>")

    def _save(self) -> None:
        with user_errors(self):
            self.dokument_id = dokumenti.novi(self.conn, "PREDRACUN", self.stavke, self.kupac.value(),
                                              napomena=self.napomena.text())
            self.accept()


class VozilaDialog(QDialog):
    """Predlog vozila za stakla bez upisanih vozila; sigurni predlozi su unapred označeni."""

    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("Vozila iz naziva stakla")
        self.predlozi = vozila.predlozi(conn)
        self.t = tabela(["Staklo", "Predlog vozila", "Napomena"], stretch=1)
        popuni(self.t, [[p.naziv, "; ".join(vozila.opis(v) for v in p.vozila), p.napomena] for p in self.predlozi])
        for r, p in enumerate(self.predlozi):
            it: QTableWidgetItem = self.t.item(r, 0)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if p.siguran and p.vozila else Qt.CheckState.Unchecked)
        bb = dugmad(self, "Upiši označena")
        bb.accepted.connect(self._save)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"Stakla bez upisanih vozila: <b>{len(self.predlozi)}</b>. Označena su ona koja su "
                             "sigurno prepoznata; ostala proverite ili ih upišite ručno (Izmeni staklo)."))
        lay.addWidget(self.t)
        lay.addWidget(bb)
        self.resize(1000, 600)

    def _save(self) -> None:
        with user_errors(self):
            n = 0
            for r, p in enumerate(self.predlozi):
                if self.t.item(r, 0).checkState() == Qt.CheckState.Checked and p.vozila:
                    vozila.upisi(self.conn, p.staklo_id, p.vozila)
                    n += 1
            QMessageBox.information(self, "Vozila", f"Upisana vozila za {n} stakala.")
            self.accept()


class FirmaDialog(QDialog):
    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("Podaci o firmi i PDV")
        f = dokumenti.get_firma(conn)
        self.polja = {k: QLineEdit(f[k]) for k, _ in dokumenti.FIRMA_POLJA}
        self.pdv = QSpinBox()
        self.pdv.setRange(0, 100)
        self.pdv.setSuffix(" %")
        self.pdv.setValue(novac.pdv_stopa(conn))
        form = QFormLayout(self)
        for k, naziv in dokumenti.FIRMA_POLJA:
            form.addRow(f"{naziv}:", self.polja[k])
        form.addRow("PDV stopa:", self.pdv)
        form.addRow(QLabel("<i>Podaci idu u zaglavlje predračuna i otpremnice. Cene prodaje se upisuju sa PDV-om,<br>"
                           "nabavne bez PDV-a; zarada se računa bez PDV-a.</i>"))
        bb = dugmad(self, "Sačuvaj")
        bb.accepted.connect(self._save)
        form.addRow(bb)
        self.resize(520, 340)

    def _save(self) -> None:
        with user_errors(self):
            dokumenti.set_firma(self.conn, {k: e.text() for k, e in self.polja.items()}, self.pdv.value())
            self.accept()
