"""
Edit DigitalOcean Invoice 2026 Jul (22468109-551204222).pdf

Only the NUMERIC portions are touched; the '$' signs stay original.
  28.00 -> 6.00   (4 hits)
  5.04  -> 1.08   (1 hit)
  33.04 -> 7.08   (1 hit)
"""
import os
import fitz

HERE = r"C:\Users\SHIVANSH AGRAWAL\Desktop\outlook_attachments"
SRC = os.path.join(HERE, "DigitalOcean Invoice 2026 Jul (22468109-551204222).pdf")
DST = os.path.join(HERE, "DigitalOcean Invoice 2026 Jul (22468109-551204222)_edited.pdf")

REPLACEMENTS = {
    "28.00": "6.00",
    "5.04":  "1.08",
    "33.04": "7.08",
}

doc = fitz.open(SRC)
page = doc[0]

# ---- fonts ----------------------------------------------------------------
reg = fitz.Font(fontbuffer=doc.extract_font(6)[3])        # embedded DejaVuSans
bold_embed = fitz.Font(fontbuffer=doc.extract_font(7)[3]) # embedded DejaVuSans-Bold (subset)
ARIAL_BOLD = os.path.expandvars(r"%WINDIR%\Fonts\arialbd.ttf")
bold_full = fitz.Font(fontfile=ARIAL_BOLD) if os.path.exists(ARIAL_BOLD) else bold_embed

COLOR = (0x4a / 255, 0x4a / 255, 0x4a / 255)

# ---- find the "$" x-position from each span, then locate number rects ----
blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
jobs = []
for old, new in REPLACEMENTS.items():
    full_old = "$" + old
    for block in blocks["blocks"]:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            for span in line["spans"]:
                if full_old in span["text"]:
                    sr = fitz.Rect(span["bbox"])
                    font_name = span["font"]
                    size = span["size"]
                    is_bold = "Bold" in font_name
                    font = bold_full if is_bold else reg
                    # width of "$" in this font/size = where the number starts
                    dollar_w = font.text_length("$", fontsize=size)
                    num_x0 = sr.x0 + dollar_w
                    # redact rect covers only the number area (after $)
                    num_rect = fitz.Rect(num_x0, sr.y0, sr.x1, sr.y1)
                    jobs.append({
                        "num_rect": num_rect,
                        "num_x0": num_x0,
                        "old": old,
                        "new": new,
                        "bold": is_bold,
                        "size": size,
                    })

for j in jobs:
    print(f"  {j['old']!r} -> {j['new']!r}  redact={j['num_rect']}  bold={j['bold']}")

# ---- redact only the number area ($ untouched) ---------------------------
for j in jobs:
    page.add_redact_annot(j["num_rect"], fill=(1, 1, 1))
page.apply_redactions()

# ---- redraw just the number, left-aligned right after the original $ -----
for j in jobs:
    font = bold_full if j["bold"] else reg
    size = j["size"]
    r = j["num_rect"]
    baseline = r.y1 - (r.y1 - r.y0) * 0.18

    tw = fitz.TextWriter(page.rect, color=COLOR)
    tw.append((j["num_x0"], baseline), j["new"], font=font, fontsize=size)
    tw.write_text(page)

doc.save(DST, garbage=4, deflate=True)
doc.close()
print(f"\nSaved: {DST}")
