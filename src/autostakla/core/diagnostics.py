"""Dijagnostički zip za slanje Milošu: logovi + info o verzijama (+ po izboru kopija baze)."""
from __future__ import annotations

import logging
import platform
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from autostakla import version
from autostakla.core import db, paths

log = logging.getLogger(__name__)


def build_info(conn: sqlite3.Connection) -> str:
    lines = [
        f"Program:        {version.APP_NAME} {version.VERSION} ({version.EDITION})",
        f"Napravljeno:    {datetime.now():%Y-%m-%d %H:%M:%S}",
        f"Windows:        {platform.platform()}",
        f"Python:         {platform.python_version()}",
        f"Koren:          {paths.root_dir()}",
    ]
    try:
        st = db.status(conn)
        lines += [
            f"Baza verzija:   {st.db_version} (očekivana {st.expected_version})",
            f"Migracije fale: {', '.join(f'{m.number:03d}' for m in st.pending) or 'nema'}",
            f"Integritet:     {st.integrity}",
            f"Veličina baze:  {st.db_size_bytes:,} B",
            f"Poslednji backup: {st.last_backup or 'nema'}",
        ]
    except Exception as e:  # dijagnostika mora da prođe i kad je baza loša
        log.exception("Greška pri čitanju statusa baze za dijagnostiku")
        lines.append(f"Status baze:    GREŠKA – {e}")
    try:
        rows = conn.execute(
            "SELECT vreme, akcija, COALESCE(opis,'') FROM audit_log ORDER BY id DESC LIMIT 200"
        ).fetchall()
        lines += ["", "Poslednjih 200 akcija (audit_log):"]
        lines += [f"  {r[0]}  {r[1]:<10} {r[2]}" for r in rows]
    except sqlite3.Error as e:
        lines.append(f"audit_log nedostupan: {e}")
    return "\n".join(lines) + "\n"


def create_zip(conn: sqlite3.Connection, target_dir: Path, include_db: bool) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"AutoStakla_dijagnostika_{datetime.now():%Y-%m-%d_%H%M%S}.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("info.txt", build_info(conn))
        logs = paths.logs_dir()
        if logs.exists():
            for f in sorted(logs.glob("*.log*")):
                zf.write(f, f"logs/{f.name}")
        if include_db:
            with tempfile.TemporaryDirectory() as tmp:
                copy = Path(tmp) / paths.DB_FILENAME
                dest = sqlite3.connect(copy)
                try:
                    conn.backup(dest)
                finally:
                    dest.close()
                zf.write(copy, f"data/{paths.DB_FILENAME}")
    log.info("Dijagnostika napravljena: %s (baza: %s)", target, include_db)
    return target
