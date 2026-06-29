"""PHASE 5 - unpack the 3 IPA archives to a staging dir (NO OCR here).

  * 2x .zip            -> python zipfile
  * 1x .rar            -> WinRAR / UnRAR CLI
Email members (.msg/.eml/.pst/.ost) are NOT extracted (out of scope).
Then walks staging, hashes, and writes _phase5_archive_manifest.json with the
same row schema as the main manifest (matter=ipa_litigation), flagging in_db.
"""
from __future__ import annotations
import json
import subprocess
import zipfile
from hashlib import sha256
from pathlib import Path

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

STAGING = Path("phase5_staging")
EMAIL_EXTS = {".msg", ".eml", ".pst", ".ost", ".nst"}
INSCOPE = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".csv", ".rtf", ".txt",
           ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".gif", ".webp"}
ARCHIVES = [
    r"E:\00 - IPA Litigation\00 - IPA Litigation\08 - Settlement Analysis\Settlement sheets with email.rar",
    r"E:\00 - IPA Litigation\00 - IPA Litigation\101 - MT-IPA - Discovery Docs\MANGOTREE-20210720T114943Z-001.zip",
    r"E:\00 - IPA Litigation\00 - IPA Litigation\101 - MT-IPA - Discovery Docs\MANGOTREE-20210731T112058Z-001.zip",
]
WINRAR = Path(r"C:\Program Files\WinRAR\WinRAR.exe")
UNRAR = Path(r"C:\Program Files\WinRAR\UnRAR.exe")


def _ext_path(p: Path) -> str:
    """Extended-length path to bypass Windows MAX_PATH."""
    ap = str(p.resolve())
    return ap if ap.startswith("\\\\?\\") else "\\\\?\\" + ap


def _read_bytes_safe(p: Path) -> bytes:
    try:
        return p.read_bytes()
    except (FileNotFoundError, OSError):
        with open(_ext_path(p), "rb") as f:
            return f.read()


def unpack_zip(src: Path, dest: Path) -> list:
    """Flatten members to short disk names; keep internal path as rel."""
    dest.mkdir(parents=True, exist_ok=True)
    rows = []
    n = 0
    with zipfile.ZipFile(src) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            ext = Path(info.filename).suffix.lower()
            if ext in EMAIL_EXTS or ext not in INSCOPE:
                continue
            disk = dest / f"{n:04d}_{Path(info.filename).name}"
            with z.open(info) as fsrc, open(_ext_path(disk), "wb") as fdst:
                fdst.write(fsrc.read())
            rows.append({"path": str(disk), "rel": info.filename})
            n += 1
    return rows


def unpack_rar(src: Path, dest: Path) -> list:
    dest.mkdir(parents=True, exist_ok=True)
    exe = UNRAR if UNRAR.exists() else WINRAR
    cmd = [str(exe), "x", "-y", "-ibck", str(src), str(dest) + "\\"]
    subprocess.run(cmd, capture_output=True, timeout=600)
    rows = []
    removed = 0
    for p in dest.rglob("*"):
        if p.is_file():
            if p.suffix.lower() in EMAIL_EXTS or p.suffix.lower() not in INSCOPE:
                try:
                    p.unlink()
                    removed += 1
                except Exception:  # noqa: BLE001
                    pass
            else:
                rows.append({"path": str(p), "rel": str(p.relative_to(dest))})
    print(f"   rar: kept={len(rows)} removed_email/other={removed}")
    return rows


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    existing = set()
    for a in m.db["attachments_v2"].find({}, {"sha256": 1}):
        if a.get("sha256"):
            existing.add(a["sha256"])
    for sh in m.db["email_chunks_v2"].distinct("sha256"):
        if sh:
            existing.add(sh)
    for d in m.db["documents"].find({}, {"custody.sha256": 1}):
        sh = (d.get("custody") or {}).get("sha256")
        if sh:
            existing.add(sh)
    print(f"existing fingerprints: {len(existing)}")

    STAGING.mkdir(exist_ok=True)
    members = []
    for arc in ARCHIVES:
        src = Path(arc)
        dest = STAGING / src.stem
        if not src.exists():
            print(f"MISSING archive: {src}")
            continue
        print(f"unpacking {src.name} -> {dest}")
        if src.suffix.lower() == ".zip":
            got = unpack_zip(src, dest)
        else:
            got = unpack_rar(src, dest)
        for g in got:
            g["archive"] = src.name
        members += got
        print(f"   extracted in-scope members: {len(got)}")

    rows = []
    for mem in members:
        p = Path(mem["path"])
        ext = p.suffix.lower()
        if ext not in INSCOPE:
            continue
        data = _read_bytes_safe(p)
        sh = sha256(data).hexdigest()
        rows.append({"matter": "ipa_litigation", "path": mem["path"],
                     "rel": f"{mem['archive']}/{mem['rel']}", "ext": ext,
                     "size": len(data), "sha256": sh,
                     "in_db": sh in existing, "from_archive": True})
    distinct = {r["sha256"] for r in rows}
    new = {r["sha256"] for r in rows if not r["in_db"]}
    Path("_phase5_archive_manifest.json").write_text(
        json.dumps({"files": rows}, indent=1), encoding="utf-8")
    print(f"archive members: {len(rows)} rows, distinct={len(distinct)}, NEW={len(new)}")
    print("manifest -> _phase5_archive_manifest.json")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
