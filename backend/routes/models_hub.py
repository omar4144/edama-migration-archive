"""Models & Arbitrations Hub — unified search across current + legacy."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from auth import require_role
from db import coll
from unified import unified_record, resolve_url

router = APIRouter(prefix="/models-hub", tags=["models-hub"])


@router.get("")
async def search(
    q: Optional[str] = None,
    org_id: Optional[str] = None,
    evaluator: Optional[str] = None,
    consultant: Optional[str] = None,
    model_id: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    evaluation: Optional[str] = None,
    cohort: Optional[str] = None,
    source: Optional[str] = Query(None, pattern="^(current|legacy)?$"),
    has_url: Optional[bool] = None,
    no_url: Optional[bool] = None,
    limit: int = 50, offset: int = 0,
    user: dict = Depends(require_role("admin")),
):
    include_current = source != "legacy"
    include_legacy = source != "current"

    # -- Current query --
    current_q: dict = {}
    if q:
        current_q["$or"] = [
            {"organization_name": {"$regex": q, "$options": "i"}},
            {"model_name": {"$regex": q, "$options": "i"}},
        ]
    if org_id: current_q["organization_id"] = org_id
    if model_id: current_q["model_definition_id"] = model_id
    if category: current_q["category"] = category
    if status: current_q["status"] = status
    if evaluation: current_q["evaluation"] = evaluation
    if has_url: current_q["model_url"] = {"$nin": [None, ""]}
    if no_url:
        current_q["$and"] = [{"$or": [{"model_url": None}, {"model_url": ""}]}]
    if consultant:
        p = await coll("people").find_one({"role": "consultant", "person_name": consultant})
        if p: current_q["consultant_person_id"] = p["person_id"]
        else: include_current = False
    if evaluator:
        p = await coll("people").find_one({"role": "evaluator", "person_name": evaluator})
        if p: current_q["evaluator_person_id"] = p["person_id"]
        else: include_current = False
    if cohort:
        # current records don't have cohort — filter via legacy crosswalk org set
        org_ids = [d["current_org_id"] for d in await coll("crosswalk_organizations").find(
            {"legacy_cohort": cohort}, {"current_org_id": 1, "_id": 0}).to_list(200)
                   if d.get("current_org_id")]
        if org_ids:
            current_q["organization_id"] = {"$in": org_ids}
        else:
            include_current = False

    # -- Legacy query --
    legacy_q: dict = {}
    if q:
        legacy_q["$or"] = [
            {"organization_name": {"$regex": q, "$options": "i"}},
            {"model_name": {"$regex": q, "$options": "i"}},
        ]
    if org_id:
        # try legacy id direct AND via crosswalk
        legacy_org_ids = [d["legacy_org_id"] for d in await coll("crosswalk_organizations").find(
            {"current_org_id": org_id}, {"legacy_org_id": 1, "_id": 0}).to_list(20)
                          if d.get("legacy_org_id")]
        legacy_q["legacy_org_id"] = {"$in": [org_id] + legacy_org_ids} if legacy_org_ids else org_id
    if category: legacy_q["category"] = category
    if evaluator: legacy_q["evaluator_name"] = evaluator
    if consultant: legacy_q["consultant_name"] = consultant
    if cohort: legacy_q["cohort"] = cohort
    if evaluation:
        legacy_q["$or"] = (legacy_q.get("$or") or []) + [
            {"arbitration_result": evaluation}, {"arbitration_result_raw": evaluation},
        ]
    if status: legacy_q["evaluation_status"] = status
    if has_url:
        legacy_q["$or"] = (legacy_q.get("$or") or []) + [
            {"model_url_canonical": {"$ne": None}}, {"model_url_hyperlink_target": {"$ne": None}},
            {"model_url": {"$ne": None}},
        ]

    total_current = await coll("records_current").count_documents(current_q) if include_current else 0
    total_legacy = await coll("historical_arbitrations").count_documents(legacy_q) if include_legacy else 0
    total = total_current + total_legacy

    # Fetch items — simple approach: current first then legacy (paginated across combined)
    items = []
    if include_current and offset < total_current:
        cursor = coll("records_current").find(current_q, {"_id": 0}) \
            .sort("submitted_at_iso", -1).skip(offset).limit(min(limit, 200))
        async for r in cursor:
            u = unified_record(r, "current")
            # Resolve evaluator name from person
            if r.get("evaluator_person_id"):
                p = await coll("people").find_one({"person_id": r["evaluator_person_id"]}, {"person_name": 1, "_id": 0})
                if p: u["evaluator_name"] = p.get("person_name")
            items.append(u)
    remaining = min(limit, 200) - len(items)
    if include_legacy and remaining > 0:
        skip = max(0, offset - total_current)
        cursor = coll("historical_arbitrations").find(legacy_q, {"_id": 0}) \
            .sort("arbitration_date_iso", -1).skip(skip).limit(remaining)
        async for r in cursor:
            items.append(unified_record(r, "legacy"))

    return {"total": total, "total_current": total_current, "total_legacy": total_legacy, "items": items}


@router.get("/{record_id}")
async def record_detail(record_id: str, user: dict = Depends(require_role("admin"))):
    # Try current first
    r = await coll("records_current").find_one({"migration_id": record_id})
    if r:
        r.pop("_id", None)
        u = unified_record(r, "current")
        if r.get("evaluator_person_id"):
            p = await coll("people").find_one({"person_id": r["evaluator_person_id"]}, {"_id": 0})
            if p: u["evaluator_name"] = p.get("person_name")
        # attach linked crosswalk info
        cw = await coll("crosswalk_records").find_one({"current_migration_id": record_id}, {"_id": 0})
        u["crosswalk"] = cw
        # duplicate group siblings
        if r.get("duplicate_link_group_id"):
            u["duplicate_group"] = await coll("duplicate_links_current").find_one(
                {"duplicate_link_group_id": r["duplicate_link_group_id"]}, {"_id": 0})
        return u
    # Try legacy
    r = await coll("historical_arbitrations").find_one({"legacy_review_id": record_id})
    if r:
        r.pop("_id", None)
        u = unified_record(r, "legacy")
        return u
    raise HTTPException(status_code=404, detail="Record not found")
