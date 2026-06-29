"""Sprint 8 — REST endpoints for the portfolio grid, property detail, findings
dashboard, and observability. All read the already-materialized collections
(property_dossier, findings, events, dashboard_stats) — NO live agent — so the
UI is instant. JWT-protected via get_current_user.
"""
from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from api.auth import User, get_current_user
from api.rag_singleton import get_mongo
from src.timeline.builder import timeline_for, flow_of_funds, evidence_packet, property_graph

router = APIRouter(prefix="/api", tags=["sprint8"])


def _db():
    return get_mongo().db


# ── dashboard ────────────────────────────────────────────────────────────────
@router.get("/dashboard/stats")
async def dashboard_stats(_: User = Depends(get_current_user)):
    doc = _db()["dashboard_stats"].find_one({"_id": "current"}) or {}
    doc.pop("_id", None)
    return doc


# ── portfolio ────────────────────────────────────────────────────────────────
@router.get("/portfolio/properties")
async def portfolio_properties(
    _: User = Depends(get_current_user),
    side: Optional[str] = None,
    is_david: Optional[bool] = None,
    has_litigation: Optional[bool] = None,
    q: Optional[str] = None,
    limit: int = Query(300, le=1000),
):
    flt = {}
    if side:
        flt["side"] = side
    if is_david is not None:
        flt["is_david"] = is_david
    if has_litigation is not None:
        flt["has_litigation"] = has_litigation
    if q:
        flt["canonical_address"] = {"$regex": q, "$options": "i"}
    rows = list(_db()["property_dossier"].find(flt).limit(limit))
    out = []
    for d in rows:
        out.append({
            "property_id": d["_id"], "address": d.get("canonical_address"),
            "parcel_id": d.get("parcel_id"), "county": d.get("county"),
            "is_david": d.get("is_david"), "side": d.get("side"),
            "owners": [o.get("name") for o in (d.get("owners") or [])],
            "title_count": (d.get("title") or {}).get("count", 0),
            "latest_title_date": (d.get("title") or {}).get("latest_date"),
            "insurance_in_force": (d.get("insurance") or {}).get("in_force", False),
            "equity": (d.get("equity") or {}).get("equity"),
            "mortgage_amount": (d.get("equity") or {}).get("mortgage_amount"),
            "active_foreclosure": (d.get("equity") or {}).get("active_foreclosure"),
            "litigation_count": (d.get("litigation") or {}).get("count", 0),
            "fact_counts": d.get("fact_counts", {}),
            # current-vs-historical scoping so the grid doesn't show an
            # alarming cumulative total (e.g. mostly prior-owner mortgages).
            "fact_counts_scoped": d.get("fact_counts_scoped", {}),
            "fact_counts_basis": d.get("fact_counts_basis", "cumulative_historical"),
            "current_owner_since": d.get("current_owner_since"),
        })
    return {"total": len(out), "rows": out}


# ── property detail ──────────────────────────────────────────────────────────
def _fmt(dt):
    try:
        return dt.strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return None


