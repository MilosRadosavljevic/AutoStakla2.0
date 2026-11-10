import pytest

from autostakla.lager import repo, search
from autostakla.lager.repo import Filter, LagerError, Staklo, Vozilo


def audit_count(conn, akcija=None):
    sql = "SELECT COUNT(*) FROM audit_log" + (" WHERE akcija = ?" if akcija else "")
    return conn.execute(sql, (akcija,) if akcija else ()).fetchone()[0]


@pytest.fixture
def mesto(conn):
    sid = repo.add_skladiste(conn, "1 Stalak", "kod ulaza")
    pid = repo.list_police(conn, sid)[0]["id"]
    return sid, pid


def staklo(conn, naziv, **kw):
    return repo.add_staklo(conn, Staklo(naziv, **kw))


def golf(conn, senzor=True):
    return repo.add_staklo(conn, Staklo(
        "VW Golf 5 i 6 SENZOR" if senzor else "VW Golf 5 i 6", senzor=senzor,
        vozila=[Vozilo("VW", "Golf", "5"), Vozilo("VW", "Golf", "6")]))


def raspored(conn, sid):
    """[(pozicija, naziv, kom, polica)] za skladište, samo ono na stanju."""
    return [(r["pozicija"], r["naziv"], r["kolicina"], r["polica"])
            for r in repo.pretraga(conn, Filter(skladiste_id=sid))]


# ---------- skladišta ----------
def test_skladiste_crud(conn):
    sid = repo.add_skladiste(conn, "Terasa")
    assert [p["naziv"] for p in repo.list_police(conn, sid)] == ["Polica 1"]
    repo.update_skladiste(conn, sid, "Velika terasa", "pored garaže")
    s = repo.get_skladiste(conn, sid)
    assert s["naziv"] == "Velika terasa" and s["opis"] == "pored garaže"
    assert repo.delete_skladiste(conn, sid) == "obrisano"
    assert repo.list_skladista(conn) == []
    assert audit_count(conn, "BRISANJE") == 1


def test_skladiste_naziv_obavezan_i_jedinstven(conn):
    repo.add_skladiste(conn, "Kanta")
    with pytest.raises(LagerError, match="već postoji"):
        repo.add_skladiste(conn, "kanta")
    with pytest.raises(LagerError, match="obavezan"):
        repo.add_skladiste(conn, "   ")


def test_skladiste_sa_staklima_ne_moze_da_se_obrise(conn, mesto):
    sid, pid = mesto
    prva = repo.ulaz(conn, golf(conn), pid, 2)
    with pytest.raises(LagerError, match="ima još 2"):
        repo.delete_skladiste(conn, sid)
    repo.izlaz(conn, prva, 1)
    repo.izlaz(conn, prva + 1, 1)
    assert repo.delete_skladiste(conn, sid) == "ugaseno"  # istorija ostaje
    assert repo.list_skladista(conn) == []
    assert len(repo.list_skladista(conn, samo_aktivna=False)) == 1


def test_redosled_skladista(conn):
    a, b, c = (repo.add_skladiste(conn, n) for n in ("A", "B", "C"))
    repo.move_skladiste(conn, c, -1)
    assert [s["naziv"] for s in repo.list_skladista(conn)] == ["A", "C", "B"]


def test_police_crud(conn, mesto):
    sid, pid = mesto
    p2 = repo.add_polica(conn, sid, "Polica 2")
    repo.update_polica(conn, p2, "Gornja", "najviša")
    with pytest.raises(LagerError, match="već postoji"):
        repo.add_polica(conn, sid, "gornja")
    repo.move_polica(conn, p2, -1)
    assert [p["naziv"] for p in repo.list_police(conn, sid)] == ["Gornja", "Polica 1"]
    assert repo.delete_polica(conn, p2) == "obrisano"


# ---------- pozicije ----------
def test_ulaz_na_kraj_svaki_komad_svoj_broj(conn, mesto):
    sid, pid = mesto
    repo.ulaz(conn, staklo(conn, "Ducato"), pid, 1)
    repo.ulaz(conn, staklo(conn, "Audi A4"), pid, 2)
    assert raspored(conn, sid) == [(1, "Ducato", 1, "Polica 1"), (2, "Audi A4", 1, "Polica 1"),
                                   (3, "Audi A4", 1, "Polica 1")]


def test_ubacivanje_u_sredinu_pomera_ostale(conn, mesto):
    """Miloševprimer: između Ducata i Audija ubaci 2 Tourana -> Touran 3 i 4, Audi 5..."""
    sid, pid = mesto
    for n in ("Sprinter", "Ducato", "Audi A4", "Master"):
        repo.ulaz(conn, staklo(conn, n), pid, 1)
    repo.ulaz(conn, staklo(conn, "Touran"), pid, 2, pozicija=3)
    assert [(p, n) for p, n, *_ in raspored(conn, sid)] == [
        (1, "Sprinter"), (2, "Ducato"), (3, "Touran"), (4, "Touran"), (5, "Audi A4"), (6, "Master")]


