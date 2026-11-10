"""Isporuka korisniku: OBAVEZNO_PROCITAJ.txt iz IZMENE.md i paket za prvu instalaciju.

  isporuka.py tekstovi <folder>        -> <folder>\\update\\OBAVEZNO_PROCITAJ.txt, <folder>\\prva\\OBAVEZNO_PROCITAJ.txt
  isporuka.py prva <setup.exe> <zip>   -> paket za prvu instalaciju (Setup + uputstvo + prezentacija + txt)

Ako u IZMENE.md nema odeljka za trenutnu verziju – greška (build staje).
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from autostakla import version  # noqa: E402

IZMENE = PROJECT / "IZMENE.md"
DOK = PROJECT / "dokumentacija"
UPUTSTVO = DOK / "AutoStakla_Korisnicko_uputstvo.pdf"
PREZENTACIJA = [DOK / "AutoStakla_Prezentacija.pptx", DOK / "AutoStakla_Prezentacija.pdf"]
PROCITAJ = "OBAVEZNO_PROCITAJ.txt"
SEKCIJE = ["Dodato", "Izmenjeno", "Ispravljeno", "Uklonjeno"]


class IzmeneError(Exception):
    pass


def izmene_za(ver: str, text: str | None = None) -> tuple[str, dict[str, list[str]]]:
    """Vraća (datum, {sekcija: [stavke]}) za verziju iz IZMENE.md."""
    text = IZMENE.read_text(encoding="utf-8") if text is None else text
    m = re.search(rf"^## {re.escape(ver)}\s*\(([^)]*)\)\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    if not m:
        raise IzmeneError(f"U IZMENE.md nema odeljka „## {ver} (datum)“ – upišite šta je novo pre build-a.")
    datum, body = m.group(1).strip(), m.group(2)
    sekcije: dict[str, list[str]] = {}
    cur = None
    for line in body.splitlines():
        line = line.rstrip()
        h = re.match(r"^###\s+(.+)$", line)
        if h:
            cur = h.group(1).strip().capitalize()
            if cur not in SEKCIJE:
                raise IzmeneError(f"Nepoznat podnaslov „{cur}“ u verziji {ver} (dozvoljeno: {', '.join(SEKCIJE)}).")
            sekcije.setdefault(cur, [])
        elif line.startswith("- ") and cur:
            sekcije[cur].append(line[2:].strip())
        elif line.startswith("  ") and cur and sekcije[cur]:
            sekcije[cur][-1] += " " + line.strip()
    if not any(sekcije.values()):
        raise IzmeneError(f"Odeljak za verziju {ver} u IZMENE.md je prazan.")
    return datum, sekcije


def _blok_izmena(ver: str, datum: str, sekcije: dict[str, list[str]]) -> list[str]:
    out = [f"ŠTA JE NOVO U VERZIJI {ver}  ({datum})", "-" * 60]
    for s in SEKCIJE:
        if sekcije.get(s):
            out.append(f"{s.upper()}:")
            out += [f"  - {x}" for x in sekcije[s]]
            out.append("")
    return out


def tekst(vrsta: str, ver: str | None = None) -> str:
    ver = ver or version.VERSION
    datum, sekcije = izmene_za(ver)
    crta = "=" * 60
    out = [crta, f"  {version.APP_NAME} {ver}  –  OBAVEZNO PROČITAJ", crta, ""]
    if vrsta == "prva":
        out += [
            "ŠTA JE U OVOM PAKETU",
            "-" * 60,
            f"  AutoStakla_Setup_{ver}.exe         – instalacija programa",
            "  AutoStakla_Korisnicko_uputstvo.pdf – kompletno uputstvo",
            "  AutoStakla_Prezentacija.pdf/.pptx  – kratak prikaz programa",
            f"  {PROCITAJ}             – ovaj fajl",
            "",
            "KAKO DA INSTALIRATE",
            "-" * 60,
            "  1. Raspakujte ovaj zip (desni klik → Extract All / Izdvoji sve).",
            f"  2. Dva puta kliknite na AutoStakla_Setup_{ver}.exe.",
            "  3. Ako se pojavi plavi prozor „Windows protected your PC“:",
            "     kliknite More info, pa Run anyway. To se pojavi samo prvi put.",
            "  4. Kliknite Dalje → Instaliraj → Završi.",
            "  5. Program se pokreće ikonicom „AutoStakla“ na radnoj površini.",
            "",
            "  Sve je u folderu C:\\AutoStakla. Ništa drugo ne treba instalirati.",
            "",
        ]
    else:
        out += [
            "KAKO DA PRIMENITE OVU VERZIJU",
            "-" * 60,
            "  1. Sačuvajte ovaj zip fajl (npr. u Preuzimanja). NE RASPAKUJTE ga.",
            "  2. Otvorite AutoStakla → meni Alati → Ažuriraj iz fajla…",
            f"  3. Izaberite ovaj isti zip (AutoStakla_update_{ver}.zip) → Open → Yes.",
            "  4. Program se sam zatvori i posle par sekundi ponovo otvori",
            "     sa porukom da je ažuriran.",
            "",
            "  Podaci se ne diraju. Rezervna kopija se pravi sama pre ažuriranja.",
            "  Ako nešto ne uspe, vraća se prethodna verzija programa.",
            "",
        ]
    out += _blok_izmena(ver, datum, sekcije)
    out += [
        "UPUTSTVO",
        "-" * 60,
        "  U paketu je i ažurirano korisničko uputstvo:",
        "  AutoStakla_Korisnicko_uputstvo.pdf",
        "  Isto uputstvo je i u programu: meni Pomoć → Korisničko uputstvo.",
        "",
        "KAD NEŠTO NE RADI",
        "-" * 60,
        "  Alati → Napravi dijagnostiku… → na desktopu se pojavi zip → pošaljite ga Milošu.",
        "",
    ]
    if vrsta == "prva":
        out += [
            "PREPORUKA",
            "-" * 60,
            "  Jednom nedeljno prekopirajte folder C:\\AutoStakla\\backup na USB ili OneDrive.",
            "",
        ]
    return "\r\n".join(out) + "\r\n"


def write_tekst(path: Path, vrsta: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tekst(vrsta), encoding="utf-8-sig", newline="")
    return path


def prva(setup: Path, out_zip: Path, procitaj: Path) -> Path:
    for f in [setup, UPUTSTVO, *PREZENTACIJA, procitaj]:
        if not f.exists():
            raise FileNotFoundError(f)
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(procitaj, PROCITAJ)
        zf.write(setup, setup.name)
        zf.write(UPUTSTVO, UPUTSTVO.name)
        for p in PREZENTACIJA:
            zf.write(p, p.name)
    return out_zip


if __name__ == "__main__":
    try:
        cmd = sys.argv[1]
        if cmd == "tekstovi":
            base = Path(sys.argv[2])
            print(write_tekst(base / "update" / PROCITAJ, "update"))
            print(write_tekst(base / "prva" / PROCITAJ, "prva"))
        elif cmd == "prva":
            print(prva(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])))
        else:
            raise SystemExit(__doc__)
    except IzmeneError as e:
        print(f"GREŠKA: {e}", file=sys.stderr)
        sys.exit(2)
