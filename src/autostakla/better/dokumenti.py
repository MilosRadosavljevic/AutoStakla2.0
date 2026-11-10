"""Nefiskalni dokumenti: predračun i otpremnica (PDF). Fiskalni račun ovaj program NE izdaje – za građane to radi
samo odobreni ESIR (fiskalizacija), za firme ide e-Faktura (SEF)."""
from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from autostakla.better import novac, prodaja
from autostakla.core import audit, settings
from autostakla.lager import repo, stampa
from autostakla.lager.repo import LagerError

VRSTE = {"PREDRACUN": ("Predračun", "PR"), "OTPREMNICA": ("Otpremnica", "OT")}
FIRMA_POLJA = [("firma_naziv", "Naziv"), ("firma_adresa", "Adresa"), ("firma_mesto", "Mesto"),
               ("firma_pib", "PIB"), ("firma_mb", "Matični broj"), ("firma_telefon", "Telefon"),
               ("firma_racun", "Tekući račun")]

_CSS = """
body { font-family: 'Segoe UI', Arial; font-size: 10pt; }
h1 { font-size: 16pt; margin: 8px 0; }
.firma { font-size: 9pt; color: #333; }
table.stavke { border-collapse: collapse; width: 100%; }
table.stavke th, table.stavke td { border: 1px solid #999; padding: 3px 6px; }
table.stavke th { background: #ddd; }
.napomena { color: #555; font-size: 9pt; }
"""


def get_firma(conn) -> dict:
    return {k: settings.get(conn, k) or "" for k, _ in FIRMA_POLJA}


def set_firma(conn, podaci: dict, pdv_stopa: int | None = None) -> None:
    with repo.transaction(conn):
        for k, _ in FIRMA_POLJA:
            settings.set(conn, k, (podaci.get(k) or "").strip() or None)
        if pdv_stopa is not None:
            if not 0 <= int(pdv_stopa) <= 100:
                raise LagerError("PDV stopa mora biti između 0 i 100.")
            settings.set(conn, novac.KEY_PDV, str(int(pdv_stopa)))
        audit.write(conn, "PODESAVANJE", opis="Podaci o firmi i PDV")


@dataclass
class Stavka:
    naziv: str
    kolicina: int
    cena: int                 # po komadu, SA PDV-om
    staklo_id: int | None = None


def broj(d: dict) -> str:
    return f"{VRSTE[d['vrsta']][1]}-{d['godina']}-{d['redni_broj']:04d}"


