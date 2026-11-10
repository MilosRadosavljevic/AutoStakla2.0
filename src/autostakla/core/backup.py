"""Backup baze (SQLite backup API) i rotacija – čuva se poslednjih KEEP kopija."""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from autostakla.core import paths

log = logging.getLogger(__name__)

KEEP = 30
PREFIX = "stakla_"


def make_backup(conn: sqlite3.Connection, reason: str = "rucno") -> Path:
    paths.backup_dir().mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    target = paths.backup_dir() / f"{PREFIX}{stamp}_{reason}.db"
    n = 1
    while target.exists():  # dva backup-a u istoj sekundi
        target = paths.backup_dir() / f"{PREFIX}{stamp}_{reason}_{n}.db"
        n += 1
    dest = sqlite3.connect(target)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    log.info("Backup: %s", target.name)
    rotate()
    return target


def list_backups() -> list[Path]:
    folder = paths.backup_dir()
    if not folder.exists():
        return []
    return sorted(folder.glob(f"{PREFIX}*.db"), key=lambda p: p.name)


def last_backup() -> Path | None:
    items = list_backups()
    return items[-1] if items else None


def rotate(keep: int = KEEP) -> None:
    items = list_backups()
    for old in items[:-keep] if len(items) > keep else []:
        try:
            old.unlink()
        except OSError:
            log.warning("Ne mogu da obrišem stari backup %s", old)
