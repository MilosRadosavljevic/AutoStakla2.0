"""Šifarnik: skladišta (levo) i njihove police (desno) – dodaj, izmeni, obriši, redosled."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from autostakla.lager import repo
from autostakla.ui.common import confirm, user_errors


class NazivOpisDialog(QDialog):
    def __init__(self, parent, title: str, naziv: str = "", opis: str | None = ""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.naziv = QLineEdit(naziv)
        self.opis = QPlainTextEdit(opis or "")
        self.opis.setFixedHeight(80)
        form = QFormLayout(self)
        form.addRow("Naziv:", self.naziv)
        form.addRow("Opis:", self.opis)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText("Sačuvaj")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText("Otkaži")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)
        self.resize(420, 200)

    def values(self) -> tuple[str, str]:
        return self.naziv.text(), self.opis.toPlainText()


class SkladistaDialog(QDialog):
    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self.changed = False
        self.setWindowTitle("Skladišta i police")
        self.resize(820, 520)

        self.lst_sk = QListWidget()
        self.lst_po = QListWidget()
        self.lst_sk.currentRowChanged.connect(self._load_police)
        self.lst_sk.itemDoubleClicked.connect(lambda _: self._edit_sk())
        self.lst_po.itemDoubleClicked.connect(lambda _: self._edit_po())

        lay = QHBoxLayout()
        lay.addWidget(self._group("Skladišta", self.lst_sk, self._add_sk, self._edit_sk, self._del_sk,
                                  lambda: self._move_sk(-1), lambda: self._move_sk(1)))
        lay.addWidget(self._group("Police izabranog skladišta", self.lst_po, self._add_po, self._edit_po,
                                  self._del_po, lambda: self._move_po(-1), lambda: self._move_po(1)))
        close = QPushButton("Zatvori")
        close.clicked.connect(self.accept)
        main = QVBoxLayout(self)
        main.addLayout(lay)
        main.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
        self._load_sk()

    def _group(self, title, lst, add, edit, delete, up, down) -> QGroupBox:
        g = QGroupBox(title)
        btns = QVBoxLayout()
        for text, fn in (("Dodaj…", add), ("Izmeni…", edit), ("Obriši", delete), ("▲ Gore", up), ("▼ Dole", down)):
            b = QPushButton(text)
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch()
        h = QHBoxLayout(g)
        h.addWidget(lst)
        h.addLayout(btns)
        return g

    # ---------- učitavanje ----------
    def _load_sk(self, select_id: int | None = None) -> None:
        cur = select_id or self._sel(self.lst_sk)
        self.lst_sk.clear()
        for s in repo.list_skladista(self.conn):
            it = QListWidgetItem(s["naziv"] + (f"   – {s['opis']}" if s["opis"] else ""))
            it.setData(Qt.ItemDataRole.UserRole, s["id"])
            self.lst_sk.addItem(it)
        self._select(self.lst_sk, cur)
        self._load_police()

    def _load_police(self, *_args, select_id: int | None = None) -> None:
        cur = select_id or self._sel(self.lst_po)
        self.lst_po.clear()
        sid = self._sel(self.lst_sk)
        if sid is None:
            return
        for p in repo.list_police(self.conn, sid):
            it = QListWidgetItem(p["naziv"] + (f"   – {p['opis']}" if p["opis"] else ""))
            it.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.lst_po.addItem(it)
        self._select(self.lst_po, cur)

    @staticmethod
    def _sel(lst: QListWidget):
        it = lst.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else None

    @staticmethod
    def _select(lst: QListWidget, item_id) -> None:
        for i in range(lst.count()):
            if lst.item(i).data(Qt.ItemDataRole.UserRole) == item_id:
                lst.setCurrentRow(i)
                return
        if lst.count():
            lst.setCurrentRow(0)

    # ---------- skladišta ----------
    def _add_sk(self) -> None:
        d = NazivOpisDialog(self, "Novo skladište")
        if d.exec():
            with user_errors(self):
                sid = repo.add_skladiste(self.conn, *d.values())
                self.changed = True
                self._load_sk(sid)

    def _edit_sk(self) -> None:
        sid = self._sel(self.lst_sk)
        if sid is None:
            return
        s = repo.get_skladiste(self.conn, sid)
        d = NazivOpisDialog(self, "Izmena skladišta", s["naziv"], s["opis"])
        if d.exec():
            with user_errors(self):
                repo.update_skladiste(self.conn, sid, *d.values())
                self.changed = True
                self._load_sk(sid)

    def _del_sk(self) -> None:
        sid = self._sel(self.lst_sk)
        if sid is None:
            return
        s = repo.get_skladiste(self.conn, sid)
        if confirm(self, "Brisanje", f"Obrisati skladište „{s['naziv']}“ i sve njegove police?"):
            with user_errors(self):
                r = repo.delete_skladiste(self.conn, sid)
                self.changed = True
                self._load_sk()
                if r == "ugaseno":
                    QMessageBox.information(self, "Brisanje",
                                            "Skladište je uklonjeno iz rada. Istorija stakala je sačuvana.")

    def _move_sk(self, smer: int) -> None:
        sid = self._sel(self.lst_sk)
        if sid is not None:
            repo.move_skladiste(self.conn, sid, smer)
            self.changed = True
            self._load_sk(sid)

    # ---------- police ----------
    def _add_po(self) -> None:
        sid = self._sel(self.lst_sk)
        if sid is None:
            QMessageBox.information(self, "Police", "Prvo izaberite skladište.")
            return
        d = NazivOpisDialog(self, "Nova polica", f"Polica {self.lst_po.count() + 1}")
        if d.exec():
            with user_errors(self):
                pid = repo.add_polica(self.conn, sid, *d.values())
                self.changed = True
                self._load_police(select_id=pid)

    def _edit_po(self) -> None:
        pid = self._sel(self.lst_po)
        if pid is None:
            return
        p = repo.get_polica(self.conn, pid)
        d = NazivOpisDialog(self, "Izmena police", p["naziv"], p["opis"])
        if d.exec():
            with user_errors(self):
                repo.update_polica(self.conn, pid, *d.values())
                self.changed = True
                self._load_police(select_id=pid)

    def _del_po(self) -> None:
        pid = self._sel(self.lst_po)
        if pid is None:
            return
        p = repo.get_polica(self.conn, pid)
        if confirm(self, "Brisanje", f"Obrisati policu „{p['naziv']}“?"):
            with user_errors(self):
                repo.delete_polica(self.conn, pid)
                self.changed = True
                self._load_police()

    def _move_po(self, smer: int) -> None:
        pid = self._sel(self.lst_po)
        if pid is not None:
            repo.move_polica(self.conn, pid, smer)
            self.changed = True
            self._load_police(select_id=pid)
