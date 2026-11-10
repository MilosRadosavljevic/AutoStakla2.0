"""Rad sa lagerom: skladišta, police, stakla, ulaz/izlaz/korekcija/premeštanje, pretraga.

Svaka izmena ide u transakciji zajedno sa upisom u audit_log.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field

from autostakla.core import audit
from autostakla.lager import search

TIPOVI = {"vetrobran": "Vetrobran", "zadnje": "Zadnje", "bocno": "Bočno", "ostalo": "Ostalo"}


class LagerError(Exception):
    """Greška sa porukom razumljivom korisniku."""


@contextmanager
def transaction(conn: sqlite3.Connection):
    if conn.in_transaction:  # već smo u transakciji (ugnježdeno)
        yield
        return
    conn.execute("BEGIN")
    try:
        yield
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def _row(conn, sql, params=()) -> dict | None:
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None


def _clean(text: str | None) -> str | None:
    text = (text or "").strip()
    return text or None


# =====================================================================
# Skladišta
# =====================================================================
def list_skladista(conn, samo_aktivna: bool = True) -> list[dict]:
    sql = "SELECT * FROM skladiste"
    if samo_aktivna:
        sql += " WHERE aktivno = 1"
    return [dict(r) for r in conn.execute(sql + " ORDER BY redosled, id")]


def get_skladiste(conn, skladiste_id: int) -> dict:
    s = _row(conn, "SELECT * FROM skladiste WHERE id = ?", (skladiste_id,))
    if not s:
        raise LagerError("Skladište ne postoji.")
    return s


def _check_naziv_skladista(conn, naziv: str, osim_id: int | None = None) -> str:
    naziv = _clean(naziv)
    if not naziv:
        raise LagerError("Naziv skladišta je obavezan.")
    dup = _row(conn, "SELECT id, aktivno FROM skladiste WHERE naziv = ? AND id IS NOT ?", (naziv, osim_id))
    if dup:
        extra = " (obrisano je, ali je ostalo u istoriji)" if not dup["aktivno"] else ""
        raise LagerError(f"Skladište „{naziv}“ već postoji{extra}.")
    return naziv


def add_skladiste(conn, naziv: str, opis: str | None = None, prva_polica: str = "Polica 1") -> int:
    with transaction(conn):
        naziv = _check_naziv_skladista(conn, naziv)
        red = conn.execute("SELECT COALESCE(MAX(redosled), 0) + 1 FROM skladiste").fetchone()[0]
        sid = conn.execute(
            "INSERT INTO skladiste (naziv, opis, redosled) VALUES (?, ?, ?)", (naziv, _clean(opis), red)
        ).lastrowid
        audit.write(conn, "DODATO", entitet="skladiste", entitet_id=sid, opis=naziv,
                    novo={"naziv": naziv, "opis": opis})
        if prva_polica:
            add_polica(conn, sid, prva_polica)
    return sid


def update_skladiste(conn, skladiste_id: int, naziv: str, opis: str | None) -> None:
    with transaction(conn):
        staro = get_skladiste(conn, skladiste_id)
        naziv = _check_naziv_skladista(conn, naziv, skladiste_id)
        conn.execute(
            "UPDATE skladiste SET naziv = ?, opis = ?, izmenjeno = datetime('now','localtime') WHERE id = ?",
            (naziv, _clean(opis), skladiste_id),
        )
        audit.write(conn, "IZMENA", entitet="skladiste", entitet_id=skladiste_id, opis=naziv,
                    staro={"naziv": staro["naziv"], "opis": staro["opis"]},
                    novo={"naziv": naziv, "opis": _clean(opis)})


def _stanje_na(conn, where: str, params) -> int:
    return conn.execute(f"SELECT COALESCE(SUM(kolicina), 0) FROM v_stanje WHERE {where}", params).fetchone()[0]


def _ima_istoriju(conn, where: str, params) -> bool:
    return conn.execute(f"SELECT COUNT(*) FROM v_stanje WHERE {where}", params).fetchone()[0] > 0


def delete_skladiste(conn, skladiste_id: int) -> str:
    """Prazno skladište bez istorije se briše; sa istorijom se samo gasi. Vraća 'obrisano'/'ugaseno'."""
    with transaction(conn):
        s = get_skladiste(conn, skladiste_id)
        kol = _stanje_na(conn, "skladiste_id = ?", (skladiste_id,))
        if kol > 0:
            raise LagerError(
                f"Na skladištu „{s['naziv']}“ ima još {kol} stakala.\n"
                "Prvo ih premestite ili razdužite, pa onda obrišite skladište."
            )
        if _ima_istoriju(conn, "skladiste_id = ?", (skladiste_id,)):
            conn.execute("UPDATE skladiste SET aktivno = 0, izmenjeno = datetime('now','localtime') WHERE id = ?",
                         (skladiste_id,))
            conn.execute("UPDATE polica SET aktivno = 0 WHERE skladiste_id = ?", (skladiste_id,))
            rezultat = "ugaseno"
        else:
            conn.execute("DELETE FROM polica WHERE skladiste_id = ?", (skladiste_id,))
            conn.execute("DELETE FROM skladiste WHERE id = ?", (skladiste_id,))
            rezultat = "obrisano"
        audit.write(conn, "BRISANJE", entitet="skladiste", entitet_id=skladiste_id,
                    opis=f"{s['naziv']} ({rezultat})", staro=s)
    return rezultat


def move_skladiste(conn, skladiste_id: int, smer: int) -> None:
    _move(conn, "skladiste", skladiste_id, smer, "aktivno = 1")


# =====================================================================
# Police
# =====================================================================
def list_police(conn, skladiste_id: int, samo_aktivne: bool = True) -> list[dict]:
    sql = "SELECT * FROM polica WHERE skladiste_id = ?"
    if samo_aktivne:
        sql += " AND aktivno = 1"
    return [dict(r) for r in conn.execute(sql + " ORDER BY redosled, id", (skladiste_id,))]


def get_polica(conn, polica_id: int) -> dict:
    p = _row(conn, "SELECT * FROM polica WHERE id = ?", (polica_id,))
    if not p:
        raise LagerError("Polica ne postoji.")
    return p


def _check_naziv_police(conn, skladiste_id: int, naziv: str, osim_id: int | None = None) -> str:
    naziv = _clean(naziv)
    if not naziv:
        raise LagerError("Naziv police je obavezan.")
    if _row(conn, "SELECT id FROM polica WHERE skladiste_id = ? AND naziv = ? AND id IS NOT ?",
            (skladiste_id, naziv, osim_id)):
        raise LagerError(f"Polica „{naziv}“ već postoji na ovom skladištu.")
    return naziv


def add_polica(conn, skladiste_id: int, naziv: str, opis: str | None = None) -> int:
    with transaction(conn):
        get_skladiste(conn, skladiste_id)
        naziv = _check_naziv_police(conn, skladiste_id, naziv)
        red = conn.execute("SELECT COALESCE(MAX(redosled), 0) + 1 FROM polica WHERE skladiste_id = ?",
                           (skladiste_id,)).fetchone()[0]
        pid = conn.execute(
            "INSERT INTO polica (skladiste_id, naziv, opis, redosled) VALUES (?, ?, ?, ?)",
            (skladiste_id, naziv, _clean(opis), red),
        ).lastrowid
        audit.write(conn, "DODATO", entitet="polica", entitet_id=pid, opis=naziv,
                    novo={"skladiste_id": skladiste_id, "naziv": naziv, "opis": opis})
    return pid


def update_polica(conn, polica_id: int, naziv: str, opis: str | None) -> None:
    with transaction(conn):
        staro = get_polica(conn, polica_id)
        naziv = _check_naziv_police(conn, staro["skladiste_id"], naziv, polica_id)
        conn.execute("UPDATE polica SET naziv = ?, opis = ?, izmenjeno = datetime('now','localtime') WHERE id = ?",
                     (naziv, _clean(opis), polica_id))
        audit.write(conn, "IZMENA", entitet="polica", entitet_id=polica_id, opis=naziv,
                    staro={"naziv": staro["naziv"], "opis": staro["opis"]},
                    novo={"naziv": naziv, "opis": _clean(opis)})


def delete_polica(conn, polica_id: int) -> str:
    with transaction(conn):
        p = get_polica(conn, polica_id)
        kol = _stanje_na(conn, "polica_id = ?", (polica_id,))
        if kol > 0:
            raise LagerError(f"Na polici „{p['naziv']}“ ima još {kol} stakala.\n"
                             "Prvo ih premestite ili razdužite.")
        if _ima_istoriju(conn, "polica_id = ?", (polica_id,)):
            conn.execute("UPDATE polica SET aktivno = 0, izmenjeno = datetime('now','localtime') WHERE id = ?",
                         (polica_id,))
            rezultat = "ugaseno"
        else:
            conn.execute("DELETE FROM polica WHERE id = ?", (polica_id,))
            rezultat = "obrisano"
        audit.write(conn, "BRISANJE", entitet="polica", entitet_id=polica_id,
                    opis=f"{p['naziv']} ({rezultat})", staro=p)
    return rezultat


def move_polica(conn, polica_id: int, smer: int) -> None:
    p = get_polica(conn, polica_id)
    _move(conn, "polica", polica_id, smer, f"aktivno = 1 AND skladiste_id = {int(p['skladiste_id'])}")


def _move(conn, table: str, item_id: int, smer: int, scope: str) -> None:
    """Pomeri stavku gore (smer=-1) ili dole (+1) i prenumeriše redosled 1..n."""
    with transaction(conn):
        ids = [r[0] for r in conn.execute(f"SELECT id FROM {table} WHERE {scope} ORDER BY redosled, id")]
        if item_id not in ids:
            return
        i = ids.index(item_id)
        j = i + smer
        if 0 <= j < len(ids):
            ids[i], ids[j] = ids[j], ids[i]
        for n, x in enumerate(ids, 1):
            conn.execute(f"UPDATE {table} SET redosled = ? WHERE id = ?", (n, x))


# =====================================================================
# Stakla
# =====================================================================
@dataclass
class Vozilo:
    marka: str
    model: str | None = None
    generacija: str | None = None
    godina_od: int | None = None
    godina_do: int | None = None


@dataclass
class Staklo:
    naziv: str
    tip: str = "vetrobran"
    senzor: bool = False
    senzor_opis: str | None = None
    kamera: bool = False
    kamera_opis: str | None = None
    plocica: str | None = None
    polovno: bool = False
    napomena: str | None = None
    vozila: list[Vozilo] = field(default_factory=list)
    id: int | None = None


def _validate_staklo(s: Staklo) -> None:
    if not _clean(s.naziv):
        raise LagerError("Naziv stakla je obavezan.")
    if s.tip not in TIPOVI:
        raise LagerError(f"Nepoznat tip stakla: {s.tip}")
    for v in s.vozila:
        if not _clean(v.marka):
            raise LagerError("Svako vozilo mora imati marku.")
        if v.godina_od and v.godina_do and v.godina_od > v.godina_do:
            raise LagerError(f"{v.marka} {v.model or ''}: godina od je veća od godine do.")


def _staklo_values(s: Staklo) -> tuple:
    return (_clean(s.naziv), s.tip, int(s.senzor), _clean(s.senzor_opis), int(s.kamera),
            _clean(s.kamera_opis), _clean(s.plocica), int(s.polovno), _clean(s.napomena))


def _save_vozila(conn, staklo_id: int, vozila: list[Vozilo]) -> None:
    conn.execute("DELETE FROM staklo_vozilo WHERE staklo_id = ?", (staklo_id,))
    for v in vozila:
        conn.execute(
            "INSERT INTO staklo_vozilo (staklo_id, marka, model, generacija, godina_od, godina_do) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (staklo_id, _clean(v.marka), _clean(v.model), _clean(v.generacija), v.godina_od, v.godina_do),
        )


def add_staklo(conn, s: Staklo) -> int:
    _validate_staklo(s)
    with transaction(conn):
        sid = conn.execute(
            "INSERT INTO staklo (naziv, tip, senzor, senzor_opis, kamera, kamera_opis, plocica, polovno, napomena) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", _staklo_values(s),
        ).lastrowid
        _save_vozila(conn, sid, s.vozila)
        audit.write(conn, "DODATO", entitet="staklo", entitet_id=sid, opis=s.naziv, novo=_as_dict(s))
    return sid


def update_staklo(conn, s: Staklo) -> None:
    _validate_staklo(s)
    with transaction(conn):
        staro = get_staklo(conn, s.id)
        conn.execute(
            "UPDATE staklo SET naziv = ?, tip = ?, senzor = ?, senzor_opis = ?, kamera = ?, kamera_opis = ?, "
            "plocica = ?, polovno = ?, napomena = ?, izmenjeno = datetime('now','localtime') WHERE id = ?",
            _staklo_values(s) + (s.id,),
        )
        _save_vozila(conn, s.id, s.vozila)
        audit.write(conn, "IZMENA", entitet="staklo", entitet_id=s.id, opis=s.naziv,
                    staro=_as_dict(staro), novo=_as_dict(s))


def get_staklo(conn, staklo_id: int) -> Staklo:
    r = _row(conn, "SELECT * FROM staklo WHERE id = ?", (staklo_id,))
    if not r:
        raise LagerError("Staklo ne postoji.")
    vozila = [Vozilo(v["marka"], v["model"], v["generacija"], v["godina_od"], v["godina_do"])
              for v in conn.execute("SELECT * FROM staklo_vozilo WHERE staklo_id = ? ORDER BY id", (staklo_id,))]
    return Staklo(r["naziv"], r["tip"], bool(r["senzor"]), r["senzor_opis"], bool(r["kamera"]),
                  r["kamera_opis"], r["plocica"], bool(r["polovno"]), r["napomena"], vozila, r["id"])


def find_staklo_by_naziv(conn, naziv: str) -> int | None:
    r = conn.execute("SELECT id FROM staklo WHERE naziv = ? COLLATE NOCASE AND aktivno = 1 ORDER BY id LIMIT 1",
                     (_clean(naziv),)).fetchone()
    return r[0] if r else None


def list_stakla(conn) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT id, naziv FROM staklo WHERE aktivno = 1 ORDER BY naziv")]


def _as_dict(s: Staklo) -> dict:
    d = dict(s.__dict__)
    d["vozila"] = [v.__dict__ for v in s.vozila]
    return d


# =====================================================================
# Kretanja
# =====================================================================
def stanje_stavke(conn, stavka_id: int) -> int:
    r = conn.execute("SELECT kolicina FROM v_stanje WHERE lager_stavka_id = ?", (stavka_id,)).fetchone()
    if r is None:
        raise LagerError("Stavka lagera ne postoji.")
    return r[0]


def _opis_stavke(conn, stavka_id: int) -> str:
    r = conn.execute(
        "SELECT s.naziv, sk.naziv, p.naziv, ls.pozicija FROM lager_stavka ls "
        "JOIN staklo s ON s.id = ls.staklo_id JOIN polica p ON p.id = ls.polica_id "
        "JOIN skladiste sk ON sk.id = p.skladiste_id WHERE ls.id = ?", (stavka_id,)).fetchone()
    poz = f", poz. {r[3]}" if r[3] else ""
    return f"{r[0]} – {r[1]} / {r[2]}{poz}"


def _check_kolicina(kolicina: int) -> int:
    try:
        kolicina = int(kolicina)
    except (TypeError, ValueError):
        raise LagerError("Količina mora biti ceo broj.") from None
    if kolicina <= 0:
        raise LagerError("Količina mora biti veća od nule.")
    return kolicina


def _kretanje(conn, stavka_id, kolicina, vrsta, napomena=None, veza_id=None) -> int:
    kid = conn.execute(
        "INSERT INTO kretanje (lager_stavka_id, kolicina, vrsta, napomena, veza_id) VALUES (?, ?, ?, ?, ?)",
        (stavka_id, kolicina, vrsta, _clean(napomena), veza_id),
    ).lastrowid
    audit.write(conn, vrsta, entitet="kretanje", entitet_id=kid,
                opis=f"{kolicina:+d} | {_opis_stavke(conn, stavka_id)}" + (f" | {napomena}" if napomena else ""))
    return kid


# ---------------------------------------------------------------------
# Pozicije: redni broj ide kroz CELO skladište (preko svih polica, po redosledu polica).
# Ubacivanje na poziciju P pomera sve od P naniže; kad mesto ostane prazno, ostali se penju.
# ---------------------------------------------------------------------
def _stavka(conn, stavka_id: int) -> dict:
    r = _row(conn, "SELECT ls.*, p.skladiste_id FROM lager_stavka ls JOIN polica p ON p.id = ls.polica_id "
                   "WHERE ls.id = ?", (stavka_id,))
    if not r:
        raise LagerError("Stavka lagera ne postoji.")
    return r


def _max_pozicija(conn, skladiste_id: int) -> int:
    return conn.execute(
        "SELECT COALESCE(MAX(ls.pozicija), 0) FROM lager_stavka ls JOIN polica p ON p.id = ls.polica_id "
        "WHERE p.skladiste_id = ?", (skladiste_id,)).fetchone()[0]


def polica_raspon(conn, polica_id: int, osim_stavke: int | None = None) -> tuple[int, int]:
    """Dozvoljene pozicije za ubacivanje na ovu policu: (od, do). 'do' = odmah posle poslednjeg na polici."""
    p = get_polica(conn, polica_id)
    r = conn.execute(
        "SELECT MIN(pozicija), MAX(pozicija) FROM lager_stavka WHERE polica_id = ? AND pozicija IS NOT NULL "
        "AND id IS NOT ?", (polica_id, osim_stavke)).fetchone()
    if r[0] is not None:
        od, do = r[0], r[1] + 1
    else:
        # prazna polica: posle poslednjeg broja na policama iznad nje
        prev = conn.execute(
            "SELECT COALESCE(MAX(ls.pozicija), 0) FROM lager_stavka ls JOIN polica x ON x.id = ls.polica_id "
            "WHERE x.skladiste_id = ? AND (x.redosled < ? OR (x.redosled = ? AND x.id < ?)) AND ls.id IS NOT ?",
            (p["skladiste_id"], p["redosled"], p["redosled"], p["id"], osim_stavke)).fetchone()[0]
        od = do = prev + 1
    if osim_stavke is not None:
        # brojevi kakvi će biti kad se ta stavka skine sa svog mesta (svi ispod nje se penju za 1)
        s = _stavka(conn, osim_stavke)
        if s["pozicija"] is not None and s["skladiste_id"] == p["skladiste_id"]:
            od -= od > s["pozicija"]
            do -= do > s["pozicija"]
    return od, do


def _napravi_mesto(conn, polica_id: int, pozicija: int | None, broj: int) -> int:
    """Oslobodi 'broj' uzastopnih pozicija počev od 'pozicija' (pomeri ostale naniže). Vraća početnu poziciju."""
    od, do = polica_raspon(conn, polica_id)
    p = do if pozicija is None else max(od, min(int(pozicija), do))
    sk = get_polica(conn, polica_id)["skladiste_id"]
    conn.execute(
        "UPDATE lager_stavka SET pozicija = pozicija + ? WHERE pozicija >= ? "
        "AND polica_id IN (SELECT id FROM polica WHERE skladiste_id = ?)", (broj, p, sk))
    return p


def _oslobodi_poziciju(conn, stavka_id: int) -> None:
    """Stavka više nema stakla (ili se seli): skini joj broj, a one ispod pomeri gore."""
    s = _stavka(conn, stavka_id)
    if s["pozicija"] is None:
        return
    conn.execute("UPDATE lager_stavka SET pozicija = NULL WHERE id = ?", (stavka_id,))
    # ako na istom broju stoji još nešto (npr. sa papira „2 bez + 1 senzor"), broj ostaje zauzet
    deli = conn.execute(
        "SELECT COUNT(*) FROM lager_stavka ls JOIN polica p ON p.id = ls.polica_id "
        "WHERE p.skladiste_id = ? AND ls.pozicija = ?", (s["skladiste_id"], s["pozicija"])).fetchone()[0]
    if not deli:
        conn.execute(
            "UPDATE lager_stavka SET pozicija = pozicija - 1 WHERE pozicija > ? "
            "AND polica_id IN (SELECT id FROM polica WHERE skladiste_id = ?)", (s["pozicija"], s["skladiste_id"]))


def _nova_mesta(conn, staklo_id: int, polica_id: int, pozicija: int | None, kolicina: int,
                vrsta: str, napomena: str | None, stavka_napomena: str | None = None,
                veza_id: int | None = None) -> list[int]:
    """Svaki komad dobija svoje mesto (svoj broj); ostali se pomeraju naniže za 'kolicina'."""
    p = _napravi_mesto(conn, polica_id, pozicija, kolicina)
    ids = []
    for i in range(kolicina):
        sid = conn.execute(
            "INSERT INTO lager_stavka (staklo_id, polica_id, pozicija, napomena) VALUES (?, ?, ?, ?)",
            (staklo_id, polica_id, p + i, _clean(stavka_napomena))).lastrowid
        _kretanje(conn, sid, 1, vrsta, napomena, veza_id=veza_id)
        ids.append(sid)
    return ids


def ulaz(conn, staklo_id: int, polica_id: int, kolicina: int, pozicija: int | None = None,
         napomena: str | None = None, vrsta: str = "ULAZ") -> int:
    """Ulaz: svaki komad dobija svoj broj od 'pozicija' (None = na kraj police); ostali se pomeraju.
    Vraća id prve nove stavke."""
    kolicina = _check_kolicina(kolicina)
    with transaction(conn):
        get_staklo(conn, staklo_id)
        get_polica(conn, polica_id)
        return _nova_mesta(conn, staklo_id, polica_id, pozicija, kolicina, vrsta, napomena)[0]


def izlaz(conn, stavka_id: int, kolicina: int, napomena: str | None = None) -> None:
    kolicina = _check_kolicina(kolicina)
    with transaction(conn):
        ima = stanje_stavke(conn, stavka_id)
        if kolicina > ima:
            raise LagerError(f"Na stanju je {ima} kom, ne može izaći {kolicina}.")
        _kretanje(conn, stavka_id, -kolicina, "IZLAZ", napomena)
        if ima == kolicina:
            _oslobodi_poziciju(conn, stavka_id)


def korekcija(conn, stavka_id: int, nova_kolicina: int, napomena: str | None = None) -> None:
    try:
        nova_kolicina = int(nova_kolicina)
    except (TypeError, ValueError):
        raise LagerError("Količina mora biti ceo broj.") from None
    if nova_kolicina < 0:
        raise LagerError("Količina ne može biti manja od nule.")
    with transaction(conn):
        ima = stanje_stavke(conn, stavka_id)
        razlika = nova_kolicina - ima
        if razlika == 0:
            raise LagerError("Količina je ista kao trenutna – nema šta da se ispravi.")
        s = _stavka(conn, stavka_id)
        if ima <= 0 < nova_kolicina and s["pozicija"] is None:
            # vraća se nešto čega nije bilo – dobija broj na kraju svoje police
            p = _napravi_mesto(conn, s["polica_id"], None, 1)
            conn.execute("UPDATE lager_stavka SET pozicija = ? WHERE id = ?", (p, stavka_id))
        _kretanje(conn, stavka_id, razlika, "KOREKCIJA", napomena)
        if nova_kolicina == 0:
            _oslobodi_poziciju(conn, stavka_id)


def premesti(conn, stavka_id: int, kolicina: int, polica_id: int, pozicija: int | None = None,
             napomena: str | None = None) -> int:
    """Premešta komade na drugu policu/poziciju; svaki premešteni komad dobija svoj broj."""
    kolicina = _check_kolicina(kolicina)
    with transaction(conn):
        ima = stanje_stavke(conn, stavka_id)
        if kolicina > ima:
            raise LagerError(f"Na stanju je {ima} kom, ne može se premestiti {kolicina}.")
        s = _stavka(conn, stavka_id)
        get_polica(conn, polica_id)
        k1 = _kretanje(conn, stavka_id, -kolicina, "PREMESTANJE", napomena)
        if ima == kolicina:
            _oslobodi_poziciju(conn, stavka_id)
        nove = _nova_mesta(conn, s["staklo_id"], polica_id, pozicija, kolicina, "PREMESTANJE", napomena,
                           stavka_napomena=s["napomena"], veza_id=k1)
        k2 = conn.execute("SELECT id FROM kretanje WHERE lager_stavka_id = ? ORDER BY id LIMIT 1",
                          (nove[0],)).fetchone()[0]
        conn.execute("UPDATE kretanje SET veza_id = ? WHERE id = ?", (k2, k1))
    return nove[0]


def izmeni_mesto(conn, stavka_id: int, polica_id: int, pozicija: int | None, napomena: str | None) -> None:
    """Izmena napomene i/ili pomeranje stavke na drugu policu/poziciju u ISTOM skladištu (ostali se pomeraju)."""
    with transaction(conn):
        s = _stavka(conn, stavka_id)
        nova_p = get_polica(conn, polica_id)
        if nova_p["skladiste_id"] != s["skladiste_id"]:
            raise LagerError("Za drugo skladište koristite „Premesti“.")
        staro = {"polica_id": s["polica_id"], "pozicija": s["pozicija"], "napomena": s["napomena"]}
        conn.execute("UPDATE lager_stavka SET napomena = ? WHERE id = ?", (_clean(napomena), stavka_id))
        if s["pozicija"] is not None and (polica_id != s["polica_id"] or pozicija != s["pozicija"]):
            _oslobodi_poziciju(conn, stavka_id)
            conn.execute("UPDATE lager_stavka SET polica_id = ? WHERE id = ?", (polica_id, stavka_id))
            p = _napravi_mesto(conn, polica_id, pozicija, 1)
            conn.execute("UPDATE lager_stavka SET pozicija = ? WHERE id = ?", (p, stavka_id))
        novo = _stavka(conn, stavka_id)
        audit.write(conn, "IZMENA", entitet="lager_stavka", entitet_id=stavka_id,
                    opis=_opis_stavke(conn, stavka_id), staro=staro,
                    novo={"polica_id": novo["polica_id"], "pozicija": novo["pozicija"],
                          "napomena": novo["napomena"]})


def istorija(conn, stavka_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        "SELECT datum, vrsta, kolicina, napomena FROM kretanje WHERE lager_stavka_id = ? ORDER BY id DESC",
        (stavka_id,))]


# =====================================================================
# Pretraga
# =====================================================================
@dataclass
class Filter:
    tekst: str = ""
    skladiste_id: int | None = None
    polica_id: int | None = None
    tip: str | None = None
    senzor: bool | None = None
    kamera: bool | None = None
    polovno: bool | None = None
    samo_na_stanju: bool = True


_SEARCH_SQL = """
SELECT v.lager_stavka_id, v.kolicina, v.pozicija, v.stavka_napomena,
       s.id AS staklo_id, s.naziv, s.tip, s.senzor, s.senzor_opis, s.kamera, s.kamera_opis,
       s.plocica, s.polovno, s.napomena,
       sk.id AS skladiste_id, sk.naziv AS skladiste, sk.redosled AS sk_red,
       p.id AS polica_id, p.naziv AS polica, p.redosled AS p_red,
       (SELECT group_concat(COALESCE(sv.marka,'') || ' ' || COALESCE(sv.model,'') || ' ' || COALESCE(sv.generacija,''), ' ')
          FROM staklo_vozilo sv WHERE sv.staklo_id = s.id) AS vozila
