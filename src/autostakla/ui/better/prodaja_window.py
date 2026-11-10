"""Prodaja po periodu i reklamacije."""
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
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from autostakla.better import dokumenti, nabavka, novac, prodaja, reklamacije
from autostakla.better.reklamacije import ISHODI, PRELAZI, STATUSI
from autostakla.ui.better.common import (
    datum_edit,
    dugmad,
    iso,
    iznos_edit,
    izabrano,
    otvori,
    popuni,
    stampa_folder,
    tabela,
)
from autostakla.ui.common import fill_combo, user_errors


class ProdajaDialog(QDialog):
    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("Prodaja")
        danas = date.today()
        self.od = datum_edit(danas.replace(day=1))
        self.do = datum_edit(danas)
        self.trazi = QLineEdit()
        self.trazi.setPlaceholderText("kupac, tablice, staklo, vozilo…")
        prikazi = QPushButton("Prikaži")
        prikazi.clicked.connect(self.refresh)
        self.trazi.returnPressed.connect(self.refresh)
        top = QHBoxLayout()
        for w in (QLabel("Od:"), self.od, QLabel("do:"), self.do, self.trazi, prikazi):
            top.addWidget(w, 1 if w is self.trazi else 0)

        self.t = tabela(["Datum", "Staklo", "Kom", "Cena", "Ukupno", "Kupac", "Telefon", "Vozilo", "Tablice",
                         "Ugradnja", "Napomena"], stretch=10)
        self.zbir = QLabel()
        b_ot = QPushButton("Otpremnica (PDF)")
        b_ot.clicked.connect(self.otpremnica)
        b_rek = QPushButton("Prijavi reklamaciju…")
        b_rek.clicked.connect(self.reklamacija)
        zatvori = QPushButton("Zatvori")
        zatvori.clicked.connect(self.accept)
        dole = QHBoxLayout()
        dole.addWidget(self.zbir, 1)
        for b in (b_ot, b_rek, zatvori):
            dole.addWidget(b)
        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.t)
        lay.addLayout(dole)
        self.resize(1200, 640)
        self.refresh()

    def refresh(self) -> None:
        rows = prodaja.list_prodaja(self.conn, iso(self.od), iso(self.do), self.trazi.text())
        popuni(self.t, [[r["datum"][:16], r["staklo"], r["kom"], novac.fmt(r["cena"]), novac.fmt(r["ukupno"]),
                         r["kupac"], r["telefon"], r["vozilo"], r["tablice"], "da" if r["sa_ugradnjom"] else "",
                         r["napomena"]] for r in rows], [r["id"] for r in rows], desno=(2, 3, 4))
        self.zbir.setText(f"Prodaja: <b>{len(rows)}</b>, komada: <b>{sum(r['kom'] for r in rows)}</b>, "
                          f"ukupno: <b>{novac.fmt(sum(r['ukupno'] for r in rows))}</b> (sa PDV-om)")

    def _izabrana(self) -> int | None:
        pid = izabrano(self.t)
        if pid is None:
            QMessageBox.information(self, "Prodaja", "Izaberite prodaju u tabeli.")
        return pid

    def otpremnica(self) -> None:
        pid = self._izabrana()
        if pid is not None:
            with user_errors(self):
                did = dokumenti.otpremnica_za_prodaju(self.conn, pid)
                otvori(self, dokumenti.pdf(self.conn, did, stampa_folder()))

    def reklamacija(self) -> None:
        pid = self._izabrana()
        if pid is not None and NovaReklamacijaDialog(self, self.conn, pid).exec():
            QMessageBox.information(self, "Reklamacija", "Reklamacija je prijavljena (Poslovanje → Reklamacije).")


class NovaReklamacijaDialog(QDialog):
    def __init__(self, parent, conn, prodaja_id: int):
        super().__init__(parent)
        self.conn, self.prodaja_id = conn, prodaja_id
        p = prodaja.get_prodaja(conn, prodaja_id)
        self.setWindowTitle("Nova reklamacija")
        self.opis = QPlainTextEdit()
        self.opis.setPlaceholderText("šta je problem (pukotina, curi, senzor ne radi…)")
        self.dobavljac = QComboBox()
        fill_combo(self.dobavljac, [(d["naziv"], d["id"]) for d in nabavka.list_dobavljaci(conn, False)],
                   keep=False, first=("(nepoznat)", None))
        self.dobavljac.setCurrentIndex(max(0, self.dobavljac.findData(reklamacije.dobavljac_za_prodaju(conn, prodaja_id))))
        form = QFormLayout(self)
        form.addRow(QLabel(f"<b>{p['staklo']}</b><br>Prodato {p['datum'][:10]}"
                           + (f", {p['kupac']}" if p["kupac"] else "") + (f", {p['tablice']}" if p["tablice"] else "")))
        form.addRow("Opis:", self.opis)
        form.addRow("Dobavljač stakla:", self.dobavljac)
        bb = dugmad(self, "Prijavi")
        bb.accepted.connect(self._save)
        form.addRow(bb)
        self.resize(520, 300)

    def _save(self) -> None:
        with user_errors(self):
            self.reklamacija_id = reklamacije.nova(self.conn, self.prodaja_id, self.opis.toPlainText(),
                                                   self.dobavljac.currentData())
            self.accept()


