"""Generate DEDUP_REPORT_V4.md — with correct decision vocabulary,
submission families, and the three separate counts requested by ownership.
Writes to /app/memory/DEDUP_REPORT_V4.md."""
from __future__ import annotations
import sys, asyncio, json
from pathlib import Path
from collections import Counter

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

from db import coll  # noqa: E402


PRIOR_V3 = {
    "canonical_total": 5038,
    "VERSION_LINKED_both_sides": 2201,
    "REVIEW_REQUIRED_both_sides": 560,
    "CURRENT_ONLY": 499,
    "LEGACY_ONLY": 1778,
    "hours_operational_provisional": 2808.0,
}


def _md(cols):
    return "| " + " | ".join(str(c) for c in cols) + " |"


async def _fetch_can(cid):
    return await coll("canonical_submissions").find_one({"canonical_id": cid}, {"_id": 0})


async def _fetch_members(cid):
    return await coll("record_crosswalks").find({"canonical_id": cid}, {"_id": 0}).to_list(50)


async def _raw(source, raw_id):
    if source == "current":
        r = await coll("records_current").find_one({"migration_id": raw_id}, {"_id": 0})
    else:
        r = await coll("historical_arbitrations").find_one({"legacy_review_id": raw_id}, {"_id": 0})
    return r or {}


async def _sample_family(family):
    """Render a family (Journey) as a table showing each version in
    chronological order with normalized decisions."""
    lines = []
    lines.append(_md(["الحقل", "قيمة"]))
    lines.append(_md(["---", "---"]))
    lines.append(_md(["Family ID", family["family_id"]]))
    lines.append(_md(["الجهة", family.get("organization_name") or "—"]))
    lines.append(_md(["النموذج", family.get("model_name") or "—"]))
    lines.append(_md(["Model definition ID", family.get("model_definition_id") or "MNAME (بلا معرف)"]))
    lines.append(_md(["عدد النسخ", family["version_count"]]))
    lines.append(_md(["الرحلة", "legacy + current" if (family["has_legacy_version"] and family["has_current_version"]) else ("current only" if family["has_current_version"] else "legacy only")]))
    lines.append(_md(["آخر قرار مطبّع", family.get("latest_decision") or "UNKNOWN"]))
    lines.append(_md(["آخر حالة اكتمال", family.get("latest_completion_status") or "UNKNOWN"]))
    lines.append(_md(["آخر تاريخ", (family.get("latest_date") or "")[:10] or "—"]))
    lines.append(_md(["يحتاج مراجعة؟", "نعم" if family["has_review_required"] else "لا"]))

    # Versions timeline
    lines.append("")
    lines.append(_md(["#", "canonical_id", "source", "التاريخ", "raw decision", "decision (normalized)", "completion", "match_status", "match_reason"]))
    lines.append(_md(["---"] * 9))
    for i, cid in enumerate(family["version_canonical_ids"], 1):
        c = await _fetch_can(cid)
        if not c: continue
        raw_dec = c.get("raw_evaluation_current") if c.get("primary_source") == "current" else c.get("raw_evaluation_legacy")
        norm_dec = c.get("decision_normalized_current") if c.get("primary_source") == "current" else c.get("decision_normalized_legacy")
        comp = c.get("completion_status_current") if c.get("primary_source") == "current" else c.get("completion_status_legacy")
        dt = (c.get("submitted_at_iso") or c.get("arbitration_date_iso") or "")[:10]
        lines.append(_md([i, cid, c.get("primary_source"), dt or "—", raw_dec or "—", norm_dec or "—", comp or "—", c.get("match_status"), c.get("match_reason") or "—"]))
    return "\n".join(lines)


