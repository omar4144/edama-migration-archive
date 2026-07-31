"""Participating organizations registry — manual review layer.

Aggregates candidates from all sources (Lovable current, legacy historical,
crosswalks, canonical families) and lets an admin mark each org's
participation_review_status. Never touches raw data.
"""
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from typing import Optional
from datetime import datetime, timezone

from auth import require_role
from db import coll, get_db

router = APIRouter(prefix="/participating-orgs", tags=["participating-orgs"])


STATUS_VALUES = {
    "PENDING_REVIEW", "CONFIRMED_PARTICIPANT", "EXCLUDED",
    "WITHDRAWN", "REPLACED", "DUPLICATE_CANDIDATE",
}
STATUS_AR = {
    "PENDING_REVIEW": "تحتاج مراجعة",
    "CONFIRMED_PARTICIPANT": "مشاركة مؤكدة",
    "EXCLUDED": "مستبعدة",
    "WITHDRAWN": "منسحبة",
    "REPLACED": "استبدلت",
    "DUPLICATE_CANDIDATE": "مشتبه تكرارها",
}


async def _seed_if_empty():
    """Materialize candidates from all sources on first read."""
    db = get_db()
    if await db.participating_orgs.count_documents({}) > 0:
        return
    docs = {}
    # Current-side orgs from Lovable
    async for r in coll("organizations_current").find({}, {"_id": 0}):
        oid = r.get("organization_id")
        if not oid: continue
        docs.setdefault(oid, {
            "org_id": oid, "canonical_name": r.get("organization_name"),
            "alt_names": set(), "sources": set(),
            "cohorts": set(), "linked_legacy_id": None,
        })
        docs[oid]["sources"].add("current")
        if r.get("organization_name"): docs[oid]["alt_names"].add(r["organization_name"])
    # Legacy orgs
    async for r in coll("historical_organizations").find({}, {"_id": 0}):
        oid = r.get("legacy_org_id") or r.get("organization_id")
        if not oid: continue
        docs.setdefault(oid, {
            "org_id": oid, "canonical_name": r.get("organization_name"),
            "alt_names": set(), "sources": set(),
            "cohorts": set(), "linked_legacy_id": None,
        })
        docs[oid]["sources"].add("legacy")
        if r.get("organization_name"): docs[oid]["alt_names"].add(r["organization_name"])
        if r.get("cohort"): docs[oid]["cohorts"].add(str(r["cohort"]))
    # Cohorts from legacy_arbitrations
    async for r in coll("historical_arbitrations").find(
        {}, {"legacy_org_id": 1, "cohort": 1, "organization_name": 1, "_id": 0}
    ):
        oid = r.get("legacy_org_id")
        if not oid: continue
        docs.setdefault(oid, {
            "org_id": oid, "canonical_name": r.get("organization_name"),
            "alt_names": set(), "sources": set(),
            "cohorts": set(), "linked_legacy_id": None,
        })
        docs[oid]["sources"].add("legacy")
        if r.get("cohort"): docs[oid]["cohorts"].add(str(r["cohort"]))
        if r.get("organization_name"): docs[oid]["alt_names"].add(r["organization_name"])
    # Crosswalk links (current ↔ legacy pairs)
    async for cw in coll("crosswalk_records").find(
        {"crosswalk_status": "MATCHED_ORG_AND_MODEL"},
        {"current_org_id": 1, "legacy_org_id": 1, "current_organization_name": 1, "_id": 0}
    ):
        coid = cw.get("current_org_id")
        loid = cw.get("legacy_org_id")
        if coid and coid in docs and loid:
            docs[coid]["linked_legacy_id"] = loid
            docs[coid]["sources"].add("crosswalk_matched")

    now = datetime.now(timezone.utc).isoformat()
    to_insert = []
    for d in docs.values():
        to_insert.append({
            "org_id": d["org_id"],
            "canonical_name": d["canonical_name"],
            "alt_names": sorted(d["alt_names"]),
            "sources": sorted(d["sources"]),
            "cohorts": sorted(d["cohorts"]),
            "linked_legacy_id": d["linked_legacy_id"],
            "participation_review_status": "PENDING_REVIEW",
            "participation_notes": None,
            "reviewed_by": None,
            "reviewed_at": None,
            "replaced_by_org_id": None,
            "duplicate_of_org_id": None,
            "created_at": now,
        })
    if to_insert:
        await coll("participating_orgs").insert_many(to_insert, ordered=False)
        await db.participating_orgs.create_index("org_id", unique=True)
        await db.participating_orgs.create_index([("participation_review_status", 1)])


async def _augment(rows: list) -> list:
    """Attach family counts + latest decision per org."""
    for r in rows:
        oid = r["org_id"]
        fam_total = await coll("canonical_submission_families").count_documents({"organization_id": oid})
        fam_review = await coll("canonical_submission_families").count_documents(
            {"organization_id": oid, "has_review_required": True})
        ver_total = await coll("canonical_submissions").count_documents({"organization_id": oid})
        r["families_count"] = fam_total
        r["families_review"] = fam_review
        r["versions_count"] = ver_total
        r["status_ar"] = STATUS_AR.get(r["participation_review_status"], r["participation_review_status"])
    return rows


