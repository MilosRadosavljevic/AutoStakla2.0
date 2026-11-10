"""Analitika prodaje: promet, zarada, najprodavanija stakla i vozila, šta stoji, predlog nabavke.

Prodajne cene su SA PDV-om; zarada se računa bez PDV-a: osnovica prodaje − prosečna ponderisana nabavna cena
(nabavke tog stakla do dana prodaje; ako ih nema – sve nabavke tog stakla; ako ni toga nema – zarada nepoznata).
Svi iznosi su celi dinari.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from autostakla.better import nabavka, novac, prodaja


@dataclass
class Kpi:
    broj_prodaja: int = 0
    komada: int = 0
    promet: int = 0                 # sa PDV-om
    promet_bez_pdv: int = 0
    promet_poznata_nabavna: int = 0  # osnovica samo za prodaje kojima znamo nabavnu (za maržu)
    nabavna: int = 0
    zarada: int = 0
    bez_nabavne: int = 0            # prodaje bez poznate nabavne cene
    razbijeno: int = 0
    vraceno_dobavljacu: int = 0
    reklamacija: int = 0
    reklamacija_trosak: int = 0

    @property
    def prosecna_prodaja(self) -> int | None:
        return (self.promet + self.broj_prodaja // 2) // self.broj_prodaja if self.broj_prodaja else None

    @property
    def marza(self) -> str:
        return novac.procenat(self.zarada, self.promet_poznata_nabavna)


def prethodni_period(od: str, do: str) -> tuple[str, str]:
    d1, d2 = date.fromisoformat(od), date.fromisoformat(do)
    n = (d2 - d1).days + 1
    kraj = d1 - timedelta(days=1)
    return (kraj - timedelta(days=n - 1)).isoformat(), kraj.isoformat()


def prodaje(conn, od: str, do: str) -> list[dict]:
    """Prodaje u periodu sa osnovicom, nabavnom vrednošću i zaradom (None kad nabavna nije poznata)."""
    stopa = novac.pdv_stopa(conn)
    cache: dict[tuple[int, str], int | None] = {}
    rows = prodaja.list_prodaja(conn, od, do)
    for r in rows:
        dan = r["datum"][:10]
        key = (r["staklo_id"], dan)
        if key not in cache:
            jed = nabavka.prosecna_nabavna(conn, r["staklo_id"], dan)
            cache[key] = jed if jed is not None else nabavka.prosecna_nabavna(conn, r["staklo_id"])
        r["bez_pdv"] = novac.bez_pdv(r["ukupno"], stopa)
        r["nabavna_jed"] = cache[key]
        r["nabavna"] = cache[key] * r["kom"] if cache[key] is not None else None
        r["zarada"] = r["bez_pdv"] - r["nabavna"] if r["nabavna"] is not None else None
    return rows


def _izlazi_po_razlogu(conn, od: str, do: str, razlog: str) -> int:
    return conn.execute(
        "SELECT COALESCE(SUM(-k.kolicina), 0) FROM kretanje k JOIN kretanje_razlog r ON r.kretanje_id = k.id "
        "WHERE r.razlog = ? AND substr(k.datum, 1, 10) BETWEEN ? AND ?", (razlog, od, do)).fetchone()[0]


def kpi(conn, od: str, do: str) -> Kpi:
    k = Kpi()
    for r in prodaje(conn, od, do):
        k.broj_prodaja += 1
        k.komada += r["kom"]
        k.promet += r["ukupno"]
        k.promet_bez_pdv += r["bez_pdv"]
        if r["nabavna"] is None:
            k.bez_nabavne += 1
        else:
            k.nabavna += r["nabavna"]
            k.zarada += r["zarada"]
            k.promet_poznata_nabavna += r["bez_pdv"]
    k.razbijeno = _izlazi_po_razlogu(conn, od, do, "RAZBIJENO")
    k.vraceno_dobavljacu = _izlazi_po_razlogu(conn, od, do, "POVRAT_DOBAVLJACU")
    k.reklamacija, k.reklamacija_trosak = conn.execute(
        "SELECT COUNT(*), COALESCE(SUM(trosak), 0) FROM reklamacija WHERE datum_prijave BETWEEN ? AND ?",
        (od, do)).fetchone()
    return k


def _top(items: dict, n: int) -> list[dict]:
    return sorted(items.values(), key=lambda x: (-x["kom"], -x["promet"], x["naziv"]))[:n]


def top_stakla(conn, od: str, do: str, n: int = 10) -> list[dict]:
    agg: dict[int, dict] = {}
    for r in prodaje(conn, od, do):
        a = agg.setdefault(r["staklo_id"], {"naziv": r["staklo"], "kom": 0, "promet": 0, "zarada": 0})
        a["kom"] += r["kom"]
        a["promet"] += r["ukupno"]
        a["zarada"] += r["zarada"] or 0
    return _top(agg, n)


def top_vozila(conn, od: str, do: str, n: int = 10) -> list[dict]:
    """Za koja vozila se najviše prodaje (staklo koje odgovara za više vozila broji se za svako)."""
    vozila: dict[int, list[str]] = {}
    for v in conn.execute("SELECT staklo_id, marka, model FROM staklo_vozilo"):
        naziv = " ".join(x for x in (v["marka"], v["model"]) if x)
        lst = vozila.setdefault(v["staklo_id"], [])
        if naziv not in lst:
            lst.append(naziv)
    agg: dict[str, dict] = {}
    for r in prodaje(conn, od, do):
        for naziv in vozila.get(r["staklo_id"], ["(vozilo nije upisano)"]):
            a = agg.setdefault(naziv, {"naziv": naziv, "kom": 0, "promet": 0})
            a["kom"] += r["kom"]
            a["promet"] += r["ukupno"]
    return _top(agg, n)


def po_mesecima(conn, od: str, do: str) -> list[dict]:
    agg: dict[str, dict] = {}
    for r in prodaje(conn, od, do):
        m = r["datum"][:7]
        a = agg.setdefault(m, {"mesec": m, "kom": 0, "promet": 0, "zarada": 0})
        a["kom"] += r["kom"]
        a["promet"] += r["ukupno"]
        a["zarada"] += r["zarada"] or 0
    return [agg[m] for m in sorted(agg)]


def stakla_koja_stoje(conn, dana: int = 180, danas: date | None = None) -> list[dict]:
    """Stakla na stanju koja su na lageru bar 'dana' dana i nisu se prodala u poslednjih 'dana' dana.
    (Premeštanje pravi novo mesto, pa se tad „na lageru od“ računa od premeštanja.)"""
    danas = danas or date.today()
    granica = (danas - timedelta(days=dana)).isoformat()
    rows = [dict(r) for r in conn.execute(
        """SELECT s.id AS staklo_id, s.naziv, SUM(v.kolicina) AS kom,
                  MIN((SELECT MIN(k.datum) FROM kretanje k WHERE k.lager_stavka_id = v.lager_stavka_id)) AS od,
                  (SELECT MAX(k.datum) FROM kretanje k JOIN kretanje_razlog r ON r.kretanje_id = k.id
                     JOIN lager_stavka l2 ON l2.id = k.lager_stavka_id
                    WHERE l2.staklo_id = s.id AND r.razlog = 'PRODATO') AS poslednja_prodaja,
                  group_concat(DISTINCT sk.naziv) AS skladista
           FROM v_stanje v JOIN staklo s ON s.id = v.staklo_id
           JOIN skladiste sk ON sk.id = v.skladiste_id
           WHERE v.kolicina > 0 GROUP BY s.id""")]
    result = []
    for r in rows:
        if r["od"] and r["od"][:10] <= granica and (not r["poslednja_prodaja"] or r["poslednja_prodaja"][:10] < granica):
            r["dana"] = (danas - date.fromisoformat(r["od"][:10])).days
            result.append(r)
    return sorted(result, key=lambda x: (-x["dana"], x["naziv"]))


def predlog_nabavke(conn, dana: int = 90, danas: date | None = None) -> list[dict]:
    """Šta naručiti: prodato u poslednjih 'dana' dana naspram stanja, uz najjeftinijeg dobavljača."""
    danas = danas or date.today()
    od = (danas - timedelta(days=dana - 1)).isoformat()
    prodato: dict[int, dict] = {}
    for r in prodaja.list_prodaja(conn, od, danas.isoformat()):
        p = prodato.setdefault(r["staklo_id"], {"staklo_id": r["staklo_id"], "naziv": r["staklo"], "prodato": 0})
        p["prodato"] += r["kom"]
    stanje = {r[0]: r[1] for r in conn.execute("SELECT staklo_id, SUM(kolicina) FROM v_stanje GROUP BY staklo_id")}
    result = []
    for p in prodato.values():
        p["na_stanju"] = stanje.get(p["staklo_id"], 0) or 0
        p["predlog"] = max(0, p["prodato"] - p["na_stanju"])
        n = nabavka.najjeftiniji(conn, p["staklo_id"])
        p["dobavljac"] = n["dobavljac"] if n else None
        p["cena"] = n["cena"] if n else None
        result.append(p)
    return sorted(result, key=lambda x: (-x["predlog"], -x["prodato"], x["naziv"]))


def reklamacije_po_dobavljacu(conn, od: str, do: str) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT COALESCE(d.naziv, '(nepoznat)') AS dobavljac, COUNT(*) AS broj, COALESCE(SUM(r.trosak), 0) AS trosak
           FROM reklamacija r LEFT JOIN dobavljac d ON d.id = r.dobavljac_id
           WHERE r.datum_prijave BETWEEN ? AND ? GROUP BY d.id ORDER BY broj DESC, trosak DESC""", (od, do))]


