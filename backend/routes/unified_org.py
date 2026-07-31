"""Unified Organization view — merges current + linked legacy under one record."""
from fastapi import APIRouter, Depends, HTTPException

from auth import require_role
from db import coll
from unified import unified_record, resolve_url

router = APIRouter(prefix="/organizations", tags=["organizations-unified"])


@router.get("")
async def list_organizations(
    q: str | None = None,
    cohort: str | None = None,
    user: dict = Depends(require_role("admin")),
):
    """Unified org list: 57 current + any legacy-only orgs that never re-registered."""
    current_query: dict = {}
    if q: current_query["organization_name"] = {"$regex": q, "$options": "i"}
    current = await coll("organizations_current").find(current_query, {"_id": 0}).to_list(200)

    # Build a set of legacy_org_ids linked to current (exact matches)
    cw_docs = await coll("crosswalk_organizations").find(
        {"match_status": {"$in": ["EXACT_NORMALIZED", "PROBABLE_NAME_VARIANT"]}},
        {"current_org_id": 1, "legacy_org_id": 1, "_id": 0}
    ).to_list(500)
    linked_legacy = {d["legacy_org_id"] for d in cw_docs if d.get("legacy_org_id")}
    current_to_legacy = {d["current_org_id"]: d["legacy_org_id"] for d in cw_docs}

    # For cohort filter: intersect with legacy orgs in that cohort
    if cohort:
        legacy_in_cohort = {d["legacy_org_id"] for d in await coll("historical_organizations").find(
            {"cohort": cohort}, {"legacy_org_id": 1, "_id": 0}).to_list(200)}
        # only include current orgs whose linked legacy is in this cohort
        current = [o for o in current if current_to_legacy.get(o["organization_id"]) in legacy_in_cohort]

    # Build unified rows for current orgs
    rows = []
    for o in current:
        legacy_id = current_to_legacy.get(o["organization_id"])
        legacy = None
        if legacy_id:
            legacy = await coll("historical_organizations").find_one({"legacy_org_id": legacy_id}, {"_id": 0})
        rows.append({
            "org_id": o["organization_id"],
            "organization_name": o["organization_name"],
            "cohort": legacy.get("cohort") if legacy else None,
            "sector": legacy.get("sector") if legacy else None,
            "region": legacy.get("region") if legacy else None,
            "evaluator": o.get("evaluator_name"),
            "consultants": _clean_json_list(o.get("consultant_names")),
            "records": o.get("record_count"),
            "hours": o.get("work_hours"),
            "linked_legacy_id": legacy_id,
            "source": "unified" if legacy else "current",
        })

    # Add legacy-only orgs (no current record) — appear only in historical
    legacy_only_ids = set()
    all_legacy = await coll("historical_organizations").find({}, {"_id": 0}).to_list(500)
    legacy_current_set = {d["legacy_org_id"] for d in cw_docs if d.get("legacy_org_id") and d.get("current_org_id")}
    for lo in all_legacy:
        if lo["legacy_org_id"] in legacy_current_set:
            continue
        if cohort and lo.get("cohort") != cohort:
            continue
        if q and q.lower() not in (lo.get("organization_name") or "").lower():
            continue
        rows.append({
            "org_id": lo["legacy_org_id"],
            "organization_name": lo["organization_name"],
            "cohort": lo.get("cohort"),
            "sector": lo.get("sector"),
            "region": lo.get("region"),
            "evaluator": lo.get("evaluators"),
            "consultants": [lo.get("consultants")] if lo.get("consultants") else [],
            "records": 0,
            "hours": None,
            "linked_legacy_id": lo["legacy_org_id"],
            "source": "legacy_only",
        })
    return rows


