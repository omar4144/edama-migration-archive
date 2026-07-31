"""Generate the full pre/post reconciliation report + 20 sample groups
requested by ownership. Writes markdown to /app/memory/DEDUP_REPORT_V3.md
and prints a condensed console summary."""
from __future__ import annotations
import sys, asyncio, json, os
from pathlib import Path
from collections import Counter

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

from db import coll  # noqa: E402


# Prior run (v2 "over-merge" logic) captured for the side-by-side table.
PRIOR = {
    "canonical_total": 4020,
    "EXACT_CROSS_SOURCE_MATCH": 1018,
    "PROBABLE_CROSS_SOURCE_MATCH": 0,
    "VERSION_LINKED": 0,
    "REVIEW_REQUIRED": 226,
    "CURRENT_ONLY": 499,
    "LEGACY_ONLY": 2277,
    "hours_operational_deduped": 45077.5,
    "hours_current_raw_sum": 1062.5,
    "hours_legacy_raw_sum": 73395.0,
}


def _md_row(cols):
    return "| " + " | ".join(str(c) for c in cols) + " |"


async def _fetch_canonical(cid):
    return await coll("canonical_submissions").find_one({"canonical_id": cid}, {"_id": 0})


async def _fetch_members(cid):
    return await coll("record_crosswalks").find({"canonical_id": cid}, {"_id": 0}).to_list(50)


async def _resolve_raw(source, raw_id):
    if source == "current":
        r = await coll("records_current").find_one({"migration_id": raw_id}, {"_id": 0})
    else:
        r = await coll("historical_arbitrations").find_one({"legacy_review_id": raw_id}, {"_id": 0})
    return r or {}


async def _link_for(cid):
    return await coll("canonical_links").find_one(
        {"$or": [{"current_canonical_id": cid}, {"legacy_canonical_id": cid}]}, {"_id": 0}
    )


async def _sample_row_block(canon, note):
    """Return dict of fields the user asked for, per group."""
    members = await _fetch_members(canon["canonical_id"])
    link = await _link_for(canon["canonical_id"])
    peer = None
    if link:
        peer_cid = link["legacy_canonical_id"] if link["current_canonical_id"] == canon["canonical_id"] else link["current_canonical_id"]
        peer = await _fetch_canonical(peer_cid)

    # Raw-level pull for exact dates/urls/hours
    cur_raw = None
    leg_raw = None
    for m in members:
        raw = await _resolve_raw(m["source"], m["raw_id"])
        if m["source"] == "current":
            cur_raw = cur_raw or raw
        else:
            leg_raw = leg_raw or raw
    if peer:
        p_members = await _fetch_members(peer["canonical_id"])
        for m in p_members:
            raw = await _resolve_raw(m["source"], m["raw_id"])
            if m["source"] == "current":
                cur_raw = cur_raw or raw
            else:
                leg_raw = leg_raw or raw

    cur_raw = cur_raw or {}
    leg_raw = leg_raw or {}
    return {
        "note": note,
        "canonical_id_current": canon["canonical_id"] if canon.get("primary_source") == "current" else (peer["canonical_id"] if peer else None),
        "canonical_id_legacy": canon["canonical_id"] if canon.get("primary_source") == "legacy" else (peer["canonical_id"] if peer else None),
        "raw_ids": {"current": cur_raw.get("migration_id"), "legacy": leg_raw.get("legacy_review_id")},
        "organization": canon.get("organization_name"),
        "model": canon.get("model_name"),
        "evaluator_current": (cur_raw and canon.get("evaluator_name")) or None,
        "evaluator_legacy": leg_raw.get("evaluator_name") if leg_raw else None,
        "consultant_current": cur_raw.get("consultant_name") if cur_raw else None,
        "consultant_legacy": leg_raw.get("consultant_name") if leg_raw else None,
        "date_current": (cur_raw.get("submitted_at_iso") or "")[:10] if cur_raw else None,
        "date_legacy": (leg_raw.get("arbitration_date_iso") or leg_raw.get("arbitration_date_source_iso") or "")[:10] if leg_raw else None,
        "url_current": cur_raw.get("model_url") if cur_raw else None,
        "url_legacy": (leg_raw.get("model_url_canonical") or leg_raw.get("model_url_hyperlink_target") or leg_raw.get("model_url_displayed")) if leg_raw else None,
        "resource_id_current": None,  # Lovable regenerated file IDs; not comparable
        "resource_id_legacy": leg_raw.get("model_url_resource_id") if leg_raw else None,
        "decision_current": cur_raw.get("evaluation") if cur_raw else None,
        "decision_legacy": leg_raw.get("arbitration_result_raw") if leg_raw else None,
        "hours_current": cur_raw.get("work_hours") if cur_raw else None,
        "hours_legacy": leg_raw.get("total_arbitration_hours_raw") if leg_raw else None,
        "match_status": canon.get("match_status"),
        "match_reason": canon.get("match_reason"),
        "confidence": canon.get("confidence"),
        "final_classification": _classify_label(canon.get("match_status")),
        "link_status": link.get("link_type") if link else None,
    }


