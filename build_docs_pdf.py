"""Render DEVELOPER_DOCUMENTATION.md -> a structured, styled PDF using reportlab
(no cryptography/pyhanko dependency)."""
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    Preformatted, PageBreak, HRFlowable, KeepTogether,
)

MD = "DEVELOPER_DOCUMENTATION.md"
OUT = "DEVELOPER_DOCUMENTATION.pdf"

TEAL = colors.HexColor("#234a52")
TEAL_D = colors.HexColor("#1c3d44")
GREY = colors.HexColor("#8a9aa0")
LINE = colors.HexColor("#cbd6d8")
ROW = colors.HexColor("#f2f6f7")
CODEBG = colors.HexColor("#f4f6f7")

# ---- fonts (Windows) ----
def _reg():
    F = "C:/Windows/Fonts/"
    pdfmetrics.registerFont(TTFont("Body", F + "arial.ttf"))
    pdfmetrics.registerFont(TTFont("Body-Bold", F + "arialbd.ttf"))
    pdfmetrics.registerFont(TTFont("Body-Italic", F + "ariali.ttf"))
    pdfmetrics.registerFont(TTFont("Body-BoldItalic", F + "arialbi.ttf"))
    pdfmetrics.registerFont(TTFont("Mono", F + "consola.ttf"))
    pdfmetrics.registerFontFamily(
        "Body", normal="Body", bold="Body-Bold",
        italic="Body-Italic", boldItalic="Body-BoldItalic")
_reg()

# ---- styles ----
TITLE = ParagraphStyle("Title", fontName="Body-Bold", fontSize=24, textColor=TEAL_D, leading=28, spaceAfter=6)
SUB = ParagraphStyle("Sub", fontName="Body", fontSize=13, textColor=TEAL, leading=17, spaceAfter=10)
H1 = ParagraphStyle("H1", fontName="Body-Bold", fontSize=17, textColor=TEAL_D, leading=21, spaceBefore=2, spaceAfter=8)
H2 = ParagraphStyle("H2", fontName="Body-Bold", fontSize=13, textColor=TEAL, leading=16, spaceBefore=12, spaceAfter=5)
H3 = ParagraphStyle("H3", fontName="Body-Bold", fontSize=11, textColor=colors.HexColor("#2c5560"), leading=14, spaceBefore=9, spaceAfter=3)
BODY = ParagraphStyle("Body", fontName="Body", fontSize=9.5, leading=14, textColor=colors.HexColor("#1f2933"), alignment=TA_LEFT, spaceAfter=4)
BULLET = ParagraphStyle("Bullet", parent=BODY, leftIndent=14, bulletIndent=4, spaceAfter=2)
QUOTE = ParagraphStyle("Quote", parent=BODY, leftIndent=10, borderPadding=(4, 6, 4, 6),
                       backColor=colors.HexColor("#fbf6ea"), textColor=colors.HexColor("#5b4a1e"),
                       borderColor=colors.HexColor("#b98a2e"), spaceBefore=4, spaceAfter=6)
CODE = ParagraphStyle("Code", fontName="Mono", fontSize=7.2, leading=9.2, backColor=CODEBG,
                      borderColor=LINE, borderWidth=0.5, borderPadding=6, textColor=colors.HexColor("#1f2933"))
CELL = ParagraphStyle("Cell", fontName="Body", fontSize=8, leading=10.5, textColor=colors.HexColor("#1f2933"))
CELLH = ParagraphStyle("CellH", fontName="Body-Bold", fontSize=8, leading=10.5, textColor=colors.white)

