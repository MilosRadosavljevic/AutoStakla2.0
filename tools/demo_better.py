"""Demo podaci za probu AutoStaklaBetter-a: firma, dobavljači i cene, nabavke, ~7 meseci prodaje, razbijena stakla,
reklamacije i predračuni. Kupci, telefoni i tablice su izmišljeni.

Pravi ZASEBNU bazu u demo_root\\ (prava baza i dev_root se ne diraju):
    .\\.venv\\Scripts\\python.exe tools\\demo_better.py
Najlakše preko tools\\probaj_better.ps1.
"""
from __future__ import annotations

import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("AUTOSTAKLA_ROOT", str(ROOT / "demo_root"))
sys.path.insert(0, str(ROOT / "src"))

from autostakla.better import dokumenti, nabavka, prodaja, reklamacije, vozila  # noqa: E402
from autostakla.better.prodaja import ProdajaPodaci  # noqa: E402
from autostakla.core import db, paths  # noqa: E402
from autostakla.lager import repo  # noqa: E402

DANA = 210
IMENA = ["Petar", "Marko", "Jovan", "Nikola", "Stefan", "Milan", "Dragan", "Zoran", "Ivana", "Jelena", "Ana", "Milica"]
PREZIMENA = ["Petrović", "Jovanović", "Nikolić", "Marković", "Đorđević", "Stojanović", "Ilić", "Pavlović", "Kostić"]
FIRME = ["Prevoz Morava doo", "Auto servis Kod Mileta", "Kombi linija doo", "Taxi Plavi"]
GRADOVI = ["SP", "SD", "BG", "KG", "JA", "PO"]


def _datumiraj(conn, pre: int, dan: date, rnd: random.Random) -> None:
    """Kretanja napravljena posle id-a 'pre' dobijaju datum 'dan' (demo se pravi „unazad“)."""
    vreme = f"{rnd.randrange(8, 18):02d}:{rnd.randrange(60):02d}:00"
    conn.execute("UPDATE kretanje SET datum = ? WHERE id > ?", (f"{dan} {vreme}", pre))


def _max_kretanje(conn) -> int:
    return conn.execute("SELECT COALESCE(MAX(id), 0) FROM kretanje").fetchone()[0]