def test_brojevi_idu_kroz_celo_skladiste(conn, mesto):
    sid, p1 = mesto
    p2 = repo.add_polica(conn, sid, "Polica 2")
    repo.ulaz(conn, staklo(conn, "A"), p1, 1)
    repo.ulaz(conn, staklo(conn, "B"), p1, 1)
    repo.ulaz(conn, staklo(conn, "C"), p2, 1)          # prazna polica 2 -> nastavlja: 3
    repo.ulaz(conn, staklo(conn, "X"), p1, 1)          # na kraj police 1 -> 3, C ide na 4
    assert [(p, n, pol) for p, n, _, pol in raspored(conn, sid)] == [
        (1, "A", "Polica 1"), (2, "B", "Polica 1"), (3, "X", "Polica 1"), (4, "C", "Polica 2")]
    assert repo.polica_raspon(conn, p2) == (4, 5)
    assert repo.polica_raspon(conn, p1) == (1, 4)


def test_pozicija_van_police_se_ogranicava(conn, mesto):
    sid, p1 = mesto
    p2 = repo.add_polica(conn, sid, "Polica 2")
    repo.ulaz(conn, staklo(conn, "A"), p1, 1)
    repo.ulaz(conn, staklo(conn, "C"), p2, 1)
    repo.ulaz(conn, staklo(conn, "B"), p1, 1, pozicija=99)   # ne sme da preskoči policu 2
    assert [(p, n) for p, n, *_ in raspored(conn, sid)] == [(1, "A"), (2, "B"), (3, "C")]


def test_izlaz_do_nule_oslobadja_broj(conn, mesto):
    sid, pid = mesto
    ids = [repo.ulaz(conn, staklo(conn, n), pid, 1) for n in ("A", "B", "C")]
    repo.izlaz(conn, ids[1], 1)
    assert [(p, n) for p, n, *_ in raspored(conn, sid)] == [(1, "A"), (2, "C")]
    # vraćanje ispravkom -> dobija broj na kraju police
    repo.korekcija(conn, ids[1], 1)
    assert [(p, n) for p, n, *_ in raspored(conn, sid)] == [(1, "A"), (2, "C"), (3, "B")]


def test_zajednicki_broj_sa_papira_ostaje(conn, mesto):
    """Dve stavke na istom broju (npr. „2 bez + 1 senzor“): kad jedna nestane, broj ostaje."""
    sid, pid = mesto
    a = repo.ulaz(conn, staklo(conn, "Clio 3"), pid, 1)
    b = repo.ulaz(conn, staklo(conn, "Clio 3 SENZOR"), pid, 1)
    c = repo.ulaz(conn, staklo(conn, "Megan"), pid, 1)
    conn.execute("UPDATE lager_stavka SET pozicija = 1 WHERE id = ?", (b,))
    conn.execute("UPDATE lager_stavka SET pozicija = 2 WHERE id = ?", (c,))
    repo.izlaz(conn, b, 1)
    assert [(p, n) for p, n, *_ in raspored(conn, sid)] == [(1, "Clio 3"), (2, "Megan")]
    assert a


def test_izmeni_mesto_pozicija_i_napomena(conn, mesto):
    sid, pid = mesto
    ids = [repo.ulaz(conn, staklo(conn, n), pid, 1) for n in ("A", "B", "C", "D")]
    assert repo.polica_raspon(conn, pid, osim_stavke=ids[1]) == (1, 4)  # bez B ostaju 3 -> kraj je 4
    repo.izmeni_mesto(conn, ids[3], pid, 2, "H137 163")       # D sa 4 na 2
    assert [(p, n) for p, n, *_ in raspored(conn, sid)] == [(1, "A"), (2, "D"), (3, "B"), (4, "C")]
    repo.izmeni_mesto(conn, ids[0], pid, 4, None)             # A sa 1 na kraj
    assert [(p, n) for p, n, *_ in raspored(conn, sid)] == [(1, "D"), (2, "B"), (3, "C"), (4, "A")]
    r = [r for r in repo.pretraga(conn, Filter("D")) if r["naziv"] == "D"][0]
    assert r["stavka_napomena"] == "H137 163"
    assert audit_count(conn, "IZMENA") == 2


def test_izmeni_mesto_samo_isto_skladiste(conn, mesto):
    _, pid = mesto
    s2 = repo.add_skladiste(conn, "Drugo")
    p_drugo = repo.list_police(conn, s2)[0]["id"]
    st = repo.ulaz(conn, staklo(conn, "A"), pid, 1)
    with pytest.raises(LagerError, match="Premesti"):
        repo.izmeni_mesto(conn, st, p_drugo, 1, None)