REPL = {"\U0001F50D": "[search]", "\u270D\uFE0F": "[writing]", "\u270D": "[writing]",
        "\u2B07": "", "\u25C6": "*", "\u2794": "->", "\u25CF": "*", "\uFE0F": ""}

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def inline(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`([^`]+?)`", r'<font face="Mono" size="8.5" backColor="#eef2f3">\1</font>', s)
    s = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"\[([^\]]+)\]\((?:#[^)]*)\)", r"\1", s)  # strip md anchor links
    return s

def preprocess(t):
    for k, v in REPL.items():
        t = t.replace(k, v)
    return t

def build_table(rows):
    header, body = rows[0], rows[1:]
    ncol = len(header)
    usable = A4[0] - 3.4 * cm
    w = usable / ncol
    data = [[Paragraph(inline(c), CELLH) for c in header]]
    for r in body:
        r = (r + [""] * ncol)[:ncol]
        data.append([Paragraph(inline(c), CELL) for c in r])
    t = Table(data, colWidths=[w] * ncol, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for i in range(2, len(data), 2):
        style.append(("BACKGROUND", (0, i), (-1, i), ROW))
    t.setStyle(TableStyle(style))
    return t

def parse(md):
    lines = md.split("\n")
    flow = []
    i = 0
    first_h1 = True
    para = []

    def flush_para():
        nonlocal para
        if para:
            flow.append(Paragraph(inline(" ".join(para).strip()), BODY))
            para = []

    while i < len(lines):
        ln = lines[i]
        s = ln.rstrip()

        # code fence
        if s.startswith("```"):
            flush_para()
            i += 1
            code = []
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            flow.append(Preformatted("\n".join(code) if code else " ", CODE))
            flow.append(Spacer(1, 4))
            continue

        # table
        if s.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:\-|]+\|?\s*$", lines[i + 1]):
            flush_para()
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                raw = lines[i].strip().strip("|")
                cells = [c.strip() for c in raw.split("|")]
                rows.append(cells)
                i += 1
            if len(rows) >= 2:
                del rows[1]  # separator
            flow.append(build_table(rows))
            flow.append(Spacer(1, 4))
            continue

        if not s.strip():
            flush_para()
            i += 1
            continue

        if s.startswith("### "):
            flush_para(); flow.append(Paragraph(inline(s[4:]), H3)); i += 1; continue
        if s.startswith("## "):
            flush_para(); flow.append(Paragraph(inline(s[3:]), H2)); i += 1; continue
        if s.startswith("# "):
            flush_para()
            title = s[2:]
            if first_h1:
                flow.append(Paragraph(inline(title), TITLE)); first_h1 = False
            else:
                flow.append(PageBreak())
                flow.append(Paragraph(inline(title), H1))
                flow.append(HRFlowable(width="100%", thickness=1.4, color=TEAL, spaceAfter=6))
            i += 1; continue
        if s.startswith("## ") is False and re.match(r"^\s*#{4,}\s", s):
            flush_para(); flow.append(Paragraph(inline(re.sub(r"^\s*#+\s", "", s)), H3)); i += 1; continue

        if s.strip() == "---":
            flush_para(); flow.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceBefore=6, spaceAfter=6)); i += 1; continue

        if s.startswith("> "):
            flush_para(); flow.append(Paragraph(inline(s[2:]), QUOTE)); i += 1; continue

        m = re.match(r"^(\s*)[-*]\s+(.*)$", s)
        if m:
            flush_para()
            flow.append(Paragraph(inline(m.group(2)), BULLET, bulletText="\u2022"))
            i += 1; continue
        m = re.match(r"^(\s*)(\d+)\.\s+(.*)$", s)
        if m:
            flush_para()
            flow.append(Paragraph(inline(m.group(3)), BULLET, bulletText=m.group(2) + "."))
            i += 1; continue

        para.append(s.strip())
        i += 1

    flush_para()
    return flow

def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Body", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawCentredString(
        A4[0] / 2, 1.1 * cm,
        "Mango Tree \u00b7 Legal Evidence Engine \u00b7 Developer Documentation \u00b7 Page %d" % doc.page)
    canvas.restoreState()

def main():
    md = preprocess(open(MD, encoding="utf-8").read())
    story = parse(md)
    doc = BaseDocTemplate(
        OUT, pagesize=A4,
        leftMargin=1.7 * cm, rightMargin=1.7 * cm,
        topMargin=1.8 * cm, bottomMargin=1.9 * cm,
        title="Mango Tree - Developer Documentation")
    frame = Frame(doc.leftMargin, doc.bottomMargin,
                  doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=footer)])
    doc.build(story)
    print("wrote", OUT)

if __name__ == "__main__":
    main()
