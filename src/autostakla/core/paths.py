"""Folderi aplikacije.

Spakovan program:  C:\\AutoStakla\\app\\AutoStakla.exe  -> root = C:\\AutoStakla
Razvoj:            <projekat>\\dev_root
Pregaziti:         promenljiva okruženja AUTOSTAKLA_ROOT
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

DB_FILENAME = "stakla.db"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_dir() -> Path:
    """Folder sa programom (exe) ili izvornim paketom u razvoju."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_dir() -> Path:
    """Folder sa resursima (migracije, ikonica) – kod PyInstaller-a je to _internal."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", app_dir()))
    return Path(__file__).resolve().parent.parent


def root_dir() -> Path:
    env = os.environ.get("AUTOSTAKLA_ROOT")
    if env:
        return Path(env).resolve()
    if is_frozen():
        return app_dir().parent
    # src/autostakla/core/paths.py -> projekat
    return Path(__file__).resolve().parents[3] / "dev_root"


def data_dir() -> Path:
    return root_dir() / "data"


def backup_dir() -> Path:
    return root_dir() / "backup"


def logs_dir() -> Path:
    return root_dir() / "logs"


def update_dir() -> Path:
    return root_dir() / "update"


def db_path() -> Path:
    return data_dir() / DB_FILENAME


def migrations_dir() -> Path:
    return resource_dir() / "migrations"


UPUTSTVO_PDF = "AutoStakla_Korisnicko_uputstvo.pdf"
PROCITAJ_TXT = "OBAVEZNO_PROCITAJ.txt"


def docs_dir() -> Path:
    """Uputstvo i „Šta je novo“ koji idu uz program (build ih pakuje u _internal\\docs)."""
    if is_frozen():
        return resource_dir() / "docs"
    # razvoj: ono što je build poslednji put pripremio
    return Path(__file__).resolve().parents[3] / "build" / "isporuka" / "app_docs"


def ensure_dirs() -> None:
    for d in (data_dir(), backup_dir(), logs_dir()):
        d.mkdir(parents=True, exist_ok=True)
