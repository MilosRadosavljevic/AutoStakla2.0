"""PDF štampa: spisak po skladištima (kao njegov papir) i trenutni prikaz pretrage."""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QPageLayout, QPageSize, QPdfWriter, QTextDocument

from autostakla.lager import repo
from autostakla.lager.repo import Filter

_CSS = """
body { font-family: 'Segoe UI', Arial; font-size: 11pt; }
h1 { font-size: 18pt; text-align: center; margin: 0 0 4px 0; }
.opis { text-align: center; color: #555; font-size: 9pt; }
.polica { color: #555; font-size: 9pt; margin-top: 6px; }
.kol { font-weight: bold; }
.datum { color: #888; font-size: 8pt; text-align: right; }
table.lista { border-collapse: collapse; }
table.lista td { padding: 1px 6px; }
table.prikaz { border-collapse: collapse; width: 100%; }
table.prikaz th, table.prikaz td { border: 1px solid #999; padding: 2px 5px; }
table.prikaz th { background: #ddd; }
"""


def _e(s) -> str:
    return html.escape(str(s or ""))


def _kol(n: int) -> str:
    return f' <span class="kol">{n}x</span>' if n > 1 else ""


def _footer() -> str:
    return f'<p class="datum">Odštampano {datetime.now():%d.%m.%Y %H:%M}</p>'


def html_spisak(conn, skladiste_ids: list[int] | None = None, nova_strana: bool = True) -> str:
    rows = repo.pretraga(conn, Filter())
    parts = [f"<html><head><style>{_CSS}</style></head><body>"]
    first = True
    for sk in repo.list_skladista(conn):
        if skladiste_ids and sk["id"] not in skladiste_ids:
            continue
        sk_rows = [r for r in rows if r["skladiste_id"] == sk["id"]]
        style = ' style="page-break-before: always"' if (nova_strana and not first) else ""
        parts.append(f"<h1{style}>{_e(sk['naziv'])}</h1>")
        if sk["opis"]:
            parts.append(f'<p class="opis">{_e(sk["opis"])}</p>')
        police = repo.list_police(conn, sk["id"])
        for i, p in enumerate(police):
            p_rows = [r for r in sk_rows if r["polica_id"] == p["id"]]
            if i > 0:
                parts.append("<hr>")
            parts.append(f'<p class="polica">{_e(p["naziv"])}'
                         + (f" – {_e(p['opis'])}" if p["opis"] else "") + "</p>")
            if not p_rows:
                parts.append('<p class="polica"><i>(prazno)</i></p>')
                continue
            parts.append('<table class="lista">')
            for r in p_rows:
                poz = f"{r['pozicija']}." if r["pozicija"] else "–"
                nap = f" <i>({_e(r['stavka_napomena'])})</i>" if r["stavka_napomena"] else ""
                parts.append(f"<tr><td align=right>{poz}</td><td>{_e(r['naziv'])}{_kol(r['kolicina'])}{nap}</td></tr>")
            parts.append("</table>")
        parts.append(f"<p>Ukupno na skladištu: <b>{sum(r['kolicina'] for r in sk_rows)}</b> kom</p>")
        first = False
    parts.append(_footer() + "</body></html>")
    return "".join(parts)


def html_prikaz(rows: list[dict], naslov: str) -> str:
    parts = [f"<html><head><style>{_CSS}</style></head><body><h1>{_e(naslov)}</h1>",
             '<table class="prikaz"><tr><th>Staklo</th><th>Kom</th><th>Skladište</th>'
             "<th>Polica</th><th>Poz.</th><th>Napomena</th></tr>"]
    for r in rows:
        parts.append(
            f"<tr><td>{_e(r['naziv'])}</td><td align=center>{r['kolicina']}</td><td>{_e(r['skladiste'])}</td>"
            f"<td>{_e(r['polica'])}</td><td align=center>{r['pozicija'] or ''}</td>"
            f"<td>{_e(r['stavka_napomena'] or r['napomena'])}</td></tr>")
    parts.append(f"</table><p>Stavki: {len(rows)}, ukupno komada: <b>{sum(r['kolicina'] for r in rows)}</b></p>")
    parts.append(_footer() + "</body></html>")
    return "".join(parts)


def write_pdf(html_text: str, target: Path, title: str = "AutoStakla") -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    writer = QPdfWriter(str(target))
    writer.setTitle(title)
    writer.setCreator("AutoStakla")
    writer.setResolution(300)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.PageSizeId.A4), QPageLayout.Orientation.Portrait,
                                     QMarginsF(15, 12, 15, 12), QPageLayout.Unit.Millimeter))
    doc = QTextDocument()
    doc.setDefaultStyleSheet(_CSS)
    doc.setHtml(html_text)
    # Bez setPageSize: print_() sam deli na strane i skalira sa ekranskog na DPI štampača.
    doc.print_(writer)
    return target
