"""Canonical / dedup endpoints (admin-only) — powered by canonical_submissions
+ canonical_submission_families (v4 families + decisions build)."""
from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional
from datetime import datetime, timezone

from auth import require_role
from db import coll

router = APIRouter(prefix="/canonical", tags=["canonical"])


# -- Arabic label maps used by the UI badges --
REASON_AR = {
    "wide_gap_identical_decision": "قراران متطابقان بفارق زمني كبير — يحتاج مراجعة",
    "auto_approved_identical_after_wide_gap": "معتمد تلقائيًا — تطابق كامل رغم فارق التاريخ",
    "wide_gap_conflicting_decisions": "قراران متعارضان — يحتاج مراجعة",
    "evaluator_mismatch_cross_source": "اختلاف المحكم بين المصدرين",
    "auto_linked_evaluator_reassignment": "معتمد تلقائيًا — إعادة تكليف محكم",
    "resubmission_version_resubmit_evaluator_reassigned": "إعادة إرسال بعد الرفض/الحاجة للتطوير مع إعادة تكليف محكم",
    "resubmission_completion_then_result_evaluator_reassigned": "استكمال ثم قرار مع إعادة تكليف محكم",
    "close_dates_compatible_decisions_evaluator_reassigned": "تواريخ متقاربة وقرارات متوافقة مع إعادة تكليف محكم",
    "no_direct_model_match_only_org": "تطابق الجهة فقط دون نموذج مطابق",
    "missing_date_no_auto_merge": "تاريخ ناقص — لا دمج تلقائي",
    "missing_date_and_uncertain": "تاريخ ناقص وغموض في القرار",
    "unknown_decision_state": "قرار غير معروف",
    "unclassified_pair": "زوج غير مصنّف",
    "orphaned_after_pair_link": "طرف بلا نظير",
    "no_legacy_arbitration_record": "لا يوجد تحكيم تاريخي",
    "no_current_lovable_peer": "لا يوجد استلام حالي مطابق",
    "resubmission_version_resubmit": "إعادة إرسال بعد الرفض/الحاجة للتطوير",
    "resubmission_completion_then_result": "استكمال ثم قرار",
    "composite_path_same_date_same_decision": "مطابقة كاملة — نفس اليوم ونفس القرار",
    "close_dates_compatible_decisions": "تواريخ متقاربة وقرارات متوافقة",
    "internal_lovable_duplicate_group": "تكرار داخلي (Lovable)",
    "internal_legacy_duplicate_group": "تكرار داخلي (تاريخي)",
    "no_crosswalk_row_fallback": "لا يوجد صف crosswalk — احتياطي",
    "archive_org_and_model_matched": "الجهة والنموذج متطابقان",
}


DECISION_AR = {
    "APPROVED": "معتمد", "REJECTED": "مرفوض",
    "APPROVED_WITH_RESERVATION": "معتمد بتحفظ",
    "NEEDS_IMPROVEMENT": "يحتاج تطوير",
    "PENDING": "معلّق", "UNKNOWN": "غير محدد",
    None: "غير محدد",
}

STATUS_AR = {
    "EXACT_CROSS_SOURCE_MATCH": "تطابق كامل",
    "PROBABLE_CROSS_SOURCE_MATCH": "تطابق محتمل",
    "VERSION_LINKED": "نسخ مرتبطة",
    "REVIEW_REQUIRED": "تحتاج مراجعة",
    "CURRENT_ONLY": "حالي فقط",
    "LEGACY_ONLY": "تاريخي فقط",
}


