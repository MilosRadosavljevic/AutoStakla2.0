"""AutoStaklaBetter: novac, vozila iz naziva, prodaja, nabavka, analitika, reklamacije, dokumenti."""
from datetime import date

import pytest

from autostakla.better import analitika, dokumenti, nabavka, novac, prodaja, reklamacije, vozila
from autostakla.better.prodaja import ProdajaPodaci
from autostakla.lager import repo
from autostakla.lager.repo import LagerError, Staklo


@pytest.fixture
def lager(conn):
    sid = repo.add_skladiste(conn, "1 Stalak")
    pid = repo.list_police(conn, sid)[0]["id"]
    golf = repo.add_staklo(conn, Staklo("VW Golf 5 i 6 SENZOR", senzor=True))
    ducato = repo.add_staklo(conn, Staklo("Fiat Ducato - Citroen Jumper - Peugeot Boxer 06-"))
    dob = nabavka.add_dobavljac(conn, "Stakla Beograd", telefon="011 123")
    return {"pid": pid, "golf": golf, "ducato": ducato, "dob": dob}


def _stavke(conn, staklo_id):
    return [r["lager_stavka_id"] for r in repo.pretraga(conn, repo.Filter()) if r["staklo_id"] == staklo_id]


def _prodaj(conn, staklo_id, cena, **kw):
    stavka = _stavke(conn, staklo_id)[0]
    prodaja.izlaz(conn, stavka, 1, "PRODATO", prodaja=ProdajaPodaci(cena, **kw))
    return prodaja.list_prodaja(conn)[0]


# ---------------------------------------------------------------- novac
def test_novac():
    assert novac.bez_pdv(12000, 20) == 10000
    assert novac.bez_pdv(100, 20) == 83
    assert novac.fmt(1234567) == "1.234.567 RSD" and novac.fmt(None) == "–"
    for t in ("12.500", "12500", "12 500", "12.500,00", "12500 RSD"):
        assert novac.parse(t) == 12500
    for t in ("", "12,50", "abc", "-5"):
        with pytest.raises(LagerError):
            novac.parse(t)
    assert novac.procenat(1, 3) == "33,3%" and novac.procenat(-1, 4) == "-25,0%" and novac.procenat(1, 0) == "–"


# ---------------------------------------------------------------- vozila
def test_vozila_iz_naziva():
    v, siguran, _ = vozila.parsiraj("Fiat Ducato - Citroen Jumper - Peugeot Boxer 06-")
    assert siguran and [(x.marka, x.model, x.godina_od, x.godina_do) for x in v] == [
        ("Fiat", "Ducato", 2006, None), ("Citroen", "Jumper", 2006, None), ("Peugeot", "Boxer", 2006, None)]
    v, siguran, _ = vozila.parsiraj("VW Golf 5 i 6 SENZOR")
    assert siguran and (v[0].marka, v[0].model, v[0].generacija) == ("VW", "Golf", "5 i 6")
    v, siguran, _ = vozila.parsiraj("Iveco - Master - Movano 03-10 2x")
    assert siguran and [(x.marka, x.model) for x in v] == [("Iveco", None), ("Renault", "Master"), ("Opel", "Movano")]
    assert v[1].godina_od == 2003 and v[1].godina_do == 2010
    v, _, _ = vozila.parsiraj("BMW 3 E90 05-12 SENZOR")
    assert (v[0].model, v[0].generacija) == ("3", "E90")
    v, _, _ = vozila.parsiraj("VW Golf 5 i 6 VIŠA PLOČICA")
    assert (v[0].model, v[0].generacija) == ("Golf", "5 i 6")
    v, _, _ = vozila.parsiraj("Pezo Bokser 94-06")
    assert (v[0].marka, v[0].model, v[0].godina_od) == ("Peugeot", "Boxer", 1994)
    v, siguran, _ = vozila.parsiraj("Dacia Sandero - Logan 13-20")
    assert siguran and [(x.marka, x.model) for x in v] == [("Dacia", "Sandero"), ("Dacia", "Logan")]
    v, siguran, _ = vozila.parsiraj("Hjundai Tucson")
    assert siguran and v[0].marka == "Hyundai"
    _, siguran, napomena = vozila.parsiraj("Nepoznato Nesto 2x")
    assert not siguran and "Nepoznato" in napomena


