"""Evaluators and Consultants unified directories.

The directory is a UNION of:
  - `people` collection entries with matching role (has PERSON-XXX id + hours + orgs)
  - historical names in `historical_arbitrations.evaluator_name` /
    `historical_activities.consultant_name` that may not have a current account

The directory KEY is the human name (URL-encoded). Detail endpoint aggregates
across current records + historical arbitrations/activities using name join.
"""
from fastapi import APIRouter, Depends, HTTPException
from urllib.parse import unquote

from auth import require_role
from db import coll
from unified import resolve_url

router = APIRouter(prefix="/directory", tags=["directory"])


# ---------- helpers -----------------------------------------------------
async def _people_by_role(role: str) -> list[dict]:
    return await coll("people").find({"role": role}, {"_id": 0}).to_list(200)


async def _person_by_name(role: str, name: str) -> dict | None:
    return await coll("people").find_one({"role": role, "person_name": name})


# ---------- Evaluators --------------------------------------------------
@router.get("/evaluators")
async def evaluators_directory(user: dict = Depends(require_role("admin"))):
    current = await _people_by_role("evaluator")
    current_by_name = {p["person_name"]: p for p in current if p.get("person_name")}
    hist_names = {n for n in (await coll("historical_arbitrations").distinct("evaluator_name") or []) if n}

    all_names = sorted(set(current_by_name.keys()) | hist_names)
    out = []
    for name in all_names:
        p = current_by_name.get(name)
        # Aggregate live counts
        current_records = 0
        current_hours = 0.0
        current_orgs = 0
        if p:
            current_records = await coll("records_current").count_documents(
                {"evaluator_person_id": p["person_id"]})
            agg = await coll("records_current").aggregate([
                {"$match": {"evaluator_person_id": p["person_id"]}},
                {"$group": {"_id": None, "h": {"$sum": "$work_hours"}}},
            ]).to_list(1)
            current_hours = float(agg[0]["h"]) if agg else 0.0
            current_orgs = len(await coll("records_current").distinct(
                "organization_id", {"evaluator_person_id": p["person_id"]}))
        legacy_arbs = await coll("historical_arbitrations").count_documents({"evaluator_name": name})
        legacy_cohorts = sorted({c for c in (await coll("historical_arbitrations").distinct(
            "cohort", {"evaluator_name": name}) or []) if c})
        out.append({
            "name": name,
            "person_id": p.get("person_id") if p else None,
            "has_current_account": p is not None,
            "current_records": current_records,
            "current_hours": round(current_hours, 1),
            "current_orgs": current_orgs,
            "legacy_arbitrations": legacy_arbs,
            "legacy_cohorts": legacy_cohorts,
            "total_records": current_records + legacy_arbs,
        })
    # Sort by total activity desc
    out.sort(key=lambda x: -x["total_records"])
    return out