@router.get("/exec-scene")
async def exec_scene(user: dict = Depends(require_role("admin"))):
    """Executive Scene v4 — families / versions / latest outputs, hours split."""
    # Terminology counts
    model_types = await coll("model_definitions").count_documents({})
    families_total = await coll("canonical_submission_families").count_documents({})
    versions_total = await coll("canonical_submissions").count_documents({})

    # Latest-decision distribution across families
    latest_dec = {}
    async for row in coll("canonical_submission_families").aggregate([
        {"$group": {"_id": "$latest_decision", "c": {"$sum": 1}}}
    ]):
        latest_dec[row["_id"] or "UNKNOWN"] = row["c"]

    # Review-required breakdown
    review_by_reason = {}
    async for row in coll("canonical_submissions").aggregate([
        {"$match": {"match_status": "REVIEW_REQUIRED", "primary_source": "current"}},
        {"$group": {"_id": "$match_reason", "c": {"$sum": 1}}}
    ]):
        review_by_reason[row["_id"] or "unknown"] = row["c"]

    review_families = await coll("canonical_submission_families").count_documents({"has_review_required": True})

    # Family lifecycle
    fam_full = await coll("canonical_submission_families").count_documents(
        {"has_current_version": True, "has_legacy_version": True})
    fam_current_only = await coll("canonical_submission_families").count_documents(
        {"has_current_version": True, "has_legacy_version": False})
    fam_legacy_only = await coll("canonical_submission_families").count_documents(
        {"has_current_version": False, "has_legacy_version": True})

    # Hours (two separate meters, never summed)
    latest = await coll("dedup_reports").find_one({}, sort=[("generated_at", -1)]) or {}
    hstats = latest.get("stats", {}) if latest else {}

    # Cohorts strip (from legacy)
    cohorts = []
    for c in ["1", "2", "3", "4"]:
        c_orgs = await coll("historical_organizations").count_documents({"cohort": c})
        c_arb = await coll("historical_arbitrations").count_documents({"cohort": c})
        cohorts.append({"cohort": c, "organizations": c_orgs, "arbitrations": c_arb})

    return {
        "terminology": {
            "model_types": model_types,             # 45
            "model_journeys": families_total,       # 3521
            "versions_submissions": versions_total, # 5038
            "latest_outputs": families_total,       # 3521
            "approved_journeys": latest_dec.get("APPROVED", 0),   # 2366
            "review_required_journeys": review_families,          # 868
            "needs_improvement_journeys": latest_dec.get("NEEDS_IMPROVEMENT", 0),  # 35
            "pending_journeys": latest_dec.get("PENDING", 0),     # 138
            "rejected_journeys": latest_dec.get("REJECTED", 0),   # 947
            "hours_current_per_model": hstats.get("hours_deduped_current_lovable_per_model", 1203.0),
            "hours_legacy_per_org_cohort": hstats.get("hours_deduped_legacy_per_org_cohort", 1605.0),
        },
        "family_lifecycle": {
            "full_lifecycle": fam_full,
            "current_only": fam_current_only,
            "legacy_only": fam_legacy_only,
        },
        "review_by_reason": review_by_reason,
        "review_by_reason_ar": {REASON_AR.get(k, k): v for k, v in review_by_reason.items()},
        "cohorts": cohorts,
        "logic_version": latest.get("logic_version") if latest else None,
    }


@router.get("/families")
async def list_families(
    org_id: Optional[str] = None,
    evaluator: Optional[str] = None,
    latest_decision: Optional[str] = None,
    has_review: Optional[bool] = None,
    lifecycle: Optional[str] = None,  # full / current_only / legacy_only
    limit: int = 100, offset: int = 0,
    user: dict = Depends(require_role("admin")),
):
    q: dict = {}
    if org_id: q["organization_id"] = org_id
    if evaluator: q["latest_evaluator_name"] = evaluator
    if latest_decision: q["latest_decision"] = latest_decision
    if has_review is not None: q["has_review_required"] = has_review
    if lifecycle == "full": q.update({"has_current_version": True, "has_legacy_version": True})
    elif lifecycle == "current_only": q.update({"has_current_version": True, "has_legacy_version": False})
    elif lifecycle == "legacy_only": q.update({"has_current_version": False, "has_legacy_version": True})

    total = await coll("canonical_submission_families").count_documents(q)
    fams = await coll("canonical_submission_families").find(q, {"_id": 0}) \
        .sort("family_id", 1).skip(offset).limit(min(limit, 500)).to_list(500)
    # Enrich with Arabic labels
    for f in fams:
        f["latest_decision_ar"] = DECISION_AR.get(f.get("latest_decision"), "غير محدد")
    return {"total": total, "items": fams}


@router.get("/families/{family_id}")
async def family_detail(family_id: str, user: dict = Depends(require_role("admin"))):
    fam = await coll("canonical_submission_families").find_one({"family_id": family_id}, {"_id": 0})
    if not fam:
        raise HTTPException(status_code=404, detail="Family not found")

    versions = []
    for cid in fam.get("version_canonical_ids", []):
        c = await coll("canonical_submissions").find_one({"canonical_id": cid}, {"_id": 0})
        if not c:
            continue
        members = await coll("record_crosswalks").find({"canonical_id": cid}, {"_id": 0}).to_list(10)
        c["raw_members"] = members
        c["match_reason_ar"] = REASON_AR.get(c.get("match_reason"), c.get("match_reason"))
        c["match_status_ar"] = STATUS_AR.get(c.get("match_status"), c.get("match_status"))
        raw_dec = (c.get("decision_normalized_current") or c.get("decision_normalized_legacy"))
        c["decision_ar"] = DECISION_AR.get(raw_dec, "غير محدد")
        versions.append(c)

    # Sort versions chronologically
    def _k(x):
        return (x.get("submitted_at_iso") or x.get("arbitration_date_iso") or "", x.get("canonical_id"))
    versions.sort(key=_k)

    fam["versions"] = versions
    fam["latest_decision_ar"] = DECISION_AR.get(fam.get("latest_decision"), "غير محدد")
    return fam


