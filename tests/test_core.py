import json
import sqlite3
import zipfile

import pytest

from autostakla import version
from autostakla.core import audit, backup, db, diagnostics, paths, update


# ---------- migracije ----------
def test_fresh_database_gets_all_migrations(conn_full):
    conn = conn_full
    assert db.current_version(conn) == db.available_migrations()[-1].number
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"schema_version", "audit_log", "podesavanja", "skladiste", "polica", "staklo", "kretanje"} <= tables
    assert db.apply_migrations(conn) == []  # drugi put nema šta


def test_pocetno_stanje(conn_full):
    from autostakla.lager import repo

    rows = repo.pretraga(conn_full, repo.Filter())
    assert len(rows) == 25 and sum(r["kolicina"] for r in rows) == 30
    assert len(repo.list_skladista(conn_full)) == 4
    golf5 = repo.pretraga(conn_full, repo.Filter("golf 5 senzor"))
    assert golf5 and all("Golf 5" in r["naziv"] and r["senzor"] for r in golf5)


@pytest.mark.parametrize("mig", db.available_migrations(), ids=lambda m: f"{m.number:03d}_{m.name}")
def test_every_migration_can_run_twice(tmp_path, mig):
    """Pravilo: svaka migracija mora moći da se pusti više puta (IF NOT EXISTS i sl.)."""
    c = sqlite3.connect(tmp_path / "t.db")
    for m in db.available_migrations():
        if m.number > mig.number:
            break
        c.executescript(m.path.read_text(encoding="utf-8"))
    before = c.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall()
    counts = {t: c.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
              for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    c.executescript(mig.path.read_text(encoding="utf-8"))  # drugi put – bez greške i bez duplikata
    assert c.execute("SELECT name, sql FROM sqlite_master ORDER BY name").fetchall() == before
    for t, n in counts.items():
        assert c.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0] == n, f"duplirani redovi u {t}"
    c.close()


def test_database_newer_than_program_is_refused(conn):
    conn.execute("INSERT INTO schema_version (verzija, naziv, app_verzija) VALUES (999, 'iz_buducnosti', '9.9.9')")
    with pytest.raises(db.DatabaseNewerError):
        db.pending_migrations(conn)


def test_failed_migration_is_rolled_back(tmp_path):
    folder = tmp_path / "mig"
    folder.mkdir()
    (folder / "001_ok.sql").write_text("CREATE TABLE a (x INTEGER);", encoding="utf-8")
    (folder / "002_lose.sql").write_text(
        "CREATE TABLE b (x INTEGER);\nINSERT INTO nepostojeca VALUES (1);", encoding="utf-8"
    )
    c = db.connect(tmp_path / "t.db")
    migs = db.available_migrations(folder)
    with pytest.raises(sqlite3.Error):
        db.apply_migrations(c, migs)
    assert db.current_version(c) == 1
    tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "a" in tables and "b" not in tables
    c.close()


# ---------- audit ----------
def test_audit_write(conn):
    audit.write(conn, "TEST", entitet="staklo", entitet_id=5, opis="opis", staro={"k": 1}, novo={"k": 2})
    r = conn.execute("SELECT * FROM audit_log").fetchone()
    assert r["akcija"] == "TEST" and r["entitet_id"] == 5
    assert json.loads(r["novo_json"]) == {"k": 2}
    assert r["app_verzija"] == version.VERSION


# ---------- backup ----------
def test_backup_is_valid_copy(conn):
    audit.write(conn, "TEST")
    target = backup.make_backup(conn, "test")
    c2 = sqlite3.connect(target)
    assert c2.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0] == 1
    c2.close()
    assert backup.last_backup() == target


def test_backup_rotation_keeps_last(conn):
    for i in range(backup.KEEP + 5):
        (paths.backup_dir() / f"{backup.PREFIX}2020-01-01_0000{i:02d}_x.db").write_bytes(b"")
    backup.rotate()
    items = backup.list_backups()
    assert len(items) == backup.KEEP
    assert items[0].name.endswith("000005_x.db")


# ---------- status / dijagnostika ----------
def test_status_ok(conn_full):
    st = db.status(conn_full)
    assert st.ok and st.integrity == "ok"


def test_diagnostics_zip(conn, tmp_path):
    (paths.logs_dir() / "app.log").write_text("linija", encoding="utf-8")
    z = diagnostics.create_zip(conn, tmp_path / "desktop", include_db=True)
    names = zipfile.ZipFile(z).namelist()
    assert "info.txt" in names and "logs/app.log" in names and "data/stakla.db" in names


# ---------- update paket ----------
def _make_package(path, manifest=None, files=("app/AutoStakla.exe", "app/Updater.exe")):
    with zipfile.ZipFile(path, "w") as zf:
        if manifest is not False:
            zf.writestr("manifest.json", json.dumps(manifest or {
                "app_id": "AutoStakla", "edition": "osnovna", "version": "9.0.0"}))
        for f in files:
            zf.writestr(f, b"x")
    return path


def test_valid_package(tmp_path):
    info = update.validate_package(_make_package(tmp_path / "p.zip"))
    assert info.version == "9.0.0" and info.comparison == 1


@pytest.mark.parametrize("kwargs, msg", [
    ({"manifest": False}, "manifest"),
    ({"manifest": {"app_id": "Drugi", "edition": "x", "version": "1.0.0"}}, "Drugi"),
    ({"manifest": {"app_id": "AutoStakla", "edition": "x", "version": "abc"}}, "manifest"),
    ({"files": ("app/AutoStakla.exe",)}, "Updater.exe"),
    ({"files": ("app/AutoStakla.exe", "app/Updater.exe", "../zlo.txt")}, "putanje"),
])
def test_invalid_packages(tmp_path, kwargs, msg):
    with pytest.raises(update.UpdateError, match=msg):
        update.validate_package(_make_package(tmp_path / "p.zip", **kwargs))


def test_not_a_zip(tmp_path):
    f = tmp_path / "x.zip"
    f.write_text("nije zip")
    with pytest.raises(update.UpdateError):
        update.validate_package(f)


def test_prepare_extracts_and_copies_updater(tmp_path):
    info = update.validate_package(_make_package(tmp_path / "p.zip"))
    updater, new_app = update.prepare(info)
    assert updater.exists() and updater.parent == paths.update_dir()
    assert (new_app / "AutoStakla.exe").exists()
