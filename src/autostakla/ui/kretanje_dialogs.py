"""Dijalozi za ulaz, izlaz, ispravku količine, premeštanje i istoriju."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from autostakla import version
from autostakla.lager import repo
from autostakla.ui.common import fill_combo, user_errors
from autostakla.ui.staklo_dialog import StakloDialog


def _buttons(dialog: QDialog, ok_text: str) -> QDialogButtonBox:
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    bb.button(QDialogButtonBox.StandardButton.Ok).setText(ok_text)
    bb.button(QDialogButtonBox.StandardButton.Cancel).setText("Otkaži")
    bb.rejected.connect(dialog.reject)
    return bb


class MestoPicker(QWidget):
    """Skladište + polica + pozicija. Pozicija je ograničena na brojeve te police (da red ostane ispravan)."""

    def __init__(self, conn, skladiste_id=None, polica_id=None, pozicija=None, osim_stavke=None,
                 samo_skladiste=False):
        super().__init__()
        self.conn = conn
        self.osim_stavke = osim_stavke
        self.skladiste = QComboBox()
        self.polica = QComboBox()
        self.pozicija = QSpinBox()
        self.raspon = QLabel()
        self.raspon.setStyleSheet("color: gray")
        fill_combo(self.skladiste, [(s["naziv"], s["id"]) for s in repo.list_skladista(conn)], keep=False)
        if skladiste_id is not None:
            self.skladiste.setCurrentIndex(max(0, self.skladiste.findData(skladiste_id)))
        self.skladiste.setEnabled(not samo_skladiste)
        self.skladiste.currentIndexChanged.connect(self._load_police)
        self._load_police()
        if polica_id is not None:
            self.polica.setCurrentIndex(max(0, self.polica.findData(polica_id)))
        self.polica.currentIndexChanged.connect(lambda _: self._update_range(None))
        self._update_range(pozicija)
        poz_row = QHBoxLayout()
        poz_row.addWidget(self.pozicija)
        poz_row.addWidget(self.raspon, 1)
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow("Skladište:", self.skladiste)
        form.addRow("Polica:", self.polica)
        form.addRow("Pozicija (redni broj):", poz_row)

    def _load_police(self) -> None:
        sid = self.skladiste.currentData()
        items = [(p["naziv"], p["id"]) for p in repo.list_police(self.conn, sid)] if sid else []
        fill_combo(self.polica, items, keep=False)
        self._update_range(None)

    def _update_range(self, pozicija) -> None:
        pid = self.polica.currentData()
        if pid is None:
            self.pozicija.setRange(1, 1)
            self.raspon.setText("")
            return
        od, do = repo.polica_raspon(self.conn, pid, self.osim_stavke)
        self.pozicija.setRange(od, do)
        self.pozicija.setValue(do if pozicija is None else max(od, min(pozicija, do)))
        if od == do:
            self.raspon.setText(f"polica je prazna – staklo dobija broj {od}")
        else:
            self.raspon.setText(f"na ovoj polici su brojevi {od}–{do - 1}; {do} = na kraj police")

    def values(self) -> tuple[int | None, int | None]:
        return self.polica.currentData(), self.pozicija.value()


class UlazDialog(QDialog):
    def __init__(self, parent, conn, staklo_id=None, skladiste_id=None, polica_id=None, pozicija=None):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("Ulaz stakla")
        self.resize(560, 300)

        self.staklo = QComboBox()
        self.staklo.setEditable(True)
        self.staklo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.staklo.lineEdit().setPlaceholderText("počnite da kucate naziv...")
        self._load_stakla(staklo_id)
        novo = QPushButton("Novo staklo…")
        novo.clicked.connect(self._novo)
        st_row = QHBoxLayout()
        st_row.addWidget(self.staklo, 1)
        st_row.addWidget(novo)

        self.mesto = MestoPicker(conn, skladiste_id, polica_id, pozicija)
        self.kolicina = QSpinBox()
        self.kolicina.setRange(1, 99)
        self.napomena = QLineEdit()
        self.objasnjenje = QLabel()
        self.objasnjenje.setWordWrap(True)
        self.kolicina.valueChanged.connect(self._objasni)
        self.mesto.pozicija.valueChanged.connect(self._objasni)
        self.mesto.polica.currentIndexChanged.connect(self._objasni)

        form = QFormLayout()
        form.addRow("Staklo:", st_row)
        form.addRow(self.mesto)
        form.addRow("Količina (kom):", self.kolicina)
        form.addRow("Napomena:", self.napomena)
        form.addRow(self.objasnjenje)
        self._objasni()
        bb = _buttons(self, "Upiši ulaz")
        bb.accepted.connect(self._save)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(bb)

    def _objasni(self, *_args) -> None:
        n, p = self.kolicina.value(), self.mesto.pozicija.value()
        brojevi = f"broj {p}" if n == 1 else f"brojeve {p}–{p + n - 1}"
        dalje = f"Stakla od broja {p} naniže pomeraju se za {n}." if p < self.mesto.pozicija.maximum() else ""
        self.objasnjenje.setText(f"<i>Svaki komad dobija svoj broj: {brojevi}. {dalje}</i>")

    def _load_stakla(self, select_id=None) -> None:
        fill_combo(self.staklo, [(s["naziv"], s["id"]) for s in repo.list_stakla(self.conn)], keep=False)
        comp = QCompleter([self.staklo.itemText(i) for i in range(self.staklo.count())], self)
        comp.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        comp.setFilterMode(Qt.MatchFlag.MatchContains)
        self.staklo.setCompleter(comp)
        if select_id is not None:
            self.staklo.setCurrentIndex(self.staklo.findData(select_id))
        else:
            self.staklo.setCurrentIndex(-1)

    def _novo(self) -> None:
        d = StakloDialog(self, self.conn, naziv=self.staklo.currentText())
        if d.exec():
            self._load_stakla(d.staklo_id)

    def _selected_staklo(self) -> int | None:
        idx = self.staklo.findText(self.staklo.currentText(), Qt.MatchFlag.MatchFixedString)
        return self.staklo.itemData(idx) if idx >= 0 else None

    def _save(self) -> None:
        with user_errors(self):
            sid = self._selected_staklo()
            if sid is None:
                raise repo.LagerError("Izaberite staklo sa liste ili kliknite „Novo staklo…“.")
            polica_id, poz = self.mesto.values()
            if polica_id is None:
                raise repo.LagerError("Izaberite skladište i policu.")
            repo.ulaz(self.conn, sid, polica_id, self.kolicina.value(), poz, self.napomena.text())
            self.accept()


class KolicinaDialog(QDialog):
    """Izlaz ili ispravka količine za jednu stavku."""

    def __init__(self, parent, conn, row: dict, mode: str):
        super().__init__(parent)
        self.conn, self.row, self.mode = conn, row, mode
        izlaz = mode == "izlaz"
        self.setWindowTitle("Izlaz stakla" if izlaz else "Ispravka količine")
        self.kolicina = QSpinBox()
        if izlaz:
            self.kolicina.setRange(1, max(1, row["kolicina"]))
            self.kolicina.setValue(1)
        else:
            self.kolicina.setRange(0, 999)
            self.kolicina.setValue(row["kolicina"])
        self.napomena = QLineEdit()
        form = QFormLayout(self)
        form.addRow(QLabel(f"<b>{row['naziv']}</b><br>{_mesto(row)}<br>Na stanju: <b>{row['kolicina']}</b> kom"))
        form.addRow("Izlazi komada:" if izlaz else "Tačna količina:", self.kolicina)
        form.addRow("Napomena:", self.napomena)
        bb = _buttons(self, "Upiši izlaz" if izlaz else "Ispravi")
        bb.accepted.connect(self._save)
        form.addRow(bb)
        self.resize(460, 200)

    def _save(self) -> None:
        with user_errors(self):
            if self.mode == "izlaz":
                repo.izlaz(self.conn, self.row["lager_stavka_id"], self.kolicina.value(), self.napomena.text())
            else:
                repo.korekcija(self.conn, self.row["lager_stavka_id"], self.kolicina.value(), self.napomena.text())
            self.accept()


class PremestiDialog(QDialog):
    def __init__(self, parent, conn, row: dict):
        super().__init__(parent)
        self.conn, self.row = conn, row
        self.setWindowTitle("Premeštanje stakla")
        self.kolicina = QSpinBox()
        self.kolicina.setRange(1, max(1, row["kolicina"]))
        self.kolicina.setValue(row["kolicina"])
        self.mesto = MestoPicker(conn, row["skladiste_id"], row["polica_id"], row["pozicija"])
        self.napomena = QLineEdit()
        form = QFormLayout(self)
        form.addRow(QLabel(f"<b>{row['naziv']}</b><br>Sada: {_mesto(row)}"))
        form.addRow("Komada:", self.kolicina)
        form.addRow(QLabel("<b>Novo mesto:</b>"))
        form.addRow(self.mesto)
        form.addRow("Napomena:", self.napomena)
        bb = _buttons(self, "Premesti")
        bb.accepted.connect(self._save)
        form.addRow(bb)
        self.resize(480, 300)

    def _save(self) -> None:
        with user_errors(self):
            polica_id, poz = self.mesto.values()
            if polica_id is None:
                raise repo.LagerError("Izaberite skladište i policu.")
            repo.premesti(self.conn, self.row["lager_stavka_id"], self.kolicina.value(), polica_id, poz,
                          self.napomena.text())
            self.accept()


class IzmeniMestoDialog(QDialog):
    """Izmena napomene i pozicije/police u istom skladištu."""

    def __init__(self, parent, conn, row: dict):
        super().__init__(parent)
        self.conn, self.row = conn, row
        self.setWindowTitle("Izmena mesta i napomene")
        self.mesto = MestoPicker(conn, row["skladiste_id"], row["polica_id"], row["pozicija"],
                                 osim_stavke=row["lager_stavka_id"], samo_skladiste=True)
        self.napomena = QLineEdit(row["stavka_napomena"] or "")
        form = QFormLayout(self)
        form.addRow(QLabel(f"<b>{row['naziv']}</b> – {row['kolicina']} kom<br>Sada: {_mesto(row)}"))
        form.addRow(self.mesto)
        form.addRow("Napomena:", self.napomena)
        if row["pozicija"] is None:
            self.mesto.setEnabled(False)
        form.addRow(QLabel("<i>Ako promenite poziciju, ostala stakla se sama prenumerišu.<br>"
                           "Za drugo skladište koristite „Premesti“.</i>"))
        bb = _buttons(self, "Sačuvaj")
        bb.accepted.connect(self._save)
        form.addRow(bb)
        self.napomena.setFocus()
        self.resize(520, 300)

    def _save(self) -> None:
        with user_errors(self):
            polica_id, poz = self.mesto.values()
            if self.row["pozicija"] is None:
                polica_id, poz = self.row["polica_id"], None
            repo.izmeni_mesto(self.conn, self.row["lager_stavka_id"], polica_id, poz, self.napomena.text())
            self.accept()


class IstorijaDialog(QDialog):
    VRSTE = {"POCETNO": "Početno stanje", "ULAZ": "Ulaz", "IZLAZ": "Izlaz",
             "KOREKCIJA": "Ispravka", "PREMESTANJE": "Premeštanje"}

    def __init__(self, parent, conn, row: dict):
        super().__init__(parent)
        self.setWindowTitle("Istorija")
        better = version.is_better()
        if better:
            from autostakla.better import prodaja
            rows = prodaja.istorija(conn, row["lager_stavka_id"])
        else:
            rows = repo.istorija(conn, row["lager_stavka_id"])
        headers = ["Datum", "Vrsta", "Kom", "Napomena"] + (["Razlog / detalj"] if better else [])
        t = QTableWidget(len(rows), len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for r, k in enumerate(rows):
            for c, v in enumerate((k["datum"], self.VRSTE.get(k["vrsta"], k["vrsta"]),
                                   f"{k['kolicina']:+d}", k["napomena"] or "", k.get("detalj") or "")[:len(headers)]):
                t.setItem(r, c, QTableWidgetItem(v))
        t.horizontalHeader().setSectionResizeMode(len(headers) - 1, QHeaderView.ResizeMode.Stretch)
        t.resizeColumnsToContents()
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"<b>{row['naziv']}</b> – {_mesto(row)}"))
        lay.addWidget(t)
        close = QPushButton("Zatvori")
        close.clicked.connect(self.accept)
        lay.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self.resize(640, 420)


def _mesto(row: dict) -> str:
    poz = f", pozicija {row['pozicija']}" if row.get("pozicija") else ""
    return f"{row['skladiste']} / {row['polica']}{poz}"