@router.get("/properties/{property_id}")
async def property_detail(property_id: str, _: User = Depends(get_current_user)):
    m = get_mongo()
    doss = m.db["property_dossier"].find_one({"_id": property_id})
    if not doss:
        raise HTTPException(404, "property not found")
    doss.pop("_id", None)
    docs = m.db["documents"]

    title_ids = (doss.get("title") or {}).get("doc_ids") or []
    ins_ids = (doss.get("insurance") or {}).get("doc_ids") or []
    eq_ids = (doss.get("equity") or {}).get("doc_ids") or []
    lit_ids = (doss.get("litigation") or {}).get("doc_ids") or []

    # Title reports — full + update searches, dated, vendor, latest flagged.
    title_reports = []
    for d in docs.find({"_id": {"$in": title_ids}}):
        title_reports.append({
            "doc_id": d["_id"], "vendor": d.get("vendor"),
            "type": "update search" if d.get("is_update") else "full search",
            "date": _fmt(d.get("completed_date") or d.get("search_date")),
            "effective_date": _fmt(d.get("effective_date")),
            "order_number": d.get("order_number"),
            "pages": d.get("page_count"),
            "is_latest": bool(d.get("is_latest")),
            "sha256": (d.get("custody") or {}).get("sha256"),
        })
    title_reports.sort(key=lambda r: (r["date"] or "", r["is_latest"]), reverse=True)

    # Insurance policies / evidence-of-coverage.
    insurance_reports = []
    for d in docs.find({"_id": {"$in": ins_ids}}):
        insurance_reports.append({
            "doc_id": d["_id"], "insurer": d.get("insurer"),
            "named_insured": d.get("named_insured"),
            "policy_year": d.get("policy_year"),
            "effective_date": _fmt(d.get("effective_date")),
            "expiration_date": _fmt(d.get("expiration_date")),
            "is_cancellation": bool(d.get("is_cancellation")),
        })
    insurance_reports.sort(key=lambda r: (r["effective_date"] or ""), reverse=True)

    # Chain-of-custody document list (every source doc behind this property).
    documents = []
    for d in docs.find({"_id": {"$in": title_ids + ins_ids + eq_ids + lit_ids}},
                       {"source_type": 1, "custody": 1, "page_count": 1, "vendor": 1}):
        cust = d.get("custody") or {}
        documents.append({
            "doc_id": d["_id"], "source_type": d.get("source_type"),
            "source_file": cust.get("source_file") or (cust.get("source_files") or [None])[0],
            "sha256": cust.get("sha256"), "pages": d.get("page_count"),
            "vendor": d.get("vendor"),
        })

    # Bitemporal ownership history (as_of → until per owner).
    from src.graph.bitemporal import ownership_intervals
    ents = m.db["entities"]
    ivs = ownership_intervals(m.db["relationships"], property_id)
    nm = {e["_id"]: e.get("canonical_name") or e["_id"]
          for e in ents.find({"_id": {"$in": [iv["owner"] for iv in ivs]}},
                             {"canonical_name": 1})}
    ownership = [{"owner": nm.get(iv["owner"], iv["owner"]),
                  "as_of": _fmt(iv["as_of"]), "until": _fmt(iv["until"]),
                  "amount": iv.get("amount"), "source_quote": iv.get("source_quote")}
                 for iv in ivs]

    findings = list(m.db["findings"].find({"property_id": property_id}))
    for f in findings:
        f["id"] = f.pop("_id")
    return {
        "property_id": property_id,
        "dossier": doss,                      # includes grounded_facts + fact_counts_scoped
        "title_reports": title_reports,
        "insurance_reports": insurance_reports,
        "documents": documents,
        "ownership": ownership,
        "timeline": timeline_for(m, property_id=property_id, limit=300),
        "flow_of_funds": flow_of_funds(m, property_id=property_id),
        "findings": findings,
        "finding_counts": {
            "total": len(findings),
            "critical": sum(1 for f in findings if f.get("severity") == "critical"),
            "high": sum(1 for f in findings if f.get("severity") == "high"),
        },
    }


@router.get("/properties/{property_id}/graph")
async def property_graph_view(property_id: str, _: User = Depends(get_current_user)):
    """Interactive property-map payload: mortgages/encumbrances/conveyances by
    year, title-report version chain, every linked doc, the money-records graph,
    ownership intervals and the cited event timeline."""
    return property_graph(get_mongo(), property_id=property_id)


@router.get("/properties/{property_id}/evidence-packet")
async def property_evidence(property_id: str, _: User = Depends(get_current_user)):
    return evidence_packet(get_mongo(), property_id=property_id)


# ── single document viewer (full transcript + original file) ─────────────────
# Disk roots to resolve title/discovery source PDFs that aren't stored in the DB.
_DISK_BASES = [Path(r"F:\Title reports"), Path("F:/"), Path("E:/")]


def _doc_source_paths(doc: dict) -> List[str]:
    out = []
    for sf in (doc.get("custody") or {}).get("source_files") or []:
        if isinstance(sf, dict):
            p = sf.get("source_path") or sf.get("path") or sf.get("name")
        else:
            p = sf
        if p:
            out.append(str(p))
    return out


def _locate_on_disk(doc: dict) -> Optional[Path]:
    for raw in _doc_source_paths(doc):
        p = raw.replace("/", "\\")
        cands: List[Path] = []
        if os.path.isabs(p):
            cands.append(Path(p))
        else:
            for b in _DISK_BASES:
                cands.append(b / p)
                # tolerate paths that already include the 'Title reports' anchor
                low = p.lower()
                if low.startswith("title reports\\"):
                    cands.append(b / p[len("title reports\\"):])
        for c in cands:
            try:
                if c.is_file():
                    return c
            except OSError:
                continue
    return None


def _gridfs_file_doc(db, sha: Optional[str]):
    if not sha:
        return None
    return db["attachment_files.files"].find_one({"metadata.sha256": sha})


