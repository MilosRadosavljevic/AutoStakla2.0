"""Razlog izlaza/ulaza, kupci i prodaja. Stanje i dalje vode kretanja – ovde su samo dodaci uz njih."""
from __future__ import annotations

from dataclasses import dataclass

from autostakla.better import novac
from autostakla.core import audit
from autostakla.lager import repo, search
from autostakla.lager.repo import LagerError

RAZLOZI_IZLAZ = {"PRODATO": "Prodato", "RAZBIJENO": "Razbijeno", "POVRAT_DOBAVLJACU": "Vraćeno dobavljaču",
                 "ZAMENA_REKLAMACIJA": "Zamena po reklamaciji", "OSTALO": "Ostalo"}
RAZLOZI_ULAZ = {"NABAVKA": "Nabavka", "POVRAT_KUPCA": "Vraćeno od kupca", "OSTALO": "Ostalo"}
RAZLOZI = {**RAZLOZI_IZLAZ, **RAZLOZI_ULAZ}


def _clean(text: str | None) -> str | None:
    text = (text or "").strip()
    return text or None


def tablice(text: str | None) -> str | None:
    t = _clean(text)
    return " ".join(t.upper().split()) if t else None


# =====================================================================
# Kupci
# =====================================================================
def list_kupci(conn, tekst: str = "") -> list[dict]:
    rows = [dict(r) for r in conn.execute("SELECT * FROM kupac ORDER BY ime COLLATE NOCASE, id")]
    q = search.words(tekst)
    if not q:
        return rows
    return [r for r in rows if search.matches(q, search.words(f"{r['ime']} {r['telefon'] or ''} {r['napomena'] or ''}"))]


def get_kupac(conn, kupac_id: int) -> dict:
    r = conn.execute("SELECT * FROM kupac WHERE id = ?", (kupac_id,)).fetchone()
    if not r:
        raise LagerError("Kupac ne postoji.")
    return dict(r)


def add_kupac(conn, ime: str, telefon: str | None = None, napomena: str | None = None) -> int:
    if not _clean(ime):
        raise LagerError("Ime kupca je obavezno.")
    with repo.transaction(conn):
        kid = conn.execute("INSERT INTO kupac (ime, telefon, napomena) VALUES (?, ?, ?)",
                           (_clean(ime), _clean(telefon), _clean(napomena))).lastrowid
        audit.write(conn, "DODATO", entitet="kupac", entitet_id=kid, opis=_clean(ime))
    return kid


def update_kupac(conn, kupac_id: int, ime: str, telefon: str | None, napomena: str | None) -> None:
    if not _clean(ime):
        raise LagerError("Ime kupca je obavezno.")
    with repo.transaction(conn):
        staro = get_kupac(conn, kupac_id)
        conn.execute("UPDATE kupac SET ime = ?, telefon = ?, napomena = ?, izmenjeno = datetime('now','localtime') "
                     "WHERE id = ?", (_clean(ime), _clean(telefon), _clean(napomena), kupac_id))
        audit.write(conn, "IZMENA", entitet="kupac", entitet_id=kupac_id, opis=_clean(ime), staro=staro,
                    novo={"ime": _clean(ime), "telefon": _clean(telefon), "napomena": _clean(napomena)})


# =====================================================================
# Izlaz sa razlogom / prodaja
# =====================================================================
@dataclass
class ProdajaPodaci:
    cena: int                      # po komadu, ceo dinar, SA PDV-om
    kupac_id: int | None = None
    vozilo: str | None = None
    tablice: str | None = None
    sa_ugradnjom: bool = False
    napomena: str | None = None