# =====================================================================
# Izvoz
# =====================================================================
def _sekcije(conn, od: str, do: str) -> list[tuple[str, list[str], list[list]]]:
    k = kpi(conn, od, do)
    p_od, p_do = prethodni_period(od, do)
    pk = kpi(conn, p_od, p_do)
    pregled = [
        ["Broj prodaja", k.broj_prodaja, pk.broj_prodaja],
        ["Prodato komada", k.komada, pk.komada],
        ["Promet sa PDV-om", k.promet, pk.promet],
        ["Promet bez PDV-a", k.promet_bez_pdv, pk.promet_bez_pdv],
        ["Zarada (bez PDV-a)", k.zarada, pk.zarada],
        ["Marža", k.marza, pk.marza],
        ["Prosečna prodaja", k.prosecna_prodaja, pk.prosecna_prodaja],
        ["Prodaje bez poznate nabavne cene", k.bez_nabavne, pk.bez_nabavne],
        ["Razbijeno (kom)", k.razbijeno, pk.razbijeno],
        ["Vraćeno dobavljaču (kom)", k.vraceno_dobavljacu, pk.vraceno_dobavljacu],
        ["Reklamacija", k.reklamacija, pk.reklamacija],
        ["Trošak reklamacija", k.reklamacija_trosak, pk.reklamacija_trosak],
    ]
    return [
        (f"Pregled {od} – {do}", ["Pokazatelj", "Period", f"Prethodni ({p_od} – {p_do})"], pregled),
        ("Najprodavanija stakla", ["Staklo", "Kom", "Promet", "Zarada"],
         [[r["naziv"], r["kom"], r["promet"], r["zarada"]] for r in top_stakla(conn, od, do, 50)]),
        ("Najčešća vozila", ["Vozilo", "Kom", "Promet"],
         [[r["naziv"], r["kom"], r["promet"]] for r in top_vozila(conn, od, do, 50)]),
        ("Po mesecima", ["Mesec", "Kom", "Promet", "Zarada"],
         [[r["mesec"], r["kom"], r["promet"], r["zarada"]] for r in po_mesecima(conn, od, do)]),
        ("Stakla koja stoje (180+ dana)", ["Staklo", "Kom", "Dana na lageru", "Poslednja prodaja", "Skladište"],
         [[r["naziv"], r["kom"], r["dana"], (r["poslednja_prodaja"] or "")[:10], r["skladista"]]
          for r in stakla_koja_stoje(conn)]),
        ("Predlog nabavke (90 dana)", ["Staklo", "Prodato", "Na stanju", "Naručiti", "Dobavljač", "Cena bez PDV"],
         [[r["naziv"], r["prodato"], r["na_stanju"], r["predlog"], r["dobavljac"] or "", r["cena"]]
          for r in predlog_nabavke(conn)]),
        ("Reklamacije po dobavljaču", ["Dobavljač", "Broj", "Trošak"],
         [[r["dobavljac"], r["broj"], r["trosak"]] for r in reklamacije_po_dobavljacu(conn, od, do)]),
    ]


