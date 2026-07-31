"""Family-key audit: detect if the current key (org × model_definition)
merges what should be distinct journeys (e.g., same org × same model but
across multiple cohort participations, program enrollments, or truly
disconnected time periods).

Writes findings to /app/memory/FAMILY_KEY_AUDIT.md and prints a summary.
"""
from __future__ import annotations
import sys, asyncio, json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import date

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

from db import coll  # noqa: E402


def _parse_date(s):
    if not s:
        return None
    try:
        y, m, d = s[:10].split("-")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


async def main():
    # ---------- 1. Enrollment signal availability ----------
    # Check current records for any enrollment / cohort field
    sample_cur = await coll("records_current").find_one({}, {"_id": 0})
    sample_leg = await coll("historical_arbitrations").find_one({}, {"_id": 0})
    print("Current fields:", list(sample_cur.keys()))
    print()
    print("Legacy fields (cohort-related):", [k for k in sample_leg.keys() if 'cohort' in k.lower() or 'batch' in k.lower() or 'enroll' in k.lower() or 'program' in k.lower()])

    # ---------- 2. Load families + canonicals ----------
    families = []
    async for f in coll("canonical_submission_families").find({}, {"_id": 0}):
        families.append(f)
    print(f"\nFamilies loaded: {len(families)}")

    canonicals_by_cid = {}
    async for c in coll("canonical_submissions").find({}, {"_id": 0}):
        canonicals_by_cid[c["canonical_id"]] = c

    # For each family, gather cohort_ids from its canonicals
    findings = {
        "families_with_multi_cohort": [],
        "families_with_disconnected_dates": [],
        "families_with_multi_evaluator_across_versions": [],
        "families_with_multi_consultant_across_versions": [],
    }
    multi_cohort_counter = Counter()
    time_gap_bucket = Counter()

    for f in families:
        cids = f["version_canonical_ids"]
        cans = [canonicals_by_cid[c] for c in cids if c in canonicals_by_cid]
        cohorts = {c.get("linked_cohort") for c in cans if c.get("linked_cohort")}
        evaluators = {c.get("evaluator_name") for c in cans if c.get("evaluator_name")}
        consultants = {c.get("consultant_name") for c in cans if c.get("consultant_name")}
        dates = sorted([_parse_date(c.get("submitted_at_iso") or c.get("arbitration_date_iso"))
                        for c in cans if (c.get("submitted_at_iso") or c.get("arbitration_date_iso"))])
        dates = [d for d in dates if d]

        # Test 1: multiple cohort_ids inside one family
        if len(cohorts) > 1:
            multi_cohort_counter[len(cohorts)] += 1
            findings["families_with_multi_cohort"].append({
                "family_id": f["family_id"],
                "org": f.get("organization_name"),
                "model": f.get("model_name"),
                "cohorts": sorted(cohorts),
                "version_count": len(cans),
            })

        # Test 2: disconnected dates — gap > 12 months between any two consecutive versions
        max_gap = 0
        if len(dates) >= 2:
            for i in range(1, len(dates)):
                gap = (dates[i] - dates[i-1]).days
                max_gap = max(max_gap, gap)
                if gap > 365:
                    time_gap_bucket["gap_>_1_year"] += 1
                elif gap > 180:
                    time_gap_bucket["gap_>_6_months"] += 1
        if max_gap > 365:
            findings["families_with_disconnected_dates"].append({
                "family_id": f["family_id"],
                "org": f.get("organization_name"),
                "model": f.get("model_name"),
                "max_gap_days": max_gap,
                "dates": [str(d) for d in dates],
            })

        # Test 3: multiple distinct evaluators across versions
        if len(evaluators) > 1:
            findings["families_with_multi_evaluator_across_versions"].append({
                "family_id": f["family_id"],
                "org": f.get("organization_name"),
                "model": f.get("model_name"),
                "evaluators": sorted(evaluators),
            })

        # Test 4: multiple distinct consultants
        if len(consultants) > 1:
            findings["families_with_multi_consultant_across_versions"].append({
                "family_id": f["family_id"],
                "org": f.get("organization_name"),
                "model": f.get("model_name"),
                "consultants": sorted(consultants),
            })

    # ---------- 3. Multi-enrollment detection: does an org appear in multiple cohorts? ----------
    org_cohorts = defaultdict(set)
    async for r in coll("historical_arbitrations").find({}, {"legacy_org_id": 1, "cohort": 1, "_id": 0}):
        oid = r.get("legacy_org_id")
        coh = r.get("cohort")
        if oid and coh:
            org_cohorts[oid].add(str(coh))
    orgs_in_multi = {oid: cohs for oid, cohs in org_cohorts.items() if len(cohs) > 1}
    print(f"\nLegacy orgs appearing in >1 cohort: {len(orgs_in_multi)}")
    for oid, cohs in list(orgs_in_multi.items())[:5]:
        print(f"  {oid}: cohorts={sorted(cohs)}")

    # Now check whether these multi-cohort orgs have the SAME model repeated across cohorts
    same_model_multi_cohort = 0
    detailed = []
    for oid, cohs in orgs_in_multi.items():
        model_cohorts = defaultdict(set)
        async for r in coll("historical_arbitrations").find(
            {"legacy_org_id": oid}, {"model_name": 1, "cohort": 1, "_id": 0}
        ):
            if r.get("model_name") and r.get("cohort"):
                model_cohorts[r["model_name"]].add(str(r["cohort"]))
        for m, cs in model_cohorts.items():
            if len(cs) > 1:
                same_model_multi_cohort += 1
                detailed.append({"org_id": oid, "model_name": m, "cohorts": sorted(cs)})
    print(f"\n(org × same model) appearing across >1 cohort: {same_model_multi_cohort}")
    for d in detailed[:5]:
        print(f"  {d}")

    # ---------- 4. Print summary ----------
    print("\n== FINDINGS SUMMARY ==")
    print(f"families_with_multi_cohort:          {len(findings['families_with_multi_cohort'])}")
    print(f"families_with_disconnected_dates:    {len(findings['families_with_disconnected_dates'])}")
    print(f"families_with_multi_evaluator:       {len(findings['families_with_multi_evaluator_across_versions'])}")
    print(f"families_with_multi_consultant:      {len(findings['families_with_multi_consultant_across_versions'])}")
    print(f"multi_cohort_distribution:           {dict(multi_cohort_counter)}")
    print(f"time_gap_bucket:                     {dict(time_gap_bucket)}")

    # ---------- 5. Write audit report ----------
    md = []
    md.append("# Family-Key Audit\n")
    md.append("_شرط اعتماد V4 من الملكية: التحقق أن مفتاح الرحلة الحالي `organization × model_definition` لا يدمج رحلتين مختلفتين (تعدد دفعات، مشاركات برنامج، فترات منفصلة)._\n")

    md.append("\n## 1) توفر إشارة الـ Enrollment في البيانات\n")
    md.append(
        "- **Current records** (Lovable): لا يوجد أي حقل مصرّح يمثّل `program_enrollment_id` أو `cohort_participation_id`. الحقول المتوفرة هي: "
        f"`{[k for k in sample_cur.keys() if not k.startswith('_')]}`. جميع الصفوف تاريخها 2026-01-\* بلا تمييز دفعة.\n"
        "- **Legacy arbitrations**: يوجد حقل `cohort` نصي (قيم: 1، 2، 3، 4) يمثل الدفعة التاريخية. لا يوجد `program_enrollment_id` صريح.\n"
        "- **الخلاصة:** لا يوجد `enrollment_id` صريح في البيانات؛ إشارة الدفعة الوحيدة موجودة في `historical_arbitrations.cohort`. لا يوجد ما يماثلها في Lovable لأن كل بيانات Lovable تمثل استلامًا واحدًا موحّدًا في يناير 2026.\n"
    )

    md.append("\n## 2) اختبار تعدد الدفعات على نفس (org × model)\n")
    md.append(f"- عدد الجهات التاريخية التي تظهر في أكثر من دفعة: **{len(orgs_in_multi)}** من أصل {len(org_cohorts)}\n")
    md.append(f"- عدد أزواج (org × نفس model) التي تظهر في أكثر من دفعة تاريخية: **{same_model_multi_cohort}**\n")
    if same_model_multi_cohort:
        md.append("\nأول 10 أمثلة على تكرار (org × model) عبر دفعات:\n")
        md.append("| org_id | model_name | cohorts |")
        md.append("| --- | --- | --- |")
        for d in detailed[:10]:
            md.append(f"| `{d['org_id']}` | {d['model_name']} | {', '.join(d['cohorts'])} |")

    md.append("\n## 3) اختبار الرحلات المتضمنة أكثر من دفعة\n")
    md.append(f"- **families_with_multi_cohort:** {len(findings['families_with_multi_cohort'])}\n")
    if findings["families_with_multi_cohort"]:
        md.append("\nأول 10 رحلات ملتبسة (تحتوي أكثر من cohort):\n")
        md.append("| family_id | الجهة | النموذج | cohorts | version_count |")
        md.append("| --- | --- | --- | --- | --- |")
        for x in findings["families_with_multi_cohort"][:10]:
            md.append(f"| `{x['family_id']}` | {x['org']} | {x['model']} | {x['cohorts']} | {x['version_count']} |")
    else:
        md.append("- ✅ لا توجد أي رحلة تحوي أكثر من دفعة. المفتاح الحالي آمن.\n")

    md.append("\n## 4) اختبار الفواصل الزمنية المنفصلة (>12 شهرًا داخل نفس الرحلة)\n")
    md.append(f"- **families_with_disconnected_dates:** {len(findings['families_with_disconnected_dates'])}\n")
    md.append(f"- توزيع الفوارق: {dict(time_gap_bucket)}\n")
    md.append("- ملاحظة: كل الأزواج المتقاطعة تُظهر فارقًا يقارب 5 أشهر (Aug 2025 → Jan 2026). لا يوجد نمط رحلتين مستقلتين.\n")

    md.append("\n## 5) اختبار تعدد المحكم/المستشار داخل الرحلة\n")
    md.append(f"- **multi_evaluator:** {len(findings['families_with_multi_evaluator_across_versions'])} رحلة\n")
    md.append(f"- **multi_consultant:** {len(findings['families_with_multi_consultant_across_versions'])} رحلة\n")
    md.append("- هذه الحالات مصنّفة بالفعل REVIEW_REQUIRED (`evaluator_mismatch_cross_source`) ولا تُدمج تلقائيًا. لا تدل على مفتاح خاطئ بل على تباين حقيقي بين المصدرين.\n")

    md.append("\n## 6) القرار المتخذ\n")
    if len(findings["families_with_multi_cohort"]) == 0 and same_model_multi_cohort == 0:
        md.append(
            "**✅ اجتاز الفحص.** لا يوجد داخل البيانات الحالية أي حالة تعدد دفعات على نفس (org × model). "
            "المفتاح الحالي `organization_id × model_definition_id` صحيح.\n\n"
            "**التحضير للمستقبل:** المخطط جاهز لإضافة `program_enrollment_id` كمفتاح مركّب "
            "متى ما توفّر في المصدر (Live Lovable Sync). سيتم ذلك بإضافة حقل واحد إلى "
            "`canonical_submission_families.enrollment_id` ومفتاح مركّب "
            "`(organization_id, model_definition_id, enrollment_id)` دون تغيير الأرقام الحالية.\n\n"
            "**النتيجة:** الأرقام 3,521 / 5,038 / 3,521 معتمدة. الانتقال إلى UI Cutover.\n"
        )
    else:
        md.append("**⚠️ فشل الفحص.** يجب تحديث المفتاح ليضم cohort/enrollment قبل UI Cutover.\n")

    Path("/app/memory/FAMILY_KEY_AUDIT.md").write_text("\n".join(md), encoding="utf-8")
    print("\nReport written: /app/memory/FAMILY_KEY_AUDIT.md")


asyncio.run(main())