def _read_original(db, doc: dict):
    """Return (bytes, filename) for the original document, or None.
    Source priority: GridFS attachment_files (by sha) -> attachments_v2 gridfs_id
    -> on-disk source_files (F:/E:)."""
    sha = (doc.get("custody") or {}).get("sha256")
    fdoc = _gridfs_file_doc(db, sha)
    if fdoc:
        from gridfs import GridFSBucket
        b = GridFSBucket(db, bucket_name="attachment_files")
        return b.open_download_stream(fdoc["_id"]).read(), (fdoc.get("filename") or "document")
    if sha:
        av = db["attachments_v2"].find_one({"sha256": sha})
        if av and av.get("gridfs_id"):
            from gridfs import GridFSBucket
            for bn in ("attachment_files", "fs"):
                try:
                    b = GridFSBucket(db, bucket_name=bn)
                    return (b.open_download_stream(av["gridfs_id"]).read(),
                            (av.get("filename") or "document"))
                except Exception:  # noqa: BLE001
                    continue
    p = _locate_on_disk(doc)
    if p:
        try:
            return p.read_bytes(), p.name
        except OSError:
            return None
    return None


def _has_original(db, doc: dict) -> bool:
    sha = (doc.get("custody") or {}).get("sha256")
    if _gridfs_file_doc(db, sha):
        return True
    if sha and db["attachments_v2"].find_one({"sha256": sha}, {"_id": 1}):
        return True
    return _locate_on_disk(doc) is not None


@router.get("/documents/{doc_id}")
async def document_detail(doc_id: str, _: User = Depends(get_current_user)):
    """Full single-document payload: metadata + the complete frontier-OCR
    transcript (always available) + whether an original file can be served."""
    db = _db()
    d = db["documents"].find_one({"_id": doc_id})
    if not d:
        raise HTTPException(404, "document not found")
    srcs = _doc_source_paths(d)
    fname = None
    if srcs:
        fname = srcs[0].replace("/", "\\").split("\\")[-1]
    return {
        "doc_id": d["_id"],
        "source_type": d.get("source_type"),
        "vendor": d.get("vendor"),
        "label": fname or d["_id"],
        "date": _fmt(d.get("completed_date") or d.get("search_date")
                     or d.get("effective_date") or d.get("created_at")),
        "pages": d.get("page_count"),
        "sha256": (d.get("custody") or {}).get("sha256"),
        "order_number": d.get("order_number"),
        "is_latest": bool(d.get("is_latest")),
        "extraction_method": d.get("extraction_method"),
        "property_address": d.get("property_address"),
        "text": d.get("extracted_text") or "",
        "has_original": _has_original(db, d),
        "original_filename": fname,
    }


@router.get("/documents/{doc_id}/file")
async def document_file(doc_id: str, _: User = Depends(get_current_user)):
    """Stream the original document bytes (PDF/image/office) for inline viewing."""
    db = _db()
    d = db["documents"].find_one({"_id": doc_id}, {"custody": 1})
    if not d:
        raise HTTPException(404, "document not found")
    res = _read_original(db, d)
    if not res:
        raise HTTPException(404, "original file not available")
    data, fname = res
    media = mimetypes.guess_type(fname)[0] or "application/octet-stream"
    return Response(content=data, media_type=media,
                    headers={"Content-Disposition": f'inline; filename="{fname}"'})


# ── findings ─────────────────────────────────────────────────────────────────
@router.get("/findings")
async def list_findings(
    _: User = Depends(get_current_user),
    severity: Optional[str] = None,
    finding_type: Optional[str] = None,
    status: Optional[str] = None,
    property_id: Optional[str] = None,
    limit: int = Query(300, le=1000),
):
    m = get_mongo()
    flt = {}
    for k, v in [("severity", severity), ("finding_type", finding_type),
                 ("status", status), ("property_id", property_id)]:
        if v:
            flt[k] = v
    rows = list(m.db["findings"].find(flt).limit(limit))
    # resolve property addresses for display
    pids = list({f.get("property_id") for f in rows if f.get("property_id")})
    addr = {e["_id"]: e.get("canonical_address")
            for e in m.db["entities"].find({"_id": {"$in": pids}}, {"canonical_address": 1})}
    items = []
    for f in rows:
        f["id"] = f.pop("_id")
        f["property_address"] = addr.get(f.get("property_id"))
        items.append(f)
    sev_order = {"critical": 0, "high": 1, "medium": 2, "info": 3}
    items.sort(key=lambda f: (sev_order.get(f.get("severity"), 9),))

    def facet(field):
        out = {}
        for f in m.db["findings"].find(flt, {field: 1}):
            out[f.get(field)] = out.get(f.get(field), 0) + 1
        return {str(k): v for k, v in out.items()}

    return {"total": len(items), "items": items,
            "facets": {"by_severity": facet("severity"), "by_type": facet("finding_type"),
                       "by_status": facet("status")}}


