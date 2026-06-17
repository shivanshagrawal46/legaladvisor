"""Sprint 8 — REST endpoints for the portfolio grid, property detail, findings
dashboard, and observability. All read the already-materialized collections
(property_dossier, findings, events, dashboard_stats) — NO live agent — so the
UI is instant. JWT-protected via get_current_user.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from api.auth import User, get_current_user
from api.rag_singleton import get_mongo
from src.timeline.builder import timeline_for, flow_of_funds, evidence_packet

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
@router.get("/properties/{property_id}")
async def property_detail(property_id: str, _: User = Depends(get_current_user)):
    m = get_mongo()
    doss = m.db["property_dossier"].find_one({"_id": property_id})
    if not doss:
        raise HTTPException(404, "property not found")
    doss.pop("_id", None)
    findings = list(m.db["findings"].find({"property_id": property_id}))
    for f in findings:
        f["id"] = f.pop("_id")
    return {
        "property_id": property_id,
        "dossier": doss,
        "timeline": timeline_for(m, property_id=property_id, limit=300),
        "flow_of_funds": flow_of_funds(m, property_id=property_id),
        "findings": findings,
        "finding_counts": {
            "total": len(findings),
            "critical": sum(1 for f in findings if f.get("severity") == "critical"),
            "high": sum(1 for f in findings if f.get("severity") == "high"),
        },
    }


@router.get("/properties/{property_id}/evidence-packet")
async def property_evidence(property_id: str, _: User = Depends(get_current_user)):
    return evidence_packet(get_mongo(), property_id=property_id)


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
