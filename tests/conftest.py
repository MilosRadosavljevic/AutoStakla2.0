import sys
from pathlib import Path

import pytest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "updater"))


@pytest.fixture(autouse=True)
def isolated_root(tmp_path, monkeypatch):
    """Svaki test radi u svom privremenom C:\\AutoStakla."""
    root = tmp_path / "AutoStakla"
    monkeypatch.setenv("AUTOSTAKLA_ROOT", str(root))
    from autostakla.core import paths

    paths.ensure_dirs()
    return root


@pytest.fixture
def conn():
    """Baza sa svom strukturom, ali BEZ početnog stanja (migracije sa podacima se preskaču)."""
    from autostakla.core import db

    c = db.connect()
    db.apply_migrations(c, [m for m in db.available_migrations() if "pocetno" not in m.name])
    yield c
    c.close()


@pytest.fixture
def conn_full():
    """Baza sa svim migracijama, uključujući početno stanje."""
    from autostakla.core import db

    c = db.connect()
    db.apply_migrations(c)
    yield c
    c.close()
