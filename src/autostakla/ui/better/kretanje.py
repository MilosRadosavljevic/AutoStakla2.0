"""Prošireni izlaz (razlog + prodaja) i ulaz (razlog + dobavljač i nabavna cena)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QDialog,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
)

from autostakla.better import nabavka, novac, prodaja, vozila
from autostakla.better.prodaja import RAZLOZI_IZLAZ, RAZLOZI_ULAZ, ProdajaPodaci
from autostakla.lager import repo
from autostakla.ui.better.common import dugmad, iznos_edit
from autostakla.ui.better.kupac_dialog import KupacPicker
from autostakla.ui.common import fill_combo, user_errors
from autostakla.ui.kretanje_dialogs import UlazDialog, _mesto


class IzlazDialog(QDialog):
    def __init__(self, parent, conn, row: dict):
        super().__init__(parent)
        self.conn, self.row = conn, row
        self.setWindowTitle("Izlaz stakla")
        self.kolicina = QSpinBox()
        self.kolicina.setRange(1, max(1, row["kolicina"]))
        self.razlog = QComboBox()
        fill_combo(self.razlog, [(t, k) for k, t in RAZLOZI_IZLAZ.items()], keep=False)
        self.napomena = QLineEdit()

        self.grupa = QGroupBox("Prodaja")
        self.cena = iznos_edit()
        self.kupac = KupacPicker(conn)
        s = repo.get_staklo(conn, row["staklo_id"])
        self.vozilo = QLineEdit(vozila.opis(s.vozila[0]) if len(s.vozila) == 1 else "")
        self.vozilo.setPlaceholderText("npr. Golf 5, 2007")
        self.tablice = QLineEdit()
        self.tablice.setPlaceholderText("npr. SD 123-AB")
        self.ugradnja = QCheckBox("cena uključuje ugradnju")
        g = QFormLayout(self.grupa)
        g.addRow("Cena po komadu (sa PDV-om):", self.cena)
        g.addRow("Kupac:", self.kupac)
        g.addRow("Vozilo:", self.vozilo)
        g.addRow("Tablice:", self.tablice)
        g.addRow(self.ugradnja)
        self.razlog.currentIndexChanged.connect(lambda _: self.grupa.setVisible(self.razlog.currentData() == "PRODATO"))

        form = QFormLayout(self)
        form.addRow(QLabel(f"<b>{row['naziv']}</b><br>{_mesto(row)}<br>Na stanju: <b>{row['kolicina']}</b> kom"))
        form.addRow("Izlazi komada:", self.kolicina)
        form.addRow("Razlog:", self.razlog)
        form.addRow(self.grupa)
        form.addRow("Napomena:", self.napomena)
        bb = dugmad(self, "Upiši izlaz")
        bb.accepted.connect(self._save)
        form.addRow(bb)
        self.resize(560, 360)

    def _save(self) -> None:
        with user_errors(self):
            razlog = self.razlog.currentData()
            podaci = None
            if razlog == "PRODATO":
                podaci = ProdajaPodaci(novac.parse(self.cena.text()), self.kupac.value(), self.vozilo.text(),
                                       self.tablice.text(), self.ugradnja.isChecked())
            prodaja.izlaz(self.conn, self.row["lager_stavka_id"], self.kolicina.value(), razlog,
                          self.napomena.text(), podaci)
            self.accept()


class UlazBetterDialog(UlazDialog):
    """Ulaz iz osnovne verzije + razlog, dobavljač, nabavna cena (predlog iz cenovnika) i broj dokumenta."""

    def __init__(self, parent, conn, **kw):
        super().__init__(parent, conn, **kw)
        self.razlog = QComboBox()
        fill_combo(self.razlog, [(t, k) for k, t in RAZLOZI_ULAZ.items()], keep=False)
        self.dobavljac = QComboBox()
        fill_combo(self.dobavljac, [(d["naziv"], d["id"]) for d in nabavka.list_dobavljaci(conn)], keep=False,
                   first=("(bez dobavljača)", None))
        self.cena = iznos_edit()
        self.dokument = QLineEdit()
        self.dokument.setPlaceholderText("broj fakture/otpremnice dobavljača")
        self.cene = QLabel()
        self.cene.setWordWrap(True)
        self.grupa = QGroupBox("Nabavka")
        g = QFormLayout(self.grupa)
        g.addRow("Dobavljač:", self.dobavljac)
        g.addRow("Nabavna cena po komadu (bez PDV-a):", self.cena)
        g.addRow("Dokument:", self.dokument)
        g.addRow(self.cene)
        box = QFormLayout()
        box.addRow("Razlog:", self.razlog)
        box.addRow(self.grupa)
        lay: QVBoxLayout = self.layout()
        lay.insertLayout(1, box)
        lay.insertStretch(2, 1)  # višak visine ide iznad dugmadi, ne između polja
        self.razlog.currentIndexChanged.connect(lambda _: self.grupa.setVisible(self.razlog.currentData() == "NABAVKA"))
        self.dobavljac.currentIndexChanged.connect(self._predlozi_cenu)
        self.staklo.currentIndexChanged.connect(self._predlozi_cenu)
        self._auto_cena = ""
        self._predlozi_cenu()
        self.resize(600, 470)

    def _predlozi_cenu(self, *_args) -> None:
        sid = self._selected_staklo()
        cene = nabavka.cene_za_staklo(self.conn, sid) if sid else []
        self.cene.setText("<i>Cene u cenovniku: " + (", ".join(
            f"{c['dobavljac']} {novac.fmt(c['cena'])}" for c in cene) or "nema") + "</i>")
        if self.cena.text() not in ("", self._auto_cena):
            return  # korisnik je već upisao svoju cenu
        did = self.dobavljac.currentData()
        c = nabavka.vazeca_cena(self.conn, sid, did) if (sid and did) else None
        self._auto_cena = f"{c:,}".replace(",", ".") if c is not None else ""
        self.cena.setText(self._auto_cena)

    def _save(self) -> None:
        with user_errors(self):
            sid = self._selected_staklo()
            if sid is None:
                raise repo.LagerError("Izaberite staklo sa liste ili kliknite „Novo staklo…“.")
            polica_id, poz = self.mesto.values()
            if polica_id is None:
                raise repo.LagerError("Izaberite skladište i policu.")
            razlog = self.razlog.currentData()
            je_nabavka = razlog == "NABAVKA"
            nabavka.ulaz(self.conn, sid, polica_id, self.kolicina.value(), poz, self.napomena.text(), razlog,
                         self.dobavljac.currentData() if je_nabavka else None,
                         novac.parse(self.cena.text(), "Nabavna cena") if je_nabavka else None,
                         self.dokument.text() if je_nabavka else None)
            self.accept()