def test_popunjavanje_vozila_i_pretraga(conn, lager):
    nabavka.ulaz(conn, lager["ducato"], lager["pid"], 1, nabavna_cena=9000)
    pred = {p.naziv: p for p in vozila.predlozi(conn)}
    assert set(pred) == {"VW Golf 5 i 6 SENZOR", "Fiat Ducato - Citroen Jumper - Peugeot Boxer 06-"}
    p = pred["Fiat Ducato - Citroen Jumper - Peugeot Boxer 06-"]
    vozila.upisi(conn, p.staklo_id, p.vozila)
    assert len(vozila.predlozi(conn)) == 1
    assert [r["naziv"] for r in repo.pretraga(conn, repo.Filter("boxer"))] == [p.naziv]


# ---------------------------------------------------------------- prodaja
def test_izlaz_sa_razlogom_i_prodaja(conn, lager):
    nabavka.ulaz(conn, lager["golf"], lager["pid"], 2, razlog="POVRAT_KUPCA")
    with pytest.raises(LagerError):
        prodaja.izlaz(conn, _stavke(conn, lager["golf"])[0], 1, "XYZ")
    with pytest.raises(LagerError):
        prodaja.izlaz(conn, _stavke(conn, lager["golf"])[0], 1, "PRODATO")
    kupac = prodaja.add_kupac(conn, "Petar Petrović", "064 111 222")
    p = _prodaj(conn, lager["golf"], 14400, kupac_id=kupac, vozilo="Golf 5", tablice=" bg 123-ab ", sa_ugradnjom=True)
    assert (p["kupac"], p["tablice"], p["cena"], p["kom"], p["ukupno"]) == ("Petar Petrović", "BG 123-AB", 14400, 1, 14400)
    assert prodaja.list_prodaja(conn, tekst="petrović")[0]["id"] == p["id"]
    assert prodaja.list_prodaja(conn, tekst="passat") == []
    stavka = _stavke(conn, lager["golf"])[0]
    prodaja.izlaz(conn, stavka, 1, "RAZBIJENO", napomena="pao")
    assert repo.pretraga(conn, repo.Filter("golf")) == []
    ist = prodaja.istorija(conn, p["lager_stavka_id"])
    assert "Prodato" in ist[0]["detalj"] and "BG 123-AB" in ist[0]["detalj"]
    assert ist[1]["detalj"] == "Vraćeno od kupca"


def test_kupci(conn):
    with pytest.raises(LagerError):
        prodaja.add_kupac(conn, "  ")
    k = prodaja.add_kupac(conn, "Marko", "065")
    prodaja.update_kupac(conn, k, "Marko M.", "065 1", "stalni")
    assert prodaja.get_kupac(conn, k)["ime"] == "Marko M."
    assert [x["ime"] for x in prodaja.list_kupci(conn, "stalni")] == ["Marko M."]


# ---------------------------------------------------------------- nabavka
def test_dobavljaci_i_cenovnik(conn, lager):
    with pytest.raises(LagerError):
        nabavka.add_dobavljac(conn, "stakla beograd")
    d2 = nabavka.add_dobavljac(conn, "AutoGlas Niš")
    nabavka.postavi_cenu(conn, lager["golf"], lager["dob"], 9000, "2026-01-01")
    nabavka.postavi_cenu(conn, lager["golf"], lager["dob"], 9500, "2026-06-01")
    nabavka.postavi_cenu(conn, lager["golf"], d2, 9200, "2026-03-01")
    nabavka.postavi_cenu(conn, lager["golf"], d2, 7000, "2099-01-01")  # buduća cena još ne važi
    cene = nabavka.cene_za_staklo(conn, lager["golf"], "2026-11-10")
    assert [(c["dobavljac"], c["cena"]) for c in cene] == [("AutoGlas Niš", 9200), ("Stakla Beograd", 9500)]
    assert nabavka.najjeftiniji(conn, lager["golf"])["dobavljac"] == "AutoGlas Niš"
    nabavka.set_aktivan(conn, d2, False)
    assert nabavka.najjeftiniji(conn, lager["golf"])["dobavljac"] == "Stakla Beograd"
    assert len(nabavka.istorija_cena(conn, lager["golf"])) == 4
    with pytest.raises(LagerError):
        nabavka.postavi_cenu(conn, lager["golf"], lager["dob"], 100, "2026-13-01")