def test_premestanje(conn, mesto):
    sid, pid = mesto
    s2 = repo.add_skladiste(conn, "Terasa")
    p_t = repo.list_police(conn, s2)[0]["id"]
    repo.ulaz(conn, staklo(conn, "X"), p_t, 1)
    a = repo.ulaz(conn, staklo(conn, "A"), pid, 1)
    b = repo.ulaz(conn, staklo(conn, "B"), pid, 1)
    conn.execute("INSERT INTO kretanje (lager_stavka_id, kolicina, vrsta) VALUES (?, 2, 'ULAZ')", (b,))  # B = 3 kom
    nova = repo.premesti(conn, b, 2, p_t, pozicija=1)
    assert [(p, n, k) for p, n, k, _ in raspored(conn, s2)] == [(1, "B", 1), (2, "B", 1), (3, "X", 1)]
    assert repo.stanje_stavke(conn, b) == 1
    repo.premesti(conn, a, 1, p_t)                            # A sasvim ode -> B na Stalku postaje 1
    assert [(p, n) for p, n, *_ in raspored(conn, sid)] == [(1, "B")]
    k = conn.execute("SELECT id, veza_id FROM kretanje WHERE vrsta='PREMESTANJE' ORDER BY id").fetchall()
    assert k[0]["veza_id"] is not None and nova


def test_ulaz_izlaz_korekcija_istorija(conn, mesto):
    _, pid = mesto
    st = repo.ulaz(conn, golf(conn), pid, 1)
    conn.execute("INSERT INTO kretanje (lager_stavka_id, kolicina, vrsta) VALUES (?, 3, 'POCETNO')", (st,))
    repo.izlaz(conn, st, 1, "ugrađeno")
    with pytest.raises(LagerError, match="Na stanju je 3"):
        repo.izlaz(conn, st, 5)
    repo.korekcija(conn, st, 1, "prebrojano")
    assert repo.stanje_stavke(conn, st) == 1
    assert [k["vrsta"] for k in repo.istorija(conn, st)] == ["KOREKCIJA", "IZLAZ", "POCETNO", "ULAZ"]
    assert audit_count(conn, "IZLAZ") == 1


@pytest.mark.parametrize("kol", [0, -1, "abc"])
def test_neispravna_kolicina(conn, mesto, kol):
    with pytest.raises(LagerError):
        repo.ulaz(conn, golf(conn), mesto[1], kol)


def test_greska_u_sredini_ne_ostavlja_pola_posla(conn, mesto):
    _, pid = mesto
    stavka = repo.ulaz(conn, golf(conn), pid, 1)
    before = conn.execute("SELECT COUNT(*) FROM kretanje").fetchone()[0]
    with pytest.raises(LagerError):
        repo.premesti(conn, stavka, 1, 99999)  # nepostojeća polica
    assert conn.execute("SELECT COUNT(*) FROM kretanje").fetchone()[0] == before
    assert repo.stanje_stavke(conn, stavka) == 1
    assert not conn.in_transaction


# ---------- pretraga ----------
def test_search_words():
    assert search.words("Pežo 307 SENZOROM") == ["pezo", "307", "senzor"]
    assert search.words("Škoda Octavia A5 04-11") == ["skoda", "octavia", "a5", "04", "11"]


def test_pretraga(conn, mesto):
    sid, pid = mesto
    repo.ulaz(conn, golf(conn), pid, 1)
    repo.ulaz(conn, golf(conn, senzor=False), pid, 1)
    repo.ulaz(conn, staklo(conn, "VW Golf 4 - Bora 05-"), pid, 1)
    repo.ulaz(conn, staklo(conn, "Pezo 307 SENZOR ROMB", senzor=True, senzor_opis="ROMB"), pid, 1)

    def nadji(tekst, **kw):
        return [r["naziv"] for r in repo.pretraga(conn, Filter(tekst=tekst, **kw))]

    assert nadji("golf 5") == ["VW Golf 5 i 6 SENZOR", "VW Golf 5 i 6"]   # ne i Golf 4 (05-)
    assert nadji("golf 5", senzor=True) == ["VW Golf 5 i 6 SENZOR"]
    assert nadji("peugeot 307") == ["Pezo 307 SENZOR ROMB"]
    assert nadji("romb") == ["Pezo 307 SENZOR ROMB"]
    assert len(nadji("stalak")) == 4                                      # po nazivu skladišta
    assert nadji("") and nadji("nema takvog") == []


def test_pretraga_samo_na_stanju(conn, mesto):
    _, pid = mesto
    stavka = repo.ulaz(conn, golf(conn), pid, 1)
    repo.izlaz(conn, stavka, 1)
    assert repo.pretraga(conn, Filter("golf")) == []
    assert len(repo.pretraga(conn, Filter("golf", samo_na_stanju=False))) == 1


def test_staklo_validacija(conn):
    with pytest.raises(LagerError):
        repo.add_staklo(conn, Staklo(""))
    with pytest.raises(LagerError, match="godina od"):
        repo.add_staklo(conn, Staklo("X", vozila=[Vozilo("VW", "Golf", godina_od=2010, godina_do=2005)]))
    sid = golf(conn)
    s = repo.get_staklo(conn, sid)
    s.napomena = "niža pločica"
    s.vozila = s.vozila[:1]
    repo.update_staklo(conn, s)
    s2 = repo.get_staklo(conn, sid)
    assert s2.napomena == "niža pločica" and len(s2.vozila) == 1
