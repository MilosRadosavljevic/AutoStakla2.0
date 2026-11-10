"""Podešavanja programa u tabeli podesavanja (ključ -> vrednost)."""
from __future__ import annotations

import sqlite3

KEY_TEMA = "tema"          # "svetla" | "tamna"; ako ne postoji -> kao Windows
TEME = ("svetla", "tamna")


def get(conn: sqlite3.Connection, kljuc: str, default: str | None = None) -> str | None:
    r = conn.execute("SELECT vrednost FROM podesavanja WHERE kljuc = ?", (kljuc,)).fetchone()
    return r[0] if r else default


def set(conn: sqlite3.Connection, kljuc: str, vrednost: str | None) -> None:  # noqa: A001
    conn.execute("INSERT OR REPLACE INTO podesavanja (kljuc, vrednost) VALUES (?, ?)", (kljuc, vrednost))