def test_nabavka_i_prosecna_cena(conn, lager):
    with pytest.raises(LagerError):
        nabavka.ulaz(conn, lager["golf"], lager["pid"], 1)  # nabavka bez cene
    nabavka.ulaz(conn, lager["golf"], lager["pid"], 1, dobavljac_id=lager["dob"], nabavna_cena=8000, dokument="F-1")
    nabavka.ulaz(conn, lager["golf"], lager["pid"], 3, dobavljac_id=lager["dob"], nabavna_cena=9000)
    assert conn.execute("SELECT COUNT(*) FROM nabavka").fetchone()[0] == 4
    assert nabavka.prosecna_nabavna(conn, lager["golf"]) == 8750
    assert nabavka.prosecna_nabavna(conn, lager["ducato"]) is None
    assert sum(r["kolicina"] for r in repo.pretraga(conn, repo.Filter("golf"))) == 4


# ---------------------------------------------------------------- analitika
def test_analitika(conn, lager):
    nabavka.ulaz(conn, lager["golf"], lager["pid"], 3, dobavljac_id=lager["dob"], nabavna_cena=8000)
    nabavka.ulaz(conn, lager["ducato"], lager["pid"], 1, razlog="POVRAT_KUPCA")
    p = vozila.parsiraj("Fiat Ducato - Citroen Jumper - Peugeot Boxer 06-")[0]
    vozila.upisi(conn, lager["ducato"], p)
    _prodaj(conn, lager["golf"], 12000)
    _prodaj(conn, lager["golf"], 12000)
    _prodaj(conn, lager["ducato"], 24000)          # bez nabavne cene
    prodaja.izlaz(conn, _stavke(conn, lager["golf"])[0], 1, "RAZBIJENO")
    danas = date.today().isoformat()
    k = analitika.kpi(conn, danas, danas)
    assert (k.broj_prodaja, k.komada, k.promet, k.promet_bez_pdv) == (3, 3, 48000, 40000)
    assert (k.nabavna, k.zarada, k.bez_nabavne, k.marza, k.razbijeno) == (16000, 4000, 1, "20,0%", 1)
    assert k.prosecna_prodaja == 16000
    top = analitika.top_stakla(conn, danas, danas)
    assert [(t["naziv"], t["kom"]) for t in top][0] == ("VW Golf 5 i 6 SENZOR", 2)
    voz = {v["naziv"]: v["kom"] for v in analitika.top_vozila(conn, danas, danas)}
    assert voz == {"(vozilo nije upisano)": 2, "Fiat Ducato": 1, "Citroen Jumper": 1, "Peugeot Boxer": 1}
    assert analitika.po_mesecima(conn, danas, danas)[0]["kom"] == 3
    pred = {r["naziv"]: r for r in analitika.predlog_nabavke(conn)}
    assert pred["VW Golf 5 i 6 SENZOR"]["prodato"] == 2 and pred["VW Golf 5 i 6 SENZOR"]["na_stanju"] == 0
    assert pred["VW Golf 5 i 6 SENZOR"]["predlog"] == 2
    assert analitika.prethodni_period("2026-11-01", "2026-11-30") == ("2026-10-02", "2026-10-31")


def test_stakla_koja_stoje(conn, lager):
    nabavka.ulaz(conn, lager["golf"], lager["pid"], 1, nabavna_cena=8000)
    nabavka.ulaz(conn, lager["ducato"], lager["pid"], 1, nabavna_cena=9000)
    conn.execute("UPDATE kretanje SET datum = '2025-01-10 10:00:00' WHERE lager_stavka_id IN "
                 "(SELECT id FROM lager_stavka WHERE staklo_id = ?)", (lager["ducato"],))
    r = analitika.stakla_koja_stoje(conn, 180, date(2026, 11, 10))
    assert [(x["naziv"], x["dana"]) for x in r] == [("Fiat Ducato - Citroen Jumper - Peugeot Boxer 06-", 669)]


def test_izvoz(conn, lager, tmp_path):
    nabavka.ulaz(conn, lager["golf"], lager["pid"], 1, nabavna_cena=8000)
    _prodaj(conn, lager["golf"], 12000)
    danas = date.today().isoformat()
    f = analitika.izvoz_excel(conn, danas, danas, tmp_path / "a.xlsx")
    from openpyxl import load_workbook
    wb = load_workbook(f)
    assert wb.sheetnames[0].startswith("Pregled") and wb[wb.sheetnames[1]]["A2"].value == "VW Golf 5 i 6 SENZOR"
    assert "Najprodavanija stakla" in analitika.html_izvestaj(conn, danas, danas)


