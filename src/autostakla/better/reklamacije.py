"""Reklamacije vezane za prodaju: statusi, ishod, trošak. Uticaj na lager ide kroz obične ulaze/izlaze sa razlogom
(zamena = izlaz „Zamena po reklamaciji“, vraćeno od kupca = ulaz „Vraćeno od kupca“, dobavljaču = izlaz „Vraćeno
dobavljaču“)."""
from __future__ import annotations

from autostakla.better import prodaja
from autostakla.core import audit
from autostakla.lager import repo
from autostakla.lager.repo import LagerError

STATUSI = {"PRIJAVLJENA": "Prijavljena", "KOD_DOBAVLJACA": "Kod dobavljača", "ODOBRENA": "Odobrena",
           "ODBIJENA": "Odbijena", "RESENA": "Rešena"}
ISHODI = {"ZAMENA": "Zamena stakla", "POVRAT_NOVCA": "Povrat novca", "POPRAVKA": "Popravka"}
PRELAZI = {"PRIJAVLJENA": ("KOD_DOBAVLJACA", "ODOBRENA", "ODBIJENA"),
           "KOD_DOBAVLJACA": ("ODOBRENA", "ODBIJENA"),
           "ODOBRENA": ("RESENA",),
           "ODBIJENA": (),
           "RESENA": ()}
ZATVORENI = ("ODBIJENA", "RESENA")


def _clean(text: str | None) -> str | None:
    text = (text or "").strip()
    return text or None


def dobavljac_za_prodaju(conn, prodaja_id: int) -> int | None:
    """Od koga je nabavljen prodati komad (prati i premeštanja do prvog ulaza)."""
    stavka = prodaja.get_prodaja(conn, prodaja_id)["lager_stavka_id"]
    for _ in range(50):
        prvo = conn.execute("SELECT id, vrsta, veza_id FROM kretanje WHERE lager_stavka_id = ? ORDER BY id LIMIT 1",
                            (stavka,)).fetchone()
        if not prvo:
            return None
        if prvo["vrsta"] == "PREMESTANJE" and prvo["veza_id"]:
            stavka = conn.execute("SELECT lager_stavka_id FROM kretanje WHERE id = ?", (prvo["veza_id"],)).fetchone()[0]
            continue
        r = conn.execute("SELECT dobavljac_id FROM nabavka WHERE kretanje_id = ?", (prvo["id"],)).fetchone()
        return r[0] if r else None
    return None


def nova(conn, prodaja_id: int, opis: str, dobavljac_id: int | None = None) -> int:
    if not _clean(opis):
        raise LagerError("Upišite šta je problem (opis reklamacije).")
    with repo.transaction(conn):
        p = prodaja.get_prodaja(conn, prodaja_id)
        if dobavljac_id is None:
            dobavljac_id = dobavljac_za_prodaju(conn, prodaja_id)
        rid = conn.execute("INSERT INTO reklamacija (prodaja_id, opis, dobavljac_id) VALUES (?, ?, ?)",
                           (prodaja_id, _clean(opis), dobavljac_id)).lastrowid
        audit.write(conn, "REKLAMACIJA", entitet="reklamacija", entitet_id=rid,
                    opis=f"Prijavljena: {p['staklo']} | {_clean(opis)}")
    return rid


def get(conn, reklamacija_id: int) -> dict:
    r = conn.execute(_SQL + " WHERE r.id = ?", (reklamacija_id,)).fetchone()
    if not r:
        raise LagerError("Reklamacija ne postoji.")
    return dict(r)


def promeni_status(conn, reklamacija_id: int, status: str, ishod: str | None = None, trosak: int | None = None,
                   napomena: str | None = None) -> None:
    if ishod is not None and ishod not in ISHODI:
        raise LagerError("Nepoznat ishod reklamacije.")
    if trosak is not None and int(trosak) < 0:
        raise LagerError("Trošak ne može biti negativan.")
    with repo.transaction(conn):
        r = get(conn, reklamacija_id)
        if status not in PRELAZI.get(r["status"], ()):
            raise LagerError(f"Reklamacija je „{STATUSI[r['status']]}“ – ne može da pređe u "
                             f"„{STATUSI.get(status, status)}“.")
        ishod = ishod or r["ishod"]
        if status == "ODOBRENA" and not ishod:
            raise LagerError("Za odobrenu reklamaciju izaberite ishod (zamena, povrat novca, popravka).")
        conn.execute(
            "UPDATE reklamacija SET status = ?, ishod = ?, trosak = ?, napomena = ?, "
            "zatvoreno = CASE WHEN ? THEN datetime('now','localtime') ELSE zatvoreno END, "
            "izmenjeno = datetime('now','localtime') WHERE id = ?",
            (status, ishod, int(trosak) if trosak is not None else r["trosak"],
             _clean(napomena) if napomena is not None else r["napomena"], int(status in ZATVORENI), reklamacija_id))
        audit.write(conn, "REKLAMACIJA", entitet="reklamacija", entitet_id=reklamacija_id,
                    opis=f"{STATUSI[r['status']]} → {STATUSI[status]}" + (f" | {ISHODI[ishod]}" if ishod else "")
                         + (f" | {_clean(napomena)}" if _clean(napomena) else ""))


_SQL = """
SELECT r.*, d.naziv AS dobavljac, s.naziv AS staklo, ku.ime AS kupac, ku.telefon, p.tablice, p.vozilo,
       k.datum AS datum_prodaje, p.cena
FROM reklamacija r
JOIN prodaja p        ON p.id = r.prodaja_id
JOIN kretanje k       ON k.id = p.kretanje_id
JOIN lager_stavka ls  ON ls.id = k.lager_stavka_id
JOIN staklo s         ON s.id = ls.staklo_id
LEFT JOIN kupac ku    ON ku.id = p.kupac_id
LEFT JOIN dobavljac d ON d.id = r.dobavljac_id
"""


def list_reklamacije(conn, samo_otvorene: bool = False) -> list[dict]:
    sql = _SQL + (" WHERE r.status NOT IN ('ODBIJENA', 'RESENA')" if samo_otvorene else "")
    return [dict(r) for r in conn.execute(sql + " ORDER BY r.datum_prijave DESC, r.id DESC")]


def istorija(conn, reklamacija_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT vreme, opis FROM audit_log WHERE entitet = 'reklamacija' AND entitet_id = ? ORDER BY id",
        (reklamacija_id,))]