@router.get("/{org_id}")
async def organization_unified(org_id: str, user: dict = Depends(require_role("admin"))):
    """Unified detail: current + linked legacy under one journey. Handles both
    ORG-XXX (current) and LEG-ORG-XXX (legacy-only) identifiers."""
    current = await coll("organizations_current").find_one({"organization_id": org_id}, {"_id": 0})
    legacy = None
    crosswalk = None
    if current:
        crosswalk = await coll("crosswalk_organizations").find_one(
            {"current_org_id": org_id}, {"_id": 0})
        if crosswalk and crosswalk.get("legacy_org_id"):
            legacy = await coll("historical_organizations").find_one(
                {"legacy_org_id": crosswalk["legacy_org_id"]}, {"_id": 0})
    else:
        # legacy-only path
        legacy = await coll("historical_organizations").find_one({"legacy_org_id": org_id}, {"_id": 0})
        if not legacy:
            raise HTTPException(status_code=404, detail="Organization not found")

    # ---- Unified header ----
    header = {
        "org_id": org_id,
        "organization_name": (current or legacy).get("organization_name"),
        "cohort": legacy.get("cohort") if legacy else None,
        "sector": legacy.get("sector") if legacy else None,
        "region": legacy.get("region") if legacy else None,
        "target_group": legacy.get("target_group") if legacy else None,
        "roster_status": legacy.get("roster_status") if legacy else None,
        "graduation_date": (legacy.get("graduation_date_iso") if legacy else None),
        "consultants": _clean_json_list((current or {}).get("consultant_names")) or ([legacy.get("consultants")] if legacy else []),
        "evaluator": (current or {}).get("evaluator_name") or (legacy.get("evaluators") if legacy else None),
        "linked_legacy_id": legacy.get("legacy_org_id") if legacy else None,
        "linked_current_id": current.get("organization_id") if current else None,
        "match_status": crosswalk.get("match_status") if crosswalk else None,
        "match_score": crosswalk.get("match_score") if crosswalk else None,
    }

    # ---- Current models grouped by category ----
    current_records = []
    if current:
        current_records = await coll("records_current").find(
            {"organization_id": org_id}, {"_id": 0}).to_list(500)
    records_unified = []
    for r in current_records:
        u = unified_record(r, "current")
        if r.get("evaluator_person_id"):
            p = await coll("people").find_one({"person_id": r["evaluator_person_id"]}, {"_id": 0})
            if p: u["evaluator_name"] = p.get("person_name")
        records_unified.append(u)

    # ---- Legacy arbitrations for this org ----
    legacy_id = legacy.get("legacy_org_id") if legacy else None
    if legacy_id:
        legacy_arbs = await coll("historical_arbitrations").find(
            {"legacy_org_id": legacy_id}, {"_id": 0}).to_list(500)
        for r in legacy_arbs:
            records_unified.append(unified_record(r, "legacy"))
        legacy_activities = await coll("historical_activities").count_documents(
            {"legacy_org_id": legacy_id})
    else:
        legacy_activities = 0

    # ---- Summary strip (impact-oriented) ----
    accepted = sum(1 for r in records_unified if r.get("evaluation") == "مقبول")
    needs_dev = sum(1 for r in records_unified if r.get("evaluation") == "يحتاج لتطوير")
    incomplete = sum(1 for r in records_unified if r.get("evaluation") == "غير مكتمل")
    hours = sum(r.get("work_hours") or 0 for r in records_unified)

    return {
        "header": header,
        "totals": {
            "records": len(records_unified),
            "current": len(current_records),
            "legacy_arbitrations": len(records_unified) - len(current_records),
            "legacy_activities": legacy_activities,
            "accepted": accepted,
            "needs_dev": needs_dev,
            "incomplete": incomplete,
            "hours": round(hours, 1),
        },
        "records": records_unified,
    }


def _clean_json_list(v):
    """Handle CSV-stored JSON lists like '["a","b"]' → ["a","b"]."""
    if not v: return []
    if isinstance(v, list): return v
    if isinstance(v, str):
        s = v.strip()
        if s.startswith("["):
            try:
                import json
                return json.loads(s)
            except Exception:
                pass
        return [s] if s else []
    return []
