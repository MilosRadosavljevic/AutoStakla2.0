"""Dobavljači, cenovnik (nabavne cene bez PDV-a, sa istorijom) i ulaz sa razlogom / nabavka."""
from __future__ import annotations

from datetime import date

from autostakla.better import novac
from autostakla.better.prodaja import RAZLOZI_ULAZ
from autostakla.core import audit
from autostakla.lager import repo
from autostakla.lager.repo import LagerError


def _clean(text: str | None) -> str | None:
    text = (text or "").strip()
    return text or None


# =====================================================================
# Dobavljači
# =====================================================================
def list_dobavljaci(conn, samo_aktivni: bool = True) -> list[dict]:
    sql = "SELECT * FROM dobavljac" + (" WHERE aktivno = 1" if samo_aktivni else "")
    return [dict(r) for r in conn.execute(sql + " ORDER BY naziv COLLATE NOCASE")]


def get_dobavljac(conn, dobavljac_id: int) -> dict:
    r = conn.execute("SELECT * FROM dobavljac WHERE id = ?", (dobavljac_id,)).fetchone()
    if not r:
        raise LagerError("Dobavljač ne postoji.")
    return dict(r)


def _proveri_naziv(conn, naziv: str | None, osim: int | None = None) -> str:
    naziv = _clean(naziv)
    if not naziv:
        raise LagerError("Naziv dobavljača je obavezan.")
    if conn.execute("SELECT 1 FROM dobavljac WHERE naziv = ? COLLATE NOCASE AND id IS NOT ?", (naziv, osim)).fetchone():
        raise LagerError(f"Dobavljač „{naziv}“ već postoji.")
    return naziv


def add_dobavljac(conn, naziv: str, telefon: str | None = None, email: str | None = None,
                  napomena: str | None = None) -> int:
    with repo.transaction(conn):
        naziv = _proveri_naziv(conn, naziv)
        did = conn.execute("INSERT INTO dobavljac (naziv, telefon, email, napomena) VALUES (?, ?, ?, ?)",
                           (naziv, _clean(telefon), _clean(email), _clean(napomena))).lastrowid
        audit.write(conn, "DODATO", entitet="dobavljac", entitet_id=did, opis=naziv)
    return did


def update_dobavljac(conn, dobavljac_id: int, naziv: str, telefon: str | None, email: str | None,
                     napomena: str | None) -> None:
    with repo.transaction(conn):
        staro = get_dobavljac(conn, dobavljac_id)
        naziv = _proveri_naziv(conn, naziv, dobavljac_id)
        conn.execute("UPDATE dobavljac SET naziv = ?, telefon = ?, email = ?, napomena = ?, "
                     "izmenjeno = datetime('now','localtime') WHERE id = ?",
                     (naziv, _clean(telefon), _clean(email), _clean(napomena), dobavljac_id))
        audit.write(conn, "IZMENA", entitet="dobavljac", entitet_id=dobavljac_id, opis=naziv, staro=staro)


def set_aktivan(conn, dobavljac_id: int, aktivan: bool) -> None:
    with repo.transaction(conn):
        d = get_dobavljac(conn, dobavljac_id)
        conn.execute("UPDATE dobavljac SET aktivno = ?, izmenjeno = datetime('now','localtime') WHERE id = ?",
                     (int(aktivan), dobavljac_id))
        audit.write(conn, "IZMENA", entitet="dobavljac", entitet_id=dobavljac_id,
                    opis=f"{d['naziv']}: {'aktiviran' if aktivan else 'deaktiviran'}")


# =====================================================================
# Cenovnik
# =====================================================================
def postavi_cenu(conn, staklo_id: int, dobavljac_id: int, cena: int, vazi_od: str | None = None,
                 napomena: str | None = None) -> int:
    """Nova nabavna cena (bez PDV-a). Stara ostaje u istoriji."""
    if cena is None or int(cena) < 0:
        raise LagerError("Cena ne može biti negativna.")
    vazi_od = vazi_od or date.today().isoformat()
    try:
        date.fromisoformat(vazi_od)
    except ValueError:
        raise LagerError(f"Datum „{vazi_od}“ nije ispravan.") from None
    with repo.transaction(conn):
        s = repo.get_staklo(conn, staklo_id)
        d = get_dobavljac(conn, dobavljac_id)
        cid = conn.execute("INSERT INTO cenovnik (staklo_id, dobavljac_id, cena, vazi_od, napomena) "
                           "VALUES (?, ?, ?, ?, ?)", (staklo_id, dobavljac_id, int(cena), vazi_od, _clean(napomena))
                           ).lastrowid
        audit.write(conn, "CENA", entitet="cenovnik", entitet_id=cid,
                    opis=f"{s.naziv} | {d['naziv']} | {novac.fmt(int(cena))} od {vazi_od}")
    return cid


