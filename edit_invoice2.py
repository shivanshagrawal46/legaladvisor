# -*- coding: utf-8 -*-
"""
Build Invoice-4972B44D-0003_edit2.pdf from the original 0003:

  - dates      -> June 14, 2026
  - invoice no -> 4972B44D-0006
  - Pay online -> removed
  - figures:   unit price / amount / subtotal / total-excl -> $100.00
               IGST (18% on $100.00) -> $18.00
               INR line -> (₹1,728.00)
               Total -> $118.00 ; Amount due -> $118.00 USD
               header -> $118.00 USD due June 14, 2026

Fonts:
  - money values reuse the EMBEDDED Inter-Regular (vendor-exact; it has every
    needed glyph incl. $ . , % ₹ ( ) and all digits), right-aligned like the
    original.
  - date/invoice/SemiBold amounts that need glyphs missing from the embedded
    subsets (4, 6, 8) use full Inter (Medium/SemiBold) instances.
"""
import fitz

HERE = r"C:\Users\SHIVANSH AGRAWAL\Desktop\outlook_attachments"
SRC = r"C:\Users\SHIVANSH AGRAWAL\Downloads\Invoice-4972B44D-0003.pdf"
DST = HERE + r"\Invoice-4972B44D-0003_edit2.pdf"

doc = fitz.open(SRC)
page = doc[0]

reg = fitz.Font(fontbuffer=doc.extract_font(7)[3])       # embedded Inter-Regular
med = fitz.Font(fontfile=HERE + r"\_inter_medium.ttf")   # full Inter Medium
semi = fitz.Font(fontfile=HERE + r"\_inter_semibold.ttf")  # full Inter SemiBold

NB = "\u00a0"  # non-breaking space used in "$..USD"

# ---- redactions to run first (rect, fill) -------------------------------
redactions = []

def R(x0, y0, x1, y1):
    r = fitz.Rect(x0, y0, x1, y1)
    redactions.append(r)
    return r

# right-aligned money values in embedded Regular @9pt: (rect, right_x, baseline, text)
money_right = [
    (R(420, 345.3, 456, 356.2), 455.3, 354.0, "$100.00"),   # unit price
    (R(548, 345.3, 582, 356.2), 582.0, 354.0, "$100.00"),   # amount
    (R(548, 374.5, 582, 385.4), 582.0, 383.2, "$100.00"),   # subtotal
    (R(548, 388.8, 582, 399.7), 582.0, 397.5, "$100.00"),   # total excl tax
    (R(552, 403.0, 582, 413.9), 582.0, 411.8, "$18.00"),    # IGST amount
    (R(534, 416.5, 582, 427.4), 582.0, 425.2, "(₹1,728.00)"),  # INR line
    (R(550, 430.8, 582, 441.7), 582.0, 439.5, "$118.00"),   # Total
]
# left-aligned Regular label
igst_label = (R(306.0, 409.8, 427.0, 420.7), 306.0, 418.5, "IGST - India (18% on $100.00)")
# right-aligned SemiBold amount due
amount_due = (R(528, 445.0, 582, 455.9), 582.0, 453.8, "$118.00" + NB + "USD")

# dates
date1 = (R(103.5, 82.8, 160.0, 93.7), 103.5, 91.5, "June 14, 2026", med, 9.0)
date2 = (R(103.5, 96.3, 160.0, 107.2), 103.5, 105.0, "June 14, 2026", med, 9.0)
header = (R(30.0, 257.7, 221.0, 274.0), 30.0, 270.8, "$118.00 USD due June 14, 2026", semi, 13.5)

# invoice number trailing digit 3 -> 6
inv_digit = (R(172.64, 69.28, 178.9, 80.17), 172.64, 78.0, "6", semi, 9.0)

# Pay online
pay_rects = page.search_for("Pay online")
for link in list(page.get_links()):
    page.delete_link(link)
for r in pay_rects:
    redactions.append(r)

# apply all redactions at once (white fill)
for r in redactions:
    page.add_redact_annot(r, fill=(1, 1, 1))
page.apply_redactions()

# ---- redraw -------------------------------------------------------------
tw = fitz.TextWriter(page.rect, color=(0, 0, 0))

def right(text, right_x, baseline, font, size=9.0):
    x = right_x - font.text_length(text, fontsize=size)
    tw.append((x, baseline), text, font=font, fontsize=size)

def left(text, x, baseline, font, size=9.0):
    tw.append((x, baseline), text, font=font, fontsize=size)

for _r, rx, by, txt in money_right:
    right(txt, rx, by, reg, 9.0)
left(igst_label[3], igst_label[1], igst_label[2], reg, 9.0)
right(amount_due[3], amount_due[1], amount_due[2], semi, 9.0)

for _r, x, by, txt, font, size in (date1, date2, header, inv_digit):
    left(txt, x, by, font, size)

tw.write_text(page)
doc.save(DST, garbage=4, deflate=True)
print("saved:", DST)
