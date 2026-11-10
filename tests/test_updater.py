import shutil

import pytest

import updater


def _setup(root):
    (root / "app").mkdir(parents=True)
    (root / "app" / "AutoStakla.exe").write_text("stara")
    staging = root / "update" / "staging" / "app"
    staging.mkdir(parents=True)
    (staging / "AutoStakla.exe").write_text("nova")
    (root / "data").mkdir(exist_ok=True)
    (root / "data" / "stakla.db").write_text("PODACI")
    return staging


def test_update_replaces_app_and_keeps_data(tmp_path):
    root = tmp_path / "AutoStakla"
    staging = _setup(root)
    updater.perform_update(root, staging, delay=0)
    assert (root / "app" / "AutoStakla.exe").read_text() == "nova"
    assert not (root / "app_old").exists()
    assert (root / "data" / "stakla.db").read_text() == "PODACI"


def test_failed_move_restores_old_version(tmp_path, monkeypatch):
    root = tmp_path / "AutoStakla"
    staging = _setup(root)

    def boom(*a, **k):
        raise OSError("zaključan fajl")

    monkeypatch.setattr(shutil, "move", boom)
    with pytest.raises(OSError):
        updater.perform_update(root, staging, delay=0)
    assert (root / "app" / "AutoStakla.exe").read_text() == "stara"
    assert (root / "data" / "stakla.db").read_text() == "PODACI"


def test_missing_staging_does_not_touch_app(tmp_path):
    root = tmp_path / "AutoStakla"
    _setup(root)
    with pytest.raises(RuntimeError):
        updater.perform_update(root, root / "nema", delay=0)
    assert (root / "app" / "AutoStakla.exe").read_text() == "stara"
