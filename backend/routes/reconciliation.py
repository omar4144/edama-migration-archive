"""Reconciliation dashboard & mapping decisions (admin-only)."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone

from auth import require_role
from db import coll
from models import MappingDecisionIn
from migrations.import_archive import EXPECTED

router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])


@router.get("/summary")
async def summary(user: dict = Depends(require_role("admin"))):
    """Live counts vs. contract targets."""
    async def _cnt(name):
        return await coll(name).count_documents({})

    counts = {
        "records_current": await _cnt("records_current"),
        "organizations_current": await _cnt("organizations_current"),
        "people": await _cnt("people"),
        "model_definitions": await _cnt("model_definitions"),
        "duplicate_links_current": await _cnt("duplicate_links_current"),
        "historical_organizations": await _cnt("historical_organizations"),
        "historical_activities": await _cnt("historical_activities"),
        "historical_arbitrations": await _cnt("historical_arbitrations"),
        "historical_duplicate_links": await _cnt("historical_duplicate_links"),
        "historical_batch_plans": await _cnt("historical_batch_plans"),
        "historical_batch_kpis": await _cnt("historical_batch_kpis"),
        "crosswalk_organizations": await _cnt("crosswalk_organizations"),
        "crosswalk_models": await _cnt("crosswalk_models"),
        "crosswalk_records": await _cnt("crosswalk_records"),
        "assignments": await _cnt("assignments"),
        "mappings_pending": await coll("mappings").count_documents({"status": "pending"}),
        "mappings_approved": await coll("mappings").count_documents({"status": "approved"}),
        "mappings_rejected": await coll("mappings").count_documents({"status": "rejected"}),
    }

    # Work hours aggregate
    agg = await coll("records_current").aggregate(
        [{"$group": {"_id": None, "total": {"$sum": "$work_hours"}}}]
    ).to_list(1)
    counts["work_hours_total"] = float(agg[0]["total"]) if agg else 0.0

    # Cohort coverage
    cohort_orgs = await coll("historical_organizations").aggregate(
        [{"$group": {"_id": "$cohort", "count": {"$sum": 1}}},
         {"$sort": {"_id": 1}}]
    ).to_list(20)

    cohort_activities = await coll("historical_activities").aggregate(
        [{"$group": {"_id": "$cohort", "count": {"$sum": 1}}},
         {"$sort": {"_id": 1}}]
    ).to_list(20)

    cohort_arbitrations = await coll("historical_arbitrations").aggregate(
        [{"$group": {"_id": "$cohort", "count": {"$sum": 1}}},
         {"$sort": {"_id": 1}}]
    ).to_list(20)

    # Crosswalk breakdowns
    async def _bucket(collection, field):
        return await coll(collection).aggregate(
            [{"$group": {"_id": f"${field}", "count": {"$sum": 1}}}]
        ).to_list(50)

    org_status = await _bucket("crosswalk_organizations", "match_status")
    model_status = await _bucket("crosswalk_models", "crosswalk_status")
    record_status = await _bucket("crosswalk_records", "crosswalk_status")
    assign_eval = await _bucket("assignments", "evaluator_assignment_status")

    # Latest migration run
    latest_run = await coll("migration_runs").find_one(
        {}, sort=[("generated_at", -1)]
    )
    if latest_run:
        latest_run.pop("_id", None)

    return {
        "counts": counts,
        "expected": EXPECTED,
        "cohorts": {
            "organizations": cohort_orgs,
            "activities": cohort_activities,
            "arbitrations": cohort_arbitrations,
        },
        "crosswalks": {
            "organizations": org_status,
            "models": model_status,
            "records": record_status,
            "evaluator_assignments": assign_eval,
        },
        "latest_run": latest_run,
    }


@router.get("/quality-checks")
async def quality_checks(user: dict = Depends(require_role("admin"))):
    docs = await coll("quality_checks").find({}, {"_id": 0}).to_list(500)
    return docs


@router.get("/sources")
async def sources(user: dict = Depends(require_role("admin"))):
    docs = await coll("source_inventory").find({}, {"_id": 0}).to_list(500)
    return docs


# --- Mapping decisions ---------------------------------------------------
@router.get("/mappings")
async def list_mappings(
    kind: str | None = None,
    status: str = "pending",
    user: dict = Depends(require_role("admin")),
):
    q: dict = {"status": status}
    if kind:
        q["kind"] = kind
    docs = await coll("mappings").find(q, {"_id": 0}).limit(500).to_list(500)
    return docs


@router.post("/mappings/{key}")
async def decide_mapping(
    key: str,
    payload: MappingDecisionIn,
    user: dict = Depends(require_role("admin")),
):
    now = datetime.now(timezone.utc).isoformat()
    existing = await coll("mappings").find_one({"key": key})
    if not existing:
        raise HTTPException(status_code=404, detail="Mapping not found")
    if existing.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Mapping already decided")
    await coll("mappings").update_one(
        {"key": key},
        {"$set": {
            "status": payload.decision,
            "decision": payload.decision,
            "decided_by": user["email"],
            "decided_at": now,
            "note": payload.note,
        }},
    )
    await coll("audit_log").insert_one({
        "user_email": user["email"],
        "user_id": user["id"],
        "action": "mapping_decision",
        "entity": "mapping",
        "entity_key": key,
        "before": {"status": existing.get("status")},
        "after": {"status": payload.decision, "note": payload.note},
        "created_at": now,
    })
    return {"ok": True}


@router.get("/audit-log")
async def audit_log(
    limit: int = 100,
    user: dict = Depends(require_role("admin")),
):
    docs = await coll("audit_log").find({}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return docs
