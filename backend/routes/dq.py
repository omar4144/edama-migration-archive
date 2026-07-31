"""Data Quality Center — drilldowns for the 16 quality checks + 108 sources."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional

from auth import require_role
from db import coll

router = APIRouter(prefix="/dq", tags=["dq"])


@router.get("/summary")
async def summary(user: dict = Depends(require_role("admin"))):
    """Live quality signals derived from the imported archive."""
    # Static checks table (from quality_checks.csv)
    checks = await coll("quality_checks").find({}, {"_id": 0}).to_list(200)

    # Additional live signals derived from real data
    async def _cnt(name, q):
        return await coll(name).count_documents(q)

    signals = [
        {"id": "template_metadata_stale",
         "label": "بيانات قالب تحكيم تاريخية مشبوهة",
         "affected": await _cnt("historical_arbitrations", {"metadata_status": "STALE_OR_MISMATCHED_TEMPLATE_METADATA"}),
         "severity": "HIGH",
         "action": "الاعتماد على الحقول الموثوقة (اسم الملف/الورقة) بدل قيم القالب."},
        {"id": "template_metadata_consistent",
         "label": "سجلات تحكيم تاريخية اجتازت فحص القالب",
         "affected": await _cnt("historical_arbitrations", {"metadata_status": "CONSISTENT"}),
         "severity": "OK", "action": "لا يوجد إجراء مطلوب."},
        {"id": "activity_name_variant",
         "label": "أنشطة باسم جهة مختلف عن الاسم المعياري",
         "affected": await _cnt("historical_activities", {"source_name_status": "NAME_VARIANT"}),
         "severity": "MEDIUM",
         "action": "الاسم المطبّع هو المرجع؛ القيمة الخام محفوظة كما وردت."},
        {"id": "activity_row_sheet_mismatch",
         "label": "أنشطة اسم جهة الصف ≠ اسم ورقة العمل",
         "affected": await _cnt("historical_activities", {"source_name_status": "ROW_SHEET_MISMATCH"}),
         "severity": "MEDIUM",
         "action": "الاسم المشتق من اسم الورقة هو المعتمد."},
        {"id": "arbitration_no_metadata_check",
         "label": "سجلات تحكيم بدون فحص اتساق قالب",
         "affected": await _cnt("historical_arbitrations", {"metadata_status": None}),
         "severity": "LOW", "action": "مراجعة يدوية إن لزم."},
        {"id": "current_records_no_legacy",
         "label": "سجلات حالية بلا نظير تاريخي",
         "affected": await coll("crosswalk_records").count_documents({"crosswalk_status": "NO_LEGACY_ARBITRATION_RECORD"}),
         "severity": "LOW", "action": "متوقع لبعض النماذج الجديدة."},
        {"id": "current_records_no_model",
         "label": "سجلات حالية بلا مطابقة نموذج مباشرة",
         "affected": await coll("crosswalk_records").count_documents({"crosswalk_status": "NO_DIRECT_MODEL_MATCH"}),
         "severity": "MEDIUM", "action": "مرشحة لقائمة المراجعة."},
    ]

    sources_total = await coll("source_inventory").count_documents({})
    return {"checks": checks, "signals": signals, "sources_total": sources_total}


@router.get("/sources")
async def sources(
    role: Optional[str] = None,
    scope: Optional[str] = None,
    user: dict = Depends(require_role("admin")),
):
    q: dict = {}
    if role:
        q["source_role"] = role
    if scope:
        q["migration_scope"] = scope
    docs = await coll("source_inventory").find(q, {"_id": 0}).limit(500).to_list(500)
    return docs


@router.get("/affected/{signal_id}")
async def affected(
    signal_id: str,
    limit: int = 50, offset: int = 0,
    user: dict = Depends(require_role("admin")),
):
    """Drill-down: real rows affected by a signal."""
    mapping = {
        "template_metadata_stale": ("historical_arbitrations",
                                    {"metadata_status": "STALE_OR_MISMATCHED_TEMPLATE_METADATA"}),
        "template_metadata_consistent": ("historical_arbitrations",
                                          {"metadata_status": "CONSISTENT"}),
        "activity_name_variant": ("historical_activities", {"source_name_status": "NAME_VARIANT"}),
        "activity_row_sheet_mismatch": ("historical_activities", {"source_name_status": "ROW_SHEET_MISMATCH"}),
        "arbitration_no_metadata_check": ("historical_arbitrations", {"metadata_status": None}),
        "current_records_no_legacy": ("crosswalk_records", {"crosswalk_status": "NO_LEGACY_ARBITRATION_RECORD"}),
        "current_records_no_model": ("crosswalk_records", {"crosswalk_status": "NO_DIRECT_MODEL_MATCH"}),
    }
    if signal_id not in mapping:
        raise HTTPException(status_code=404, detail="Signal not found")
    collection, q = mapping[signal_id]
    total = await coll(collection).count_documents(q)
    docs = await coll(collection).find(q, {"_id": 0}).skip(offset).limit(min(limit, 200)).to_list(200)
    return {"total": total, "items": docs, "collection": collection}