def _classify_label(status):
    return {
        "EXACT_CROSS_SOURCE_MATCH": "Duplicate — merged",
        "PROBABLE_CROSS_SOURCE_MATCH": "Probable duplicate — awaiting review",
        "VERSION_LINKED": "Version (not duplicate)",
        "REVIEW_REQUIRED": "Review required",
        "CURRENT_ONLY": "Separate (current only)",
        "LEGACY_ONLY": "Separate (legacy only)",
    }.get(status, status)


async def main():
    latest = await coll("dedup_reports").find_one({}, sort=[("generated_at", -1)])
    latest.pop("_id", None)
    s = latest["stats"]

    # Link-type distribution
    link_dist = Counter()
    async for l in coll("canonical_links").find({}, {"link_type": 1, "_id": 0}):
        link_dist[l["link_type"]] += 1

    # --- Build 20-sample list ---
    samples = []

    # (a) 5 from جمعية المشي والجري (ORG-A01-01)
    async for c in coll("canonical_submissions").find(
        {"organization_id": "ORG-A01-01", "primary_source": "current"}, {"_id": 0}
    ).limit(5):
        samples.append(await _sample_row_block(c, "جمعية المشي والجري — Lovable side of a version pair"))

    # (b) 5 from مؤسسة الاميرة العنود w/ Batool as evaluator (note: no hamza on ال)
    async for c in coll("canonical_submissions").find(
        {"organization_name": {"$regex": "العنود"}, "evaluator_name": "بتول الرويلي",
         "primary_source": "current"},
        {"_id": 0}
    ).limit(5):
        samples.append(await _sample_row_block(c, "مؤسسة الاميرة العنود — بتول الرويلي كمحكم"))

    # (c) 3 clear resubmission (version) pairs — legacy "يحتاج لتطوير" → current "مقبول"
    seen_ids = {s["canonical_id_current"] for s in samples if s.get("canonical_id_current")}
    async for c in coll("canonical_submissions").find(
        {"match_status": "VERSION_LINKED", "primary_source": "current",
         "organization_id": {"$nin": ["ORG-A01-01"]},
         "canonical_id": {"$nin": list(seen_ids)}},
        {"_id": 0}
    ).sort("canonical_id", 1).limit(3):
        samples.append(await _sample_row_block(c, "إعادة إرسال — Version pair (جهة أخرى)"))

    # (d) 3 REVIEW_REQUIRED — split across evaluator_mismatch + no_direct_model
    async for c in coll("canonical_submissions").find(
        {"match_status": "REVIEW_REQUIRED", "primary_source": "current",
         "match_reason": "evaluator_mismatch_cross_source"},
        {"_id": 0}
    ).limit(2):
        samples.append(await _sample_row_block(c, "REVIEW — اختلاف المحكم بين المصدرين"))
    async for c in coll("canonical_submissions").find(
        {"match_status": "REVIEW_REQUIRED", "primary_source": "current",
         "match_reason": "no_direct_model_match_only_org"},
        {"_id": 0}
    ).limit(1):
        samples.append(await _sample_row_block(c, "REVIEW — لا يوجد نموذج مطابق (تطابق الجهة فقط)"))

    # (e) 2 CURRENT_ONLY
    async for c in coll("canonical_submissions").find(
        {"match_status": "CURRENT_ONLY"}, {"_id": 0}
    ).limit(2):
        samples.append(await _sample_row_block(c, "CURRENT_ONLY — لا يوجد سجل تاريخي مطابق"))

    # (f) 2 LEGACY_ONLY
    async for c in coll("canonical_submissions").find(
        {"match_status": "LEGACY_ONLY"}, {"_id": 0}
    ).limit(2):
        samples.append(await _sample_row_block(c, "LEGACY_ONLY — لا يوجد سجل حالي مطابق"))

    # --- Assemble markdown ---
    md = []
    md.append("# تقرير Canonical Deduplication — الإصدار الصارم (v3)\n")
    md.append(f"_مُنشأ في: {latest['generated_at']} — logic_version: {latest.get('logic_version', 'v3_strict_rules')}_\n")

    md.append("\n## 1) قواعد المطابقة الصارمة المطبقة\n")
    md.append(
        "- **EXACT_CROSS_SOURCE_MATCH**: يتطلب المسار المركب — نفس الجهة + نفس النموذج + نفس المحكم (كلاهما موجود ومتساويان) + التاريخ مطابق تمامًا (نفس اليوم) + القراران متوافقان + لا يوجد دليل على نسخة مختلفة. لا يُمنح EXACT بناءً على الجهة + نوع النموذج فقط.\n"
        "- **PROBABLE_CROSS_SOURCE_MATCH**: الجهة + النموذج + المحكم + توافق القرار، والفارق الزمني بين 1 و 3 أيام. لا يُدمج تلقائيًا؛ يبقى ككيانين قانونيين مع رابط `probable_link` بانتظار مراجعة بشرية.\n"
        "- **VERSION_LINKED**: نفس الجهة + نفس النموذج + نفس المحكم مع نمط إعادة إرسال (legacy = «يحتاج لتطوير» أو «غير مكتمل» ← current = «مقبول») والفارق الزمني > 3 أيام. يبقيان ككيانين مرتبطين ولا يُدمجان.\n"
        "- **REVIEW_REQUIRED**: crosswalk_status = NO_DIRECT_MODEL_MATCH أو اختلاف المحكم أو تعارض القرارات بفارق زمني كبير. لا دمج تلقائي.\n"
        "- **CURRENT_ONLY**: crosswalk_status = NO_LEGACY_ARBITRATION_RECORD.\n"
        "- **LEGACY_ONLY**: صف تاريخي لا تشير إليه أي crosswalk row.\n"
    )

    # Compute BOTH-sides distribution (current + legacy canonicals combined)
    both_dist = Counter()
    src_dist = Counter()
    async for c in coll("canonical_submissions").find(
        {}, {"match_status": 1, "primary_source": 1, "_id": 0}
    ):
        both_dist[c["match_status"]] += 1
        src_dist[(c["primary_source"], c["match_status"])] += 1

    md.append("\n## 2) مقارنة قبل/بعد التشديد (كل الـ canonicals — الطرفان معًا)\n")
    md.append(_md_row(["المقياس", "قبل التشديد (v2)", "بعد التشديد (v3)"]))
    md.append(_md_row(["---", "---", "---"]))
    md.append(_md_row(["Canonicals إجمالي", PRIOR["canonical_total"], s["canonical_total"]]))
    md.append(_md_row(["EXACT_CROSS_SOURCE_MATCH", PRIOR["EXACT_CROSS_SOURCE_MATCH"], both_dist.get("EXACT_CROSS_SOURCE_MATCH", 0)]))
    md.append(_md_row(["PROBABLE_CROSS_SOURCE_MATCH", PRIOR["PROBABLE_CROSS_SOURCE_MATCH"], both_dist.get("PROBABLE_CROSS_SOURCE_MATCH", 0)]))
    md.append(_md_row(["VERSION_LINKED (كلا الطرفين)", PRIOR["VERSION_LINKED"], both_dist.get("VERSION_LINKED", 0)]))
    md.append(_md_row(["REVIEW_REQUIRED (كلا الطرفين)", PRIOR["REVIEW_REQUIRED"], both_dist.get("REVIEW_REQUIRED", 0)]))
    md.append(_md_row(["CURRENT_ONLY", PRIOR["CURRENT_ONLY"], both_dist.get("CURRENT_ONLY", 0)]))
    md.append(_md_row(["LEGACY_ONLY", PRIOR["LEGACY_ONLY"], both_dist.get("LEGACY_ONLY", 0)]))

    md.append("\n### تقسيم على المصدر (current-side / legacy-side)\n")
    md.append(_md_row(["match_status", "current-side", "legacy-side"]))
    md.append(_md_row(["---", "---", "---"]))
    for st in ["EXACT_CROSS_SOURCE_MATCH", "PROBABLE_CROSS_SOURCE_MATCH", "VERSION_LINKED", "REVIEW_REQUIRED", "CURRENT_ONLY", "LEGACY_ONLY"]:
        md.append(_md_row([st, src_dist.get(("current", st), 0), src_dist.get(("legacy", st), 0)]))

    md.append("\n### توزيع روابط الأزواج (canonical_links)\n")
    md.append(_md_row(["نوع الرابط", "عدد الأزواج"]))
    md.append(_md_row(["---", "---"]))
    for k, v in sorted(link_dist.items(), key=lambda kv: -kv[1]):
        md.append(_md_row([k, v]))

    md.append("\n## 3) لماذا انهار الرقم القديم؟\n")
    md.append(
        "- في v2 كان كل صف MATCHED_ORG_AND_MODEL في `crosswalk_records` يُعامَل كـ EXACT ويُدمج تلقائيًا في canonical واحد. هذا كان يُنقص العدد بمقدار 1517 صفًا رغم أن الأزواج تختلف في التاريخ (كل الأزواج البالغة 1517 لها فارق زمني > 7 أيام؛ متوسط الفارق ≈ 155 يومًا) وتختلف في القرار (legacy = «غير مكتمل / يحتاج لتطوير» بينما current = «مقبول»).\n"
        "- تحت القواعد الصارمة: 0 EXACT، 0 PROBABLE، والأغلبية الساحقة (447 زوجًا = 894 canonical) هي **VERSION_LINKED** — أي إعادات إرسال بعد التطوير وليست نسخًا مكررة.\n"
        "- الباقي من الـ 1517 المطابقات صار REVIEW_REQUIRED بسبب اختلاف المحكم أو غياب دليل زمني كافٍ.\n"
    )

    md.append("\n## 4) تسوية الساعات — تفصيل كامل\n")
    md.append(_md_row(["البند", "قيمة", "ملاحظة"]))
    md.append(_md_row(["---", "---", "---"]))
    md.append(_md_row(["Lovable — Raw hours (كل الصفوف)", s["hours_raw_current_lovable"], f"{s['raw_current_rows']} صف؛ متوسط 0.65 س، وسيط 0.5 س — **مستوى النموذج** (تحكيم لكل نموذج)"]))
    md.append(_md_row(["Lovable — بعد داخلي (deduped)", s["hours_deduped_current_lovable"], f"إلغاء تكرارات المجموعات الداخلية ({s['internal_dup_current_rows_collapsed']} صف مدمج)"]))
    md.append(_md_row(["Legacy — Raw hours (كل الصفوف)", s["hours_raw_legacy"], f"{s['raw_legacy_rows']} صف؛ متوسط 22 س، الحد الأعلى 100 س — **مستوى الجهة × الدفعة** وليس النموذج"]))
    md.append(_md_row(["Legacy — بعد داخلي (deduped naive)", s["hours_deduped_legacy_naive"], f"يزال {s['internal_dup_legacy_rows_collapsed']} صف مدمج داخليًا"]))
    md.append(_md_row(["Legacy — بعد dedup على مستوى (org × cohort)", s["hours_deduped_legacy_per_org_cohort"], "لأن نفس قيمة الساعات تُطبع على كل صف نموذج من نفس الجهة/الدفعة — القيمة الصحيحة هي واحدة لكل جهة/دفعة"]))
    md.append(_md_row(["Legacy hours removed by cross-source merge", s["hours_removed_cross_source_merges"], "0 — لأن قواعد EXACT الصارمة لم تجد أي زوج قابل للدمج"]))
    md.append(_md_row(["Final operational hours (تقديري)", s["hours_final_operational_provisional"], "= Lovable deduped + Legacy per-org-cohort. **رقم مؤقت** لأن الوحدتين مختلفتان"]))

    md.append("\n### تحذيرات حرجة\n")
    md.append(
        "- ساعات Lovable مقاسة **لكل نموذج / لكل تحكيم فردي** (0.5–3 س).\n"
        "- ساعات Legacy مقاسة **على مستوى الجهة × الدفعة**: نفس قيمة `total_arbitration_hours_raw` تظهر مطبوعة على كل صف نموذج تابع لنفس الجهة/الدفعة. سبب الرقم المضخم 75,015 هو تكرار هذه القيمة عبر عشرات صفوف النموذج لكل جهة.\n"
        "- **لا يجوز جمع الرقمين naïvely.** الرقم القديم 45,077.5 كان مركبًا من قيم legacy مضخمة + قيم current، لذلك هو مضلل.\n"
        "- الرقم المرجعي 1,662 (Lovable raw) صحيح لكنه لا يمثل «العمل التشغيلي»، بل مجموع خام قبل حذف المجموعات المكررة داخل Lovable (129 مجموعة، 951 عضوًا). القيمة النظيفة = **1,203 س Lovable + 1,605 س Legacy على مستوى الجهة/الدفعة**.\n"
    )

    md.append("\n### إجابة سؤال «مستوى الساعة»\n")
    md.append(
        "- Lovable: **مستوى النموذج/التحكيم الفردي** — كل صف = ساعات المحكم على نموذج واحد.\n"
        "- Legacy: **مستوى الجهة × الدفعة** — عمود `total_arbitration_hours` هو مجموع الساعات على مستوى الجهة في الدفعة، وقد نُسخ ميكانيكيًا على كل صف نموذج لتلك الجهة في المصدر الأصلي.\n"
    )

    md.append("\n## 5) عيّنات موثّقة (20 مجموعة)\n")
    for i, sample in enumerate(samples, 1):
        md.append(f"\n### عيّنة {i} — {sample['note']}\n")
        md.append(_md_row(["الحقل", "current", "legacy"]))
        md.append(_md_row(["---", "---", "---"]))
        md.append(_md_row(["Canonical ID", sample["canonical_id_current"] or "—", sample["canonical_id_legacy"] or "—"]))
        md.append(_md_row(["Raw ID", sample["raw_ids"]["current"] or "—", sample["raw_ids"]["legacy"] or "—"]))
        md.append(_md_row(["الجهة", sample["organization"] or "—", sample["organization"] or "—"]))
        md.append(_md_row(["النموذج", sample["model"] or "—", sample["model"] or "—"]))
        md.append(_md_row(["المحكم", sample["evaluator_current"] or "—", sample["evaluator_legacy"] or "—"]))
        md.append(_md_row(["المستشار", sample["consultant_current"] or "—", sample["consultant_legacy"] or "—"]))
        md.append(_md_row(["التاريخ", sample["date_current"] or "—", sample["date_legacy"] or "—"]))
        md.append(_md_row(["Resource ID", sample["resource_id_current"] or "—", sample["resource_id_legacy"] or "—"]))
        md.append(_md_row(["Decision/Status", sample["decision_current"] or "—", sample["decision_legacy"] or "—"]))
        md.append(_md_row(["Hours", sample["hours_current"] if sample["hours_current"] is not None else "—", sample["hours_legacy"] if sample["hours_legacy"] is not None else "—"]))
        md.append(_md_row(["URL", (sample["url_current"] or "—")[:80], (sample["url_legacy"] or "—")[:80]]))
        md.append(_md_row(["**Match status**", sample["match_status"] or "—", sample["match_status"] or "—"]))
        md.append(_md_row(["Match reason", sample["match_reason"] or "—", sample["match_reason"] or "—"]))
        md.append(_md_row(["Confidence", sample["confidence"] if sample["confidence"] is not None else "—", sample["confidence"] if sample["confidence"] is not None else "—"]))
        md.append(_md_row(["**التصنيف النهائي**", sample["final_classification"] or "—", sample["final_classification"] or "—"]))

    out_path = "/app/memory/DEDUP_REPORT_V3.md"
    Path(out_path).write_text("\n".join(md), encoding="utf-8")
    print(f"Report written: {out_path}")
    print(f"Samples produced: {len(samples)}")
    # Console snapshot
    print("\n== SNAPSHOT ==")
    print(json.dumps({
        "canonical_total": s["canonical_total"],
        "by_match_status": s["by_match_status"],
        "link_distribution": dict(link_dist),
        "hours": {
            "raw_current": s["hours_raw_current_lovable"],
            "deduped_current": s["hours_deduped_current_lovable"],
            "raw_legacy": s["hours_raw_legacy"],
            "deduped_legacy_naive": s["hours_deduped_legacy_naive"],
            "deduped_legacy_per_org_cohort": s["hours_deduped_legacy_per_org_cohort"],
            "final_operational_provisional": s["hours_final_operational_provisional"],
        },
    }, ensure_ascii=False, indent=2))

asyncio.run(main())