FROM v_stanje v
JOIN staklo s     ON s.id = v.staklo_id
JOIN polica p     ON p.id = v.polica_id
JOIN skladiste sk ON sk.id = p.skladiste_id
WHERE sk.aktivno = 1 AND p.aktivno = 1
"""


def pretraga(conn, f: Filter) -> list[dict]:
    sql, params = _SEARCH_SQL, []
    for col, val in (("sk.id", f.skladiste_id), ("p.id", f.polica_id), ("s.tip", f.tip)):
        if val is not None:
            sql += f" AND {col} = ?"
            params.append(val)
    for col, val in (("s.senzor", f.senzor), ("s.kamera", f.kamera), ("s.polovno", f.polovno)):
        if val is not None:
            sql += f" AND {col} = ?"
            params.append(int(val))
    if f.samo_na_stanju:
        sql += " AND v.kolicina > 0"
    sql += " ORDER BY sk.redosled, sk.id, p.redosled, p.id, v.pozicija IS NULL, v.pozicija, s.naziv"

    rows = [dict(r) for r in conn.execute(sql, params)]
    q = search.words(f.tekst)
    if not q:
        return rows
    result = []
    for r in rows:
        text = " ".join(str(r[k] or "") for k in (
            "naziv", "napomena", "stavka_napomena", "senzor_opis", "kamera_opis", "plocica",
            "vozila", "skladiste", "polica"))
        if r["senzor"]:
            text += " senzor"
        if r["kamera"]:
            text += " kamera"
        if r["polovno"]:
            text += " polovno"
        if search.matches(q, search.words(text)):
            result.append(r)
    return result