def novi(conn, vrsta: str, stavke: list[Stavka], kupac_id: int | None = None, prodaja_id: int | None = None,
         napomena: str | None = None, datum: str | None = None) -> int:
    if vrsta not in VRSTE:
        raise LagerError("Nepoznata vrsta dokumenta.")
    if not stavke:
        raise LagerError("Dokument mora imati bar jednu stavku.")
    for s in stavke:
        if not (s.naziv or "").strip():
            raise LagerError("Svaka stavka mora imati naziv.")
        if int(s.kolicina) <= 0:
            raise LagerError("Količina mora biti veća od nule.")
        if int(s.cena) < 0:
            raise LagerError("Cena ne može biti negativna.")
    datum = datum or date.today().isoformat()
    godina = int(datum[:4])
    with repo.transaction(conn):
        if kupac_id is not None:
            prodaja.get_kupac(conn, kupac_id)
        redni = conn.execute("SELECT COALESCE(MAX(redni_broj), 0) + 1 FROM dokument WHERE vrsta = ? AND godina = ?",
                             (vrsta, godina)).fetchone()[0]
        did = conn.execute(
            "INSERT INTO dokument (vrsta, godina, redni_broj, datum, kupac_id, prodaja_id, napomena) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (vrsta, godina, redni, datum, kupac_id, prodaja_id, (napomena or "").strip() or None)).lastrowid
        for s in stavke:
            conn.execute("INSERT INTO dokument_stavka (dokument_id, staklo_id, naziv, kolicina, cena) "
                         "VALUES (?, ?, ?, ?, ?)", (did, s.staklo_id, s.naziv.strip(), int(s.kolicina), int(s.cena)))
        audit.write(conn, "DOKUMENT", entitet="dokument", entitet_id=did,
                    opis=f"{VRSTE[vrsta][0]} {VRSTE[vrsta][1]}-{godina}-{redni:04d}")
    return did


def otpremnica_za_prodaju(conn, prodaja_id: int) -> int:
    """Otpremnica za prodaju (jedna po prodaji – ako već postoji, vraća postojeću)."""
    r = conn.execute("SELECT id FROM dokument WHERE vrsta = 'OTPREMNICA' AND prodaja_id = ?", (prodaja_id,)).fetchone()
    if r:
        return r[0]
    p = prodaja.get_prodaja(conn, prodaja_id)
    nap = " | ".join(x for x in (p["vozilo"], p["tablice"], "sa ugradnjom" if p["sa_ugradnjom"] else None) if x)
    return novi(conn, "OTPREMNICA", [Stavka(p["staklo"], p["kom"], p["cena"], p["staklo_id"])],
                kupac_id=p["kupac_id"], prodaja_id=prodaja_id, napomena=nap or None, datum=p["datum"][:10])


def get(conn, dokument_id: int) -> dict:
    r = conn.execute("SELECT d.*, k.ime AS kupac, k.telefon FROM dokument d LEFT JOIN kupac k ON k.id = d.kupac_id "
                     "WHERE d.id = ?", (dokument_id,)).fetchone()
    if not r:
        raise LagerError("Dokument ne postoji.")
    d = dict(r)
    d["broj"] = broj(d)
    d["stavke"] = [dict(s) for s in conn.execute("SELECT * FROM dokument_stavka WHERE dokument_id = ? ORDER BY id",
                                                 (dokument_id,))]
    d["ukupno"] = sum(s["kolicina"] * s["cena"] for s in d["stavke"])
    return d


def list_dokumenti(conn) -> list[dict]:
    rows = [dict(r) for r in conn.execute(
        "SELECT d.*, k.ime AS kupac, (SELECT SUM(kolicina * cena) FROM dokument_stavka WHERE dokument_id = d.id) "
        "AS ukupno FROM dokument d LEFT JOIN kupac k ON k.id = d.kupac_id ORDER BY d.datum DESC, d.id DESC")]
    for r in rows:
        r["broj"] = broj(r)
    return rows


def html_dokument(conn, dokument_id: int) -> str:
    d = get(conn, dokument_id)
    f = get_firma(conn)
    stopa = novac.pdv_stopa(conn)
    e = lambda s: html.escape(str(s or ""))  # noqa: E731
    firma = "<br>".join(e(f"{naziv}: {f[k]}") if k != "firma_naziv" else f"<b>{e(f[k])}</b>"
                        for k, naziv in FIRMA_POLJA if f[k])
    osnovica = novac.bez_pdv(d["ukupno"], stopa)
    parts = [f"<html><head><style>{_CSS}</style></head><body>",
             f"<p class='firma'>{firma or '<i>(podaci o firmi nisu upisani – Poslovanje → Podaci o firmi)</i>'}</p>",
             f"<h1>{VRSTE[d['vrsta']][0]} br. {e(d['broj'])}</h1>",
             f"<p>Datum: {date.fromisoformat(d['datum']):%d.%m.%Y}"
             + (f"<br>Kupac: <b>{e(d['kupac'])}</b>" + (f", tel. {e(d['telefon'])}" if d["telefon"] else "")
                if d["kupac"] else "") + "</p>",
             "<table class='stavke'><tr><th>R.br.</th><th>Naziv</th><th>Kom</th><th>Cena sa PDV</th>"
             "<th>Ukupno</th></tr>"]
    for i, s in enumerate(d["stavke"], 1):
        parts.append(f"<tr><td align=center>{i}</td><td>{e(s['naziv'])}</td><td align=center>{s['kolicina']}</td>"
                     f"<td align=right>{novac.fmt(s['cena'])}</td>"
                     f"<td align=right>{novac.fmt(s['kolicina'] * s['cena'])}</td></tr>")
    parts.append("</table>")
    parts.append(f"<p align=right>Osnovica: {novac.fmt(osnovica)}<br>PDV {stopa}%: {novac.fmt(d['ukupno'] - osnovica)}"
                 f"<br><b>Ukupno za uplatu: {novac.fmt(d['ukupno'])}</b></p>")
    if d["napomena"]:
        parts.append(f"<p>Napomena: {e(d['napomena'])}</p>")
    parts.append("<p class='napomena'>Ovaj dokument nije fiskalni račun.</p>")
    if d["vrsta"] == "OTPREMNICA":
        parts.append("<br><br><table width='100%'><tr><td>Robu izdao: ____________________</td>"
                     "<td align=right>Robu primio: ____________________</td></tr></table>")
    parts.append("</body></html>")
    return "".join(parts)


def pdf(conn, dokument_id: int, target_folder: Path) -> Path:
    d = get(conn, dokument_id)
    target = target_folder / f"{VRSTE[d['vrsta']][0]}_{d['broj']}.pdf"
    return stampa.write_pdf(html_dokument(conn, dokument_id), target, f"{VRSTE[d['vrsta']][0]} {d['broj']}")
