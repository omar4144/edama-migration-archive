"""Admin routes: organizations, records browser, users, historical views."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone

from auth import require_role, hash_password
from db import coll
from models import new_id

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/organizations")
async def organizations(
    q: Optional[str] = None,
    user: dict = Depends(require_role("admin")),
):
    query: dict = {}
    if q:
        query["organization_name"] = {"$regex": q, "$options": "i"}
    docs = await coll("organizations_current").find(
        query, {"_id": 0}
    ).limit(200).to_list(200)
    return docs


@router.get("/organizations/historical")
async def historical_orgs(
    cohort: Optional[str] = None,
    user: dict = Depends(require_role("admin")),
):
    query: dict = {}
    if cohort:
        query["cohort"] = cohort
    docs = await coll("historical_organizations").find(
        query, {"_id": 0}
    ).limit(500).to_list(500)
    return docs


@router.get("/records")
async def records(
    org_id: Optional[str] = None,
    evaluator_id: Optional[str] = None,
    consultant_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    user: dict = Depends(require_role("admin")),
):
    query: dict = {}
    if org_id:
        query["organization_id"] = org_id
    if evaluator_id:
        query["evaluator_person_id"] = evaluator_id
    if consultant_id:
        query["consultant_person_id"] = consultant_id
    if status:
        query["status"] = status
    total = await coll("records_current").count_documents(query)
    docs = await coll("records_current").find(
        query, {"_id": 0}
    ).skip(offset).limit(min(limit, 500)).to_list(500)
    return {"total": total, "items": docs}


@router.get("/people")
async def people(user: dict = Depends(require_role("admin"))):
    docs = await coll("people").find({}, {"_id": 0}).to_list(200)
    return docs


@router.get("/models")
async def models(user: dict = Depends(require_role("admin"))):
    docs = await coll("model_definitions").find({}, {"_id": 0}).to_list(200)
    return docs


@router.get("/duplicate-links")
async def duplicate_links(
    scope: str = Query("current", pattern="^(current|legacy)$"),
    user: dict = Depends(require_role("admin")),
):
    name = "duplicate_links_current" if scope == "current" else "historical_duplicate_links"
    docs = await coll(name).find({}, {"_id": 0}).limit(500).to_list(500)
    return docs


# --- Users management ----------------------------------------------------
@router.get("/users")
async def list_users(user: dict = Depends(require_role("admin"))):
    docs = await coll("users").find({}, {"_id": 0, "password_hash": 0}).to_list(200)
    return docs


@router.post("/users")
async def create_user(payload: dict, user: dict = Depends(require_role("admin"))):
    email = (payload.get("email") or "").lower().strip()
    if not email or not payload.get("password") or payload.get("role") not in ("admin", "consultant", "evaluator"):
        raise HTTPException(status_code=400, detail="بيانات ناقصة")
    existing = await coll("users").find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="البريد مستخدم مسبقاً")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": new_id(),
        "email": email,
        "password_hash": hash_password(payload["password"]),
        "name_ar": payload.get("name_ar") or email,
        "role": payload["role"],
        "person_id": payload.get("person_id"),
        "must_change_password": True,
        "created_at": now,
        "updated_at": now,
    }
    await coll("users").insert_one(doc)
    await coll("audit_log").insert_one({
        "user_email": user["email"],
        "user_id": user["id"],
        "action": "create_user",
        "entity": "user",
        "entity_key": doc["id"],
        "after": {"email": email, "role": payload["role"]},
        "created_at": now,
    })
    doc.pop("password_hash", None)
    doc.pop("_id", None)
    return doc


@router.patch("/users/{user_id}")
async def update_user(user_id: str, payload: dict, user: dict = Depends(require_role("admin"))):
    updates = {}
    for k in ("name_ar", "role", "person_id"):
        if k in payload:
            updates[k] = payload[k]
    if "password" in payload and payload["password"]:
        updates["password_hash"] = hash_password(payload["password"])
        updates["must_change_password"] = True
    if not updates:
        raise HTTPException(status_code=400, detail="No updates")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    res = await coll("users").update_one({"id": user_id}, {"$set": updates})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    await coll("audit_log").insert_one({
        "user_email": user["email"],
        "user_id": user["id"],
        "action": "update_user",
        "entity": "user",
        "entity_key": user_id,
        "after": {k: v for k, v in updates.items() if k != "password_hash"},
        "created_at": updates["updated_at"],
    })
    return {"ok": True}
