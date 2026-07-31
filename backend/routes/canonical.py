"""Canonical / deduplication endpoints (admin-only, read-only)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
import json

from auth import require_role
from db import coll

router = APIRouter(prefix="/canonical", tags=["canonical"])


@router.get("/report")
async def dedup_report(user: dict = Depends(require_role("admin"))):
    """Latest canonicalization report + summary + 20 sample match groups
    (including جمعية المشي والجري + بتول الرويلي)."""
    latest = await coll("dedup_reports").find_one({}, sort=[("generated_at", -1)])
    if not latest:
        raise HTTPException(status_code=404, detail="No dedup run yet — run build_canonical.py")
    latest.pop("_id", None)

    # -- Sample: 5 EXACT matches for بتول + Batool org + few others --
    samples = []
    # Batool org (ORG-A01-01, جمعية المشي والجري)
    batool_org = await coll("canonical_submissions").find(
        {"organization_id": "ORG-A01-01", "match_status": "EXACT_CROSS_SOURCE_MATCH"},
        {"_id": 0}
    ).limit(5).to_list(5)
    samples.extend(batool_org)
    # Batool as evaluator
    batool_eval = await coll("canonical_submissions").find(
        {"evaluator_name": "بتول الرويلي", "match_status": "EXACT_CROSS_SOURCE_MATCH",
         "organization_id": {"$ne": "ORG-A01-01"}},
        {"_id": 0}
    ).limit(5).to_list(5)
    samples.extend(batool_eval)
    # 5 samples of CURRENT_ONLY
    cur_only = await coll("canonical_submissions").find(
        {"match_status": "CURRENT_ONLY"}, {"_id": 0}
    ).limit(5).to_list(5)
    samples.extend(cur_only)
    # 5 samples of LEGACY_ONLY
    leg_only = await coll("canonical_submissions").find(
        {"match_status": "LEGACY_ONLY"}, {"_id": 0}
    ).limit(5).to_list(5)
    samples.extend(leg_only)

    # Enrich each sample with the raw member IDs from record_crosswalks
    enriched = []
    for s in samples:
        members = await coll("record_crosswalks").find(
            {"canonical_id": s["canonical_id"]}, {"_id": 0}).to_list(20)
        s["members"] = members
        enriched.append(s)

    # Match-status distribution
    by_status = await coll("canonical_submissions").aggregate([
        {"$group": {"_id": "$match_status", "count": {"$sum": 1}}}
    ]).to_list(20)

    return {
        "report": latest,
        "samples": enriched[:20],
        "by_match_status": {b["_id"]: b["count"] for b in by_status},
    }


@router.get("/submissions")
async def list_canonicals(
    org_id: Optional[str] = None,
    match_status: Optional[str] = None,
    limit: int = 50, offset: int = 0,
    user: dict = Depends(require_role("admin")),
):
    q: dict = {}
    if org_id: q["organization_id"] = org_id
    if match_status: q["match_status"] = match_status
    total = await coll("canonical_submissions").count_documents(q)
    docs = await coll("canonical_submissions").find(q, {"_id": 0}).skip(offset).limit(min(limit, 200)).to_list(200)
    return {"total": total, "items": docs}


@router.get("/submissions/{canonical_id}")
async def canonical_detail(canonical_id: str, user: dict = Depends(require_role("admin"))):
    doc = await coll("canonical_submissions").find_one({"canonical_id": canonical_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Canonical not found")
    members = await coll("record_crosswalks").find(
        {"canonical_id": canonical_id}, {"_id": 0}).to_list(50)
    doc["members"] = members
    return doc