def cene_za_staklo(conn, staklo_id: int, na_dan: str | None = None) -> list[dict]:
    """Važeća cena po dobavljaču (poslednja sa vazi_od <= na_dan), najjeftinija prva."""
    na_dan = na_dan or date.today().isoformat()
    return [dict(r) for r in conn.execute(
        """SELECT c.*, d.naziv AS dobavljac, d.aktivno
           FROM cenovnik c JOIN dobavljac d ON d.id = c.dobavljac_id
           WHERE c.staklo_id = ? AND c.id = (
               SELECT c2.id FROM cenovnik c2
               WHERE c2.staklo_id = c.staklo_id AND c2.dobavljac_id = c.dobavljac_id AND c2.vazi_od <= ?
               ORDER BY c2.vazi_od DESC, c2.id DESC LIMIT 1)
           ORDER BY c.cena, d.naziv COLLATE NOCASE""", (staklo_id, na_dan))]


def istorija_cena(conn, staklo_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT c.*, d.naziv AS dobavljac FROM cenovnik c JOIN dobavljac d ON d.id = c.dobavljac_id "
        "WHERE c.staklo_id = ? ORDER BY d.naziv COLLATE NOCASE, c.vazi_od DESC, c.id DESC", (staklo_id,))]


def vazeca_cena(conn, staklo_id: int, dobavljac_id: int) -> int | None:
    for c in cene_za_staklo(conn, staklo_id):
        if c["dobavljac_id"] == dobavljac_id:
            return c["cena"]
    return None


def najjeftiniji(conn, staklo_id: int) -> dict | None:
    for c in cene_za_staklo(conn, staklo_id):
        if c["aktivno"]:
            return c
    return None


# =====================================================================
# Ulaz sa razlogom / nabavka
# =====================================================================
def ulaz(conn, staklo_id: int, polica_id: int, kolicina: int, pozicija: int | None = None,
         napomena: str | None = None, razlog: str = "NABAVKA", dobavljac_id: int | None = None,
         nabavna_cena: int | None = None, dokument: str | None = None) -> int:
    """Ulaz kao u osnovnoj verziji + razlog; za NABAVKA i dobavljač/nabavna cena. Vraća id prve stavke."""
    if razlog not in RAZLOZI_ULAZ:
        raise LagerError("Izaberite razlog ulaza.")
    if razlog == "NABAVKA":
        if nabavna_cena is None:
            raise LagerError("Za nabavku upišite nabavnu cenu (bez PDV-a).")
        if int(nabavna_cena) < 0:
            raise LagerError("Nabavna cena ne može biti negativna.")
    with repo.transaction(conn):
        if dobavljac_id is not None:
            get_dobavljac(conn, dobavljac_id)
        pre = conn.execute("SELECT COALESCE(MAX(id), 0) FROM kretanje").fetchone()[0]
        prva = repo.ulaz(conn, staklo_id, polica_id, kolicina, pozicija, napomena)
        nova = [r[0] for r in conn.execute("SELECT id FROM kretanje WHERE id > ? AND vrsta = 'ULAZ'", (pre,))]
        for kid in nova:
            conn.execute("INSERT INTO kretanje_razlog (kretanje_id, razlog) VALUES (?, ?)", (kid, razlog))
            if razlog == "NABAVKA":
                conn.execute("INSERT INTO nabavka (kretanje_id, dobavljac_id, nabavna_cena, dokument) "
                             "VALUES (?, ?, ?, ?)", (kid, dobavljac_id, int(nabavna_cena), _clean(dokument)))
        if razlog == "NABAVKA":
            audit.write(conn, "NABAVKA", entitet="kretanje", entitet_id=nova[0] if nova else None,
                        opis=f"{len(nova)} kom × {novac.fmt(int(nabavna_cena))} bez PDV"
                             + (f" | dokument {dokument}" if _clean(dokument) else ""))
    return prva


def prosecna_nabavna(conn, staklo_id: int, do_datuma: str | None = None) -> int | None:
    """Prosečna ponderisana nabavna cena (bez PDV-a) svih nabavki tog stakla do datuma (uključivo)."""
    s, n = conn.execute(
        """SELECT SUM(n.nabavna_cena * k.kolicina), SUM(k.kolicina)
           FROM nabavka n JOIN kretanje k ON k.id = n.kretanje_id
           JOIN lager_stavka ls ON ls.id = k.lager_stavka_id
           WHERE ls.staklo_id = ? AND (? IS NULL OR substr(k.datum, 1, 10) <= ?)""",
        (staklo_id, do_datuma, do_datuma)).fetchone()
    if not n:
        return None
    return (s + n // 2) // n
