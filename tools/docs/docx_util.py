"""Zajednički stil za Word dokumentaciju (python-docx) + pretvaranje u PDF preko Word-a."""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT  # noqa: F401
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

PROJECT = Path(__file__).resolve().parents[2]
SLIKE = PROJECT / "dokumentacija" / "slike"
OUT = PROJECT / "dokumentacija"

PLAVA = RGBColor(0x15, 0x43, 0x78)
SIVA = RGBColor(0x59, 0x59, 0x59)
FONT = "Calibri"


def _shade(cell, hex_color: str) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _cell_margins(cell, cm: float = 0.25) -> None:
    tcPr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for side in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:w"), str(int(cm * 567)))
        el.set(qn("w:type"), "dxa")
        mar.append(el)
    tcPr.append(mar)


def _field(paragraph, instr: str) -> None:
    run = paragraph.add_run()
    for kind, text in (("begin", None), (None, instr), ("separate", None), (None, None), ("end", None)):
        if kind:
            fc = OxmlElement("w:fldChar")
            fc.set(qn("w:fldCharType"), kind)
            run._r.append(fc)
        elif text:
            it = OxmlElement("w:instrText")
            it.set(qn("xml:space"), "preserve")
            it.text = text
            run._r.append(it)


class Doc:
    def __init__(self, naslov: str, podnaslov: str, verzija: str):
        self.d = Document()
        self.naslov = naslov
        sec = self.d.sections[0]
        sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
        sec.left_margin = sec.right_margin = Cm(2.2)
        sec.top_margin, sec.bottom_margin = Cm(2.0), Cm(2.0)

        st = self.d.styles
        normal = st["Normal"]
        normal.font.name = FONT
        normal.font.size = Pt(11)
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.15
        for lvl, size, before in ((1, 18, 18), (2, 14, 14), (3, 12, 10)):
            h = st[f"Heading {lvl}"]
            h.font.name = FONT
            h.font.size = Pt(size)
            h.font.bold = True
            h.font.color.rgb = PLAVA
            h.element.rPr.rFonts.set(qn("w:asciiTheme"), "")  # ne preuzimaj font teme
            h.paragraph_format.space_before = Pt(before)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.keep_with_next = True
        for name in ("List Bullet", "List Number"):
            st[name].font.name = FONT
            st[name].font.size = Pt(11)
            st[name].paragraph_format.space_after = Pt(3)

        # zaglavlje / podnožje
        hp = sec.header.paragraphs[0]
        hp.text = f"{naslov} – {verzija}"
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for r in hp.runs:
            r.font.size, r.font.color.rgb = Pt(9), SIVA
        fp = sec.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = fp.add_run("Strana ")
        r.font.size, r.font.color.rgb = Pt(9), SIVA
        _field(fp, "PAGE")
        sec.different_first_page_header_footer = True

        # naslovna strana
        for _ in range(6):
            self.d.add_paragraph()
        logo = SLIKE.parent.parent / "src" / "autostakla" / "resources" / "icon.ico"
        png = SLIKE / "_logo.png"
        if logo.exists():
            from PIL import Image
            Image.open(logo).save(png)
            p = self.d.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run().add_picture(str(png), width=Cm(3))
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(naslov)
        r.font.size, r.font.bold, r.font.color.rgb = Pt(30), True, PLAVA
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(podnaslov)
        r.font.size, r.font.color.rgb = Pt(15), SIVA
        p = self.d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(f"Verzija programa {verzija}")
        r.font.size, r.font.color.rgb = Pt(12), SIVA
        self.page_break()

    # ---------- osnovni elementi ----------
    def toc(self, title: str = "Sadržaj", page_break: bool = True) -> None:
        p = self.d.add_paragraph()
        r = p.add_run(title)
        r.bold, r.font.size, r.font.color.rgb = True, Pt(18), PLAVA
        _field(self.d.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u')
        if page_break:
            self.page_break()

    def h1(self, t):
        return self.d.add_paragraph(t, style="Heading 1")

    def h2(self, t):
        return self.d.add_paragraph(t, style="Heading 2")

    def h3(self, t):
        return self.d.add_paragraph(t, style="Heading 3")

    def p(self, *parts, italic=False, size=None, align=None):
        """Pasus; delovi mogu biti str ili ('tekst', 'b'/'i'/'bi'/'code')."""
        par = self.d.add_paragraph()
        if align == "center":
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for part in parts:
            text, fmt = (part, "") if isinstance(part, str) else part
            r = par.add_run(text)
            r.bold = "b" in fmt
            r.italic = italic or ("i" in fmt and fmt != "code")
            if fmt == "code":
                r.font.name = "Consolas"
                r.font.size = Pt(10)
            if size:
                r.font.size = Pt(size)
        return par

    def bullets(self, items):
        for it in items:
            par = self.d.add_paragraph(style="List Bullet")
            parts = it if isinstance(it, (list, tuple)) else [it]
            for part in parts:
                text, fmt = (part, "") if isinstance(part, str) else part
                r = par.add_run(text)
                r.bold = "b" in fmt
                if fmt == "code":
                    r.font.name = "Consolas"
                    r.font.size = Pt(10)

    def steps(self, items):
        """Numerisani koraci (ručno numerisani – uvek kreću od 1)."""
        for i, it in enumerate(items, 1):
            par = self.d.add_paragraph()
            par.paragraph_format.left_indent = Cm(0.9)
            par.paragraph_format.first_line_indent = Cm(-0.9)
            par.paragraph_format.space_after = Pt(3)
            r = par.add_run(f"{i}.\t")
            r.bold = True
            r.font.color.rgb = PLAVA
            par.paragraph_format.tab_stops.add_tab_stop(Cm(0.9))
            parts = it if isinstance(it, (list, tuple)) else [it]
            for part in parts:
                text, fmt = (part, "") if isinstance(part, str) else part
                rr = par.add_run(text)
                rr.bold = "b" in fmt

    def image(self, name: str, width_cm: float = 16.0, caption: str | None = None):
        par = self.d.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        par.paragraph_format.keep_with_next = bool(caption)
        par.add_run().add_picture(str(SLIKE / f"{name}.png"), width=Cm(width_cm))
        if caption:
            c = self.d.add_paragraph()
            c.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = c.add_run(caption)
            r.italic, r.font.size, r.font.color.rgb = True, Pt(9), SIVA

    def box(self, title: str, text, color: str = "E8F0FA"):
        """Istaknut okvir (savet / pažnja)."""
        t = self.d.add_table(rows=1, cols=1)
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        c = t.cell(0, 0)
        _shade(c, color)
        _cell_margins(c)
        par = c.paragraphs[0]
        r = par.add_run(title + "  ")
        r.bold = True
        r.font.color.rgb = PLAVA
        parts = text if isinstance(text, (list, tuple)) else [text]
        for part in parts:
            tx, fmt = (part, "") if isinstance(part, str) else part
            rr = par.add_run(tx)
            rr.bold = "b" in fmt
            if fmt == "code":
                rr.font.name = "Consolas"
                rr.font.size = Pt(10)
        self.d.add_paragraph().paragraph_format.space_after = Pt(0)

    def table(self, header: list[str], rows: list[list[str]], widths_cm: list[float] | None = None,
              size: int = 10, code_cols: tuple[int, ...] = ()):
        t = self.d.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(header):
            c = t.rows[0].cells[i]
            _shade(c, "154378")
            c.paragraphs[0].text = ""
            r = c.paragraphs[0].add_run(h)
            r.bold, r.font.size, r.font.color.rgb = True, Pt(size), RGBColor(0xFF, 0xFF, 0xFF)
        for ri, row in enumerate(rows):
            cells = t.add_row().cells
            for i, val in enumerate(row):
                par = cells[i].paragraphs[0]
                r = par.add_run(str(val))
                r.font.size = Pt(size)
                if i in code_cols:
                    r.font.name = "Consolas"
                    r.font.size = Pt(size - 1)
                if ri % 2:
                    _shade(cells[i], "F2F5FA")
        # ponavljaj zaglavlje na novoj strani
        trPr = t.rows[0]._tr.get_or_add_trPr()
        th = OxmlElement("w:tblHeader")
        th.set(qn("w:val"), "true")
        trPr.append(th)
        if widths_cm:
            for row in t.rows:
                for i, wcm in enumerate(widths_cm):
                    row.cells[i].width = Cm(wcm)
        self.d.add_paragraph().paragraph_format.space_after = Pt(0)
        return t

    def code(self, text: str):
        t = self.d.add_table(rows=1, cols=1)
        c = t.cell(0, 0)
        _shade(c, "F3F3F3")
        _cell_margins(c, 0.2)
        par = c.paragraphs[0]
        for i, line in enumerate(text.strip("\n").split("\n")):
            r = par.add_run(line)
            r.font.name, r.font.size = "Consolas", Pt(9)
            if i < len(text.strip("\n").split("\n")) - 1:
                r.add_break()
        self.d.add_paragraph().paragraph_format.space_after = Pt(0)

    def page_break(self):
        self.d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def save(self, name: str) -> Path:
        OUT.mkdir(parents=True, exist_ok=True)
        path = OUT / f"{name}.docx"
        self.d.save(path)
        return path


def to_pdf(docx_path: Path) -> Path:
    """Otvara u Word-u, osvežava sadržaj (TOC) i snima .docx + .pdf."""
    import win32com.client  # type: ignore

    pdf = docx_path.with_suffix(".pdf")
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(str(docx_path))
        for t in doc.TablesOfContents:
            t.Update()
        doc.Fields.Update()
        # Bez Save(): snimanje u Word-u bi dodalo firminu oznaku poverljivosti u podnožje.
        doc.ExportAsFixedFormat(str(pdf), 17)
        doc.Close(0)
    finally:
        word.Quit()
    return pdf


def mark_update_fields(docx_path: Path) -> None:
    """Word pri otvaranju osvežava sadržaj (TOC) – jer .docx ne snimamo kroz Word."""
    import shutil
    import tempfile
    import zipfile

    tmp = Path(tempfile.mkdtemp()) / docx_path.name
    with zipfile.ZipFile(docx_path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/settings.xml":
                s = data.decode("utf-8")
                if "w:updateFields" not in s:
                    s = s.replace("</w:settings>", '<w:updateFields w:val="true"/></w:settings>')
                data = s.encode("utf-8")
            zout.writestr(item, data)
    shutil.move(tmp, docx_path)
