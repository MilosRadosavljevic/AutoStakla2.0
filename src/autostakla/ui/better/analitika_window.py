"""Analitika: pokazatelji sa poređenjem, po mesecima, stakla, vozila, šta stoji, predlog nabavke, reklamacije."""
from __future__ import annotations

from datetime import date, timedelta

from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from autostakla.better import analitika, novac
from autostakla.core import audit
from autostakla.lager import stampa
from autostakla.ui.better.common import datum_edit, iso, otvori, popuni, stampa_fajl, tabela
from autostakla.ui.better.grafikon import Stubici


def _kratko(din: int) -> str:
    return f"{din // 1000}k" if abs(din) >= 10000 else str(din)


class AnalitikaDialog(QDialog):
    POKAZATELJI = [("Prodaja", "broj_prodaja", str), ("Komada", "komada", str), ("Promet sa PDV", "promet", novac.fmt),
                   ("Promet bez PDV", "promet_bez_pdv", novac.fmt), ("Zarada", "zarada", novac.fmt),
                   ("Marža", "marza", str), ("Prosečna prodaja", "prosecna_prodaja", novac.fmt),
                   ("Razbijeno (kom)", "razbijeno", str), ("Reklamacija", "reklamacija", str),
                   ("Trošak reklamacija", "reklamacija_trosak", novac.fmt)]

    def __init__(self, parent, conn):
        super().__init__(parent)
        self.conn = conn
        self.setWindowTitle("Analitika")
        danas = date.today()
        self.od = datum_edit(danas.replace(month=1, day=1))
        self.do = datum_edit(danas)
        top = QHBoxLayout()
        top.addWidget(QLabel("Od:"))
        top.addWidget(self.od)
        top.addWidget(QLabel("do:"))
        top.addWidget(self.do)
        for text, od in (("Ovaj mesec", danas.replace(day=1)), ("Ova godina", danas.replace(month=1, day=1)),
                         ("Poslednjih 12 meseci", danas - timedelta(days=364))):
            b = QPushButton(text)
            b.clicked.connect(lambda _=False, d=od: self._period(d, danas))
            top.addWidget(b)
        prikazi = QPushButton("Prikaži")
        prikazi.clicked.connect(self.refresh)
        top.addWidget(prikazi)
        top.addStretch(1)

        self.kpi = QGridLayout()
        self.kpi_labels = []
        for i, (naziv, _, _) in enumerate(self.POKAZATELJI):
            v, pr = QLabel(), QLabel()
            pr.setStyleSheet("color: gray")
            box = QVBoxLayout()
            box.addWidget(QLabel(naziv))
            box.addWidget(v)
            box.addWidget(pr)
            self.kpi.addLayout(box, i // 5, i % 5)
            self.kpi_labels.append((v, pr))
        self.napomena = QLabel()
        self.napomena.setStyleSheet("color: gray")

        self.tabs = QTabWidget()
        self.graf_mesec = Stubici("Promet po mesecima (sa PDV-om)")
        self.t_mesec = tabela(["Mesec", "Kom", "Promet", "Zarada"])
        self.t_stakla = tabela(["Staklo", "Kom", "Promet", "Zarada"], stretch=0)
        self.graf_vozila = Stubici("Najčešća vozila (komada)")
        self.t_vozila = tabela(["Vozilo", "Kom", "Promet"], stretch=0)
        self.dana_stoje = QSpinBox()
        self.dana_stoje.setRange(30, 3650)
        self.dana_stoje.setValue(180)
        self.dana_stoje.setSuffix(" dana")
        self.dana_stoje.valueChanged.connect(self.refresh)
        self.t_stoje = tabela(["Staklo", "Kom", "Dana na lageru", "Poslednja prodaja", "Skladište"], stretch=0)
        self.dana_nab = QSpinBox()
        self.dana_nab.setRange(7, 365)
        self.dana_nab.setValue(90)
        self.dana_nab.setSuffix(" dana")
        self.dana_nab.valueChanged.connect(self.refresh)
        self.t_nabavka = tabela(["Staklo", "Prodato", "Na stanju", "Naručiti", "Najjeftiniji dobavljač",
                                 "Cena bez PDV"], stretch=0)
        self.t_rekl = tabela(["Dobavljač", "Reklamacija", "Trošak"], stretch=0)
        self.tabs.addTab(self._strana(self.graf_mesec, self.t_mesec), "Po mesecima")
        self.tabs.addTab(self._strana(self.t_stakla), "Najprodavanija stakla")
        self.tabs.addTab(self._strana(self.graf_vozila, self.t_vozila), "Vozila")
        self.tabs.addTab(self._strana(self._red("Na lageru duže od:", self.dana_stoje), self.t_stoje), "Šta stoji")
        self.tabs.addTab(self._strana(self._red("Prodaja u poslednjih:", self.dana_nab), self.t_nabavka),
                         "Predlog nabavke")
        self.tabs.addTab(self._strana(self.t_rekl), "Reklamacije")

        excel = QPushButton("Izvoz u Excel")
        excel.clicked.connect(self.izvoz_excel)
        pdf = QPushButton("PDF")
        pdf.clicked.connect(self.izvoz_pdf)
        zatvori = QPushButton("Zatvori")
        zatvori.clicked.connect(self.accept)
        dole = QHBoxLayout()
        dole.addWidget(self.napomena, 1)
        for b in (excel, pdf, zatvori):
            dole.addWidget(b)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addLayout(self.kpi)
        lay.addWidget(self.tabs, 1)
        lay.addLayout(dole)
        self.resize(1200, 800)
        self.refresh()

    @staticmethod
    def _red(tekst: str, w: QWidget) -> QWidget:
        box = QWidget()
        lay = QHBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(tekst))
        lay.addWidget(w)
        lay.addStretch(1)
        return box

    @staticmethod
    def _strana(*widgets: QWidget) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        for w in widgets:
            lay.addWidget(w, 1 if isinstance(w, QTableWidget) else 0)  # višak visine dobija samo tabela
        return page

    def _period(self, od: date, do: date) -> None:
        self.od.setDate(od)
        self.do.setDate(do)
        self.refresh()

    def refresh(self, *_args) -> None:
        od, do = iso(self.od), iso(self.do)
        p_od, p_do = analitika.prethodni_period(od, do)
        k, pk = analitika.kpi(self.conn, od, do), analitika.kpi(self.conn, p_od, p_do)
        for (v, pr), (_, attr, fmt) in zip(self.kpi_labels, self.POKAZATELJI):
            v.setText(f"<b style='font-size:14pt'>{fmt(getattr(k, attr))}</b>")
            pr.setText(f"prethodni: {fmt(getattr(pk, attr))}")
        self.napomena.setText(f"Prethodni period: {p_od} – {p_do}. Zarada = prodaja bez PDV-a − prosečna nabavna."
                              + (f"  Prodaja bez poznate nabavne cene: {k.bez_nabavne}." if k.bez_nabavne else ""))

        mes = analitika.po_mesecima(self.conn, od, do)
        self.graf_mesec.postavi([(m["mesec"], m["promet"]) for m in mes], _kratko)
        popuni(self.t_mesec, [[m["mesec"], m["kom"], novac.fmt(m["promet"]), novac.fmt(m["zarada"])] for m in mes],
               desno=(1, 2, 3))
        popuni(self.t_stakla, [[r["naziv"], r["kom"], novac.fmt(r["promet"]), novac.fmt(r["zarada"])]
                               for r in analitika.top_stakla(self.conn, od, do, 50)], desno=(1, 2, 3))
        voz = analitika.top_vozila(self.conn, od, do, 50)
        self.graf_vozila.postavi([(r["naziv"], r["kom"]) for r in voz[:10]])
        popuni(self.t_vozila, [[r["naziv"], r["kom"], novac.fmt(r["promet"])] for r in voz], desno=(1, 2))
        popuni(self.t_stoje, [[r["naziv"], r["kom"], r["dana"], (r["poslednja_prodaja"] or "nikad")[:10],
                               r["skladista"]] for r in analitika.stakla_koja_stoje(self.conn, self.dana_stoje.value())],
               desno=(1, 2))
        nab = analitika.predlog_nabavke(self.conn, self.dana_nab.value())
        popuni(self.t_nabavka, [[r["naziv"], r["prodato"], r["na_stanju"], r["predlog"], r["dobavljac"] or "–",
                                 novac.fmt(r["cena"]) if r["cena"] is not None else "–"] for r in nab],
               desno=(1, 2, 3, 5), bold={i for i, r in enumerate(nab) if r["predlog"] > 0})
        popuni(self.t_rekl, [[r["dobavljac"], r["broj"], novac.fmt(r["trosak"])]
                             for r in analitika.reklamacije_po_dobavljacu(self.conn, od, do)], desno=(1, 2))

    def izvoz_excel(self) -> None:
        target = analitika.izvoz_excel(self.conn, iso(self.od), iso(self.do), stampa_fajl("Analitika", "xlsx"))
        audit.write(self.conn, "STAMPA", opis=f"Analitika Excel → {target.name}")
        otvori(self, target)

    def izvoz_pdf(self) -> None:
        target = stampa.write_pdf(analitika.html_izvestaj(self.conn, iso(self.od), iso(self.do)),
                                  stampa_fajl("Analitika"), "Analitika prodaje")
        audit.write(self.conn, "STAMPA", opis=f"Analitika PDF → {target.name}")
        otvori(self, target)
