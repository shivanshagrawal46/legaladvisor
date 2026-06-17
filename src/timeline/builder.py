"""Sprint 5 · timeline (5.2) + evidence packet (5.4).

timeline_for(): a correct, cited chronology from the `events/` store for a
property or entity (optionally date-bounded / flow-of-funds). The LLM never
orders events — it only narrates this.

evidence_packet(): a court-ready bundle for a property — every linked document
with custody (source file + SHA + pages), the grounded facts with verbatim
quotes, the event chronology, and any findings — the full provenance chain.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


def _date(d) -> Optional[str]:
    try:
        return d.strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return None


def timeline_for(m, *, property_id: Optional[str] = None, entity_id: Optional[str] = None,
                 event_types: Optional[List[str]] = None,
                 date_from: Optional[datetime] = None, date_to: Optional[datetime] = None,
                 limit: int = 300) -> List[Dict[str, Any]]:
    events = m.db["events"]
    ents = m.db["entities"]
    q: Dict[str, Any] = {}
    if property_id:
        q["property_id"] = property_id
    if entity_id:
        q["entity_ids"] = entity_id
    if event_types:
        q["event_type"] = {"$in": event_types}
    if date_from or date_to:
        dd: Dict[str, Any] = {}
        if date_from:
            dd["$gte"] = date_from
        if date_to:
            dd["$lte"] = date_to
        q["date"] = dd
    rows = list(events.find(q).sort("date", 1).limit(limit))
    # resolve entity names for display
    ids = {x for r in rows for x in (r.get("entity_ids") or [])}
    names = {e["_id"]: e.get("canonical_name") or e.get("canonical_address") or e["_id"]
             for e in ents.find({"_id": {"$in": list(ids)}},
                                {"canonical_name": 1, "canonical_address": 1})}
    out = []
    for r in rows:
        out.append({
            "date": _date(r.get("date")), "date_kind": r.get("date_kind"),
            "event_type": r.get("event_type"), "detail": r.get("detail"),
            "amount": r.get("amount"),
            "entities": [names.get(x, x) for x in (r.get("entity_ids") or [])],
            "property_id": r.get("property_id"), "doc_id": r.get("doc_id"),
            "source_quote": r.get("source_quote"),
        })
    return out


_MONEY_EVENTS = ("conveyance", "mortgage", "lien", "judgment", "assignment")


def _money(s) -> Optional[float]:
    import re
    if s is None:
        return None
    mo = re.search(r"[\d,]+(?:\.\d{2})?", str(s).replace("$", ""))
    if not mo:
        return None
    try:
        return float(mo.group(0).replace(",", ""))
    except Exception:  # noqa: BLE001
        return None


def flow_of_funds(m, *, entity_id: Optional[str] = None, property_id: Optional[str] = None,
                  limit: int = 200) -> Dict[str, Any]:
    """Money-movement view: dated monetary events (conveyances, mortgages, liens,
    judgments) for an entity or property, with amounts parsed, chronological."""
    events = m.db["events"]
    q: Dict[str, Any] = {"event_type": {"$in": list(_MONEY_EVENTS)}}
    if entity_id:
        q["entity_ids"] = entity_id
    if property_id:
        q["property_id"] = property_id
    rows = list(events.find(q).sort("date", 1).limit(limit))
    flows, total = [], 0.0
    for r in rows:
        amt = _money(r.get("amount"))
        if amt:
            total += amt
        flows.append({"date": _date(r.get("date")), "type": r.get("event_type"),
                      "amount": amt, "detail": r.get("detail"),
                      "doc_id": r.get("doc_id"), "source_quote": r.get("source_quote")})
    return {"entity_id": entity_id, "property_id": property_id,
            "n_events": len(flows), "total_amount_seen": round(total, 2), "flows": flows}


def evidence_packet(m, *, property_id: str) -> Dict[str, Any]:
    ents, docs = m.db["entities"], m.db["documents"]
    events, findings = m.db["events"], m.db["findings"]
    prop = ents.find_one({"_id": property_id})
    if not prop:
        return {"error": f"property {property_id} not found"}
    doss = m.db["property_dossier"].find_one({"_id": property_id}) or {}
    doc_ids = (prop.get("title_doc_ids") or []) + (prop.get("insurance_doc_ids") or []) + \
              (prop.get("equity_doc_ids") or []) + (prop.get("litigation_doc_ids") or [])
    doc_rows = []
    for d in docs.find({"_id": {"$in": doc_ids}},
                       {"source_type": 1, "custody": 1, "page_count": 1, "vendor": 1,
                        "property_address": 1, "grounded_facts": 1}):
        cust = d.get("custody") or {}
        doc_rows.append({
            "doc_id": d["_id"], "source_type": d.get("source_type"),
            "source_file": cust.get("source_file") or (cust.get("source_files") or [None])[0],
            "sha256": cust.get("sha256"), "pages": d.get("page_count"),
            "vendor": d.get("vendor"),
            "grounded_fact_counts": {k: len(v) for k, v in (d.get("grounded_facts") or {}).items()},
        })
    # bitemporal ownership chain (Sprint 3.2.3): each owner's as_of → until
    from src.graph.bitemporal import ownership_intervals
    _ivs = ownership_intervals(m.db["relationships"], property_id)
    ent_names = {e["_id"]: e.get("canonical_name") or e["_id"]
                 for e in ents.find({"_id": {"$in": [iv["owner"] for iv in _ivs]}},
                                    {"canonical_name": 1})}
    intervals = [{"owner": iv["owner"],
                  "owner_name": ent_names.get(iv["owner"], iv["owner"]),
                  "amount": iv.get("amount"), "source_quote": iv.get("source_quote"),
                  "as_of": _date(iv["as_of"]), "until": _date(iv["until"])}
                 for iv in _ivs]
    return {
        "property_id": property_id,
        "address": prop.get("canonical_address"), "parcel_id": prop.get("parcel_id"),
        "is_david": prop.get("is_david"), "side": prop.get("side"),
        "owners": doss.get("owners", []),
        "ownership_intervals": intervals,
        "equity": doss.get("equity", {}),
        "documents": doc_rows,
        "timeline": timeline_for(m, property_id=property_id),
        "findings": [{"type": f.get("finding_type"), "severity": f.get("severity"),
                      "title": f.get("title"), "status": f.get("status"),
                      "evidence": f.get("evidence")}
                     for f in findings.find({"property_id": property_id})],
        "generated_at": datetime.utcnow().isoformat(),
    }