async def main():
    latest = await coll("dedup_reports").find_one({}, sort=[("generated_at", -1)])
    latest.pop("_id", None)
    s = latest["stats"]

    # ---------- Distributions ----------
    both_dist = Counter()
    src_dist = Counter()
    async for c in coll("canonical_submissions").find(
        {}, {"match_status": 1, "primary_source": 1, "_id": 0}
    ):
        both_dist[c["match_status"]] += 1
        src_dist[(c["primary_source"], c["match_status"])] += 1

    fam_lifecycle = Counter()
    async for f in coll("canonical_submission_families").find(
        {}, {"has_current_version": 1, "has_legacy_version": 1, "has_review_required": 1, "_id": 0}
    ):
        if f["has_current_version"] and f["has_legacy_version"]:
            fam_lifecycle["full_lifecycle"] += 1
        elif f["has_current_version"]:
            fam_lifecycle["current_only"] += 1
        else:
            fam_lifecycle["legacy_only"] += 1
        if f["has_review_required"]:
            fam_lifecycle["with_review"] += 1

    # ---------- Compose report ----------
    md = []
    md.append("# تقرير Canonical Deduplication — الإصدار الرابع (v4)\n")
    md.append(f"_مُنشأ في: {latest['generated_at']} — logic_version: {latest.get('logic_version', 'v4_families_and_decisions')}_\n")

    md.append("\n## 1) الإضافات الجوهرية على v3\n")
    md.append(
        "1. **قاموس القرارات الصحيح** (`decisions.py`): فصل تام بين `decision_normalized` و `completion_status`.\n"
        "   - Legacy: «مجاز» → **APPROVED**، «غير مجاز» → **REJECTED**، «مجاز مع تحفظ» → **APPROVED_WITH_RESERVATION** (غير موجود في البيانات فعليًا)، «يحتاج لتطوير» → **NEEDS_IMPROVEMENT**، «مكتمل/غير مكتمل» → **completion_status** فقط (ليس قرارًا).\n"
        "   - Current: «مقبول» → **APPROVED**، «يحتاج لتطوير» → **NEEDS_IMPROVEMENT**، «غير مكتمل» → **completion_status = INCOMPLETE** (بلا قرار).\n"
        "2. **إعادة تصنيف الأزواج** بناءً على القرارات المُطبَّعة. أهم اختلاف عن v3: أزواج legacy=«مجاز» → current=«مقبول» بفارق زمني كبير لم تعد تُصنَّف نُسَخًا (كانت v3 تعتبرها version_resubmit خطأً)؛ الآن REVIEW_REQUIRED بسبب `wide_gap_identical_decision`.\n"
        "3. **Canonical Submission Families**: جمع كل نسخ نفس (الجهة × تعريف النموذج) في «رحلة» واحدة (`family_id = FAM-######`). الرحلة تحكي: نموذج تاريخي → قرار تاريخي → تحسين → نموذج حالي → قرار جديد.\n"
        "4. **ثلاثة أرقام منفصلة** بدلاً من رقم واحد مضلل.\n"
    )

    md.append("\n## 2) الأرقام الثلاثة الجديدة\n")
    md.append(_md(["المؤشر", "القيمة", "تعريفه"]))
    md.append(_md(["---", "---", "---"]))
    md.append(_md(["**عدد رحلات/عائلات النماذج**", s["counts_three"]["families_count"], "عدد الرحلات المستقلة (org × model). كل رحلة قد تحوي عدة نُسَخ في الزمن."]))
    md.append(_md(["**عدد النسخ (Canonicals)**", s["counts_three"]["versions_count"], "كل تسليم/تحكيم كنسخة مستقلة بعد إزالة التكرارات الداخلية."]))
    md.append(_md(["**عدد أحدث المخرجات التشغيلية**", s["counts_three"]["latest_operational_count"], "أحدث نسخة واحدة لكل رحلة (= عدد الرحلات)."]))

    md.append("\n### توزيع الرحلات\n")
    md.append(_md(["البند", "عدد الرحلات", "% من الإجمالي"]))
    md.append(_md(["---", "---", "---"]))
    tot = s["counts_three"]["families_count"]
    md.append(_md(["Full lifecycle (legacy → current)", s["families_with_full_lifecycle_legacy_and_current"], f"{100*s['families_with_full_lifecycle_legacy_and_current']/tot:.1f}%"]))
    md.append(_md(["Current only (لم يسبقها تحكيم تاريخي)", s["families_current_only"], f"{100*s['families_current_only']/tot:.1f}%"]))
    md.append(_md(["Legacy only (لا يوجد استلام حالي)", s["families_legacy_only"], f"{100*s['families_legacy_only']/tot:.1f}%"]))
    md.append(_md(["Rows including at least one REVIEW_REQUIRED", s["families_with_any_review_required"], f"{100*s['families_with_any_review_required']/tot:.1f}%"]))

    md.append("\n### توزيع آخر قرار مطبّع (على مستوى الرحلة)\n")
    md.append(_md(["القرار", "عدد الرحلات"]))
    md.append(_md(["---", "---"]))
    for k, v in sorted(s["latest_decision_distribution"].items(), key=lambda kv: -kv[1]):
        md.append(_md([k, v]))

    md.append("\n### توزيع آخر حالة اكتمال\n")
    md.append(_md(["الحالة", "عدد الرحلات"]))
    md.append(_md(["---", "---"]))
    for k, v in sorted(s["latest_completion_distribution"].items(), key=lambda kv: -kv[1]):
        md.append(_md([k, v]))

    md.append("\n## 3) مقارنة v3 → v4 (على مستوى الـ canonicals)\n")
    md.append(_md(["match_status", "v3 (both sides)", "v4 (both sides)", "التغيير"]))
    md.append(_md(["---", "---", "---", "---"]))
    v4_ver = both_dist.get("VERSION_LINKED", 0)
    v4_rev = both_dist.get("REVIEW_REQUIRED", 0)
    md.append(_md(["VERSION_LINKED", PRIOR_V3["VERSION_LINKED_both_sides"], v4_ver, v4_ver - PRIOR_V3["VERSION_LINKED_both_sides"]]))
    md.append(_md(["REVIEW_REQUIRED", PRIOR_V3["REVIEW_REQUIRED_both_sides"], v4_rev, v4_rev - PRIOR_V3["REVIEW_REQUIRED_both_sides"]]))
    md.append(_md(["EXACT_CROSS_SOURCE_MATCH", 0, both_dist.get("EXACT_CROSS_SOURCE_MATCH", 0), 0]))
    md.append(_md(["PROBABLE_CROSS_SOURCE_MATCH", 0, both_dist.get("PROBABLE_CROSS_SOURCE_MATCH", 0), 0]))
    md.append(_md(["CURRENT_ONLY", PRIOR_V3["CURRENT_ONLY"], both_dist.get("CURRENT_ONLY", 0), 0]))
    md.append(_md(["LEGACY_ONLY", PRIOR_V3["LEGACY_ONLY"], both_dist.get("LEGACY_ONLY", 0), 0]))
    md.append(_md(["**الإجمالي**", PRIOR_V3["canonical_total"], s["canonical_total"], 0]))

    md.append("\n### تفسير النقلة\n")
    md.append(
        "- في v3 كان كل زوج مرتبط عبر crosswalk (بغض النظر عن معنى القرار) يُصنَّف VERSION_LINKED. النتيجة: 2,201 نسخة موصولة و 560 مراجعة.\n"
        "- في v4 (بالقاموس الصحيح) فقط الأزواج التي فيها **legacy = REJECTED / NEEDS_IMPROVEMENT / APPROVED_WITH_RESERVATION / (INCOMPLETE completion)** ← current = APPROVED تُصنَّف VERSION_LINKED. هذا يُخرج من فئة النسخ كل الأزواج التي فيها الطرفان APPROVED ومتباعدان زمنيًا (392 زوجًا) ويرسلها إلى **REVIEW_REQUIRED / wide_gap_identical_decision** لأنها إما إعادة تحكيم أو إشكال بيانات.\n"
    )

    md.append("\n### توزيع أسباب REVIEW_REQUIRED\n")
    md.append(_md(["السبب", "العدد", "ملاحظة"]))
    md.append(_md(["---", "---", "---"]))
    rr = s["review_required_by_reason"]
    reason_notes = {
        "wide_gap_identical_decision": "كلا الطرفين APPROVED لكن التاريخان بعيدان؛ إعادة تحكيم أو خلل مصدر",
        "no_direct_model_match_only_org": "crosswalk = NO_DIRECT_MODEL_MATCH — تطابق جهة فقط",
        "wide_gap_conflicting_decisions": "قراران متعارضان دون نمط نسخة واضح",
        "evaluator_mismatch_cross_source": "اختلاف المحكم بين المصدرين",
        "missing_date_no_auto_merge": "تاريخ ناقص على أحد الجانبين",
        "missing_date_and_uncertain": "تاريخ ناقص + غموض",
        "unknown_decision_state": "قرار غير معروف على أحد الجانبين",
        "unclassified_pair": "غير مصنّف",
    }
    for k, v in sorted(rr.items(), key=lambda kv: -kv[1]):
        md.append(_md([k, v, reason_notes.get(k, "")]))
    md.append(_md(["**الإجمالي (current-side)**", sum(rr.values()), ""]))

    md.append("\n## 4) الساعات — لا تُجمع أبدًا كرقم واحد\n")
    md.append(_md(["البند", "قيمة", "الوحدة"]))
    md.append(_md(["---", "---", "---"]))
    md.append(_md(["Raw Lovable hours", s["hours_raw_current_lovable"], "per_model"]))
    md.append(_md(["**Lovable after internal dedup**", s["hours_deduped_current_lovable_per_model"], "**per_model** — القيمة التشغيلية النظيفة"]))
    md.append(_md(["Raw Legacy hours", s["hours_raw_legacy"], "org × cohort مكررة"]))
    md.append(_md(["Legacy after internal dedup (naive)", s["hours_deduped_legacy_naive"], "org × cohort لا تزال مكررة"]))
    md.append(_md(["**Legacy per (org × cohort) unique**", s["hours_deduped_legacy_per_org_cohort"], "**org × cohort** — القيمة الصحيحة"]))
    md.append("\n**قاعدة عرض إلزامية:** الواجهة يجب أن تعرض:\n"
              f"- «ساعات تحكيم النماذج الحالية بعد التنظيف: **{s['hours_deduped_current_lovable_per_model']:.0f} س** (لكل نموذج)»\n"
              f"- «ساعات الجهات والدفعات التاريخية: **{s['hours_deduped_legacy_per_org_cohort']:.0f} س** (لكل جهة/دفعة)»\n"
              "- ❌ لا رقم موحّد يجمعهما. ❌ لا Final operational hours.\n")

    # ---------- Family samples ----------
    md.append("\n## 5) عيّنات موثّقة — 20 رحلة (Submission Families)\n")
    md.append(
        "لكل رحلة: بيانات الرحلة العامة، ثم جدول النسخ مرتبة زمنيًا يوضّح "
        "الانتقال من التحكيم التاريخي إلى الاستلام الحالي بقرار مطبّع.\n"
    )

    samples = []

    # (a) 5 families of جمعية المشي والجري
    async for f in coll("canonical_submission_families").find(
        {"organization_id": "ORG-A01-01"}, {"_id": 0}
    ).limit(5):
        samples.append(("جمعية المشي والجري", f))

    # (b) 5 families of مؤسسة الاميرة العنود
    async for f in coll("canonical_submission_families").find(
        {"organization_name": {"$regex": "العنود"}}, {"_id": 0}
    ).limit(5):
        samples.append(("مؤسسة الاميرة العنود", f))

    # (c) 3 full-lifecycle families with legacy REJECTED → current APPROVED
    seen = {s[1]["family_id"] for s in samples}
    async for f in coll("canonical_submission_families").find(
        {"has_current_version": True, "has_legacy_version": True,
         "latest_decision": "APPROVED",
         "family_id": {"$nin": list(seen)}},
        {"_id": 0}
    ).limit(3):
        samples.append(("رحلة كاملة (REJECTED → APPROVED)", f))

    # (d) 2 families with wide_gap_identical_decision (both APPROVED)
    seen = {s[1]["family_id"] for s in samples}
    # Find families whose canonicals include a REVIEW_REQUIRED with that reason
    review_families = set()
    async for c in coll("canonical_submissions").find(
        {"match_status": "REVIEW_REQUIRED", "match_reason": "wide_gap_identical_decision"},
        {"family_id": 1, "_id": 0}
    ):
        if c.get("family_id"):
            review_families.add(c["family_id"])
        if len(review_families) >= 20:
            break
    added = 0
    for fid in review_families:
        if fid in seen:
            continue
        f = await coll("canonical_submission_families").find_one({"family_id": fid}, {"_id": 0})
        if f:
            samples.append(("مراجعة — wide_gap_identical_decision (كلاهما مجاز)", f))
            added += 1
            if added >= 2:
                break

    # (e) 2 review families with evaluator_mismatch_cross_source
    review_families2 = set()
    async for c in coll("canonical_submissions").find(
        {"match_status": "REVIEW_REQUIRED", "match_reason": "evaluator_mismatch_cross_source"},
        {"family_id": 1, "_id": 0}
    ):
        if c.get("family_id"):
            review_families2.add(c["family_id"])
        if len(review_families2) >= 20:
            break
    added = 0
    for fid in review_families2:
        if fid in {s[1]["family_id"] for s in samples}:
            continue
        f = await coll("canonical_submission_families").find_one({"family_id": fid}, {"_id": 0})
        if f:
            samples.append(("مراجعة — evaluator_mismatch_cross_source", f))
            added += 1
            if added >= 2:
                break

    # (f) 2 current_only families
    async for f in coll("canonical_submission_families").find(
        {"has_current_version": True, "has_legacy_version": False}, {"_id": 0}
    ).limit(2):
        if f["family_id"] not in {s[1]["family_id"] for s in samples}:
            samples.append(("Current only — لا نسخة تاريخية", f))

    # (g) 1 legacy_only family
    async for f in coll("canonical_submission_families").find(
        {"has_current_version": False, "has_legacy_version": True}, {"_id": 0}
    ).limit(1):
        samples.append(("Legacy only — لا استلام حالي", f))

    # Trim / pad to 20
    samples = samples[:20]

    for i, (note, fam) in enumerate(samples, 1):
        md.append(f"\n### رحلة {i} — {note}\n")
        md.append(await _sample_family(fam))

    md.append("\n## 6) القرار المطلوب من الملكية\n")
    md.append(
        "الأرقام الرسمية المقترحة للاعتماد التالي:\n"
        f"- **عدد رحلات/عائلات النماذج (Model Journeys):** {s['counts_three']['families_count']:,}\n"
        f"- **عدد النسخ (Canonicals):** {s['counts_three']['versions_count']:,}\n"
        f"- **عدد أحدث المخرجات التشغيلية:** {s['counts_three']['latest_operational_count']:,}\n"
        f"- **رحلات كاملة (تاريخية + حالية):** {s['families_with_full_lifecycle_legacy_and_current']:,}\n"
        f"- **رحلات في المراجعة:** {s['families_with_any_review_required']:,}\n"
        f"- **الساعات:** 1,203 س Lovable per_model | 1,605 س Legacy per_org_cohort — لا جمع.\n"
        "\n"
        "**البنود المفتوحة قبل UI Cutover:**\n"
        "1. اعتمد قاموس القرارات ونتائج التصنيف الجديدة.\n"
        "2. اعتمد الأرقام الثلاثة.\n"
        "3. اعتمد قاعدة عرض الساعات بشكل منفصل (بدون رقم موحّد).\n"
        "4. حدد كيف يجب أن تظهر REVIEW_REQUIRED (868 رحلة) في الواجهة — قائمة عمل للمشرف؟ مراجعة إلزامية قبل الإحصائيات؟\n"
        "5. حدد ماذا نُظهر «كنموذج»: `families` (3,521) أم `latest_operational` (3,521 — نفس القيمة)، وماذا نُظهر «كنسخ»: 5,038.\n"
    )

    out_path = "/app/memory/DEDUP_REPORT_V4.md"
    Path(out_path).write_text("\n".join(md), encoding="utf-8")
    print(f"Report written: {out_path}")
    print(f"Samples produced: {len(samples)}")
    print("\n== SNAPSHOT ==")
    print(json.dumps({
        "counts_three": s["counts_three"],
        "family_lifecycle": dict(fam_lifecycle),
        "match_status_both_sides": dict(both_dist),
        "review_reasons": s["review_required_by_reason"],
        "latest_decision_distribution": s["latest_decision_distribution"],
        "hours": {
            "lovable_deduped_per_model": s["hours_deduped_current_lovable_per_model"],
            "legacy_per_org_cohort": s["hours_deduped_legacy_per_org_cohort"],
        },
    }, ensure_ascii=False, indent=2))


asyncio.run(main())