@router.get("/evaluators/{name}")
async def evaluator_detail(name: str, user: dict = Depends(require_role("admin"))):
    name = unquote(name)
    p = await _person_by_name("evaluator", name)

    # Cohorts strip: for each cohort compute counts, hours, decisions
    cohorts = []
    # legacy cohorts where this evaluator appears
    legacy_cohorts = {c for c in (await coll("historical_arbitrations").distinct(
        "cohort", {"evaluator_name": name}) or []) if c}
    # current has no cohort field on records; org has via legacy crosswalk. Use "current" bucket.
    for c in sorted(legacy_cohorts):
        arbs = await coll("historical_arbitrations").find(
            {"evaluator_name": name, "cohort": c}, {"_id": 0}).to_list(2000)
        orgs = sorted({(a.get("legacy_org_id"), a.get("organization_name")) for a in arbs})
        results = {}
        hours = 0.0
        for a in arbs:
            r = a.get("arbitration_result") or a.get("arbitration_result_raw") or "غير موثّق"
            results[r] = results.get(r, 0) + 1
            try:
                hours += float(a.get("total_arbitration_hours_raw") or 0)
            except (ValueError, TypeError):
                pass
        cohorts.append({
            "cohort": c,
            "source": "legacy",
            "orgs": [{"org_id": oid, "organization_name": on,
                      "models": sum(1 for a in arbs if a.get("legacy_org_id") == oid)}
                     for oid, on in orgs if oid],
            "arbitrations": len(arbs),
            "hours": round(hours, 1),
            "decisions": results,
        })

    # Current bucket (if the evaluator has a person_id)
    current_records = []
    current_hours = 0.0
    current_orgs = []
    if p:
        current_records = await coll("records_current").find(
            {"evaluator_person_id": p["person_id"]}, {"_id": 0}).to_list(2000)
        current_hours = sum(r.get("work_hours", 0) or 0 for r in current_records)
        current_org_ids = sorted({r["organization_id"] for r in current_records if r.get("organization_id")})
        for oid in current_org_ids:
            org = await coll("organizations_current").find_one({"organization_id": oid}, {"_id": 0})
            recs_in_org = [r for r in current_records if r.get("organization_id") == oid]
            current_orgs.append({
                "org_id": oid,
                "organization_name": org.get("organization_name") if org else oid,
                "models": len(recs_in_org),
                "accepted": sum(1 for r in recs_in_org if r.get("evaluation") == "مقبول"),
                "needs_dev": sum(1 for r in recs_in_org if r.get("evaluation") == "يحتاج لتطوير"),
                "hours": round(sum(r.get("work_hours", 0) or 0 for r in recs_in_org), 1),
            })
    # Decision distribution across everything
    decisions_all = {}
    for a in current_records:
        v = a.get("evaluation") or "—"
        decisions_all[v] = decisions_all.get(v, 0) + 1
    for c in cohorts:
        for k, v in c["decisions"].items():
            decisions_all[k] = decisions_all.get(k, 0) + v

    return {
        "name": name,
        "person_id": p.get("person_id") if p else None,
        "has_current_account": p is not None,
        "totals": {
            "orgs": len(current_orgs) + sum(len(c["orgs"]) for c in cohorts),
            "arbitrations": sum(c["arbitrations"] for c in cohorts) + len(current_records),
            "hours": round(current_hours + sum(c["hours"] for c in cohorts), 1),
            "current_records": len(current_records),
            "legacy_arbitrations": sum(c["arbitrations"] for c in cohorts),
            "cohorts_participated": sorted(legacy_cohorts),
        },
        "decisions": decisions_all,
        "current": {"orgs": current_orgs, "hours": round(current_hours, 1)},
        "legacy_by_cohort": cohorts,
    }


@router.get("/evaluators/{name}/organization/{org_id}")
async def evaluator_org_models(
    name: str, org_id: str, user: dict = Depends(require_role("admin")),
):
    """Return every model this evaluator worked on for this organization,
    across current + legacy."""
    name = unquote(name)
    p = await _person_by_name("evaluator", name)

    items = []
    if p:
        cursor = coll("records_current").find(
            {"evaluator_person_id": p["person_id"], "organization_id": org_id}, {"_id": 0})
        async for r in cursor:
            items.append(_current_item(r))
    # legacy match by legacy_org_id
    cursor = coll("historical_arbitrations").find(
        {"evaluator_name": name, "legacy_org_id": org_id}, {"_id": 0})
    async for r in cursor:
        items.append(_legacy_item(r))
    return items


# ---------- Consultants -------------------------------------------------
@router.get("/consultants")
async def consultants_directory(user: dict = Depends(require_role("admin"))):
    current = await _people_by_role("consultant")
    current_by_name = {p["person_name"]: p for p in current if p.get("person_name")}
    hist_names = {n for n in (await coll("historical_activities").distinct("consultant_name") or []) if n}
    hist_arb_cons = {n for n in (await coll("historical_arbitrations").distinct("consultant_name") or []) if n}
    all_names = sorted(set(current_by_name.keys()) | hist_names | hist_arb_cons)
    out = []
    for name in all_names:
        p = current_by_name.get(name)
        current_records = 0
        current_hours = 0.0
        current_orgs = 0
        if p:
            current_records = await coll("records_current").count_documents(
                {"consultant_person_id": p["person_id"]})
            agg = await coll("records_current").aggregate([
                {"$match": {"consultant_person_id": p["person_id"]}},
                {"$group": {"_id": None, "h": {"$sum": "$work_hours"}}},
            ]).to_list(1)
            current_hours = float(agg[0]["h"]) if agg else 0.0
            current_orgs = len(await coll("records_current").distinct(
                "organization_id", {"consultant_person_id": p["person_id"]}))
        legacy_acts = await coll("historical_activities").count_documents({"consultant_name": name})
        legacy_cohorts = sorted({c for c in (await coll("historical_activities").distinct(
            "cohort", {"consultant_name": name}) or []) if c})
        out.append({
            "name": name,
            "person_id": p.get("person_id") if p else None,
            "has_current_account": p is not None,
            "current_records": current_records,
            "current_hours": round(current_hours, 1),
            "current_orgs": current_orgs,
            "legacy_activities": legacy_acts,
            "legacy_cohorts": legacy_cohorts,
            "total_items": current_records + legacy_acts,
        })
    out.sort(key=lambda x: -x["total_items"])
    return out


