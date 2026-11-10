import os
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import isporuka  # noqa: E402

from autostakla import version  # noqa: E402


def test_izmene_postoje_za_trenutnu_verziju():
    """Pre svakog build-a mora biti upisano šta je novo (IZMENE.md)."""
    datum, sekcije = isporuka.izmene_za(version.VERSION)
    assert datum and any(sekcije.values())


def test_izmene_parsiranje_i_greske():
    text = "## 2.0.0 (01.01.2027)\n### Dodato\n- A\n  nastavak\n### Uklonjeno\n- B\n\n## 1.0.0 (x)\n### Dodato\n- C\n"
    datum, s = isporuka.izmene_za("2.0.0", text)
    assert datum == "01.01.2027" and s == {"Dodato": ["A nastavak"], "Uklonjeno": ["B"]}
    with pytest.raises(isporuka.IzmeneError, match="nema odeljka"):
        isporuka.izmene_za("3.0.0", text)
    with pytest.raises(isporuka.IzmeneError, match="Nepoznat"):
        isporuka.izmene_za("9.9.9", "## 9.9.9 (d)\n### Svašta\n- x\n")


@pytest.mark.parametrize("vrsta, mora", [("update", "Ažuriraj iz fajla"), ("prva", "Setup")])
def test_tekst(tmp_path, vrsta, mora):
    p = isporuka.write_tekst(tmp_path / "t.txt", vrsta)
    raw = p.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf") and b"\r\n" in raw   # Notepad: BOM + CRLF
    t = p.read_text(encoding="utf-8-sig")
    assert version.VERSION in t and mora in t and "ŠTA JE NOVO" in t and "DODATO:" in t


def test_update_paket_sa_dokumentima_prolazi_proveru(tmp_path):
    """Update zip sa uputstvom i txt-om u korenu – program ga prihvata i raspakuje samo app/."""
    from autostakla.core import update

    z = tmp_path / "AutoStakla_update.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("OBAVEZNO_PROCITAJ.txt", "x")
        zf.writestr("AutoStakla_Korisnicko_uputstvo.pdf", "x")
        zf.writestr("manifest.json", '{"app_id": "AutoStakla", "edition": "osnovna", "version": "99.0.0"}')
        zf.writestr("app/AutoStakla.exe", "x")
        zf.writestr("app/Updater.exe", "x")
    info = update.validate_package(z)
    _, new_app = update.prepare(info)
    assert sorted(p.name for p in new_app.iterdir()) == ["AutoStakla.exe", "Updater.exe"]


def test_sta_je_novo_dialog(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication

    from autostakla.core import paths
    from autostakla.ui import main_window

    QApplication.instance() or QApplication([])
    monkeypatch.setattr(paths, "docs_dir", lambda: tmp_path)
    assert main_window.StaJeNovoDialog.tekst() is None
    (tmp_path / paths.PROCITAJ_TXT).write_text("ŠTA JE NOVO", encoding="utf-8-sig")
    assert main_window.StaJeNovoDialog.tekst() == "ŠTA JE NOVO"
    main_window.StaJeNovoDialog(None, "x")
