"""Better ekrani bez prikaza (offscreen): otvaranje, unos kroz dijaloge, PDF i Excel."""
import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from autostakla.better import dokumenti, nabavka, prodaja, reklamacije  # noqa: E402
from autostakla.lager import repo  # noqa: E402
from autostakla.lager.repo import Staklo  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def bez_poruka(monkeypatch):
    """Poruke i otvaranje fajlova se ne prikazuju u testu."""
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: (_ for _ in ()).throw(AssertionError(a[2])))
    monkeypatch.setattr("autostakla.ui.better.common.otvori", lambda parent, path: None)
    for mod in ("prodaja_window", "analitika_window", "ostalo"):
        monkeypatch.setattr(f"autostakla.ui.better.{mod}.otvori", lambda parent, path: None)


@pytest.fixture
def data(conn):
    sid = repo.add_skladiste(conn, "1 Stalak")
    pid = repo.list_police(conn, sid)[0]["id"]
    st = repo.add_staklo(conn, Staklo("Fiat Ducato - Citroen Jumper - Peugeot Boxer 06-"))
    dob = nabavka.add_dobavljac(conn, "Stakla Beograd")
    nabavka.postavi_cenu(conn, st, dob, 9000, "2026-01-01")
    return {"pid": pid, "st": st, "dob": dob}


def _row(conn, staklo_id):
    return [r for r in repo.pretraga(conn, repo.Filter()) if r["staklo_id"] == staklo_id][0]


def test_ulaz_izlaz_istorija(app, conn, data):
    from autostakla.ui import kretanje_dialogs as kd
    from autostakla.ui.better.kretanje import IzlazDialog, UlazBetterDialog

    d = UlazBetterDialog(None, conn, staklo_id=data["st"], polica_id=data["pid"])
    d.dobavljac.setCurrentIndex(d.dobavljac.findData(data["dob"]))
    assert d.cena.text() == "9.000"                      # predlog iz cenovnika
    d.kolicina.setValue(2)
    d._save()
    assert d.result() == 1 and conn.execute("SELECT COUNT(*) FROM nabavka").fetchone()[0] == 2

    d = IzlazDialog(None, conn, _row(conn, data["st"]))
    assert d.vozilo.text() == ""                         # staklo bez upisanih vozila
    d.cena.setText("14.400")
    d.tablice.setText("sd 123-ab")
    d._save()
    p = prodaja.list_prodaja(conn)[0]
    assert (p["cena"], p["tablice"]) == (14400, "SD 123-AB")

    d = IzlazDialog(None, conn, _row(conn, data["st"]))
    d.razlog.setCurrentIndex(d.razlog.findData("RAZBIJENO"))
    assert d.grupa.isHidden()
    d._save()
    kd.IstorijaDialog(None, conn, {**_row_svi(conn, data["st"]), "skladiste": "1 Stalak", "polica": "Polica 1"})


def _row_svi(conn, staklo_id):
    return [r for r in repo.pretraga(conn, repo.Filter(samo_na_stanju=False)) if r["staklo_id"] == staklo_id][0]


def test_poslovanje_ekrani(app, conn, data):
    from autostakla.ui.better import analitika_window, dobavljaci_dialog, ostalo, prodaja_window
    from autostakla.ui.main_window import MainWindow

    nabavka.ulaz(conn, data["st"], data["pid"], 2, dobavljac_id=data["dob"], nabavna_cena=9000)
    kupac = prodaja.add_kupac(conn, "Petar")
    prodaja.izlaz(conn, _row(conn, data["st"])["lager_stavka_id"], 1, "PRODATO",
                  prodaja=prodaja.ProdajaPodaci(14400, kupac, tablice="BG 1"))

    w = MainWindow(conn)
    assert any(a.text() == "P&oslovanje" for a in w.menuBar().actions())

    pd = prodaja_window.ProdajaDialog(None, conn)
    assert pd.t.rowCount() == 1
    pd.t.selectRow(0)
    pd.otpremnica()
    assert conn.execute("SELECT COUNT(*) FROM dokument WHERE vrsta = 'OTPREMNICA'").fetchone()[0] == 1
    nr = prodaja_window.NovaReklamacijaDialog(None, conn, prodaja.list_prodaja(conn)[0]["id"])
    assert nr.dobavljac.currentData() == data["dob"]
    nr.opis.setPlainText("pukotina")
    nr._save()
    rd = prodaja_window.ReklamacijeDialog(None, conn)
    rd.t.selectRow(0)
    sd = prodaja_window.StatusDialog(None, conn, reklamacije.get(conn, nr.reklamacija_id))
    sd.status.setCurrentIndex(sd.status.findData("ODOBRENA"))
    sd.ishod.setCurrentIndex(sd.ishod.findData("ZAMENA"))
    sd.trosak.setText("1.500")
    sd._save()
    assert reklamacije.get(conn, nr.reklamacija_id)["status"] == "ODOBRENA"

    ad = analitika_window.AnalitikaDialog(None, conn)
    assert ad.t_stakla.rowCount() == 1
    ad.izvoz_excel()
    ad.izvoz_pdf()
    ad._period(date(2020, 1, 1), date(2020, 12, 31))
    assert ad.t_stakla.rowCount() == 0

    dd = dobavljaci_dialog.DobavljaciDialog(None, conn)
    assert dd.t.rowCount() == 1
    nd = dobavljaci_dialog.DobavljacDialog(None, conn)
    nd.naziv.setText("AutoGlas Niš")
    nd._save()
    cd = dobavljaci_dialog.CeneDialog(None, conn, data["st"])
    assert cd.vazece.rowCount() == 1
    nc = dobavljaci_dialog.NovaCenaDialog(None, conn, data["st"])
    nc.dobavljac.setCurrentIndex(nc.dobavljac.findData(nd.dobavljac_id))
    nc.cena.setText("8500")
    nc._save()
    assert nabavka.najjeftiniji(conn, data["st"])["dobavljac"] == "AutoGlas Niš"

    vd = ostalo.VozilaDialog(None, conn)
    vd._save()
    assert conn.execute("SELECT COUNT(*) FROM staklo_vozilo").fetchone()[0] == 3

    fd = ostalo.FirmaDialog(None, conn)
    fd.polja["firma_naziv"].setText("Auto stakla DEMO")
    fd._save()
    pr = ostalo.PredracunDialog(None, conn)
    pr.staklo.setEditText("Ugradnja vetrobrana")
    pr.cena.setText("3000")
    pr._dodaj()
    pr._save()
    assert dokumenti.get(conn, pr.dokument_id)["broj"].startswith("PR-")
    dk = ostalo.DokumentiDialog(None, conn)
    assert dk.t.rowCount() == 2
    dk.t.selectRow(0)
    dk.pdf()
