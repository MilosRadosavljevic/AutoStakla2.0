"""Konekcija na SQLite bazu, migracije i provera baze."""
from __future__ import annotations

import logging
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from autostakla import version
from autostakla.core import paths

log = logging.getLogger(__name__)

_MIGRATION_RE = re.compile(r"^(\d{3})_([\w\-]+)\.sql$")


class DatabaseNewerError(RuntimeError):
    """Baza je migrirana novijom verzijom programa – stari program ne sme da je dira."""


@dataclass(frozen=True)
class Migration:
    number: int
    name: str
    path: Path


@dataclass
class DbStatus:
    app_version: str
    db_version: int
    expected_version: int
    pending: list[Migration] = field(default_factory=list)
    integrity: str = ""
    db_size_bytes: int = 0
    last_backup: str | None = None

    @property
    def ok(self) -> bool:
        return not self.pending and self.integrity == "ok"


def connect(db_file: Path | None = None) -> sqlite3.Connection:
    db_file = db_file or paths.db_path()
    db_file.parent.mkdir(parents=True, exist_ok=True)
    # isolation_level=None -> transakcije vodimo sami (BEGIN/COMMIT)
    conn = sqlite3.connect(db_file, isolation_level=None, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _ensure_version_table(conn)
    return conn


def _ensure_version_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            verzija      INTEGER PRIMARY KEY,
            naziv        TEXT    NOT NULL,
            primenjeno   TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            app_verzija  TEXT    NOT NULL
        )
        """
    )


def available_migrations(folder: Path | None = None) -> list[Migration]:
    folder = folder or paths.migrations_dir()
    result = []
    for f in folder.glob("*.sql"):
        m = _MIGRATION_RE.match(f.name)
        if m:
            result.append(Migration(int(m.group(1)), m.group(2), f))
    result.sort(key=lambda x: x.number)
    numbers = [m.number for m in result]
    if len(numbers) != len(set(numbers)):
        raise RuntimeError(f"Duplirani brojevi migracija u {folder}")
    return result


def current_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("SELECT COALESCE(MAX(verzija), 0) FROM schema_version").fetchone()
    return int(row[0])


def pending_migrations(
    conn: sqlite3.Connection, migrations: list[Migration] | None = None
) -> list[Migration]:
    migrations = available_migrations() if migrations is None else migrations
    applied = {r[0] for r in conn.execute("SELECT verzija FROM schema_version")}
    expected = migrations[-1].number if migrations else 0
    if applied and max(applied) > expected:
        raise DatabaseNewerError(
            f"Baza je verzije {max(applied)}, a ovaj program poznaje najviše {expected}. "
            "Baza je otvarana novijom verzijom programa."
        )
    return [m for m in migrations if m.number not in applied]


def apply_migrations(
    conn: sqlite3.Connection, migrations: list[Migration] | None = None
) -> list[Migration]:
    """Primeni migracije koje fale. Svaka migracija ide u svojoj transakciji."""
    todo = pending_migrations(conn, migrations)
    for m in todo:
        sql = m.path.read_text(encoding="utf-8")
        log.info("Primena migracije %03d_%s", m.number, m.name)
        script = (
            "BEGIN;\n"
            f"{sql}\n;\n"
            "INSERT OR IGNORE INTO schema_version (verzija, naziv, app_verzija) "
            f"VALUES ({m.number}, '{m.name}', '{version.VERSION}');\n"
            "COMMIT;"
        )
        try:
            conn.executescript(script)
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            log.exception("Migracija %03d_%s nije uspela – vraćeno", m.number, m.name)
            raise
    return todo


def integrity_check(conn: sqlite3.Connection) -> str:
    rows = conn.execute("PRAGMA integrity_check").fetchall()
    return "; ".join(str(r[0]) for r in rows)


def status(conn: sqlite3.Connection, db_file: Path | None = None) -> DbStatus:
    from autostakla.core import backup  # izbegavanje kružnog importa

    db_file = db_file or paths.db_path()
    migrations = available_migrations()
    last = backup.last_backup()
    return DbStatus(
        app_version=version.VERSION,
        db_version=current_version(conn),
        expected_version=migrations[-1].number if migrations else 0,
        pending=pending_migrations(conn, migrations),
        integrity=integrity_check(conn),
        db_size_bytes=db_file.stat().st_size if db_file.exists() else 0,
        last_backup=last.name if last else None,
    )