def main() -> int:
    paths.ensure_dirs()
    if paths.db_path().exists():
        print(f"Demo baza već postoji: {paths.db_path()}\nZa novu: tools\\probaj_better.ps1 -Novo")
        return 0
    conn = db.connect()
    db.apply_migrations(conn)
    rnd = random.Random(2026)
    danas = date.today()
    pocetak = danas - timedelta(days=DANA)

    dokumenti.set_firma(conn, {"firma_naziv": "AUTO STAKLA DEMO PR", "firma_adresa": "Primer ulica 1",
                               "firma_mesto": "11420 Smederevska Palanka", "firma_pib": "100000000",
                               "firma_telefon": "060 000 0000"}, pdv_stopa=20)
    for p in vozila.predlozi(conn):
        if p.siguran and p.vozila:
            vozila.upisi(conn, p.staklo_id, p.vozila)

    dob = [nabavka.add_dobavljac(conn, n, t) for n, t in (
        ("Stakla Beograd", "011 111 1111"), ("AutoGlas Niš", "018 222 222"), ("Euro Glass Novi Sad", "021 333 333"))]
    stakla = [s["id"] for s in repo.list_stakla(conn)]
    osnovna = {s: rnd.randrange(60, 260) * 100 for s in stakla}          # nabavna bez PDV-a
    for s in stakla:
        for d in dob:
            if rnd.random() < 0.8:
                nabavka.postavi_cenu(conn, s, d, osnovna[s] + rnd.randrange(-15, 16) * 100, pocetak.isoformat())
    popularna = rnd.sample(stakla, max(1, len(stakla) // 3))

    kupci = [prodaja.add_kupac(conn, f"{rnd.choice(IMENA)} {rnd.choice(PREZIMENA)}",
                               f"06{rnd.randrange(0, 10)} {rnd.randrange(100, 999)} {rnd.randrange(100, 999)}")
             for _ in range(30)] + [prodaja.add_kupac(conn, f) for f in FIRME]
    police = {r["staklo_id"]: r["polica_id"] for r in repo.pretraga(conn, repo.Filter())}
    prva_polica = repo.list_police(conn, repo.list_skladista(conn)[0]["id"])[0]["id"]

    def kupi(staklo: int, kom: int, dan: date) -> None:
        c = nabavka.najjeftiniji(conn, staklo)
        pre = _max_kretanje(conn)
        nabavka.ulaz(conn, staklo, police.get(staklo, prva_polica), kom,
                     dobavljac_id=c["dobavljac_id"] if c else None,
                     nabavna_cena=(c["cena"] if c else osnovna[staklo]) + rnd.randrange(-5, 6) * 100,
                     dokument=f"F-{rnd.randrange(1000, 9999)}")
        _datumiraj(conn, pre, dan, rnd)

    for s in rnd.sample(stakla, len(stakla) * 2 // 3):          # prva nabavka za veći deo stakala
        kupi(s, rnd.randrange(1, 3), pocetak)

    prodaja_ids = []
    for i in range(1, DANA + 1):
        dan = pocetak + timedelta(days=i)
        if dan.weekday() == 6:
            continue
        na_stanju = [r for r in repo.pretraga(conn, repo.Filter()) if r["kolicina"] > 0]
        for _ in range(rnd.choice([0, 1, 1, 2, 2, 3])):
            if not na_stanju:
                break
            izbor = [r for r in na_stanju if r["staklo_id"] in popularna] if rnd.random() < 0.6 else []
            r = rnd.choice(izbor or na_stanju)
            na_stanju.remove(r)
            cena = (osnovna[r["staklo_id"]] * rnd.choice([125, 135, 150, 160]) * 120 // 10000) // 100 * 100
            pre = _max_kretanje(conn)
            prodaja.izlaz(conn, r["lager_stavka_id"], 1, "PRODATO", prodaja=ProdajaPodaci(
                cena, rnd.choice(kupci) if rnd.random() < 0.85 else None,
                tablice=f"{rnd.choice(GRADOVI)} {rnd.randrange(100, 999)}-{chr(65 + rnd.randrange(26))}"
                        f"{chr(65 + rnd.randrange(26))}",
                sa_ugradnjom=rnd.random() < 0.7))
            _datumiraj(conn, pre, dan, rnd)
            prodaja_ids.append((conn.execute("SELECT MAX(id) FROM prodaja").fetchone()[0], dan))
        if na_stanju and rnd.random() < 0.03:
            pre = _max_kretanje(conn)
            prodaja.izlaz(conn, rnd.choice(na_stanju)["lager_stavka_id"], 1, "RAZBIJENO", "pao pri istovaru")
            _datumiraj(conn, pre, dan, rnd)
        if dan.weekday() == 0:                                     # ponedeljkom nabavka popularnih kojih nema
            stanje = {r["staklo_id"] for r in repo.pretraga(conn, repo.Filter())}
            for s in popularna:
                if s not in stanje and rnd.random() < 0.7:
                    kupi(s, rnd.randrange(2, 5), dan)

    for pid, dan in rnd.sample(prodaja_ids, max(1, len(prodaja_ids) // 25)):
        rid = reklamacije.nova(conn, pid, rnd.choice(["pukotina posle nekoliko dana", "curi na ivici",
                                                      "senzor kiše ne radi", "izobličenje u vidnom polju"]))
        prijava = min(danas, dan + timedelta(days=rnd.randrange(2, 20)))
        conn.execute("UPDATE reklamacija SET datum_prijave = ? WHERE id = ?", (prijava.isoformat(), rid))
        put = rnd.choice([[], ["KOD_DOBAVLJACA"], ["KOD_DOBAVLJACA", "ODOBRENA", "RESENA"], ["ODBIJENA"],
                          ["ODOBRENA", "RESENA"]])
        for st in put:
            reklamacije.promeni_status(conn, rid, st, ishod=rnd.choice(list(reklamacije.ISHODI)) if st == "ODOBRENA"
                                       else None, trosak=rnd.randrange(0, 40) * 100 if st == "RESENA" else None)

    for _ in range(3):
        s = rnd.choice(stakla)
        dokumenti.novi(conn, "PREDRACUN", [dokumenti.Stavka(repo.get_staklo(conn, s).naziv, 1,
                                                            osnovna[s] * 18 // 1000 * 100, s),
                                           dokumenti.Stavka("Ugradnja", 1, 3000)], kupac_id=rnd.choice(kupci))

    print(f"Demo baza: {paths.db_path()}")
    print(f"Prodaja: {len(prodaja_ids)}, dobavljača: {len(dob)}, kupaca: {len(kupci)}, "
          f"reklamacija: {conn.execute('SELECT COUNT(*) FROM reklamacija').fetchone()[0]}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
