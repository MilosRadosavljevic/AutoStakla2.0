"""Snimci ekrana za dokumentaciju (svetla tema) -> dokumentacija/slike/*.png

Upotreba: .venv\\Scripts\\python.exe tools\\docs\\snimci.py
Radi nad privremenom bazom sa početnim stanjem; ništa ne dira pravu bazu.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT / "dokumentacija" / "slike"
ROOT = Path(tempfile.mkdtemp(prefix="autostakla_docs_"))
os.environ["AUTOSTAKLA_ROOT"] = str(ROOT)
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"  # iste veličine slika bez obzira na skaliranje ekrana
sys.path.insert(0, str(PROJECT / "src"))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from autostakla.core import paths  # noqa: E402
from autostakla.lager import repo, stampa  # noqa: E402
from autostakla.main import open_database  # noqa: E402
from autostakla.ui import kretanje_dialogs as kd  # noqa: E402
from autostakla.ui.main_window import MainWindow, StampaDialog  # noqa: E402
from autostakla.ui.skladista_dialog import NazivOpisDialog, SkladistaDialog  # noqa: E402
from autostakla.ui.staklo_dialog import StakloDialog  # noqa: E402

app = QApplication([])
app.styleHints().setColorScheme(Qt.ColorScheme.Light)
paths.ensure_dirs()
conn = open_database()
OUT.mkdir(parents=True, exist_ok=True)


def save(widget, name: str, adjust: bool = False) -> Path:
    if adjust:
        widget.adjustSize()
    p = OUT / f"{name}.png"
    widget.grab().save(str(p))
    return p


def annotate(src: Path, marks: list[tuple[int, int, str]], dst: str, boxes=()) -> None:
    """Crveni numerisani krugovi (x, y, tekst) i okviri (x1, y1, x2, y2) na slici."""
    img = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arialbd.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for b in boxes:
        d.rectangle(b, outline=(220, 30, 30), width=4)
    for x, y, t in marks:
        r = 18
        d.ellipse((x - r, y - r, x + r, y + r), fill=(220, 30, 30), outline=(255, 255, 255), width=3)
        d.text((x, y), t, fill="white", font=font, anchor="mm")
    img.save(OUT / f"{dst}.png")


# ---------- glavni ekran ----------
w = MainWindow(conn)
w.resize(1400, 820)
v = w.lager
w.show()
app.processEvents()
p = save(w, "01_glavni_ekran")
def rect_of(*widgets, pad=3):
    """Okvir oko widget-a (u pikselima slike, uz skaliranje ekrana)."""
    from PySide6.QtCore import QPoint
    dpr = Image.open(p).size[0] / w.width()
    xs, ys = [], []
    for wd in widgets:
        tl = wd.mapTo(w, QPoint(0, 0))
        xs += [tl.x(), tl.x() + wd.width()]
        ys += [tl.y(), tl.y() + wd.height()]
    return tuple(int(c * dpr) for c in (min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad))


regions = [
    rect_of(v.search),
    rect_of(v.f_sk, v.f_nula, v.f_po, next(b for b in v.findChildren(type(v.b_ulaz)) if "Poništi" in b.text())),
    rect_of(v.table),
    rect_of(v.b_ulaz, v.b_mesto),
    rect_of(v.b_staklo, v.b_ist),
    None,
]
regions[1] = (4,) + regions[1][1:]   # ceo red, uključujući natpis „Skladište:"
# meni: samo deo sa natpisima
mb = w.menuBar()
last = mb.actions()[-1]
dpr = Image.open(p).size[0] / w.width()
regions[5] = (0, 0, int((mb.actionGeometry(last).right() + 6) * dpr), int((mb.height() + 2) * dpr))
r_ = 22 * dpr
marks = [
    (regions[0][2] - r_ * 1.6, (regions[0][1] + regions[0][3]) / 2, "1"),
    ((rect_of(v.f_nula)[2] + rect_of(next(b for b in v.findChildren(type(v.b_ulaz))
                                           if "Poništi" in b.text()))[0]) / 2,
     (regions[1][1] + regions[1][3]) / 2, "2"),
    (regions[2][2] - r_ * 1.6, regions[2][1] + r_ * 3, "3"),
    (regions[3][2] + r_ * 1.4, (regions[3][1] + regions[3][3]) / 2, "4"),
    (regions[4][0] - r_ * 1.4, (regions[4][1] + regions[4][3]) / 2, "5"),
    (regions[5][2] + r_ * 1.4, (regions[5][1] + regions[5][3]) / 2, "6"),
]
annotate(p, [(int(x), int(y), t) for x, y, t in marks], "01_glavni_ekran_oznake", boxes=regions)

v.search.setText("golf 5 senzor")
v.refresh()
v.table.selectRow(0)
app.processEvents()
save(w, "02_pretraga_golf5")

v.search.clear()
v.f_sk.setCurrentIndex(v.f_sk.findText("Dvorište"))
v.f_po.setCurrentIndex(v.f_po.findText("I deo"))
v.refresh()
v.table.selectRow(1)
app.processEvents()
save(w, "03_filter_skladiste")
row = v.selected()

# ---------- dijalozi ----------
d = kd.UlazDialog(w, conn, staklo_id=repo.find_staklo_by_naziv(conn, "VW Touran 03-10 BEZ PLOČICE"),
                  skladiste_id=row["skladiste_id"], polica_id=row["polica_id"], pozicija=row["pozicija"] + 1)
d.kolicina.setValue(2)
d.resize(640, 330)
save(d, "04_ulaz")

sd = StakloDialog(w, conn, naziv="VW Golf 7 17-19 SENZOR")
sd.senzor.setChecked(True)
sd.senzor_opis.setText("krug")
sd._add_vozilo(repo.Vozilo("VW", "Golf", "7", 2017, 2019))
sd.resize(640, 560)
save(sd, "05_novo_staklo")

v.reset_filters()
v.search.setText("ford focus")
v.refresh()
v.table.selectRow(0)
r_focus = v.selected()
for mode, name in (("izlaz", "06_izlaz"), ("korekcija", "07_ispravka")):
    kdlg = kd.KolicinaDialog(w, conn, r_focus, mode)
    kdlg.resize(480, 220)
    save(kdlg, name)
pd = kd.PremestiDialog(w, conn, r_focus)
pd.resize(560, 360)
save(pd, "08_premesti")

v.search.setText("golf 7 17")
v.refresh()
v.table.selectRow(0)
r_golf7 = v.selected()
md = kd.IzmeniMestoDialog(w, conn, r_golf7)
md.resize(560, 300)
save(md, "09_pozicija_napomena")

# istorija sa par kretanja
repo.izlaz(conn, r_focus["lager_stavka_id"], 1, "ugrađeno – kupac")
repo.korekcija(conn, r_focus["lager_stavka_id"], 3, "prebrojano")
r_focus = [r for r in repo.pretraga(conn, repo.Filter("ford focus")) if r["lager_stavka_id"] == r_focus["lager_stavka_id"]][0]
ist = kd.IstorijaDialog(w, conn, r_focus)
ist.resize(680, 300)
save(ist, "10_istorija")

sk = SkladistaDialog(w, conn)
sk.lst_sk.setCurrentRow(6)
sk.resize(900, 520)
save(sk, "11_skladista_police")
nd = NazivOpisDialog(w, "Novo skladište", "Garaža", "levo od kapije")
nd.resize(440, 210)
save(nd, "12_novo_skladiste")

st = StampaDialog(w, conn)
st.resize(380, 470)
save(st, "13_stampa_izbor")

# ---------- meniji ----------
for title, name in (("&Alati", "14_meni_alati"), ("Š&tampa", "15_meni_stampa"), ("&Šifarnici", "16_meni_sifarnici"),
                    ("&Prikaz", "19_meni_prikaz")):
    menu = next(a.menu() for a in w.menuBar().actions() if a.text() == title)
    menu.adjustSize()
    menu.grab().save(str(OUT / f"{name}.png"))

# ---------- poruke ----------
st_db = repo  # noqa: F841
mb = QMessageBox(QMessageBox.Icon.Information, "Provera baze",
                 f"Verzija programa:  {__import__('autostakla.version').version.VERSION}\n"
                 "Verzija baze:  3  (očekivana 3)\nProvera integriteta:  ispravna\n"
                 "Veličina baze:  240 KB\nPoslednji backup:  stakla_2026-11-07_181500_zatvaranje.db\n"
                 "Folder:  C:\\AutoStakla\n\nSve je u redu ✔")
save(mb, "17_provera_baze", adjust=True)

# ---------- PDF spisak ----------
import pymupdf  # noqa: E402

pdf = stampa.write_pdf(stampa.html_spisak(conn, [repo.list_skladista(conn)[0]["id"]]), ROOT / "spisak.pdf")
pymupdf.open(pdf)[0].get_pixmap(dpi=90).save(str(OUT / "18_pdf_spisak.png"))

# ---------- tamna tema ----------
from autostakla.ui import tema  # noqa: E402

v.reset_filters()
v.search.setText("golf 5")
v.refresh()
v.table.selectRow(0)
tema.primeni("tamna")
app.processEvents()
save(w, "20_glavni_tamna")
tema.primeni("svetla")

w.closing_for_update = True
w.close()
conn.close()
shutil.rmtree(ROOT, ignore_errors=True)
print("Snimci:", OUT)
for f in sorted(OUT.glob("*.png")):
    print(" ", f.name, Image.open(f).size)
