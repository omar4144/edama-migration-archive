"""Evaluator (المحكّم) workspace routes."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone

from auth import require_role
from db import coll
from models import RecordDecisionIn

router = APIRouter(prefix="/evaluator", tags=["evaluator"])


async def _person_id(user: dict) -> str:
    if not user.get("person_id"):
        raise HTTPException(status_code=403, detail="No person link on account")
    return user["person_id"]


@router.get("/queue")
async def queue(user: dict = Depends(require_role("evaluator"))):
    pid = await _person_id(user)
    docs = await coll("records_current").find(
        {"evaluator_person_id": pid}, {"_id": 0}
    ).limit(1000).to_list(1000)
    return docs


@router.get("/hours-summary")
async def hours_summary(user: dict = Depends(require_role("evaluator"))):
    pid = await _person_id(user)
    agg = await coll("records_current").aggregate([
        {"$match": {"evaluator_person_id": pid}},
        {"$group": {
            "_id": "$organization_id",
            "hours": {"$sum": "$work_hours"},
            "records": {"$sum": 1},
        }},
        {"$sort": {"hours": -1}},
    ]).to_list(200)
    total = sum(row["hours"] for row in agg)
    return {"total_hours": total, "by_organization": agg}


@router.get("/organizations")
async def organizations(user: dict = Depends(require_role("evaluator"))):
    pid = await _person_id(user)
    org_ids = await coll("records_current").distinct(
        "organization_id", {"evaluator_person_id": pid}
    )
    if not org_ids:
        return []
    docs = await coll("organizations_current").find(
        {"organization_id": {"$in": org_ids}}, {"_id": 0}
    ).to_list(500)
    return docs


@router.patch("/records/{migration_id}")
async def record_decision(
    migration_id: str, payload: RecordDecisionIn,
    user: dict = Depends(require_role("evaluator")),
):
    pid = await _person_id(user)
    rec = await coll("records_current").find_one({"migration_id": migration_id})
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    if rec.get("evaluator_person_id") != pid:
        raise HTTPException(status_code=403, detail="Not assigned to you")

    now = datetime.now(timezone.utc).isoformat()
    updates = {
        "evaluation": payload.evaluation,
        "work_hours": payload.work_hours,
        "notes": payload.notes,
        "modified_at_iso": now,
        "verified_at_iso": now,
    }
    before = {k: rec.get(k) for k in updates}
    await coll("records_current").update_one(
        {"migration_id": migration_id}, {"$set": updates}
    )
    await coll("audit_log").insert_one({
        "user_email": user["email"],
        "user_id": user["id"],
        "action": "evaluator_decision",
        "entity": "record",
        "entity_key": migration_id,
        "before": before,
        "after": updates,
        "created_at": now,
    })
    return {"ok": True}
