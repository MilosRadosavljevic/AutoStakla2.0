"""Upis u audit_log – šta je korisnik radio."""
from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

from autostakla import version

log = logging.getLogger(__name__)


def _to_json(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, default=str)


def write(
    conn: sqlite3.Connection,
    akcija: str,
    *,
    entitet: str | None = None,
    entitet_id: int | None = None,
    opis: str | None = None,
    staro: Any = None,
    novo: Any = None,
) -> None:
    """Upis jedne stavke. Greška u audit-u se loguje, ali ne ruši radnju korisnika."""
    try:
        conn.execute(
            """
            INSERT INTO audit_log (akcija, entitet, entitet_id, opis, staro_json, novo_json, app_verzija)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (akcija, entitet, entitet_id, opis, _to_json(staro), _to_json(novo), version.VERSION),
        )
    except sqlite3.Error:
        log.exception("Upis u audit_log nije uspeo (%s, %s)", akcija, opis)
