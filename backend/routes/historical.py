"""Historical (immutable) read-only views:
- /api/evaluator/historical-arbitrations — scoped to logged-in evaluator's person
- /api/admin/historical/arbitrations — full admin browser
- /api/admin/cohorts + /cohorts/{n} + /organizations/{id}/journey — V8 experience
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from auth import require_role
from db import coll

router = APIRouter(tags=["historical"])


async def _person_display_name(user: dict) -> str | None:
    if not user.get("person_id"):
        return None
    p = await coll("people").find_one({"person_id": user["person_id"]})
    return p.get("person_name") if p else None


# ------ Evaluator: read-only historical arbitrations ------------------
@router.get("/evaluator/historical-arbitrations")
async def evaluator_historical(
    q: Optional[str] = None,
    cohort: Optional[str] = None,
    limit: int = 50, offset: int = 0,
    user: dict = Depends(require_role("evaluator")),
):
    name = await _person_display_name(user)
    if not name:
        raise HTTPException(status_code=403, detail="No person link on account")
    query: dict = {"evaluator_name": name}
    if q:
        query["organization_name"] = {"$regex": q, "$options": "i"}
    if cohort:
        query["cohort"] = cohort
    total = await coll("historical_arbitrations").count_documents(query)
    docs = await coll("historical_arbitrations").find(
        query, {"_id": 0}
    ).skip(offset).limit(min(limit, 200)).to_list(200)
    return {"total": total, "items": docs, "evaluator_name": name}


# ------ Admin: full historical arbitration browser --------------------
@router.get("/admin/historical/arbitrations")
async def admin_historical_arbitrations(
    q: Optional[str] = None,
    cohort: Optional[str] = None,
    evaluator: Optional[str] = None,
    limit: int = 50, offset: int = 0,
    user: dict = Depends(require_role("admin")),
):
    query: dict = {}
    if q:
        query["$or"] = [
            {"organization_name": {"$regex": q, "$options": "i"}},
            {"model_name": {"$regex": q, "$options": "i"}},
        ]
    if cohort:
        query["cohort"] = cohort
    if evaluator:
        query["evaluator_name"] = evaluator
    total = await coll("historical_arbitrations").count_documents(query)
    docs = await coll("historical_arbitrations").find(
        query, {"_id": 0}
    ).skip(offset).limit(min(limit, 200)).to_list(200)
    return {"total": total, "items": docs}


# ------ Explicit immutability endpoint (audits any attempt) -----------
@router.patch("/admin/historical/arbitrations/{legacy_review_id}")
async def block_arb_update(
    legacy_review_id: str, payload: dict,
    user: dict = Depends(require_role("admin")),
):
    """Explicitly returns 405 and logs the attempt to audit_log."""
    from datetime import datetime, timezone
    await coll("audit_log").insert_one({
        "user_email": user["email"], "user_id": user["id"],
        "action": "historical_write_blocked",
        "collection": "historical_arbitrations",
        "op": "PATCH",
        "entity_key": legacy_review_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    raise HTTPException(status_code=405,
                        detail="IMMUTABLE_HISTORICAL: التعديل ممنوع على الطبقة التاريخية.")


@router.delete("/admin/historical/arbitrations/{legacy_review_id}")
async def block_arb_delete(
    legacy_review_id: str,
    user: dict = Depends(require_role("admin")),
):
    from datetime import datetime, timezone
    await coll("audit_log").insert_one({
        "user_email": user["email"], "user_id": user["id"],
        "action": "historical_write_blocked",
        "collection": "historical_arbitrations",
        "op": "DELETE",
        "entity_key": legacy_review_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    raise HTTPException(status_code=405,
                        detail="IMMUTABLE_HISTORICAL: الحذف ممنوع على الطبقة التاريخية.")


# ------ V8 experience: cohorts map & journeys -------------------------
@router.get("/admin/cohorts")
async def cohorts_map(user: dict = Depends(require_role("admin"))):
    """4-batch overview with counts for the cohort map screen."""
    out = []
    for c in ["1", "2", "3", "4"]:
        orgs = await coll("historical_organizations").count_documents({"cohort": c})
        acts = await coll("historical_activities").count_documents({"cohort": c})
        arbs = await coll("historical_arbitrations").count_documents({"cohort": c})
        plans = await coll("historical_batch_plans").count_documents({"cohort": c})
        out.append({
            "cohort": c,
            "organizations": orgs,
            "activities": acts,
            "arbitrations": arbs,
            "batch_plan_rows": plans,
        })
    return out


@router.get("/admin/cohorts/{cohort}")
async def cohort_detail(cohort: str, user: dict = Depends(require_role("admin"))):
    orgs = await coll("historical_organizations").find(
        {"cohort": cohort}, {"_id": 0}
    ).to_list(500)
    # Per-org counts inside this cohort
    for o in orgs:
        legacy_id = o.get("legacy_org_id")
        o["activity_count"] = await coll("historical_activities").count_documents(
            {"legacy_org_id": legacy_id})
        o["arbitration_count"] = await coll("historical_arbitrations").count_documents(
            {"legacy_org_id": legacy_id})
    # KPIs snapshot for the cohort (if any)
    kpi = await coll("historical_batch_kpis").find_one({"cohort_normalized": cohort}, {"_id": 0})
    return {"cohort": cohort, "organizations": orgs, "kpi_snapshot": kpi}


@router.get("/admin/organizations/{org_id}/journey")
async def organization_journey(org_id: str, user: dict = Depends(require_role("admin"))):
    """Full journey view: current org + crosswalk + linked legacy org + counts."""
    current = await coll("organizations_current").find_one({"organization_id": org_id}, {"_id": 0})
    if not current:
        raise HTTPException(status_code=404, detail="Organization not found")

    cw = await coll("crosswalk_organizations").find_one({"current_org_id": org_id}, {"_id": 0})
    legacy = None
    if cw and cw.get("legacy_org_id"):
        legacy = await coll("historical_organizations").find_one(
            {"legacy_org_id": cw["legacy_org_id"]}, {"_id": 0})

    # Current records grouped by model_definition
    records = await coll("records_current").find(
        {"organization_id": org_id}, {"_id": 0}
    ).to_list(200)

    # Legacy activities and arbitrations counts
    legacy_id = cw.get("legacy_org_id") if cw else None
    legacy_activities = legacy_arbitrations = 0
    if legacy_id:
        legacy_activities = await coll("historical_activities").count_documents(
            {"legacy_org_id": legacy_id})
        legacy_arbitrations = await coll("historical_arbitrations").count_documents(
            {"legacy_org_id": legacy_id})

    # Assignment comparison row
    assignment = await coll("assignments").find_one({"current_org_id": org_id}, {"_id": 0})

    return {
        "current": current,
        "crosswalk": cw,
        "legacy": legacy,
        "records": records,
        "record_count": len(records),
        "legacy_activities_count": legacy_activities,
        "legacy_arbitrations_count": legacy_arbitrations,
        "assignment": assignment,
    }