def izvoz_excel(conn, od: str, do: str, target: Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    wb.remove(wb.active)
    for naslov, zaglavlje, redovi in _sekcije(conn, od, do):
        ws = wb.create_sheet(naslov[:31].replace("/", "-"))
        ws.append(zaglavlje)
        for c in ws[1]:
            c.font = Font(bold=True)
        for red in redovi:
            ws.append(red)
        for i, _ in enumerate(zaglavlje):
            ws.column_dimensions[chr(65 + i)].width = 42 if i == 0 else 18
    target.parent.mkdir(parents=True, exist_ok=True)
    wb.save(target)
    return target


def html_izvestaj(conn, od: str, do: str) -> str:
    def cell(v) -> str:
        if isinstance(v, int) and not isinstance(v, bool):
            return f"<td align=right>{v:,}</td>".replace(",", ".")
        return f"<td>{html.escape(str(v if v is not None else '–'))}</td>"

    parts = ["<html><body><h1>Analitika prodaje</h1>",
             f"<p>Period: {od} – {do}. Iznosi su u dinarima; promet je sa PDV-om, zarada bez PDV-a.</p>"]
    for naslov, zaglavlje, redovi in _sekcije(conn, od, do):
        parts.append(f"<h2>{html.escape(naslov)}</h2><table class='prikaz'><tr>"
                     + "".join(f"<th>{html.escape(z)}</th>" for z in zaglavlje) + "</tr>")
        for red in redovi or [["(nema podataka)"] + [""] * (len(zaglavlje) - 1)]:
            parts.append("<tr>" + "".join(cell(v) for v in red) + "</tr>")
        parts.append("</table>")
    parts.append(f"<p class='datum'>Napravljeno {datetime.now():%d.%m.%Y %H:%M}</p></body></html>")
    return "".join(parts)
