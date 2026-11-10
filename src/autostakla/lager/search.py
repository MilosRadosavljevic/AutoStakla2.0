"""Pretraga: bez obzira na velika/mala slova, kvačice i način pisanja marke.

„golf 5"      -> nađe „VW Golf 5 i 6 SENZOR" (ali ne „Golf 4 ... 05-")
„peugeot 307" -> nađe „Pezo 307"
Svaka reč iz upita mora biti POČETAK neke reči u tekstu stakla.
"""
from __future__ import annotations

import re
import unicodedata

_TRANSLIT = str.maketrans({"đ": "dj", "Đ": "dj", "ß": "ss"})

# Različiti načini pisanja -> jedan oblik (važi i za upit i za tekst)
ALIASES = {
    "peugeot": "pezo", "pezho": "pezo", "pejo": "pezo",
    "renault": "reno", "renaut": "reno",
    "volkswagen": "vw", "folksvagen": "vw", "fw": "vw",
    "hjundai": "hyundai", "hundai": "hyundai", "hyunday": "hyundai",
    "mercedes-benz": "mercedes", "merc": "mercedes", "mesa": "mercedes",
    "citroen": "citroen", "sitroen": "citroen",
    "touaran": "touran", "toran": "touran",
    "megane": "megan", "scenic": "senic", "kadett": "kadet",
    "transit": "tranzit", "picasso": "picaso", "roomster": "romster",
    "sharan": "saran", "vivaro": "vivaro", "boxer": "bokser",
    "expert": "ekspert", "jumpy": "jampy", "trafic": "trafic", "traffic": "trafic",
    "qashqai": "qasqai", "kaskai": "qasqai",
    "senzorom": "senzor", "senzora": "senzor", "senzori": "senzor", "sensor": "senzor",
    "kamerom": "kamera", "kamere": "kamera",
    "plocicom": "plocica", "plocice": "plocica",
    "polovna": "polovno", "polovni": "polovno",
}

_SPLIT = re.compile(r"[^0-9a-z]+")


def normalize(text: str | None) -> str:
    if not text:
        return ""
    t = text.translate(_TRANSLIT).lower()
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t


def words(text: str | None) -> list[str]:
    result = []
    for w in _SPLIT.split(normalize(text)):
        if w:
            result.append(ALIASES.get(w, w))
    return result


def matches(query_words: list[str], text_words: list[str]) -> bool:
    return all(any(tw.startswith(q) for tw in text_words) for q in query_words)
