"""Glavni ekran: pretraga + filteri + tabela „gde je koje staklo" + dugmad za ulaz/izlaz."""
from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from autostakla import version
from autostakla.lager import repo
from autostakla.lager.repo import Filter
from autostakla.ui.common import fill_combo
from autostakla.ui.kretanje_dialogs import (
    IstorijaDialog,
    IzmeniMestoDialog,
    KolicinaDialog,
    PremestiDialog,
    UlazDialog,
)
from autostakla.ui.staklo_dialog import StakloDialog

DA_NE = [("Svejedno", None), ("Da", True), ("Ne", False)]


class LagerModel(QAbstractTableModel):
    COLS = [("Staklo", "naziv"), ("Kom", "kolicina"), ("Skladište", "skladiste"), ("Polica", "polica"),
            ("Poz.", "pozicija"), ("Senzor", "senzor"), ("Kamera", "kamera"), ("Pločica", "plocica"),
            ("Napomena", "napomena")]

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []

    def set_rows(self, rows):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.rows)

    def columnCount(self, parent=QModelIndex()):
        return len(self.COLS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.COLS[section][0]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        r = self.rows[index.row()]
        key = self.COLS[index.column()][1]
        if role == Qt.ItemDataRole.DisplayRole:
            v = r[key]
            if key == "senzor":
                return (r["senzor_opis"] or "da") if v else ""
            if key == "kamera":
                return (r["kamera_opis"] or "da") if v else ""
            if key == "napomena":
                parts = [r["stavka_napomena"], r["napomena"], "POLOVNO" if r["polovno"] else None]
                return " | ".join(p for p in parts if p)
            return "" if v is None else str(v)
        if role == Qt.ItemDataRole.TextAlignmentRole and key in ("kolicina", "pozicija"):
            return int(Qt.AlignmentFlag.AlignCenter)
        if role == Qt.ItemDataRole.FontRole and key in ("naziv", "kolicina"):
            f = QFont()
            f.setBold(True)
            return f
        if role == Qt.ItemDataRole.ForegroundRole and r["kolicina"] <= 0:
            from PySide6.QtGui import QColor
            return QColor("#999999")
        return None


class LagerView(QWidget):
    def __init__(self, conn, parent=None):
        super().__init__(parent)
        self.conn = conn

        # --- pretraga ---
        self.search = QLineEdit()
        self.search.setPlaceholderText("Pretraga – npr.  golf 5 senzor   ili   pezo 307")
        self.search.setClearButtonEnabled(True)
        f = self.search.font()
        f.setPointSize(14)
        self.search.setFont(f)
        self.search.setMinimumHeight(40)
        self._timer = QTimer(self, singleShot=True, interval=200, timeout=self.refresh)
        self.search.textChanged.connect(lambda _: self._timer.start())

        # --- filteri ---
        self.f_sk = QComboBox()
        self.f_po = QComboBox()
        self.f_tip = QComboBox()
        fill_combo(self.f_tip, [(v, k) for k, v in repo.TIPOVI.items()], first=("Svi tipovi", None))
        self.f_senzor, self.f_kamera, self.f_polovno = QComboBox(), QComboBox(), QComboBox()
        for cb in (self.f_senzor, self.f_kamera, self.f_polovno):
            fill_combo(cb, DA_NE)
        self.f_nula = QCheckBox("prikaži i ono čega nema")
        self.f_sk.currentIndexChanged.connect(self._sk_changed)
        for w in (self.f_po, self.f_tip, self.f_senzor, self.f_kamera, self.f_polovno):
            w.currentIndexChanged.connect(self.refresh)
        self.f_nula.toggled.connect(self.refresh)
        reset = QPushButton("Poništi filtere")
        reset.clicked.connect(self.reset_filters)

        filt = QHBoxLayout()
        for label, w in (("Skladište:", self.f_sk), ("Polica:", self.f_po), ("Tip:", self.f_tip),
                         ("Senzor:", self.f_senzor), ("Kamera:", self.f_kamera), ("Polovno:", self.f_polovno)):
            filt.addWidget(QLabel(label))
            filt.addWidget(w)
        filt.addWidget(self.f_nula)
        filt.addStretch()
        filt.addWidget(reset)

        # --- tabela ---
        self.model = LagerModel()
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        tf = self.table.font()
        tf.setPointSize(11)
        self.table.setFont(tf)
        self.table.verticalHeader().setDefaultSectionSize(28)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        hh.setStretchLastSection(True)  # Napomena dobija sav preostali prostor
        hh.setMinimumSectionSize(50)
        for col, width in enumerate((420, 55, 150, 160, 55, 110, 110, 110)):
            hh.resizeSection(col, width)
        self.table.doubleClicked.connect(lambda _: self.istorija())
        self.table.selectionModel().selectionChanged.connect(self._update_buttons)

        self.info = QLabel()

        # --- dugmad ---
        self.b_ulaz = self._btn("＋  Ulaz", self.ulaz, "Novo staklo ili još komada na lager")
        self.b_izlaz = self._btn("−  Izlaz", self.izlaz, "Staklo je izašlo (prodato, ugrađeno...)")
        self.b_prem = self._btn("⇄  Premesti", self.premesti)
        self.b_kor = self._btn("✎  Ispravi količinu", self.korekcija)
        self.b_mesto = self._btn("Pozicija / napomena…", self.izmeni_mesto,
                                 "Promena pozicije na polici i napomene")
        self.b_staklo = self._btn("Izmeni staklo…", self.izmeni_staklo)
        self.b_ist = self._btn("Istorija", self.istorija)
        btns = QHBoxLayout()
        for b in (self.b_ulaz, self.b_izlaz, self.b_prem, self.b_kor, self.b_mesto):
            btns.addWidget(b)
        btns.addStretch()
        btns.addWidget(self.b_staklo)
        btns.addWidget(self.b_ist)

        lay = QVBoxLayout(self)
        lay.addWidget(self.search)
        lay.addLayout(filt)
        lay.addWidget(self.table, 1)
        lay.addWidget(self.info)
        lay.addLayout(btns)

        self.reload_filters()

    def _btn(self, text, slot, tip=None) -> QPushButton:
        b = QPushButton(text)
        b.setMinimumHeight(38)
        f = b.font()
        f.setPointSize(11)
        b.setFont(f)
        if tip:
            b.setToolTip(tip)
        b.clicked.connect(slot)
        return b

    # ---------- filteri ----------
    def reload_filters(self) -> None:
        fill_combo(self.f_sk, [(s["naziv"], s["id"]) for s in repo.list_skladista(self.conn)],
                   first=("Sva skladišta", None))
        self._sk_changed()

    def _sk_changed(self) -> None:
        sid = self.f_sk.currentData()
        items = [(p["naziv"], p["id"]) for p in repo.list_police(self.conn, sid)] if sid else []
        fill_combo(self.f_po, items, first=("Sve police", None))
        self.f_po.setEnabled(sid is not None)
        self.refresh()

    def reset_filters(self) -> None:
        for cb in (self.f_sk, self.f_tip, self.f_senzor, self.f_kamera, self.f_polovno):
            cb.setCurrentIndex(0)
        self.f_nula.setChecked(False)
        self.search.clear()
        self.refresh()

    def current_filter(self) -> Filter:
        return Filter(
            tekst=self.search.text(), skladiste_id=self.f_sk.currentData(), polica_id=self.f_po.currentData(),
            tip=self.f_tip.currentData(), senzor=self.f_senzor.currentData(),
            kamera=self.f_kamera.currentData(), polovno=self.f_polovno.currentData(),
            samo_na_stanju=not self.f_nula.isChecked(),
        )

    def refresh(self, *_args, select_stavka: int | None = None) -> None:
        keep = select_stavka or (self.selected() or {}).get("lager_stavka_id")
        rows = repo.pretraga(self.conn, self.current_filter())
        self.model.set_rows(rows)
        self.info.setText(f"Pronađeno: <b>{len(rows)}</b> mesta, ukupno <b>{sum(r['kolicina'] for r in rows)}</b> kom")
        if keep:
            for i, r in enumerate(rows):
                if r["lager_stavka_id"] == keep:
                    self.table.selectRow(i)
                    break
        self._update_buttons()

    # ---------- izbor ----------
    def selected(self) -> dict | None:
        idx = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        return self.model.rows[idx[0].row()] if idx else None

    def _update_buttons(self, *_args) -> None:
        r = self.selected()
        for b in (self.b_prem, self.b_kor, self.b_mesto, self.b_staklo, self.b_ist):
            b.setEnabled(r is not None)
        self.b_izlaz.setEnabled(r is not None and r["kolicina"] > 0)
        self.b_prem.setEnabled(r is not None and r["kolicina"] > 0)

    # ---------- akcije ----------
    def ulaz(self) -> None:
        r = self.selected()
        dialog = UlazDialog
        if version.is_better():
            from autostakla.ui.better.kretanje import UlazBetterDialog as dialog
        d = dialog(self, self.conn,
                   staklo_id=r["staklo_id"] if r else None,
                   skladiste_id=r["skladiste_id"] if r else self.f_sk.currentData(),
                   polica_id=r["polica_id"] if r else self.f_po.currentData(),
                   pozicija=(r["pozicija"] + 1) if (r and r["pozicija"]) else None)  # odmah ispod izabranog
        if d.exec():
            self.refresh()

    def izmeni_mesto(self) -> None:
        r = self.selected()
        if r and IzmeniMestoDialog(self, self.conn, r).exec():
            self.refresh()

    def izlaz(self) -> None:
        r = self.selected()
        if not r:
            return
        if version.is_better():
            from autostakla.ui.better.kretanje import IzlazDialog
            d = IzlazDialog(self, self.conn, r)
        else:
            d = KolicinaDialog(self, self.conn, r, "izlaz")
        if d.exec():
            self.refresh()

    def korekcija(self) -> None:
        r = self.selected()
        if r and KolicinaDialog(self, self.conn, r, "korekcija").exec():
            self.refresh()

    def premesti(self) -> None:
        r = self.selected()
        if r and PremestiDialog(self, self.conn, r).exec():
            self.refresh()

    def izmeni_staklo(self) -> None:
        r = self.selected()
        if r and StakloDialog(self, self.conn, r["staklo_id"]).exec():
            self.refresh()

    def istorija(self) -> None:
        r = self.selected()
        if r:
            IstorijaDialog(self, self.conn, r).exec()
