"""Unos i izmena stakla (šifarnik): naziv, tip, senzor, kamera, pločica, vozila."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from autostakla.lager import repo
from autostakla.lager.repo import LagerError, Staklo, Vozilo
from autostakla.ui.common import user_errors

PLOCICE = ["", "trougao", "okrugla", "niža", "viša", "sa pločicom", "bez pločice"]


def _int_or_none(text: str, polje: str) -> int | None:
    text = (text or "").strip()
    if not text:
        return None
    if not text.isdigit():
        raise LagerError(f"{polje}: upišite godinu brojem (npr. 2008 ili 08).")
    n = int(text)
    if n < 100:  # 08 -> 2008, 95 -> 1995
        n += 2000 if n <= 50 else 1900
    return n


class StakloDialog(QDialog):
    """Ako je staklo_id zadat – izmena, inače unos novog. Posle accept() -> self.staklo_id."""

    def __init__(self, parent, conn, staklo_id: int | None = None, naziv: str = ""):
        super().__init__(parent)
        self.conn = conn
        self.staklo_id = staklo_id
        self.setWindowTitle("Izmena stakla" if staklo_id else "Novo staklo")
        self.resize(620, 560)

        self.naziv = QLineEdit(naziv)
        self.naziv.setPlaceholderText("kako ga pišete, npr. VW Golf 5 i 6 SENZOR")
        self.tip = QComboBox()
        for k, v in repo.TIPOVI.items():
            self.tip.addItem(v, k)
        self.senzor = QCheckBox("ima senzor")
        self.senzor_opis = QLineEdit()
        self.senzor_opis.setPlaceholderText("oblik: romb, krug, kruška, kocka...")
        self.kamera = QCheckBox("ima kameru")
        self.kamera_opis = QLineEdit()
        self.kamera_opis.setPlaceholderText("uska, široka, velika...")
        self.plocica = QComboBox()
        self.plocica.setEditable(True)
        self.plocica.addItems(PLOCICE)
        self.polovno = QCheckBox("polovno staklo")
        self.napomena = QLineEdit()

        self.vozila = QTableWidget(0, 5)
        self.vozila.setHorizontalHeaderLabels(["Marka", "Model", "Generacija", "Godina od", "Godina do"])
        self.vozila.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        add_v = QPushButton("+ Dodaj vozilo")
        add_v.clicked.connect(lambda: self._add_vozilo(Vozilo("")))
        del_v = QPushButton("− Ukloni vozilo")
        del_v.clicked.connect(lambda: self.vozila.removeRow(self.vozila.currentRow()))
        vbtn = QHBoxLayout()
        vbtn.addWidget(add_v)
        vbtn.addWidget(del_v)
        vbtn.addStretch()

        form = QFormLayout()
        form.addRow("Naziv:", self.naziv)
        form.addRow("Tip stakla:", self.tip)
        form.addRow("Senzor:", self._row(self.senzor, self.senzor_opis))
        form.addRow("Kamera:", self._row(self.kamera, self.kamera_opis))
        form.addRow("Pločica retrovizora:", self.plocica)
        form.addRow("", self.polovno)
        form.addRow("Napomena:", self.napomena)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Sačuvaj")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("Otkaži")
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(self._label("Za koja vozila odgovara (nije obavezno):"))
        lay.addWidget(self.vozila)
        lay.addLayout(vbtn)
        lay.addWidget(bb)

        if staklo_id:
            self._load(repo.get_staklo(conn, staklo_id))

    @staticmethod
    def _row(*widgets) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        for x in widgets:
            h.addWidget(x)
        return w

    @staticmethod
    def _label(text):
        from PySide6.QtWidgets import QLabel
        return QLabel(text)

    def _add_vozilo(self, v: Vozilo) -> None:
        r = self.vozila.rowCount()
        self.vozila.insertRow(r)
        for c, val in enumerate((v.marka, v.model, v.generacija, v.godina_od, v.godina_do)):
            self.vozila.setItem(r, c, QTableWidgetItem("" if val is None else str(val)))

    def _load(self, s: Staklo) -> None:
        self.naziv.setText(s.naziv)
        self.tip.setCurrentIndex(max(0, self.tip.findData(s.tip)))
        self.senzor.setChecked(s.senzor)
        self.senzor_opis.setText(s.senzor_opis or "")
        self.kamera.setChecked(s.kamera)
        self.kamera_opis.setText(s.kamera_opis or "")
        self.plocica.setCurrentText(s.plocica or "")
        self.polovno.setChecked(s.polovno)
        self.napomena.setText(s.napomena or "")
        for v in s.vozila:
            self._add_vozilo(v)

    def _cell(self, r, c) -> str:
        it = self.vozila.item(r, c)
        return it.text().strip() if it else ""

    def _collect(self) -> Staklo:
        vozila = []
        for r in range(self.vozila.rowCount()):
            vals = [self._cell(r, c) for c in range(5)]
            if not any(vals):
                continue
            vozila.append(Vozilo(vals[0], vals[1] or None, vals[2] or None,
                                 _int_or_none(vals[3], "Godina od"), _int_or_none(vals[4], "Godina do")))
        return Staklo(
            naziv=self.naziv.text(), tip=self.tip.currentData(),
            senzor=self.senzor.isChecked() or bool(self.senzor_opis.text().strip()),
            senzor_opis=self.senzor_opis.text(),
            kamera=self.kamera.isChecked() or bool(self.kamera_opis.text().strip()),
            kamera_opis=self.kamera_opis.text(), plocica=self.plocica.currentText(),
            polovno=self.polovno.isChecked(), napomena=self.napomena.text(), vozila=vozila, id=self.staklo_id,
        )

    def _save(self) -> None:
        with user_errors(self):
            s = self._collect()
            if self.staklo_id:
                repo.update_staklo(self.conn, s)
            else:
                self.staklo_id = repo.add_staklo(self.conn, s)
            self.accept()