class ReklamacijeDialog(QDialog):
    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("Reklamacije")
        self.otvorene = QCheckBox("samo otvorene")
        self.otvorene.setChecked(True)
        self.otvorene.toggled.connect(self.refresh)
        self.t = tabela(["Prijavljena", "Staklo", "Kupac", "Tablice", "Dobavljač", "Status", "Ishod", "Trošak",
                         "Opis"], stretch=8)
        b_status = QPushButton("Promeni status…")
        b_status.clicked.connect(self.status)
        b_ist = QPushButton("Istorija")
        b_ist.clicked.connect(self.istorija)
        zatvori = QPushButton("Zatvori")
        zatvori.clicked.connect(self.accept)
        dole = QHBoxLayout()
        dole.addWidget(self.otvorene, 1)
        for b in (b_status, b_ist, zatvori):
            dole.addWidget(b)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("<i>Nova reklamacija se prijavljuje iz prozora Prodaja (izaberite prodaju).</i>"))
        lay.addWidget(self.t)
        lay.addLayout(dole)
        self.resize(1150, 560)
        self.refresh()

    def refresh(self, *_args) -> None:
        rows = reklamacije.list_reklamacije(self.conn, self.otvorene.isChecked())
        popuni(self.t, [[r["datum_prijave"], r["staklo"], r["kupac"], r["tablice"], r["dobavljac"],
                         STATUSI[r["status"]], ISHODI.get(r["ishod"], ""), novac.fmt(r["trosak"]) if r["trosak"] else "",
                         r["opis"]] for r in rows], [r["id"] for r in rows], desno=(7,))

    def _izabrana(self) -> int | None:
        rid = izabrano(self.t)
        if rid is None:
            QMessageBox.information(self, "Reklamacije", "Izaberite reklamaciju u tabeli.")
        return rid

    def status(self) -> None:
        rid = self._izabrana()
        if rid is None:
            return
        r = reklamacije.get(self.conn, rid)
        if not PRELAZI[r["status"]]:
            QMessageBox.information(self, "Reklamacije", f"Reklamacija je zatvorena ({STATUSI[r['status']]}).")
            return
        if StatusDialog(self, self.conn, r).exec():
            self.refresh()

    def istorija(self) -> None:
        rid = self._izabrana()
        if rid is not None:
            tekst = "\n".join(f"{h['vreme'][:16]}  {h['opis']}" for h in reklamacije.istorija(self.conn, rid))
            QMessageBox.information(self, "Istorija reklamacije", tekst or "Nema zapisa.")


class StatusDialog(QDialog):
    def __init__(self, parent, conn, r: dict):
        super().__init__(parent)
        self.conn, self.r = conn, r
        self.setWindowTitle("Status reklamacije")
        self.status = QComboBox()
        fill_combo(self.status, [(STATUSI[s], s) for s in PRELAZI[r["status"]]], keep=False)
        self.ishod = QComboBox()
        fill_combo(self.ishod, [(t, k) for k, t in ISHODI.items()], keep=False, first=("(nije određen)", None))
        self.ishod.setCurrentIndex(max(0, self.ishod.findData(r["ishod"])))
        self.trosak = iznos_edit("0")
        if r["trosak"]:
            self.trosak.setText(str(r["trosak"]))
        self.napomena = QLineEdit(r["napomena"] or "")
        form = QFormLayout(self)
        form.addRow(QLabel(f"<b>{r['staklo']}</b><br>{r['opis']}<br>Sada: <b>{STATUSI[r['status']]}</b>"))
        form.addRow("Novi status:", self.status)
        form.addRow("Ishod:", self.ishod)
        form.addRow("Trošak (dinari):", self.trosak)
        form.addRow("Napomena:", self.napomena)
        form.addRow(QLabel("<i>Zamenu stakla, povrat od kupca i slanje dobavljaču upišite kao izlaz/ulaz sa "
                           "odgovarajućim razlogom.</i>"))
        bb = dugmad(self, "Sačuvaj")
        bb.accepted.connect(self._save)
        form.addRow(bb)
        self.resize(500, 320)

    def _save(self) -> None:
        with user_errors(self):
            trosak = novac.parse(self.trosak.text(), "Trošak") if self.trosak.text().strip() else 0
            reklamacije.promeni_status(self.conn, self.r["id"], self.status.currentData(), self.ishod.currentData(),
                                       trosak, self.napomena.text())
            self.accept()
