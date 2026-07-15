"""Remove the 'Pay online' text + its Stripe payment link from invoices.
Writes cleaned copies into the project folder."""
import os
import fitz

HERE = r"C:\Users\SHIVANSH AGRAWAL\Desktop\outlook_attachments"
DL = r"C:\Users\SHIVANSH AGRAWAL\Downloads"

# (source, destination)
JOBS = [
    (HERE + r"\Invoice-4972B44D-0003_edited.pdf", HERE + r"\Invoice-4972B44D-0003_edited.pdf"),
    (DL + r"\Invoice-4972B44D-0004 (3).pdf",       HERE + r"\Invoice-4972B44D-0004.pdf"),
    (DL + r"\Invoice-4972B44D-0003.pdf",            HERE + r"\Invoice-4972B44D-0003.pdf"),
    (DL + r"\Invoice-4972B44D-0002 (2).pdf",        HERE + r"\Invoice-4972B44D-0002.pdf"),
]

for src, dst in JOBS:
    doc = fitz.open(src)
    page = doc[0]
    rects = page.search_for("Pay online")

    # delete link annotations overlapping the "Pay online" area
    for link in list(page.get_links()):
        lr = fitz.Rect(link["from"])
        if any(lr.intersects(r) for r in rects) or not rects:
            page.delete_link(link)

    # erase the text (white fill on white background)
    for r in rects:
        page.add_redact_annot(r, fill=(1, 1, 1))
    if rects:
        page.apply_redactions()

    if os.path.abspath(src) == os.path.abspath(dst):
        tmp = dst + ".tmp"
        doc.save(tmp, garbage=4, deflate=True)
        doc.close()
        os.replace(tmp, dst)
    else:
        doc.save(dst, garbage=4, deflate=True)
        doc.close()
    print(f"cleaned {os.path.basename(dst)} (removed {len(rects)} 'Pay online')")