@router.get("")
async def list_participating(
    q: Optional[str] = None,
    status: Optional[str] = None,
    cohort: Optional[str] = None,
    source: Optional[str] = None,   # current | legacy | crosswalk_matched
    has_families: Optional[bool] = None,
    limit: int = 200, offset: int = 0,
    user: dict = Depends(require_role("admin")),
):
    await _seed_if_empty()
    query: dict = {}
    if status: query["participation_review_status"] = status
    if cohort: query["cohorts"] = cohort
    if source: query["sources"] = source
    if q:
        query["$or"] = [
            {"canonical_name": {"$regex": q, "$options": "i"}},
            {"alt_names": {"$regex": q, "$options": "i"}},
            {"org_id": {"$regex": q, "$options": "i"}},
        ]

    counts = {}
    async for row in coll("participating_orgs").aggregate([
        {"$group": {"_id": "$participation_review_status", "c": {"$sum": 1}}}
    ]):
        counts[row["_id"]] = row["c"]

    total = await coll("participating_orgs").count_documents(query)
    docs = await coll("participating_orgs").find(query, {"_id": 0}) \
        .sort("canonical_name", 1).skip(offset).limit(min(limit, 500)).to_list(500)
    docs = await _augment(docs)

    if has_families is True:
        docs = [d for d in docs if d.get("families_count", 0) > 0]
    elif has_families is False:
        docs = [d for d in docs if d.get("families_count", 0) == 0]

    return {
        "total": total,
        "items": docs,
        "counts_by_status": counts,
        "counts_by_status_ar": {STATUS_AR.get(k, k): v for k, v in counts.items()},
        "official_confirmed_count": counts.get("CONFIRMED_PARTICIPANT", 0),
    }


@router.post("/{org_id}/decision")
async def apply_decision(
    org_id: str,
    body: dict = Body(...),
    user: dict = Depends(require_role("admin")),
):
    status = body.get("status")
    note = (body.get("note") or "").strip()
    replaced_by = body.get("replaced_by_org_id")
    duplicate_of = body.get("duplicate_of_org_id")

    if status not in STATUS_VALUES:
        raise HTTPException(400, f"Unknown status. Allowed: {sorted(STATUS_VALUES)}")
    if status in {"EXCLUDED", "WITHDRAWN"} and not note:
        raise HTTPException(400, "السبب إلزامي عند الاستبعاد أو تسجيل الانسحاب")
    if status == "REPLACED" and not replaced_by:
        raise HTTPException(400, "أدخل معرف الجهة البديلة")
    if status == "DUPLICATE_CANDIDATE" and not duplicate_of:
        raise HTTPException(400, "أدخل معرف الجهة التي يشتبه أنها الأصلية")

    doc = await coll("participating_orgs").find_one({"org_id": org_id})
    if not doc:
        raise HTTPException(404, "الجهة غير مسجلة في السجل")

    ts = datetime.now(timezone.utc).isoformat()
    prev = doc.get("participation_review_status")
    upd = {
        "participation_review_status": status,
        "participation_notes": note or None,
        "reviewed_by": user.get("email"),
        "reviewed_at": ts,
    }
    if status == "REPLACED":
        upd["replaced_by_org_id"] = replaced_by
    if status == "DUPLICATE_CANDIDATE":
        upd["duplicate_of_org_id"] = duplicate_of
    await coll("participating_orgs").update_one({"org_id": org_id}, {"$set": upd})

    await coll("review_audit_log").insert_one({
        "at": ts, "kind": "participating_org_decision",
        "actor_email": user.get("email"), "actor_id": user.get("id"),
        "org_id": org_id, "previous_status": prev, "new_status": status,
        "note": note, "payload": body,
    })
    return {"ok": True, "org_id": org_id, "status": status, "at": ts}


@router.post("/bulk-confirm")
async def bulk_confirm(
    body: dict = Body(...),
    user: dict = Depends(require_role("admin")),
):
    ids = body.get("org_ids") or []
    if not ids or not isinstance(ids, list):
        raise HTTPException(400, "org_ids مطلوبة كقائمة")
    ts = datetime.now(timezone.utc).isoformat()
    res = await coll("participating_orgs").update_many(
        {"org_id": {"$in": ids}},
        {"$set": {
            "participation_review_status": "CONFIRMED_PARTICIPANT",
            "reviewed_by": user.get("email"),
            "reviewed_at": ts,
        }},
    )
    await coll("review_audit_log").insert_one({
        "at": ts, "kind": "participating_org_bulk_confirm",
        "actor_email": user.get("email"), "actor_id": user.get("id"),
        "org_ids": ids, "count": res.modified_count,
    })
    return {"ok": True, "confirmed": res.modified_count, "at": ts}