# ── 8.8 ad-hoc grid cell (cached scoped extraction, NOT the live agent) ───────
class CellQuery(BaseModel):
    property_id: str
    question: str


def _doc_set_version(doss: dict) -> str:
    import hashlib
    ids = sorted((doss.get("title", {}).get("doc_ids") or []) +
                 (doss.get("insurance", {}).get("doc_ids") or []) +
                 (doss.get("equity", {}).get("doc_ids") or []))
    return hashlib.sha1("|".join(ids).encode()).hexdigest()[:12]


@router.post("/portfolio/cell")
async def portfolio_cell(body: CellQuery, _: User = Depends(get_current_user)):
    import hashlib
    from api.rag_singleton import get_anthropic_client, get_settings
    m = get_mongo()
    doss = m.db["property_dossier"].find_one({"_id": body.property_id})
    if not doss:
        raise HTTPException(404, "property not found")
    ver = _doc_set_version(doss)
    qh = hashlib.sha1(body.question.strip().lower().encode()).hexdigest()[:12]
    cache = m.db["portfolio_grid_cache"]
    key = f"{body.property_id}|{qh}|{ver}"
    hit = cache.find_one({"_id": key})
    if hit:
        return {"cached": True, **{k: hit[k] for k in ("answer", "basis", "status")}}
    # scoped context = the dossier (already-materialized facts) — cheap, no agent
    ctx = {k: doss.get(k) for k in ("canonical_address", "owners", "title", "insurance",
                                    "equity", "litigation", "fact_counts", "grounded_facts")}
    findings = [f.get("title") for f in m.db["findings"].find({"property_id": body.property_id}, {"title": 1})]
    import json as _json
    client = get_anthropic_client()
    model = get_settings().rag_v2_summary_model
    try:
        resp = client.messages.create(model=model, max_tokens=400,
            system=("Answer the question about THIS ONE property using ONLY the provided "
                    "dossier facts. Be concise (<=2 sentences). If the facts don't answer it, "
                    "say 'not in dossier'. Return ONLY the tool call."),
            tools=[{"name": "cell", "description": "Answer for one property",
                    "input_schema": {"type": "object", "properties": {
                        "answer": {"type": "string"}, "basis": {"type": "string"}},
                        "required": ["answer"]}}],
            tool_choice={"type": "tool", "name": "cell"},
            messages=[{"role": "user", "content":
                       f"PROPERTY DOSSIER:\n{_json.dumps(ctx, default=str)[:14000]}\n\n"
                       f"FINDINGS: {findings}\n\nQUESTION: {body.question}"}])
        out = {}
        for b in resp.content:
            if getattr(b, "type", None) == "tool_use":
                out = dict(b.input or {})
        ans = {"answer": out.get("answer", "not in dossier"), "basis": out.get("basis", ""),
               "status": "ok"}
    except Exception as exc:  # noqa: BLE001
        ans = {"answer": f"error: {exc}", "basis": "", "status": "error"}
    import datetime as _dt
    cache.update_one({"_id": key}, {"$set": {"_id": key, "property_id": body.property_id,
        "question": body.question, "doc_set_version": ver, **ans,
        "computed_at": _dt.datetime.now(_dt.timezone.utc)}}, upsert=True)
    return {"cached": False, **ans}


class FindingStatus(BaseModel):
    status: str  # confirmed | rejected | pending


@router.patch("/findings/{finding_id}")
async def update_finding(finding_id: str, body: FindingStatus,
                         current: User = Depends(get_current_user)):
    if body.status not in ("confirmed", "rejected", "pending"):
        raise HTTPException(400, "invalid status")
    import datetime as _dt
    r = _db()["findings"].update_one({"_id": finding_id}, {"$set": {
        "status": body.status, "reviewed_by": current.email,
        "reviewed_at": _dt.datetime.now(_dt.timezone.utc)}})
    if r.matched_count == 0:
        raise HTTPException(404, "finding not found")
    return {"ok": True, "finding_id": finding_id, "status": body.status}