# ---------------------------------------------------------------- reklamacije
def test_reklamacije(conn, lager):
    nabavka.ulaz(conn, lager["golf"], lager["pid"], 1, dobavljac_id=lager["dob"], nabavna_cena=8000)
    pid2 = repo.add_polica(conn, repo.list_skladista(conn)[0]["id"], "Polica 2")
    repo.premesti(conn, _stavke(conn, lager["golf"])[0], 1, pid2)          # dobavljač se prati i kroz premeštanje
    p = _prodaj(conn, lager["golf"], 12000)
    with pytest.raises(LagerError):
        reklamacije.nova(conn, p["id"], " ")
    rid = reklamacije.nova(conn, p["id"], "pukotina posle 3 dana")
    r = reklamacije.get(conn, rid)
    assert (r["status"], r["dobavljac"]) == ("PRIJAVLJENA", "Stakla Beograd")
    with pytest.raises(LagerError):
        reklamacije.promeni_status(conn, rid, "RESENA")                     # preskače korake
    with pytest.raises(LagerError):
        reklamacije.promeni_status(conn, rid, "ODOBRENA")                   # bez ishoda
    reklamacije.promeni_status(conn, rid, "KOD_DOBAVLJACA")
    reklamacije.promeni_status(conn, rid, "ODOBRENA", ishod="ZAMENA", trosak=1500)
    assert len(reklamacije.list_reklamacije(conn, samo_otvorene=True)) == 1
    reklamacije.promeni_status(conn, rid, "RESENA", napomena="zamenjeno")
    r = reklamacije.get(conn, rid)
    assert (r["status"], r["ishod"], r["trosak"], r["napomena"]) == ("RESENA", "ZAMENA", 1500, "zamenjeno")
    assert r["zatvoreno"] and reklamacije.list_reklamacije(conn, samo_otvorene=True) == []
    assert len(reklamacije.istorija(conn, rid)) == 4
    danas = date.today().isoformat()
    assert analitika.reklamacije_po_dobavljacu(conn, danas, danas) == [
        {"dobavljac": "Stakla Beograd", "broj": 1, "trosak": 1500}]


# ---------------------------------------------------------------- dokumenti
def test_dokumenti(conn, lager):
    nabavka.ulaz(conn, lager["golf"], lager["pid"], 1, nabavna_cena=8000)
    kupac = prodaja.add_kupac(conn, "Jovan")
    p = _prodaj(conn, lager["golf"], 12000, kupac_id=kupac, tablice="SD 111-AA")
    with pytest.raises(LagerError):
        dokumenti.novi(conn, "PREDRACUN", [])
    d1 = dokumenti.novi(conn, "PREDRACUN", [dokumenti.Stavka("Golf 7 vetrobran", 2, 15000)], kupac_id=kupac,
                        datum="2026-11-10")
    d2 = dokumenti.novi(conn, "PREDRACUN", [dokumenti.Stavka("X", 1, 100)], datum="2026-11-11")
    assert (dokumenti.get(conn, d1)["broj"], dokumenti.get(conn, d2)["broj"]) == ("PR-2026-0001", "PR-2026-0002")
    o = dokumenti.otpremnica_za_prodaju(conn, p["id"])
    assert dokumenti.otpremnica_za_prodaju(conn, p["id"]) == o
    assert dokumenti.get(conn, o)["broj"].startswith("OT-") and dokumenti.get(conn, d1)["ukupno"] == 30000
    dokumenti.set_firma(conn, {"firma_naziv": "Auto stakla DEMO", "firma_pib": "100000000"}, pdv_stopa=20)
    h = dokumenti.html_dokument(conn, d1)
    assert "Auto stakla DEMO" in h and "nije fiskalni" in h and "25.000 RSD" in h and "30.000 RSD" in h
    with pytest.raises(LagerError):
        dokumenti.set_firma(conn, {}, pdv_stopa=150)
    assert len(dokumenti.list_dokumenti(conn)) == 3


def test_izdanje():
    from autostakla import version
    assert version.is_better() and version.APP_NAME == "AutoStaklaBetter"
