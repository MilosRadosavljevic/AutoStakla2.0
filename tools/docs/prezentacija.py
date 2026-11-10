"""Prezentacija za korisnika -> dokumentacija/AutoStakla_Prezentacija.pptx (+ .pdf)"""
import sys
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from autostakla import version  # noqa: E402

PROJECT = Path(__file__).resolve().parents[2]
SLIKE = PROJECT / "dokumentacija" / "slike"
OUT = PROJECT / "dokumentacija" / "AutoStakla_Prezentacija.pptx"

NAVY = RGBColor(0x0F, 0x2A, 0x44)
BLUE = RGBColor(0x15, 0x43, 0x78)
ICE = RGBColor(0xE6, 0xF1, 0xFA)
GLASS = RGBColor(0x96, 0xCD, 0xF5)
AMBER = RGBColor(0xF2, 0xA3, 0x3A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
TEXT = RGBColor(0x22, 0x2B, 0x36)
MUTED = RGBColor(0x5F, 0x6B, 0x78)
FONT = "Calibri"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
W, H = 13.333, 7.5
M = 0.6


# ---------------------------------------------------------------- pomoćne
def bg(slide, color):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = color


def text(slide, x, y, w, h, runs, size=16, color=TEXT, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, name=None, spacing=None):
    """runs: str | lista pasusa; pasus = str ili lista (tekst, {bold, color, size})."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    paras = runs if isinstance(runs, list) else [runs]
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing:
            p.space_after = Pt(spacing)
        parts = para if isinstance(para, list) else [(para, {})]
        for part in parts:
            t, opt = (part, {}) if isinstance(part, str) else part
            r = p.add_run()
            r.text = t
            r.font.name = FONT
            r.font.size = Pt(opt.get("size", size))
            r.font.bold = opt.get("bold", bold)
            r.font.color.rgb = opt.get("color", color)
    return tb


def title(slide, t, sub=None, dark=False):
    text(slide, M, 0.45, W - 2 * M, 0.8, t, size=36, bold=True, color=WHITE if dark else NAVY, name="Naslov")
    if sub:
        text(slide, M, 1.18, W - 2 * M, 0.5, sub, size=17, color=GLASS if dark else MUTED, name="Podnaslov")


def box(slide, x, y, w, h, fill=ICE, radius=True, line=None, name=None):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE,
                                 Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:
        shp.adjustments[0] = 0.08
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    if line:
        shp.line.color.rgb = line
        shp.line.width = Pt(1.25)
    else:
        shp.line.fill.background()
    shp.shadow.inherit = False
    if name:
        shp.name = name
    return shp


def circle(slide, x, y, d, label, fill=BLUE, size=20, color=WHITE):
    c = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    c.fill.solid()
    c.fill.fore_color.rgb = fill
    c.line.fill.background()
    c.shadow.inherit = False
    tf = c.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(size), True, color
    return c


def image(slide, name, x, y, w=None, h=None, frame=True):
    """Slika upisana u (w, h) uz očuvan odnos strana; vraća (x, y, w, h)."""
    path = SLIKE / f"{name}.png"
    iw, ih = Image.open(path).size
    ratio = iw / ih
    if w and h:
        if w / h > ratio:
            w = h * ratio
        else:
            h = w / ratio
    elif w:
        h = w / ratio
    else:
        w = h * ratio
    if frame:
        f = box(slide, x - 0.06, y - 0.06, w + 0.12, h + 0.12, fill=WHITE, radius=False, line=RGBColor(0xC9, 0xD6, 0xE3))
        f.shadow.inherit = False
    slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
    return x, y, w, h


def notes(slide, t):
    slide.notes_slide.notes_text_frame.text = t


def new(dark=False):
    s = prs.slides.add_slide(BLANK)
    bg(s, NAVY if dark else WHITE)
    return s


def step_list(slide, x, y, w, items, size=16, gap=0.62):
    for i, it in enumerate(items, 1):
        circle(slide, x, y + (i - 1) * gap, 0.42, str(i), size=15)
        text(slide, x + 0.6, y + (i - 1) * gap + 0.04, w - 0.6, gap, it, size=size, anchor=MSO_ANCHOR.TOP)


# ---------------------------------------------------------------- 1 naslovna
s = new(dark=True)
logo = SLIKE / "_logo.png"
s.shapes.add_picture(str(logo), Inches(M), Inches(1.6), Inches(1.5), Inches(1.5))
text(s, M, 3.35, 9, 1.1, "AutoStakla", size=60, bold=True, color=WHITE)
text(s, M, 4.45, 10, 0.6, "Evidencija lagera auto stakala – kako se radi u programu", size=24, color=GLASS)
text(s, M, 6.55, 8, 0.4, f"Verzija {version.VERSION}", size=14, color=GLASS)
image(s, "20_glavni_tamna", 8.25, 1.15, w=4.5, frame=False)
notes(s, "Kratak pregled programa AutoStakla: šta radi i kako se koristi svaka opcija.")

# ---------------------------------------------------------------- 2 šta radi
s = new()
title(s, "Šta program radi", "Ceo lager na jednom mestu – umesto papira i olovke")
cards = [
    ("Pretraga", "Ukucate „golf 5“ i odmah vidite gde stoji svako takvo staklo."),
    ("Ulaz i izlaz", "Staklo stigne ili izađe – upiše se jednim klikom, sa datumom."),
    ("Skladišta i police", "Sami uređujete gde šta stoji: stalci, police, redni brojevi."),
    ("Štampa", "Spisak po skladištima u PDF-u, isti kao onaj na papiru."),
]
cw = (W - 2 * M - 3 * 0.35) / 4
for i, (h, d_) in enumerate(cards):
    x = M + i * (cw + 0.35)
    box(s, x, 2.15, cw, 3.9, fill=ICE, name=f"Kartica {h}")
    circle(s, x + 0.35, 2.5, 0.75, str(i + 1), size=24)
    text(s, x + 0.35, 3.5, cw - 0.7, 0.85, h, size=21, bold=True, color=NAVY, anchor=MSO_ANCHOR.BOTTOM)
    text(s, x + 0.35, 4.5, cw - 0.7, 1.45, d_, size=16)
text(s, M, 6.45, W - 2 * M, 0.5, "Sve se čuva samo – nema dugmeta „Sačuvaj“. Program sam pravi i rezervne kopije.",
     size=16, color=BLUE, bold=True)
notes(s, "Četiri glavne stvari koje program radi.")

# ---------------------------------------------------------------- 3 brojevi
s = new()
title(s, "Spisak sa papira je već u programu", "Svih 10 strana je prekucano – ne kreće se od nule")
stats = [("11", "skladišta"), ("329", "mesta na policama"), ("390", "komada stakla")]
sw = (W - 2 * M - 2 * 0.5) / 3
for i, (n, lbl) in enumerate(stats):
    x = M + i * (sw + 0.5)
    box(s, x, 2.2, sw, 2.6, fill=ICE)
    text(s, x, 2.45, sw, 1.4, n, size=72, bold=True, color=BLUE, align=PP_ALIGN.CENTER)
    text(s, x, 3.9, sw, 0.6, lbl, size=20, color=TEXT, align=PP_ALIGN.CENTER)
text(s, M, 5.3, W - 2 * M, 1.6, [
    "Na primer: 1 Stalak, 2 Stalak, Dvorište, Garaža.",
    "Redni brojevi su kao na papiru – samo idu redom kroz celo skladište.",
], size=17, spacing=6)
notes(s, "Početno stanje je preneto sa papira. Rukom dopisane stavke su posebno proverene.")

# ---------------------------------------------------------------- 4 glavni ekran
s = new()
title(s, "Glavni ekran")
_, _, iw, ih = image(s, "01_glavni_ekran_oznake", M, 1.35, w=8.3)
legend = [("1", "Pretraga"), ("2", "Filteri"), ("3", "Spisak stakala"), ("4", "Dugmad za rad"),
          ("5", "Izmena i istorija"), ("6", "Meni")]
lx = M + iw + 0.55
for i, (n, t) in enumerate(legend):
    y = 1.5 + i * 0.78
    circle(s, lx, y, 0.5, n, fill=RGBColor(0xDC, 0x1E, 0x1E), size=17)
    text(s, lx + 0.7, y + 0.08, 3.3, 0.5, t, size=19, color=TEXT)
text(s, lx, 6.35, 3.9, 0.8, "Prvo kliknite na red u tabeli – onda rade Izlaz, Premesti i ostalo.",
     size=14, color=MUTED)
notes(s, "Ekran ima šest delova. Najvažnije je polje za pretragu na vrhu.")

# ---------------------------------------------------------------- 5 pretraga
s = new()
title(s, "Pretraga: gde je koje staklo", "Kucate – spisak se menja odmah, bez Enter-a")
image(s, "02_pretraga_golf5", M, 1.95, w=7.6)
tips = [
    [("golf 5 senzor", {"bold": True, "color": BLUE}), " – sve reči moraju da se poklope"],
    [("peugeot", {"bold": True, "color": BLUE}), " = pezo,  ", ("renault", {"bold": True, "color": BLUE}), " = reno"],
    [("škoda", {"bold": True, "color": BLUE}), " = skoda – kvačice i velika slova nisu bitni"],
    [("dvorište, garaža, krug", {"bold": True, "color": BLUE}), " – i po mestu i po napomeni"],
]
tx = M + 7.6 + 0.6
for i, t in enumerate(tips):
    box(s, tx, 1.95 + i * 1.12, W - tx - M, 0.95, fill=ICE)
    text(s, tx + 0.25, 1.95 + i * 1.12, W - tx - M - 0.5, 0.95, [t], size=16, anchor=MSO_ANCHOR.MIDDLE)
notes(s, "Pretraga je najvažnija opcija. Primer: golf 5 senzor.")

# ---------------------------------------------------------------- 6 filteri
s = new()
title(s, "Filteri: suzite spisak", "Kombinuju se sa pretragom")
image(s, "03_filter_skladiste", M, 1.95, w=7.6)
rows = [("Skladište / Polica", "samo jedno mesto – kao strana sa papira"),
        ("Tip", "vetrobran, zadnje, bočno"),
        ("Senzor / Kamera / Polovno", "Da, Ne ili Svejedno"),
        ("prikaži i ono čega nema", "i stakla kojih više nema (sivo)"),
        ("Poništi filtere", "sve na početno")]
for i, (a, b) in enumerate(rows):
    y = 1.95 + i * 0.92
    text(s, tx, y, W - tx - M, 0.4, a, size=17, bold=True, color=NAVY)
    text(s, tx, y + 0.38, W - tx - M, 0.45, b, size=15, color=MUTED)
notes(s, "Filteri sužavaju spisak. Poništi filtere vraća sve.")

# ---------------------------------------------------------------- 7 pozicije
s = new()
title(s, "Pozicija: redni broj na polici", "Ubacite staklo između dva – svi ispod se sami pomere")
pre = [("1", "Sprinter"), ("2", "Ducato"), ("3", "Audi A4"), ("4", "Master")]
posle = [("1", "Sprinter"), ("2", "Ducato"), ("3", "Touran"), ("4", "Touran"), ("5", "Audi A4"), ("6", "Master")]


def kolona(x, naslov, items, novo=()):
    text(s, x, 1.95, 4, 0.5, naslov, size=20, bold=True, color=NAVY)
    for i, (n, t) in enumerate(items):
        y = 2.55 + i * 0.66
        hl = t in novo
        box(s, x, y, 4.0, 0.55, fill=AMBER if hl else ICE)
        text(s, x + 0.2, y, 0.6, 0.55, n, size=18, bold=True, color=NAVY, anchor=MSO_ANCHOR.MIDDLE)
        text(s, x + 0.85, y, 3.0, 0.55, t, size=18, color=TEXT, anchor=MSO_ANCHOR.MIDDLE, bold=hl)


kolona(M, "Pre", pre)
arrow = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(M + 4.35), Inches(3.55), Inches(1.0), Inches(0.6))
arrow.fill.solid()
arrow.fill.fore_color.rgb = BLUE
arrow.line.fill.background()
kolona(M + 5.7, "Posle: ubačena 2 Tourana na 3", posle, novo=("Touran",))
box(s, M + 10.1, 2.55, W - M - (M + 10.1), 3.9, fill=ICE)
text(s, M + 10.3, 2.75, W - M - (M + 10.5), 3.6, [
    [("Svaki komad", {"bold": True}), " dobija svoj broj."],
    "Brojevi idu kroz celo skladište, preko svih polica.",
    "Kad izađe poslednji komad – mesto nestaje, ostali se penju.",
], size=15, spacing=10)
notes(s, "Primer sa papira: dva Tourana ubačena na mesto 3, Audi prelazi na 5.")

# ---------------------------------------------------------------- 8 ulaz
s = new()
title(s, "Ulaz stakla", "Novo staklo stiglo – upiše se za pola minuta")
step_list(s, M, 2.0, 5.6, [
    "Kliknite red posle kog staklo stoji (nije obavezno)",
    "Dugme  ＋ Ulaz",
    "Izaberite staklo ili „Novo staklo…“",
    "Skladište, polica, pozicija",
    "Količina i napomena",
    "Upiši ulaz",
], size=17, gap=0.7)
image(s, "04_ulaz", M + 6.1, 2.0, w=W - M - (M + 6.1))
notes(s, "Ulaz: izbor stakla, mesta i količine. Program ispod ispisuje šta će se desiti sa brojevima.")

# ---------------------------------------------------------------- 9 izlaz / ispravka / premesti
s = new()
title(s, "Izlaz, ispravka i premeštanje", "Uvek: prvo klik na red u tabeli")
cols = [("−  Izlaz", "Staklo prodato ili ugrađeno. Upišete broj komada i napomenu (npr. kome).", "06_izlaz"),
        ("✎  Ispravi količinu", "Kad prebrojite i broj nije tačan. Upišete tačan broj – razlika ide u istoriju.",
         "07_ispravka"),
        ("⇄  Premesti", "Na drugo skladište ili policu. Brojevi se sami srede na oba mesta.", "08_premesti")]
cw = (W - 2 * M - 2 * 0.4) / 3
for i, (h, d_, img) in enumerate(cols):
    x = M + i * (cw + 0.4)
    box(s, x, 1.95, cw, 5.0, fill=ICE)
    text(s, x + 0.3, 2.15, cw - 0.6, 0.5, h, size=21, bold=True, color=NAVY)
    text(s, x + 0.3, 2.75, cw - 0.6, 1.2, d_, size=15)
    image(s, img, x + 0.3, 4.05, w=cw - 0.6, h=2.65)
notes(s, "Tri najčešće radnje posle ulaza.")

# ---------------------------------------------------------------- 10 pozicija/napomena + istorija
s = new()
title(s, "Pozicija, napomena i istorija")
half = (W - 2 * M - 0.5) / 2
text(s, M, 1.4, half, 0.5, "Pozicija / napomena…", size=21, bold=True, color=NAVY)
text(s, M, 1.9, half, 0.9, "Napomena za to mesto (npr. „H137 163“) i pomeranje na drugu poziciju u istom skladištu.",
     size=15)
image(s, "09_pozicija_napomena", M, 2.95, w=half, h=3.9)
x2 = M + half + 0.5
text(s, x2, 1.4, half, 0.5, "Istorija (dupli klik na red)", size=21, bold=True, color=NAVY)
text(s, x2, 1.9, half, 0.9, "Svaki ulaz, izlaz, ispravka i premeštanje – sa datumom i napomenom.", size=15)
image(s, "10_istorija", x2, 2.95, w=half, h=3.9)
notes(s, "Napomena se menja preko dugmeta Pozicija / napomena. Istorija pokazuje sve promene.")

# ---------------------------------------------------------------- 11 skladišta
s = new()
title(s, "Skladišta i police", "Meni  Šifarnici → Skladišta i police…")
image(s, "11_skladista_police", M, 1.95, w=7.3)
rules = [("Dodaj…", "novo skladište ili polica"), ("Izmeni…", "naziv i opis (ili dupli klik)"),
         ("Obriši", "samo kad je prazno – istorija ostaje"), ("▲ / ▼", "redosled u programu i na štampi")]
tx2 = M + 7.3 + 0.6
for i, (a, b) in enumerate(rules):
    y = 1.95 + i * 1.12
    box(s, tx2, y, W - tx2 - M, 0.95, fill=ICE)
    text(s, tx2 + 0.25, y + 0.1, W - tx2 - M - 0.5, 0.4, a, size=17, bold=True, color=NAVY)
    text(s, tx2 + 0.25, y + 0.5, W - tx2 - M - 0.5, 0.4, b, size=15)
notes(s, "Skladišta i police se dodaju, menjaju, brišu i pomeraju gore-dole.")

# ---------------------------------------------------------------- 12 štampa
s = new()
title(s, "Štampa", "PDF se otvara u pregledaču (Edge / Chrome) – odatle Ctrl + P")
image(s, "18_pdf_spisak", M, 1.95, h=5.0)
step_list(s, 5.0, 2.1, 4.3, [
    "Štampa → Spisak po skladištima",
    "Označite skladišta",
    "Napravi PDF",
    "U pregledaču: Ctrl + P",
], size=17, gap=0.8)
box(s, 9.6, 2.1, W - 9.6 - M, 2.9, fill=ICE)
text(s, 9.85, 2.3, W - 9.85 - M - 0.2, 2.6, [
    [("Trenutni prikaz", {"bold": True, "color": NAVY})],
    "Štampa tačno ono što je u tabeli – npr. rezultat pretrage.",
], size=15, spacing=6)
text(s, 5.0, 5.6, W - 5.0 - M, 0.8, "Svi PDF-ovi ostaju u folderu C:\\AutoStakla\\stampa.", size=15, color=MUTED)
notes(s, "Spisak izgleda kao papir: naslov skladišta, police odvojene linijom, 2x podebljano.")

# ---------------------------------------------------------------- 13 tema
s = new()
title(s, "Svetla ili tamna tema", "Meni  Prikaz → Svetla / Tamna tema  –  program pamti izbor")
half = (W - 2 * M - 0.5) / 2
image(s, "02_pretraga_golf5", M, 2.0, w=half)
image(s, "20_glavni_tamna", M + half + 0.5, 2.0, w=half)
text(s, M, 5.75, half, 0.4, "Svetla", size=17, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
text(s, M + half + 0.5, 5.75, half, 0.4, "Tamna", size=17, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
notes(s, "Tema se bira u meniju Prikaz i važi i pri sledećem pokretanju.")

# ---------------------------------------------------------------- 14 sigurnost
s = new()
title(s, "Podaci su sigurni", "Meni  Alati")
grid = [("Rezervne kopije", "Same se prave pri zatvaranju i pre ažuriranja. Čuva se 30 poslednjih.\n"
                            "Preporuka: povremeno kopija foldera backup na USB."),
        ("Provera baze", "Pokazuje verziju i proverava da li su podaci ispravni."),
        ("Ažuriraj iz fajla…", "Nova verzija stiže kao zip (Viber). Program se sam zameni i ponovo otvori – "
                               "podaci se ne diraju."),
        ("Napravi dijagnostiku…", "Kad nešto ne radi: zip na desktopu → pošaljete Milošu.")]
gw = (W - 2 * M - 0.4) / 2
for i, (h, d_) in enumerate(grid):
    x = M + (i % 2) * (gw + 0.4)
    y = 1.95 + (i // 2) * 2.5
    box(s, x, y, gw, 2.2, fill=ICE)
    circle(s, x + 0.3, y + 0.35, 0.6, str(i + 1), size=19)
    text(s, x + 1.1, y + 0.35, gw - 1.4, 0.5, h, size=20, bold=True, color=NAVY)
    text(s, x + 1.1, y + 0.9, gw - 1.4, 1.2, d_, size=15)
notes(s, "Program sam čuva kopije. Ažuriranje i dijagnostika su u meniju Alati.")

# ---------------------------------------------------------------- 15 brzi pregled
s = new()
title(s, "Brzi pregled")
rows = [("Nađem staklo", "Kucam u pretragu"),
        ("Novo staklo na lager", "＋ Ulaz"),
        ("Staklo izašlo", "Klik na red → − Izlaz"),
        ("Pogrešan broj komada", "Klik na red → ✎ Ispravi količinu"),
        ("Drugo mesto", "Klik na red → ⇄ Premesti"),
        ("Napomena / pozicija", "Klik na red → Pozicija / napomena…"),
        ("Šta se dešavalo", "Dupli klik na red"),
        ("Skladišta i police", "Šifarnici → Skladišta i police…"),
        ("Štampa", "Štampa → Spisak po skladištima (Ctrl + P)"),
        ("Nova verzija / problem", "Alati → Ažuriraj iz fajla / Napravi dijagnostiku")]
tbl = s.shapes.add_table(len(rows) + 1, 2, Inches(M), Inches(1.45), Inches(W - 2 * M), Inches(5.6)).table
tbl.columns[0].width = Inches(4.6)
tbl.columns[1].width = Inches(W - 2 * M - 4.6)
for c, h in enumerate(("Želim da…", "Uradim ovo")):
    cell = tbl.cell(0, c)
    cell.text = h
    cell.fill.solid()
    cell.fill.fore_color.rgb = NAVY
    r = cell.text_frame.paragraphs[0].runs[0]
    r.font.name, r.font.size, r.font.bold, r.font.color.rgb = FONT, Pt(17), True, WHITE
for i, (a, b) in enumerate(rows, 1):
    for c, val in enumerate((a, b)):
        cell = tbl.cell(i, c)
        cell.text = val
        cell.fill.solid()
        cell.fill.fore_color.rgb = ICE if i % 2 else WHITE
        r = cell.text_frame.paragraphs[0].runs[0]
        r.font.name, r.font.size, r.font.color.rgb = FONT, Pt(15), TEXT
        r.font.bold = c == 0
notes(s, "Sve opcije na jednom mestu.")

# ---------------------------------------------------------------- 16 kraj
s = new(dark=True)
text(s, M, 2.2, W - 2 * M, 1.0, "Pitanja?", size=54, bold=True, color=WHITE)
text(s, M, 3.4, W - 2 * M, 1.6, [
    "Detaljno uputstvo: u programu  Pomoć → Korisničko uputstvo  (taster F1)",
    "Kad nešto ne radi:  Alati → Napravi dijagnostiku…  →  pošaljite zip Milošu",
], size=20, color=GLASS, spacing=10)
s.shapes.add_picture(str(logo), Inches(W - M - 1.4), Inches(5.6), Inches(1.2), Inches(1.2))
notes(s, "Kraj prezentacije.")

prs.save(OUT)
print(OUT)

# PDF preko PowerPoint-a (za pregled i štampu)
import win32com.client  # noqa: E402

pp = win32com.client.DispatchEx("PowerPoint.Application")
try:
    deck = pp.Presentations.Open(str(OUT), ReadOnly=True, WithWindow=False)
    deck.SaveAs(str(OUT.with_suffix(".pdf")), 32)
    deck.Close()
finally:
    pp.Quit()
print(OUT.with_suffix(".pdf"))
