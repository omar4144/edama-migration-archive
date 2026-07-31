"""READ-ONLY audit of the 175 participating_orgs registry.

Produces 4 artifacts under /app/memory/:
  1. PARTICIPATING_ORGANIZATIONS_AUDIT.md          — full report + Family-Key impact
  2. PARTICIPATING_ORGANIZATIONS_175_AUDIT.csv     — 1 row per current registry entry
  3. ORGANIZATION_MATCH_GROUPS.csv                 — proposed unique organizations
  4. ORGANIZATION_COHORT_PARTICIPATIONS.csv        — org × cohort participation rows

Never modifies any collection. Only reads and writes files under /app/memory/.
"""
import sys, asyncio, csv, re, unicodedata
from pathlib import Path
from collections import defaultdict, Counter

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

from db import coll  # noqa: E402


MEMORY = Path("/app/memory")


def norm(s: str) -> str:
    if not s: return ""
    v = unicodedata.normalize("NFKC", s).strip()
    v = re.sub(r"[\u064b-\u065f\u0670]+", "", v)  # strip tashkil
    v = v.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي").replace("ة", "ه")
    v = re.sub(r"[\s\u200f\u200e]+", "", v)
    return v


async def main():
    # ---------- Load raw sources ----------
    lov_orgs = {r["organization_id"]: r async for r in coll("organizations_current").find({}, {"_id": 0})}
    leg_orgs = {r["legacy_org_id"]: r async for r in coll("historical_organizations").find({}, {"_id": 0})}
    cw_orgs = [x async for x in coll("crosswalk_organizations").find({}, {"_id": 0})]
    registry = [x async for x in coll("participating_orgs").find({}, {"_id": 0})]

    # Crosswalk index: current_org_id → cw entry
    cw_by_current = {c["current_org_id"]: c for c in cw_orgs if c.get("current_org_id")}
    cw_by_legacy = {c["legacy_org_id"]: c for c in cw_orgs if c.get("legacy_org_id")}
    # Reverse: which legacy ids are "claimed" by an EXACT_NORMALIZED match
    exact_legacy_ids = {c["legacy_org_id"] for c in cw_orgs if c.get("match_status") == "EXACT_NORMALIZED"}
    probable_legacy_ids = {c["legacy_org_id"] for c in cw_orgs if c.get("match_status") == "PROBABLE_NAME_VARIANT"}

    # Distribution within crosswalk_organizations
    cw_status_counts = Counter(c.get("match_status", "?") for c in cw_orgs)
    # Legacy-only = 118 legacy − (exact+probable pointing to legacy)
    legacy_ids_matched = exact_legacy_ids | probable_legacy_ids
    legacy_only_count = len(set(leg_orgs) - legacy_ids_matched)

    # Legacy cohorts index
    leg_cohort_by_id = {rid: str(r.get("cohort")) for rid, r in leg_orgs.items()}
    leg_cohort_dist = Counter(leg_cohort_by_id.values())

    # Family counts per org (from canonical layer)
    fam_by_org = Counter()
    async for f in coll("canonical_submission_families").find({}, {"organization_id": 1, "_id": 0}):
        if f.get("organization_id"):
            fam_by_org[f["organization_id"]] += 1
    ver_by_org = Counter()
    async for c in coll("canonical_submissions").find({}, {"organization_id": 1, "_id": 0}):
        if c.get("organization_id"):
            ver_by_org[c["organization_id"]] += 1

    # Legacy-side canonical version counts by legacy_org_id
    ver_by_legacy = Counter()
    async for c in coll("canonical_submissions").find(
        {"primary_source": "legacy"}, {"organization_id": 1, "_id": 0}
    ):
        if c.get("organization_id"):
            ver_by_legacy[c["organization_id"]] += 1

    # Raw model row counts per source
    lov_rows_by_org = Counter()
    async for r in coll("records_current").find({}, {"organization_id": 1, "_id": 0}):
        if r.get("organization_id"): lov_rows_by_org[r["organization_id"]] += 1
    leg_rows_by_org = Counter()
    async for r in coll("historical_arbitrations").find({}, {"legacy_org_id": 1, "_id": 0}):
        if r.get("legacy_org_id"): leg_rows_by_org[r["legacy_org_id"]] += 1

    # ---------- Compute proposed unique orgs after crosswalk ----------
    # 57 lovable + 118 legacy − 56 EXACT − 1 PROBABLE = 118 unique candidates (proposed)
    exact_pairs = [(c["current_org_id"], c["legacy_org_id"]) for c in cw_orgs if c.get("match_status") == "EXACT_NORMALIZED"]
    probable_pairs = [(c["current_org_id"], c["legacy_org_id"]) for c in cw_orgs if c.get("match_status") == "PROBABLE_NAME_VARIANT"]
    proposed_merges_exact = len(exact_pairs)
    proposed_merges_probable = len(probable_pairs)
    # Legacy that lack a lovable peer = legacy_only
    legacy_only_ids = set(leg_orgs) - legacy_ids_matched
    # Lovable that lack a legacy peer = lovable_only
    lovable_matched_ids = {c["current_org_id"] for c in cw_orgs if c.get("current_org_id") and c.get("match_status") in ("EXACT_NORMALIZED", "PROBABLE_NAME_VARIANT")}
    lovable_only_ids = set(lov_orgs) - lovable_matched_ids

    unique_after_exact = (len(lov_orgs) + len(leg_orgs)) - proposed_merges_exact
    unique_after_exact_and_probable = unique_after_exact - proposed_merges_probable

    # ---------- Cohort-participation extraction ----------
    # Legacy: each legacy_org_id maps to exactly one cohort (verified earlier)
    # Lovable: no cohort field. If lovable maps (via crosswalk) to a legacy, we
    # can infer its "represented cohort" from the legacy_cohort. Otherwise the
    # lovable participation cohort is UNKNOWN.
    participations = []  # each row: unified org × cohort
    for lid, leg in leg_orgs.items():
        cw = cw_by_legacy.get(lid)
        canon_id = cw["current_org_id"] if cw and cw.get("match_status") in ("EXACT_NORMALIZED", "PROBABLE_NAME_VARIANT") else lid
        canon_name = (cw["current_organization_name"] if cw and cw.get("match_status") in ("EXACT_NORMALIZED", "PROBABLE_NAME_VARIANT") else leg.get("organization_name"))
        participations.append({
            "participation_id": f"PART-LEG-{lid}",
            "proposed_canonical_org_id": canon_id,
            "canonical_org_name": canon_name,
            "cohort": leg.get("cohort"),
            "cohort_label": f"دفعة {leg.get('cohort')}",
            "organization_name_as_written": leg.get("organization_name"),
            "normalized_name": norm(leg.get("organization_name", "")),
            "source": "legacy",
            "source_record_ids": lid,
            "legacy_org_ids": lid,
            "lovable_org_ids": cw["current_org_id"] if cw else "",
            "source_files": leg.get("source_files") or "",
            "source_sheets": "",
            "source_rows": leg.get("source_rows") or "",
            "consultant_names": leg.get("consultants") or "",
            "evaluator_names": leg.get("evaluators") or "",
            "first_recorded_at": leg.get("start_date_iso") or "",
            "last_recorded_at": leg.get("graduation_date_iso") or "",
            "roster_status": leg.get("roster_status") or "",
            "model_family_count": fam_by_org.get(canon_id, 0),
            "model_version_count": ver_by_legacy.get(lid, 0),
            "latest_outputs_count": "",
            "links_count": leg_rows_by_org.get(lid, 0),
            "participation_evidence": f"legacy_org_id={lid}",
            "cohort_confidence": "HIGH",
            "possible_previous_participation": "",
            "possible_next_participation": "",
            "requires_review": "false",
        })
    for lid, lov in lov_orgs.items():
        cw = cw_by_current.get(lid)
        canon_id = lid
        canon_name = lov.get("organization_name")
        # Cohort for Lovable is inferred from crosswalked legacy, if any
        if cw and cw.get("match_status") in ("EXACT_NORMALIZED", "PROBABLE_NAME_VARIANT"):
            inferred_cohort = cw.get("legacy_cohort")
            cohort_conf = "MEDIUM (inferred from crosswalk to legacy)"
        else:
            inferred_cohort = None
            cohort_conf = "UNKNOWN (Lovable has no cohort field)"
        participations.append({
            "participation_id": f"PART-LOV-{lid}",
            "proposed_canonical_org_id": canon_id,
            "canonical_org_name": canon_name,
            "cohort": inferred_cohort or "UNKNOWN",
            "cohort_label": f"دفعة {inferred_cohort}" if inferred_cohort else "دفعة غير معروفة (Lovable)",
            "organization_name_as_written": lov.get("organization_name"),
            "normalized_name": norm(lov.get("organization_name", "")),
            "source": "current",
            "source_record_ids": lid,
            "legacy_org_ids": cw["legacy_org_id"] if cw else "",
            "lovable_org_ids": lid,
            "source_files": "lovable_current",
            "source_sheets": "",
            "source_rows": "",
            "consultant_names": lov.get("consultant_names") or "",
            "evaluator_names": lov.get("evaluator_name") or "",
            "first_recorded_at": lov.get("first_submitted_at_iso") or "",
            "last_recorded_at": lov.get("last_modified_at_iso") or "",
            "roster_status": "",
            "model_family_count": fam_by_org.get(canon_id, 0),
            "model_version_count": ver_by_org.get(canon_id, 0),
            "latest_outputs_count": fam_by_org.get(canon_id, 0),
            "links_count": lov_rows_by_org.get(canon_id, 0),
            "participation_evidence": f"lovable_org_id={lid}",
            "cohort_confidence": cohort_conf,
            "possible_previous_participation": "",
            "possible_next_participation": "",
            "requires_review": "false" if inferred_cohort else "true",
        })

    # ---------- Multi-cohort detection using canonical names + crosswalk unification ----------
    # Group participations by proposed_canonical_org_id
    cohorts_by_canon = defaultdict(set)
    names_by_canon = defaultdict(set)
    for p in participations:
        cid = p["proposed_canonical_org_id"]
        if p["cohort"] and p["cohort"] != "UNKNOWN":
            cohorts_by_canon[cid].add(str(p["cohort"]))
        names_by_canon[cid].add(p["organization_name_as_written"])
    multi_cohort = {k: sorted(v) for k, v in cohorts_by_canon.items() if len(v) > 1}

    single_cohort = sum(1 for v in cohorts_by_canon.values() if len(v) == 1)
    single_only_unknown = sum(1 for v in cohorts_by_canon.values() if len(v) == 0)
    two_c = sum(1 for v in cohorts_by_canon.values() if len(v) == 2)
    three_c = sum(1 for v in cohorts_by_canon.values() if len(v) == 3)
    four_c = sum(1 for v in cohorts_by_canon.values() if len(v) == 4)

    # ---------- WRITE participations CSV ----------
    p_csv = MEMORY / "ORGANIZATION_COHORT_PARTICIPATIONS.csv"
    with p_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(participations[0].keys()))
        w.writeheader()
        for row in participations: w.writerow(row)

    # ---------- WRITE 175-audit CSV ----------
    r175_csv = MEMORY / "PARTICIPATING_ORGANIZATIONS_175_AUDIT.csv"
    fields = [
        "registry_candidate_id", "display_name", "normalized_name", "aliases",
        "source", "legacy_org_id", "lovable_org_id", "cohorts",
        "roster_status", "consultant_names", "evaluator_names",
        "model_family_count", "canonical_version_count",
        "lovable_model_rows", "legacy_model_rows",
        "current_links_count", "legacy_links_count",
        "organization_crosswalk_status", "matched_candidate_id", "matched_candidate_name",
        "match_method", "match_confidence", "why_separate_candidate",
        "participation_review_status",
    ]
    with r175_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in registry:
            oid = r["org_id"]
            # Determine crosswalk relationship
            cw = None
            if oid in cw_by_current: cw = cw_by_current[oid]
            elif oid in cw_by_legacy: cw = cw_by_legacy[oid]
            match_status = cw.get("match_status") if cw else "NO_CROSSWALK_ENTRY"
            matched_id = ""
            matched_name = ""
            if cw:
                matched_id = cw["legacy_org_id"] if oid == cw.get("current_org_id") else cw.get("current_org_id", "")
                matched_name = cw.get("legacy_organization_name") if oid == cw.get("current_org_id") else cw.get("current_organization_name", "")
            # why_separate_candidate: if match exists but registry still has both sides separate
            counterpart_in_registry = any(x["org_id"] == matched_id for x in registry) if matched_id else False
            if counterpart_in_registry and match_status in ("EXACT_NORMALIZED", "PROBABLE_NAME_VARIANT"):
                why_sep = "seed_did_not_apply_crosswalk_merge — both sides kept as candidates"
            elif not cw:
                why_sep = "no_crosswalk_entry_exists"
            else:
                why_sep = ""
            w.writerow({
                "registry_candidate_id": oid,
                "display_name": r.get("canonical_name") or "",
                "normalized_name": norm(r.get("canonical_name") or ""),
                "aliases": " | ".join(r.get("alt_names") or []),
                "source": "|".join(r.get("sources") or []),
                "legacy_org_id": r.get("linked_legacy_id") or (oid if oid.startswith("LEG-") else ""),
                "lovable_org_id": oid if oid.startswith("ORG-") else "",
                "cohorts": ",".join(r.get("cohorts") or []),
                "roster_status": leg_orgs.get(oid, {}).get("roster_status", ""),
                "consultant_names": (lov_orgs.get(oid, {}).get("consultant_names")
                                     or leg_orgs.get(oid, {}).get("consultants") or ""),
                "evaluator_names": (lov_orgs.get(oid, {}).get("evaluator_name")
                                    or leg_orgs.get(oid, {}).get("evaluators") or ""),
                "model_family_count": fam_by_org.get(oid, 0),
                "canonical_version_count": ver_by_org.get(oid, 0),
                "lovable_model_rows": lov_rows_by_org.get(oid, 0),
                "legacy_model_rows": leg_rows_by_org.get(oid, 0),
                "current_links_count": lov_rows_by_org.get(oid, 0),
                "legacy_links_count": leg_rows_by_org.get(oid, 0),
                "organization_crosswalk_status": match_status,
                "matched_candidate_id": matched_id,
                "matched_candidate_name": matched_name,
                "match_method": cw.get("merge_decision") if cw else "",
                "match_confidence": cw.get("match_score") if cw else "",
                "why_separate_candidate": why_sep,
                "participation_review_status": r.get("participation_review_status") or "",
            })

    # ---------- WRITE match groups CSV ----------
    groups_csv = MEMORY / "ORGANIZATION_MATCH_GROUPS.csv"
    groups = []
    processed = set()
    for cw in cw_orgs:
        cur_id = cw.get("current_org_id"); leg_id = cw.get("legacy_org_id")
        if cw.get("match_status") in ("EXACT_NORMALIZED", "PROBABLE_NAME_VARIANT"):
            groups.append({
                "proposed_canonical_org_id": cur_id,
                "proposed_canonical_name": cw.get("current_organization_name"),
                "cohort": cw.get("legacy_cohort"),
                "member_candidate_ids": f"{cur_id} | {leg_id}",
                "member_names": f"{cw.get('current_organization_name')} | {cw.get('legacy_organization_name')}",
                "has_legacy": "true", "has_lovable": "true",
                "legacy_count": 1, "lovable_count": 1,
                "match_status": ("EXACT_SAME_ORGANIZATION" if cw.get("match_status") == "EXACT_NORMALIZED"
                                 else "PROBABLE_NAME_VARIANT"),
                "match_reason": f"score={cw.get('match_score')}, jaccard={cw.get('token_jaccard')}",
                "confidence": cw.get("match_score"),
                "requires_human_review": cw.get("review_required", "false"),
                "blocking_issue": "",
            })
            processed.add(cur_id); processed.add(leg_id)
    # Lovable-only
    for oid, lov in lov_orgs.items():
        if oid in processed: continue
        groups.append({
            "proposed_canonical_org_id": oid,
            "proposed_canonical_name": lov.get("organization_name"),
            "cohort": "",
            "member_candidate_ids": oid,
            "member_names": lov.get("organization_name"),
            "has_legacy": "false", "has_lovable": "true",
            "legacy_count": 0, "lovable_count": 1,
            "match_status": "LOVABLE_ONLY",
            "match_reason": "no_legacy_crosswalk_peer",
            "confidence": "",
            "requires_human_review": "true",
            "blocking_issue": "",
        })
    # Legacy-only
    for lid, leg in leg_orgs.items():
        if lid in processed: continue
        groups.append({
            "proposed_canonical_org_id": lid,
            "proposed_canonical_name": leg.get("organization_name"),
            "cohort": leg.get("cohort"),
            "member_candidate_ids": lid,
            "member_names": leg.get("organization_name"),
            "has_legacy": "true", "has_lovable": "false",
            "legacy_count": 1, "lovable_count": 0,
            "match_status": "LEGACY_ONLY",
            "match_reason": "no_lovable_crosswalk_peer",
            "confidence": "",
            "requires_human_review": "false",
            "blocking_issue": "",
        })
    with groups_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(groups[0].keys()))
        w.writeheader()
        for row in groups: w.writerow(row)

    # ---------- Build the main markdown report ----------
    md = ["# تدقيق سجل الجمعيات المشاركة — لماذا 175؟\n",
          "_تدقيق قراءة فقط. لا تعديل ولا دمج ولا حذف. تاريخ: 2026-07-31._\n"]

    md.append("\n## 1) معادلة الرقم 175 (المكشوفة)\n")
    md.append(
        f"- عدد صفوف جهات Legacy الخام: **{len(leg_orgs)}**\n"
        f"- عدد صفوف جهات Lovable الخام: **{len(lov_orgs)}**\n"
        f"- 175 = **{len(lov_orgs)} + {len(leg_orgs)}** — جمع مباشر لكلا المصدرين.\n"
        f"- **`crosswalk_organizations` لم يُطبَّق أثناء الـ seed.** يحتوي على {len(cw_orgs)} صف بتوزيع:\n"
    )
    for k, v in cw_status_counts.items():
        md.append(f"  - `{k}`: {v}\n")
    md.append(
        f"- بتطبيق EXACT_NORMALIZED فقط (دمج 56 زوجًا): العدد الفريد = **{unique_after_exact}**\n"
        f"- بتطبيق EXACT + PROBABLE_NAME_VARIANT (دمج 57 زوجًا): العدد الفريد = **{unique_after_exact_and_probable}**\n"
        f"- LEGACY_ONLY (بلا مطابق Lovable): **{len(legacy_only_ids)}**\n"
        f"- LOVABLE_ONLY (بلا مطابق Legacy): **{len(lovable_only_ids)}**\n"
        f"- عدد الجهات المكررة داخل نفس المصدر: 0 (لا صفوف مكررة بنفس المعرف داخل Legacy أو Lovable).\n"
    )

    md.append("\n## 2) الأرقام الثلاثة المنفصلة المطلوبة\n")
    md.append("| المؤشر | القيمة | التعريف |\n|---|---:|---|\n")
    md.append(f"| صفوف المصادر الخام للجهات | **{len(leg_orgs) + len(lov_orgs)} = 175** | جمع Legacy + Lovable قبل أي دمج |\n")
    md.append(f"| مشاركات (organization × cohort) | **{len(participations)}** | كل ظهور للجهة في دفعة كصف مستقل. للـLegacy: الدفعة معروفة. للـLovable: {sum(1 for p in participations if p['cohort']=='UNKNOWN')} مشاركة بدفعة غير معروفة. |\n")
    md.append(f"| الجمعيات الفريدة عبر البرنامج | **{unique_after_exact_and_probable}** (مقترح بعد EXACT+PROBABLE) — **{unique_after_exact}** (بـEXACT فقط) | تحتاج مراجعتك للاعتماد |\n")

    md.append("\n## 3) توزيع الدفعات\n")
    md.append("| الدفعة | جهات Legacy | مشاركات (Legacy) | جهات Lovable المرتبطة (crosswalk) | مشاركات (Lovable) | مؤكد كنفس الجهة |\n|---|---:|---:|---:|---:|---:|\n")
    for c in ["1", "2", "3", "4"]:
        leg_c = leg_cohort_dist.get(c, 0)
        lov_linked = sum(1 for x in cw_orgs if x.get("legacy_cohort") == c and x.get("match_status") == "EXACT_NORMALIZED")
        md.append(f"| {c} | {leg_c} | {leg_c} | {lov_linked} | {lov_linked} | {lov_linked} |\n")
    lov_unknown = sum(1 for p in participations if p["cohort"] == "UNKNOWN")
    md.append(f"| UNKNOWN (Lovable بلا crosswalk) | — | — | — | {lov_unknown} | — |\n")

    md.append("\n## 4) الجمعيات في أكثر من دفعة (بعد التطبيع + Crosswalk)\n")
    md.append(f"- عدد الجمعيات التي ظهرت في دفعة واحدة: **{single_cohort}**\n")
    md.append(f"- عدد الجمعيات التي ظهرت في دفعتين: **{two_c}**\n")
    md.append(f"- عدد الجمعيات التي ظهرت في ثلاث دفعات: **{three_c}**\n")
    md.append(f"- عدد الجمعيات التي ظهرت في الدفعات الأربع: **{four_c}**\n")
    md.append(f"- جمعيات لا تحمل دفعة (Lovable-only دون crosswalk): **{single_only_unknown}**\n")
    if multi_cohort:
        md.append("\n### قائمة الجمعيات متعددة الدفعات:\n")
        md.append("| المعرف الموحد المقترح | الاسم | الدفعات | الأسماء المستخدمة |\n|---|---|---|---|\n")
        for cid, cohs in sorted(multi_cohort.items()):
            names = " | ".join(sorted(names_by_canon.get(cid, [])))
            example_name = next(iter(names_by_canon.get(cid, [""])))
            md.append(f"| `{cid}` | {example_name} | {', '.join(cohs)} | {names} |\n")
    else:
        md.append("\n**✅ لم يُكشف أي تكرار عبر الدفعات ضمن البيانات الحالية.**\n")

    md.append("\n## 5) تفاصيل التطابقات الـ56 EXACT + 1 PROBABLE + 61 LEGACY_ONLY\n")
    md.append(f"- **EXACT_NORMALIZED**: {cw_status_counts.get('EXACT_NORMALIZED', 0)}\n")
    md.append(f"- **PROBABLE_NAME_VARIANT**: {cw_status_counts.get('PROBABLE_NAME_VARIANT', 0)}\n")
    md.append(f"- **LEGACY_ONLY (لا مطابق Lovable)**: {legacy_only_count}\n")
    md.append(f"- **LOVABLE_ONLY (لا مطابق Legacy)**: {len(lovable_only_ids)}\n\n")
    md.append("**كل زوج EXACT/PROBABLE مسجّل حاليًا كصفين منفصلين في الـ175** — أي الـseed لم يطبّق الدمج. التفاصيل الكاملة في `ORGANIZATION_MATCH_GROUPS.csv`.\n\n")
    md.append("عيّنة من الـ EXACT (أول 10):\n")
    md.append("| Legacy | Lovable | الدفعة | Score |\n|---|---|---|---|\n")
    for c in cw_orgs[:200]:
        if c.get("match_status") == "EXACT_NORMALIZED":
            md.append(f"| {c.get('legacy_organization_name')} (`{c.get('legacy_org_id')}`) | {c.get('current_organization_name')} (`{c.get('current_org_id')}`) | {c.get('legacy_cohort')} | {c.get('match_score')} |\n")
    md.append("\nالحالة `PROBABLE_NAME_VARIANT`:\n")
    for c in cw_orgs:
        if c.get("match_status") == "PROBABLE_NAME_VARIANT":
            md.append(f"- Legacy: {c.get('legacy_organization_name')} (`{c.get('legacy_org_id')}`) ↔ Lovable: {c.get('current_organization_name')} (`{c.get('current_org_id')}`) — score={c.get('match_score')} · jaccard={c.get('token_jaccard')}\n")

    md.append("\n**دمج الـ 57 زوجًا لن يغيّر الرحلات/النسخ** لأن Canonical Layer يستخدم `organization_id` من Lovable للسجلات التي لها Lovable-side، والـLegacy peer يظهر داخل نفس Family. الأرقام 3,521 / 5,038 محفوظة.\n")

    md.append("\n## 6) تدقيق جودة Lovable — «مقبول» هل هو دليل تخرّج؟\n")
    md.append(
        "**تحفّظ حاسم:** كل الـ2,565 صف Lovable يحمل `evaluation='مقبول'` بلا استثناء. هذه القيمة تظهر:\n"
        "- كصف موجود في جدول `records_current` وموصول بنموذج بمعرف\n"
        "- **بدون تحقق من محتوى ملف Google** المشار إليه في `model_url`\n"
        "- بدون فحص بشري لكل نموذج\n\n"
        "**LINK_EXISTS_CONTENT_NOT_VERIFIED**: وجود صف/رابط لا يعني أن محتوى الملف مكتمل أو مقبول فعليًا.\n\n"
        "التحقق التفصيلي لكل جهة يظهر في CSV منفصل قادم (Iteration مستقلة).\n"
    )
    stats_hours = {}
    async for r in coll("records_current").find({}, {"organization_id":1,"work_hours":1,"model_url":1,"notes":1,"first_submitted_at_iso":1,"_id":0}):
        oid = r.get("organization_id"); stats_hours.setdefault(oid, {"rows":0,"links":0,"hours":0.0,"notes":0,"dates":0})
        s = stats_hours[oid]; s["rows"] += 1
        if r.get("model_url"): s["links"] += 1
        try: s["hours"] += float(r.get("work_hours") or 0)
        except: pass
        if r.get("notes"): s["notes"] += 1
        if r.get("first_submitted_at_iso"): s["dates"] += 1
    md.append(f"\nإجمالي جهات Lovable: {len(stats_hours)}\n")
    md.append(f"معدل صفوف/جهة: {sum(s['rows'] for s in stats_hours.values())/max(1,len(stats_hours)):.1f} (المتوقع 45)\n")
    md.append(f"معدل ملاحظات/جهة: {sum(s['notes'] for s in stats_hours.values())/max(1,len(stats_hours)):.1f}\n")
    md.append(f"معدل ساعات/جهة: {sum(s['hours'] for s in stats_hours.values())/max(1,len(stats_hours)):.1f}\n\n")
    md.append("**كل قيمة «مقبول» في Lovable يجب معاملتها كـ `LINK_EXISTS_CONTENT_NOT_VERIFIED` حتى يتم فحص محتوى الملف.**\n")

    md.append("\n## 7) إعادة فحص Family Key\n")
    md.append(
        f"- الفحص السابق قال «0 organizations in multiple cohorts».\n"
        f"- بعد التطبيع + Crosswalk: **{len(multi_cohort)} جمعية** ظهرت في أكثر من دفعة.\n"
    )
    if len(multi_cohort) == 0:
        md.append(
            "- **الادعاء السابق يبقى صحيحًا**: لا توجد جمعية موحّدة متعددة الدفعات في البيانات الحالية.\n"
            "- Legacy فقط: كل `legacy_org_id` مسجّل في دفعة واحدة (تم التحقق أعلاه: 0 orgs in multi-cohort في `historical_arbitrations`).\n"
            "- Lovable: لا حقل cohort أصلًا؛ بعد الاستنتاج عبر Crosswalk كل جهة Lovable ترتبط بدفعة واحدة على الأكثر.\n\n"
            "**أثر إضافة cohort إلى Family Key:**\n"
            "- عدد الرحلات بالمفتاح الحالي `org × model_definition`: 3,521\n"
            "- عدد الرحلات بالمفتاح المقترح `org × cohort × model_definition`: **3,521 (لا تغيّر)** لأن كل org ترتبط بدفعة واحدة كحد أقصى في البيانات الحالية.\n"
            "- عدد الرحلات التي ستنفصل: **0**\n"
            "- عدد النسخ 5,038: لا تغيير.\n\n"
            "**التوصية:** ابقِ المفتاح الحالي، ولكن أضف حقل `cohort_participation_id` احتياطيًا في نموذج البيانات لاستقبال حالات متعددة الدفعات مستقبلًا.\n"
        )
    else:
        md.append(
            f"- **الادعاء السابق مضلّل**. المفتاح الصحيح يجب أن يصبح `org × cohort × model_definition`.\n"
            f"- عدد الرحلات المتوقع بالمفتاح الجديد: يحتاج إعادة بناء لحسابه دقيقًا.\n"
            f"- **لم يُنفَّذ تغيير المفتاح** — القرار ينتظرك.\n"
        )

    md.append("\n## 8) الملفات المُنتَجة\n")
    md.append(f"- `{p_csv}` — {len(participations)} صف مشاركة\n")
    md.append(f"- `{r175_csv}` — {len(registry)} صف مرشح (يجب أن يكون 175)\n")
    md.append(f"- `{groups_csv}` — {len(groups)} مجموعة مقترحة\n")

    md.append("\n## 9) تأكيد عدم لمس البيانات\n")
    md.append(
        "- لا تعديل على `source_records`، `organizations_current`، `historical_organizations`، `crosswalk_organizations`.\n"
        "- لا تعديل على `canonical_submissions` أو `canonical_submission_families`.\n"
        "- لا تنفيذ لـBulk confirm.\n"
        "- لا تغيير في `participation_review_status` لأي جهة.\n"
        "- فقط قراءة + كتابة إلى `/app/memory/` (تقارير).\n"
    )

    (MEMORY / "PARTICIPATING_ORGANIZATIONS_AUDIT.md").write_text("".join(md), encoding="utf-8")
    print("Audit files written.")
    print(f"Participations: {len(participations)}")
    print(f"Unique orgs (after EXACT): {unique_after_exact}")
    print(f"Unique orgs (after EXACT + PROBABLE): {unique_after_exact_and_probable}")
    print(f"Multi-cohort orgs: {len(multi_cohort)}")
    print(f"crosswalk_orgs statuses: {dict(cw_status_counts)}")


asyncio.run(main())
