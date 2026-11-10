"""Vozila iz naziva stakla: „Fiat Ducato - Citroen Jumper - Peugeot Boxer 06-“ -> tri vozila, 2006–.

Popunjava staklo_vozilo (treba za analitiku „za koje automobile“ i za pretragu po modelu).
Ono što parser ne prepozna sigurno ide korisniku na proveru, ne upisuje se samo.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from autostakla.lager import repo
from autostakla.lager.repo import Vozilo

MARKE = {
    "vw": "VW", "volkswagen": "VW", "fiat": "Fiat", "citroen": "Citroen", "citroën": "Citroen",
    "peugeot": "Peugeot", "pezo": "Peugeot", "pežo": "Peugeot", "renault": "Renault", "opel": "Opel",
    "ford": "Ford", "mercedes": "Mercedes", "bmw": "BMW", "audi": "Audi", "skoda": "Skoda", "škoda": "Skoda",
    "seat": "Seat", "toyota": "Toyota", "hyundai": "Hyundai", "hjundai": "Hyundai", "hundai": "Hyundai",
    "reno": "Renault", "kia": "Kia", "nissan": "Nissan", "mazda": "Mazda",
    "honda": "Honda", "dacia": "Dacia", "iveco": "Iveco", "volvo": "Volvo", "suzuki": "Suzuki",
    "mitsubishi": "Mitsubishi", "alfa": "Alfa Romeo", "lancia": "Lancia", "chevrolet": "Chevrolet",
    "daewoo": "Daewoo", "zastava": "Zastava", "lada": "Lada", "smart": "Smart", "mini": "Mini", "jeep": "Jeep",
    "porsche": "Porsche", "subaru": "Subaru", "tesla": "Tesla", "man": "MAN",
}
# model bez marke (kako se piše na papiru: „Iveco - Master - Movano“)
MODEL_MARKA = {
    "ducato": "Fiat", "doblo": "Fiat", "scudo": "Fiat", "fiorino": "Fiat", "jumper": "Citroen", "jumpy": "Citroen",
    "berlingo": "Citroen", "nemo": "Citroen", "boxer": "Peugeot", "bokser": "Peugeot", "partner": "Peugeot",
    "expert": "Peugeot", "bipper": "Peugeot", "master": "Renault", "trafic": "Renault", "kangoo": "Renault",
    "movano": "Opel", "vivaro": "Opel", "daily": "Iveco", "sprinter": "Mercedes", "vito": "Mercedes",
    "crafter": "VW", "caddy": "VW", "transporter": "VW", "bora": "VW", "transit": "Ford",
}
MODEL_ALIAS = {"bokser": "Boxer", "džamper": "Jumper", "dzamper": "Jumper"}
# reči posle kojih više ne ide vozilo nego osobine stakla
STOP = {"senzor", "senzora", "kamera", "kamerom", "pločica", "plocica", "pločice", "plocice", "bez", "polovno",
        "polovan", "zadnja", "zadnje", "prednja", "bočno", "bocno", "niži", "nizi", "niža", "niza", "viši", "visi",
        "viša", "visa", "kombi", "romb", "krug", "kruška", "kruska", "uska", "široka", "siroka", "trougao",
        "okrugla", "+"}
_GODINE = re.compile(r"^(\d{2}|\d{4})-(\d{2}|\d{4})?$")
_OSTALO_STOP = re.compile(r"^\d+(x|cm)$", re.IGNORECASE)


@dataclass
class Predlog:
    staklo_id: int
    naziv: str
    vozila: list[Vozilo]
    siguran: bool
    napomena: str = ""


def _godina(t: str | None) -> int | None:
    if not t:
        return None
    g = int(t)
    if len(t) == 2:
        g += 1900 if g >= 50 else 2000
    return g


def parsiraj(naziv: str) -> tuple[list[Vozilo], bool, str]:
    """Vraća (vozila, siguran, napomena)."""
    tokens = naziv.split()
    od = do = None
    deo: list[str] = []
    for t in tokens:
        m = _GODINE.match(t)
        if m:
            od, do = _godina(m.group(1)), _godina(m.group(2))
            break
        if t.lower() in STOP or _OSTALO_STOP.match(t):
            break
        deo.append(t)
    segmenti, tekuci = [], []
    for t in deo:
        if t in ("-", "–", "/"):
            segmenti.append(tekuci)
            tekuci = []
        else:
            tekuci.append(t)
    segmenti.append(tekuci)

    vozila, nesigurno = [], []
    for words in segmenti:
        if not words:
            continue
        w0 = words[0].lower()
        if w0 in MARKE:
            marka, rest = MARKE[w0], words[1:]
        elif w0 in MODEL_MARKA:
            marka, rest = MODEL_MARKA[w0], words
        elif vozila:  # „Dacia Sandero - Logan“: model bez marke nasleđuje marku prethodnog
            marka, rest = vozila[-1].marka, words
        else:
            marka, rest = words[0], words[1:]
            nesigurno.append(words[0])
        model = MODEL_ALIAS.get(rest[0].lower(), rest[0]) if rest else None
        generacija = " ".join(rest[1:]) or None
        vozila.append(Vozilo(marka, model, generacija, od, do))
    if not vozila:
        return [], False, "nije prepoznato nijedno vozilo"
    if od and do and od > do:
        return vozila, False, "godina od je veća od godine do"
    if nesigurno:
        return vozila, False, "nepoznata marka: " + ", ".join(nesigurno)
    return vozila, True, ""


def opis(v: Vozilo) -> str:
    god = ""
    if v.godina_od or v.godina_do:
        god = f" ({v.godina_od or ''}–{v.godina_do or ''})"
    return " ".join(x for x in (v.marka, v.model, v.generacija) if x) + god


def predlozi(conn) -> list[Predlog]:
    """Predlog vozila za sva stakla koja još nemaju nijedno vozilo."""
    rows = conn.execute(
        "SELECT id, naziv FROM staklo WHERE aktivno = 1 "
        "AND NOT EXISTS (SELECT 1 FROM staklo_vozilo v WHERE v.staklo_id = staklo.id) ORDER BY naziv").fetchall()
    result = []
    for r in rows:
        vozila, siguran, napomena = parsiraj(r["naziv"])
        result.append(Predlog(r["id"], r["naziv"], vozila, siguran, napomena))
    return result


def upisi(conn, staklo_id: int, vozila: list[Vozilo]) -> None:
    s = repo.get_staklo(conn, staklo_id)
    s.vozila = vozila
    repo.update_staklo(conn, s)