@router.get("/consultants/{name}")
async def consultant_detail(name: str, user: dict = Depends(require_role("admin"))):
    name = unquote(name)
    p = await _person_by_name("consultant", name)

    # current records
    current_records = []
    if p:
        current_records = await coll("records_current").find(
            {"consultant_person_id": p["person_id"]}, {"_id": 0}).to_list(3000)

    current_hours = sum(r.get("work_hours", 0) or 0 for r in current_records)
    current_orgs = sorted({r["organization_id"] for r in current_records if r.get("organization_id")})

    # legacy activities grouped by cohort
    legacy_cohorts_data = []
    legacy_cohort_set = {c for c in (await coll("historical_activities").distinct(
        "cohort", {"consultant_name": name}) or []) if c}
    for c in sorted(legacy_cohort_set):
        acts = await coll("historical_activities").find(
            {"consultant_name": name, "cohort": c}, {"_id": 0}).to_list(3000)
        legacy_cohorts_data.append({
            "cohort": c,
            "activities": len(acts),
            "orgs": len({a.get("legacy_org_id") for a in acts if a.get("legacy_org_id")}),
            "stages": _bucketize(acts, "stage"),
            "completion": _bucketize(acts, "completion_status"),
        })

    # decisions on current submissions
    decisions = _bucketize(current_records, "evaluation")

    # orgs strip for current
    orgs_strip = []
    for oid in current_orgs:
        org = await coll("organizations_current").find_one({"organization_id": oid}, {"_id": 0})
        recs = [r for r in current_records if r.get("organization_id") == oid]
        orgs_strip.append({
            "org_id": oid,
            "organization_name": org.get("organization_name") if org else oid,
            "models": len(recs),
            "accepted": sum(1 for r in recs if r.get("evaluation") == "مقبول"),
            "needs_dev": sum(1 for r in recs if r.get("evaluation") == "يحتاج لتطوير"),
            "hours": round(sum(r.get("work_hours", 0) or 0 for r in recs), 1),
        })

    return {
        "name": name,
        "person_id": p.get("person_id") if p else None,
        "has_current_account": p is not None,
        "totals": {
            "orgs": len(current_orgs) + sum(c["orgs"] for c in legacy_cohorts_data),
            "current_records": len(current_records),
            "legacy_activities": sum(c["activities"] for c in legacy_cohorts_data),
            "hours": round(current_hours, 1),
            "cohorts_participated": sorted(legacy_cohort_set),
        },
        "decisions": decisions,
        "current": {"orgs": orgs_strip, "hours": round(current_hours, 1)},
        "legacy_by_cohort": legacy_cohorts_data,
    }


# ---------- helpers -----------------------------------------------------
def _bucketize(rows, field):
    out = {}
    for r in rows:
        v = r.get(field) or "—"
        out[v] = out.get(v, 0) + 1
    return out


def _current_item(r):
    return {
        "id": r.get("migration_id"), "source": "current",
        "model_name": r.get("model_name"), "category": r.get("category"),
        "status": r.get("status"), "evaluation": r.get("evaluation"),
        "work_hours": r.get("work_hours"), "notes": r.get("notes"),
        "url": resolve_url(r), "submitted_at": r.get("submitted_at_iso"),
        "decided_at": r.get("modified_at_iso"),
        "consultant_name": r.get("consultant_name"),
    }


def _legacy_item(r):
    return {
        "id": r.get("legacy_review_id"), "source": "legacy",
        "model_name": r.get("model_name"), "category": r.get("category"),
        "status": r.get("evaluation_status"),
        "evaluation": r.get("arbitration_result") or r.get("arbitration_result_raw"),
        "work_hours": r.get("total_arbitration_hours") or r.get("total_arbitration_hours_raw"),
        "notes": r.get("note"),
        "url": resolve_url(r),
        "submitted_at": None, "decided_at": r.get("arbitration_date_iso") or r.get("arbitration_date_source_iso"),
        "consultant_name": r.get("consultant_name"),
        "cohort": r.get("cohort"),
    }
