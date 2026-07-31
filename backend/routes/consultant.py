"""Consultant workspace routes (data-isolated at API layer)."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone

from auth import require_role
from db import coll
from models import DraftUpdateIn

router = APIRouter(prefix="/consultant", tags=["consultant"])


async def _person_id(user: dict) -> str:
    if not user.get("person_id"):
        raise HTTPException(status_code=403, detail="No person link on account")
    return user["person_id"]


@router.get("/submissions")
async def submissions(user: dict = Depends(require_role("consultant"))):
    pid = await _person_id(user)
    docs = await coll("records_current").find(
        {"consultant_person_id": pid}, {"_id": 0}
    ).limit(500).to_list(500)
    return docs


@router.get("/organizations")
async def organizations(user: dict = Depends(require_role("consultant"))):
    pid = await _person_id(user)
    org_ids = await coll("records_current").distinct(
        "organization_id", {"consultant_person_id": pid}
    )
    if not org_ids:
        return []
    docs = await coll("organizations_current").find(
        {"organization_id": {"$in": org_ids}}, {"_id": 0}
    ).to_list(500)
    return docs


@router.get("/activities")
async def activities(user: dict = Depends(require_role("consultant"))):
    """Historical consultant activities for this consultant name."""
    docs = await coll("historical_activities").find(
        {"consultant_name": user.get("name_ar")}, {"_id": 0}
    ).limit(500).to_list(500)
    return docs


@router.patch("/records/{migration_id}")
async def update_draft(
    migration_id: str, payload: DraftUpdateIn,
    user: dict = Depends(require_role("consultant")),
):
    pid = await _person_id(user)
    rec = await coll("records_current").find_one({"migration_id": migration_id})
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    if rec.get("consultant_person_id") != pid:
        raise HTTPException(status_code=403, detail="Not your record")

    updates = {}
    for k in ("model_url", "notes", "status"):
        v = getattr(payload, k)
        if v is not None:
            updates[k] = v
    if not updates:
        return {"ok": True, "changed": 0}
    updates["modified_at_iso"] = datetime.now(timezone.utc).isoformat()

    before = {k: rec.get(k) for k in updates}
    await coll("records_current").update_one(
        {"migration_id": migration_id}, {"$set": updates}
    )
    await coll("audit_log").insert_one({
        "user_email": user["email"],
        "user_id": user["id"],
        "action": "consultant_draft_update",
        "entity": "record",
        "entity_key": migration_id,
        "before": before,
        "after": updates,
        "created_at": updates["modified_at_iso"],
    })
    return {"ok": True, "changed": len(updates)}
