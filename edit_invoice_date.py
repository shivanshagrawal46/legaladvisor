"""
Edit Invoice-4972B44D-0003 to look like an exact vendor render:

  1. Date "June 9, 2026" -> "June 12, 2026" on all three date fields.
     The two Medium date lines are rendered with 0004's OWN embedded
     Inter-Medium (which contains the real '1' glyph the 0003 subset lacked),
     so the dates match the 0004 original exactly. The amount-due line keeps
     0003's embedded Inter-SemiBold (already has the needed glyphs).

  2. Invoice number last digit "4972B44D-0003" -> "4972B44D-0005".
     Neither invoice embeds a SemiBold '5', so the single '5' is drawn from a
     full Inter-SemiBold (open-source Inter pinned to weight 600) — same
     typeface/weight as its neighbours; only the last glyph is replaced.

Untouched: GST number (9925USA29095OS3), ZIP (94158), all amounts.
Prereq: _inter_semibold.ttf sits next to this script.
"""
import fitz

HERE = r"C:\Users\SHIVANSH AGRAWAL\Desktop\outlook_attachments"
SRC = r"C:\Users\SHIVANSH AGRAWAL\Downloads\Invoice-4972B44D-0003.pdf"
SRC0004 = r"C:\Users\SHIVANSH AGRAWAL\Downloads\Invoice-4972B44D-0004 (3).pdf"
DST = HERE + r"\Invoice-4972B44D-0003_edited.pdf"
INTER_SEMIBOLD = HERE + r"\_inter_semibold.ttf"

doc = fitz.open(SRC)
page = doc[0]
doc4 = fitz.open(SRC0004)

# Exact vendor Inter-Medium (from 0004; has 0,1,2,6 -> covers "June 12, 2026").
med_exact = fitz.Font(fontbuffer=doc4.extract_font(9)[3])
# 0003 embedded SemiBold (covers the amount-due date's glyphs).
semi_embed = fitz.Font(fontbuffer=doc.extract_font(8)[3])
# Full Inter-SemiBold (only needed for the '5' the embedded subset lacks).
semi_full = fitz.Font(fontfile=INTER_SEMIBOLD)

# ---- 1. dates ------------------------------------------------------------
targets = {
    round(91.5): dict(size=9.0, kind="medium"),
    round(105.0): dict(size=9.0, kind="medium"),
    round(270.8): dict(size=13.5, kind="semibold"),
}
date_rects = page.search_for("June 9, 2026")
assert len(date_rects) == 3, f"expected 3 dates, found {len(date_rects)}"
date_plan = []
for r in date_rects:
    approx = min(targets, key=lambda b: abs(b - r.y1) + abs(b - r.y0))
    date_plan.append((r, targets[approx], approx))

# ---- 2. invoice-number last digit ---------------------------------------
# Exact bbox/origin of the trailing '3' (from rawdict inspection).
digit_rect = fitz.Rect(172.64, 69.28, 178.9, 80.17)
digit_origin = (172.64, 78.0)
digit_size = 9.0

# ---- redactions (dates + trailing digit) --------------------------------
for r, _cfg, _b in date_plan:
    page.add_redact_annot(r, fill=(1, 1, 1))
page.add_redact_annot(digit_rect, fill=(1, 1, 1))
page.apply_redactions()

# ---- redraw --------------------------------------------------------------
tw = fitz.TextWriter(page.rect, color=(0, 0, 0))
for r, cfg, baseline in date_plan:
    font = semi_embed if cfg["kind"] == "semibold" else med_exact
    tw.append((r.x0, float(baseline)), "June 12, 2026", font=font, fontsize=cfg["size"])
tw.append(digit_origin, "5", font=semi_full, fontsize=digit_size)
tw.write_text(page)

doc.save(DST, garbage=4, deflate=True)
print("saved:", DST)