def izlaz(conn, stavka_id: int, kolicina: int, razlog: str, napomena: str | None = None,
          prodaja: ProdajaPodaci | None = None) -> int:
    """Izlaz kao u osnovnoj verziji + razlog; za PRODATO i podaci o prodaji. Vraća id kretanja."""
    if razlog not in RAZLOZI_IZLAZ:
        raise LagerError("Izaberite razlog izlaza.")
    if razlog == "PRODATO":
        if prodaja is None:
            raise LagerError("Za prodaju upišite cenu.")
        if prodaja.cena < 0:
            raise LagerError("Cena ne može biti negativna.")
    with repo.transaction(conn):
        if prodaja and prodaja.kupac_id is not None:
            get_kupac(conn, prodaja.kupac_id)
        repo.izlaz(conn, stavka_id, kolicina, napomena)
        kid = conn.execute("SELECT MAX(id) FROM kretanje WHERE lager_stavka_id = ? AND vrsta = 'IZLAZ'",
                           (stavka_id,)).fetchone()[0]
        conn.execute("INSERT INTO kretanje_razlog (kretanje_id, razlog) VALUES (?, ?)", (kid, razlog))
        if razlog == "PRODATO":
            pid = conn.execute(
                "INSERT INTO prodaja (kretanje_id, kupac_id, vozilo, tablice, cena, sa_ugradnjom, napomena) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (kid, prodaja.kupac_id, _clean(prodaja.vozilo), tablice(prodaja.tablice), int(prodaja.cena),
                 int(prodaja.sa_ugradnjom), _clean(prodaja.napomena))).lastrowid
            audit.write(conn, "PRODAJA", entitet="prodaja", entitet_id=pid,
                        opis=f"{kolicina} kom × {novac.fmt(prodaja.cena)}" + (
                            f" | {tablice(prodaja.tablice)}" if prodaja.tablice else ""))
    return kid


_PRODAJA_SQL = """
SELECT p.id, k.id AS kretanje_id, k.datum, -k.kolicina AS kom, p.cena, -k.kolicina * p.cena AS ukupno,
       s.id AS staklo_id, s.naziv AS staklo, ku.id AS kupac_id, ku.ime AS kupac, ku.telefon,
       p.vozilo, p.tablice, p.sa_ugradnjom, p.napomena, k.lager_stavka_id
FROM prodaja p
JOIN kretanje k      ON k.id = p.kretanje_id
JOIN lager_stavka ls ON ls.id = k.lager_stavka_id
JOIN staklo s        ON s.id = ls.staklo_id
LEFT JOIN kupac ku   ON ku.id = p.kupac_id
"""


def list_prodaja(conn, od: str | None = None, do: str | None = None, tekst: str = "") -> list[dict]:
    """Prodaja u periodu (datumi 'YYYY-MM-DD', uključivo), najnovija prva."""
    sql = _PRODAJA_SQL + " WHERE (? IS NULL OR substr(k.datum, 1, 10) >= ?) AND (? IS NULL OR substr(k.datum, 1, 10) <= ?)"
    rows = [dict(r) for r in conn.execute(sql + " ORDER BY k.datum DESC, p.id DESC", (od, od, do, do))]
    q = search.words(tekst)
    if not q:
        return rows
    return [r for r in rows if search.matches(q, search.words(" ".join(
        str(r[k] or "") for k in ("staklo", "kupac", "telefon", "vozilo", "tablice", "napomena"))))]


def get_prodaja(conn, prodaja_id: int) -> dict:
    r = conn.execute(_PRODAJA_SQL + " WHERE p.id = ?", (prodaja_id,)).fetchone()
    if not r:
        raise LagerError("Prodaja ne postoji.")
    return dict(r)


def istorija(conn, stavka_id: int) -> list[dict]:
    """Kao repo.istorija, plus razlog i detalj (cena, kupac, dobavljač)."""
    rows = [dict(r) for r in conn.execute(
        """SELECT k.id, k.datum, k.vrsta, k.kolicina, k.napomena, r.razlog,
                  p.cena AS prodajna_cena, ku.ime AS kupac, p.tablice,
                  n.nabavna_cena, d.naziv AS dobavljac
           FROM kretanje k
           LEFT JOIN kretanje_razlog r ON r.kretanje_id = k.id
           LEFT JOIN prodaja p ON p.kretanje_id = k.id
           LEFT JOIN kupac ku ON ku.id = p.kupac_id
           LEFT JOIN nabavka n ON n.kretanje_id = k.id
           LEFT JOIN dobavljac d ON d.id = n.dobavljac_id
           WHERE k.lager_stavka_id = ? ORDER BY k.id DESC""", (stavka_id,))]
    for r in rows:
        delovi = [RAZLOZI.get(r["razlog"], "")] if r["razlog"] else []
        if r["prodajna_cena"] is not None:
            delovi.append(novac.fmt(r["prodajna_cena"]) + "/kom")
            delovi += [x for x in (r["kupac"], r["tablice"]) if x]
        if r["nabavna_cena"] is not None:
            delovi.append(novac.fmt(r["nabavna_cena"]) + "/kom bez PDV")
            if r["dobavljac"]:
                delovi.append(r["dobavljac"])
        r["detalj"] = " – ".join(d for d in delovi if d)
    return rows
