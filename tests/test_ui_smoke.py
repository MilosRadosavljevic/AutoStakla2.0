"""Otvara sve ekrane bez prikaza (offscreen) i pravi PDF – hvata greške u UI kodu."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from autostakla.lager import repo, stampa  # noqa: E402
from autostakla.lager.repo import Staklo  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def data(conn):
    sid = repo.add_skladiste(conn, "1 Stalak")
    pid = repo.list_police(conn, sid)[0]["id"]
    st = repo.add_staklo(conn, Staklo("VW Golf 5 i 6 SENZOR", senzor=True))
    stavka = repo.ulaz(conn, st, pid, 1)
    conn.execute("INSERT INTO kretanje (lager_stavka_id, kolicina, vrsta) VALUES (?, 1, 'POCETNO')", (stavka,))
    return sid, pid, st, stavka


def test_main_window_and_dialogs(app, conn, data):
    from autostakla.ui import kretanje_dialogs as kd
    from autostakla.ui.main_window import MainWindow, StampaDialog
    from autostakla.ui.skladista_dialog import SkladistaDialog
    from autostakla.ui.staklo_dialog import StakloDialog

    w = MainWindow(conn)
    view = w.lager
    assert view.model.rowCount() == 1
    view.search.setText("golf 5")
    view.refresh()
    assert view.model.rowCount() == 1
    view.search.setText("passat")
    view.refresh()
    assert view.model.rowCount() == 0
    view.reset_filters()
    view.table.selectRow(0)
    row = view.selected()
    assert row and row["kolicina"] == 2

    SkladistaDialog(w, conn)
    StakloDialog(w, conn, data[2])
    StakloDialog(w, conn)
    kd.UlazDialog(w, conn, staklo_id=data[2], skladiste_id=data[0], polica_id=data[1])
    kd.KolicinaDialog(w, conn, row, "izlaz")
    kd.KolicinaDialog(w, conn, row, "korekcija")
    kd.PremestiDialog(w, conn, row)
    d = kd.IzmeniMestoDialog(w, conn, row)
    d.napomena.setText("H137 163")
    d._save()
    view.refresh()
    assert view.selected()["stavka_napomena"] == "H137 163"
    kd.IstorijaDialog(w, conn, row)
    StampaDialog(w, conn)
    for c in range(view.model.columnCount()):
        view.model.data(view.model.index(0, c))
    w.closing_for_update = True
    w.close()


def test_tema_se_pamti(app, conn):
    from autostakla.core import settings
    from autostakla.ui import tema
    from autostakla.ui.main_window import MainWindow

    w = MainWindow(conn)
    w.set_tema("tamna")
    assert settings.get(conn, settings.KEY_TEMA) == "tamna"
    assert tema.trenutna(conn) == "tamna"
    w.set_tema("svetla")
    w2 = MainWindow(conn)  # „sledeće pokretanje"
    assert w2.tema_akcije["svetla"].isChecked() and not w2.tema_akcije["tamna"].isChecked()
    for x in (w, w2):
        x.closing_for_update = True
        x.close()


def test_pdf(app, conn, data, tmp_path):
    p1 = stampa.write_pdf(stampa.html_spisak(conn), tmp_path / "spisak.pdf")
    p2 = stampa.write_pdf(stampa.html_prikaz(repo.pretraga(conn, repo.Filter()), "Test"), tmp_path / "p.pdf")
    for p in (p1, p2):
        assert p.read_bytes()[:4] == b"%PDF" and p.stat().st_size > 1000