@router.get("/review-queue")
async def review_queue(
    reason: Optional[str] = None,
    limit: int = 100, offset: int = 0,
    user: dict = Depends(require_role("admin")),
):
    """Families that contain at least one REVIEW_REQUIRED canonical, filterable
    by the REVIEW reason."""
    # Find families whose canonicals include the target reason
    match_can = {"match_status": "REVIEW_REQUIRED"}
    if reason:
        match_can["match_reason"] = reason
    fam_ids = set()
    async for c in coll("canonical_submissions").find(match_can, {"family_id": 1, "_id": 0}):
        if c.get("family_id"):
            fam_ids.add(c["family_id"])
    fam_ids = list(fam_ids)
    total = len(fam_ids)

    # By-reason counts (independent of filter for the chip counts)
    counts_by_reason = {}
    async for row in coll("canonical_submissions").aggregate([
        {"$match": {"match_status": "REVIEW_REQUIRED"}},
        {"$group": {"_id": "$match_reason", "c": {"$sum": 1}}}
    ]):
        counts_by_reason[row["_id"] or "unknown"] = row["c"]

    fams = await coll("canonical_submission_families").find(
        {"family_id": {"$in": fam_ids[offset:offset + min(limit, 500)]}}, {"_id": 0}
    ).sort("family_id", 1).to_list(500)
    for f in fams:
        f["latest_decision_ar"] = DECISION_AR.get(f.get("latest_decision"), "غير محدد")

    return {
        "total": total,
        "items": fams,
        "counts_by_reason": counts_by_reason,
        "counts_by_reason_ar": {k: {"reason_ar": REASON_AR.get(k, k), "count": v}
                                for k, v in counts_by_reason.items()},
    }


@router.post("/review-queue/{family_id}/decision")
async def apply_review_decision(
    family_id: str,
    body: dict = Body(...),
    user: dict = Depends(require_role("admin")),
):
    """Apply a review decision to a family. Never mutates raw source_records.
    Actions supported: link_as_versions | keep_separate | select_evaluator |
    select_model | defer | reopen.
    """
    action = body.get("action")
    note = body.get("note") or ""
    allowed = {"link_as_versions", "keep_separate", "select_evaluator",
               "select_model", "defer", "reopen"}
    if action not in allowed:
        raise HTTPException(400, f"Unknown action. Allowed: {sorted(allowed)}")
    fam = await coll("canonical_submission_families").find_one({"family_id": family_id})
    if not fam:
        raise HTTPException(404, "Family not found")

    ts = datetime.now(timezone.utc).isoformat()
    audit = {
        "at": ts, "actor_email": user.get("email"), "actor_id": user.get("id"),
        "family_id": family_id, "action": action, "note": note,
        "payload": body,
    }
    await coll("review_audit_log").insert_one(audit)

    # Update family: mark decision-applied and clear/keep review flag as instructed.
    resolved = action in {"link_as_versions", "keep_separate", "select_evaluator", "select_model"}
    update = {"$set": {
        "review_action": action,
        "review_action_at": ts,
        "review_action_by": user.get("email"),
        "review_note": note,
    }}
    if resolved:
        update["$set"]["has_review_required"] = False
    if action == "reopen":
        update["$set"]["has_review_required"] = True
    await coll("canonical_submission_families").update_one({"family_id": family_id}, update)

    # Mirror the resolution flag onto member canonicals (does NOT touch raw).
    if resolved:
        await coll("canonical_submissions").update_many(
            {"family_id": family_id, "match_status": "REVIEW_REQUIRED"},
            {"$set": {"review_action": action, "review_action_at": ts,
                      "review_action_by": user.get("email")}},
        )

    return {"ok": True, "family_id": family_id, "action": action, "at": ts}


@router.get("/report")
async def dedup_report(user: dict = Depends(require_role("admin"))):
    latest = await coll("dedup_reports").find_one({}, sort=[("generated_at", -1)])
    if not latest:
        raise HTTPException(status_code=404, detail="No dedup run yet")
    latest.pop("_id", None)
    by_status = await coll("canonical_submissions").aggregate([
        {"$group": {"_id": "$match_status", "count": {"$sum": 1}}}
    ]).to_list(20)
    return {
        "report": latest,
        "by_match_status": {b["_id"]: b["count"] for b in by_status},
    }


@router.get("/submissions")
async def list_canonicals(
    org_id: Optional[str] = None,
    match_status: Optional[str] = None,
    family_id: Optional[str] = None,
    limit: int = 50, offset: int = 0,
    user: dict = Depends(require_role("admin")),
):
    q: dict = {}
    if org_id: q["organization_id"] = org_id
    if match_status: q["match_status"] = match_status
    if family_id: q["family_id"] = family_id
    total = await coll("canonical_submissions").count_documents(q)
    docs = await coll("canonical_submissions").find(q, {"_id": 0}) \
        .skip(offset).limit(min(limit, 200)).to_list(200)
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
