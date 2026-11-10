"""Iz pocetno_stanje/spisak_sirovo.txt pravi:
  1) pocetno_stanje/Pocetno_stanje_za_proveru.xlsx   – za pregled (žuto = za proveru)
  2) src/autostakla/migrations/003_pocetno_stanje.sql – uvoz (ponovljiv: IF NOT EXISTS / WHERE NOT EXISTS)

Upotreba:  .venv\\Scripts\\python.exe tools\\pocetno_stanje.py
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "pocetno_stanje" / "spisak_sirovo.txt"
XLSX = ROOT / "pocetno_stanje" / "Pocetno_stanje_za_proveru.xlsx"
SQL = ROOT / "src" / "autostakla" / "migrations" / "003_pocetno_stanje.sql"

QTY = re.compile(r"\s+(\d+)\s*[xX]\s*$")
LINE = re.compile(r"^(\d+[a-z]?)\.\s+(.+)$")

SENZOR_OBLICI = ["2 SENZORA", "1 SENZOR", "OKRUGLI", "KRUŠKA", "KOCKA", "ROMB", "KRUG", "CIGARET"]
KAMERA_OPISI = ["USKA", "ŠIROKA", "VELIKA"]
PLOCICE = [("▲", "trougao"), ("NIŽA PLOČICA", "niža"), ("VIŠA PLOČICA", "viša"),
           ("BEZ PLOČICE", "bez pločice"), ("SA PLOČICOM", "sa pločicom")]


@dataclass
class Stavka:
    skladiste: str
    sk_opis: str | None
    polica: str
    polica_opis: str | None
    pozicija: int
    naziv: str
    kolicina: int
    napomena: str | None
    komentar: str | None
    linija: int
    papir_br: str = ""
    tip: str = "vetrobran"
    senzor: bool = False
    senzor_opis: str | None = None
    kamera: bool = False
    kamera_opis: str | None = None
    plocica: str | None = None
    polovno: bool = False


def _split(text: str, sep: str) -> tuple[str, str | None]:
    if sep in text:
        a, b = text.split(sep, 1)
        return a.strip(), b.strip() or None
    return text.strip(), None


def derive(s: Stavka) -> None:
    up = s.naziv.upper()
    if "SENZOR" in up and "BEZ SENZORA" not in up:
        s.senzor = True
        s.senzor_opis = next((o for o in SENZOR_OBLICI if re.search(rf"\b{o}\b", up)), None)
        if s.senzor_opis:
            s.senzor_opis = s.senzor_opis.lower()
    if "KAMERA" in up:
        s.kamera = True
        opis = next((o for o in KAMERA_OPISI if o in up), None)
        s.kamera_opis = opis.lower() if opis else None
    s.polovno = "POLOVN" in up
    if "ZADNJA" in up:
        s.tip = "zadnje"
    for znak, val in PLOCICE:
        if znak in up:
            s.plocica = val
            break
    s.naziv = re.sub(r"\s+", " ", s.naziv.replace("▲", "").strip())


def parse(path: Path) -> list[Stavka]:
    result: list[Stavka] = []
    sk = sk_opis = po = po_opis = None
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        body, komentar = _split(line, "##")
        if body.startswith("= "):
            sk, sk_opis = _split(body[2:], "|")
            po = po_opis = None
            continue
        if body.startswith("- "):
            po, po_opis = _split(body[2:], "|")
            continue
        m = LINE.match(body)
        if not m:
            raise ValueError(f"Linija {n}: ne razumem „{raw}“")
        if not (sk and po):
            raise ValueError(f"Linija {n}: stavka pre skladišta/police")
        text, napomena = _split(m.group(2), "//")
        kol = 1
        q = QTY.search(text)
        if q:
            kol = int(q.group(1))
            text = text[: q.start()].strip()
        s = Stavka(sk, sk_opis, po, po_opis, 0, text, kol, napomena, komentar, n, papir_br=m.group(1))
        derive(s)
        result.append(s)
    renumber(result)
    return result


def renumber(items: list[Stavka]) -> None:
    """Neprekidni brojevi po skladištu; uzastopni redovi sa istim brojem sa papira dele broj."""
    sk = prev = None
    n = 0
    for s in items:
        if s.skladiste != sk:
            sk, prev, n = s.skladiste, None, 0
        if s.papir_br != prev:
            n += 1
            prev = s.papir_br
        s.pozicija = n


def merge_duplicates(items: list[Stavka]) -> list[Stavka]:
    seen: dict[tuple, Stavka] = {}
    out = []
    for s in items:
        key = (s.skladiste, s.polica, s.pozicija, s.naziv.lower())
        if key in seen:
            seen[key].kolicina += s.kolicina
            continue
        seen[key] = s
        out.append(s)
    return out


# ---------------------------------------------------------------- SQL
def q(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return str(int(v))
    if isinstance(v, int):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def build_sql(items: list[Stavka]) -> str:
    out = [
        "-- 003: početno stanje sa papira (AutostaklaSpisak.pdf). GENERISANO: tools/pocetno_stanje.py – ne menjati ručno.",
        "-- PRAVILO: ponovljivo – INSERT OR IGNORE / WHERE NOT EXISTS.",
        "",
    ]
    skl: list[tuple[str, str | None]] = []
    pol: list[tuple[str, str, str | None]] = []
    for s in items:
        if (s.skladiste, s.sk_opis) not in skl:
            skl.append((s.skladiste, s.sk_opis))
        if (s.skladiste, s.polica, s.polica_opis) not in pol:
            pol.append((s.skladiste, s.polica, s.polica_opis))

    out.append("-- Skladišta")
    for i, (naziv, opis) in enumerate(skl, 1):
        out.append(f"INSERT OR IGNORE INTO skladiste (naziv, opis, redosled) VALUES ({q(naziv)}, {q(opis)}, {i});")

    out += ["", "-- Police"]
    red: dict[str, int] = {}
    for sk, naziv, opis in pol:
        red[sk] = red.get(sk, 0) + 1
        out.append(
            f"INSERT OR IGNORE INTO polica (skladiste_id, naziv, opis, redosled) "
            f"SELECT id, {q(naziv)}, {q(opis)}, {red[sk]} FROM skladiste WHERE naziv = {q(sk)};")

    out += ["", "-- Stakla (šifarnik, bez duplikata po nazivu)"]
    done = set()
    for s in items:
        if s.naziv.lower() in done:
            continue
        done.add(s.naziv.lower())
        out.append(
            "INSERT INTO staklo (naziv, tip, senzor, senzor_opis, kamera, kamera_opis, plocica, polovno) "
            f"SELECT {q(s.naziv)}, {q(s.tip)}, {q(s.senzor)}, {q(s.senzor_opis)}, {q(s.kamera)}, "
            f"{q(s.kamera_opis)}, {q(s.plocica)}, {q(s.polovno)} "
            f"WHERE NOT EXISTS (SELECT 1 FROM staklo WHERE naziv = {q(s.naziv)} COLLATE NOCASE);")

    out += ["", "-- Mesta (staklo + polica + pozicija) i početna količina"]
    for s in items:
        mesto = (f"FROM staklo st, polica p JOIN skladiste sk ON sk.id = p.skladiste_id "
                 f"WHERE st.naziv = {q(s.naziv)} COLLATE NOCASE AND sk.naziv = {q(s.skladiste)} "
                 f"AND p.naziv = {q(s.polica)}")
        out.append(
            f"INSERT INTO lager_stavka (staklo_id, polica_id, pozicija, napomena) "
            f"SELECT st.id, p.id, {s.pozicija}, {q(s.napomena)} {mesto} "
            f"AND NOT EXISTS (SELECT 1 FROM lager_stavka x WHERE x.staklo_id = st.id AND x.polica_id = p.id "
            f"AND x.pozicija = {s.pozicija});")
        out.append(
            f"INSERT INTO kretanje (lager_stavka_id, kolicina, vrsta, napomena) "
            f"SELECT ls.id, {s.kolicina}, 'POCETNO', 'Početno stanje sa papira' "
            f"FROM lager_stavka ls JOIN staklo st ON st.id = ls.staklo_id JOIN polica p ON p.id = ls.polica_id "
            f"JOIN skladiste sk ON sk.id = p.skladiste_id "
            f"WHERE st.naziv = {q(s.naziv)} COLLATE NOCASE AND sk.naziv = {q(s.skladiste)} "
            f"AND p.naziv = {q(s.polica)} AND ls.pozicija = {s.pozicija} "
            f"AND NOT EXISTS (SELECT 1 FROM kretanje k WHERE k.lager_stavka_id = ls.id AND k.vrsta = 'POCETNO');")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- Excel
def build_xlsx(items: list[Stavka]) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "Spisak"
    head = ["Skladište", "Polica", "Poz.", "Br. na papiru", "Staklo", "Kom", "Senzor", "Oblik senzora", "Kamera",
            "Opis kamere", "Pločica", "Polovno", "Tip", "Napomena", "ZA PROVERU"]
    ws.append(head)
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F4E78")
    yellow = PatternFill("solid", fgColor="FFF2CC")
    da = lambda b: "da" if b else ""  # noqa: E731
    for s in items:
        ws.append([s.skladiste, s.polica, s.pozicija, s.papir_br, s.naziv, s.kolicina, da(s.senzor), s.senzor_opis or "",
                   da(s.kamera), s.kamera_opis or "", s.plocica or "", da(s.polovno), s.tip, s.napomena or "",
                   s.komentar or ""])
        if s.komentar:
            for c in ws[ws.max_row]:
                c.fill = yellow
    widths = [18, 20, 6, 8, 52, 6, 8, 14, 8, 12, 12, 9, 11, 22, 70]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2):
        row[14].alignment = Alignment(wrap_text=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    sum_ws = wb.create_sheet("Zbir po skladištu")
    sum_ws.append(["Skladište", "Stavki", "Komada"])
    for c in sum_ws[1]:
        c.font = Font(bold=True)
    order = []
    for s in items:
        if s.skladiste not in order:
            order.append(s.skladiste)
    for sk in order:
        its = [s for s in items if s.skladiste == sk]
        sum_ws.append([sk, len(its), sum(s.kolicina for s in its)])
    sum_ws.append(["UKUPNO", len(items), sum(s.kolicina for s in items)])
    sum_ws[sum_ws.max_row][0].font = Font(bold=True)
    sum_ws.column_dimensions["A"].width = 24
    XLSX.parent.mkdir(parents=True, exist_ok=True)
    wb.save(XLSX)


def main() -> int:
    items = merge_duplicates(parse(SRC))
    SQL.write_text(build_sql(items), encoding="utf-8")
    build_xlsx(items)
    stakla = len({s.naziv.lower() for s in items})
    print(f"Stavki (mesta): {len(items)} | različitih stakala: {stakla} | komada: {sum(s.kolicina for s in items)}")
    print(f"Za proveru: {sum(1 for s in items if s.komentar)}")
    print(SQL)
    print(XLSX)
    return 0


if __name__ == "__main__":
    sys.exit(main())
