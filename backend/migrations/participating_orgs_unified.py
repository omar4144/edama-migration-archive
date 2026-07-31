"""
Iteration 13.1 — UNIFIED audit deliverables (READ-ONLY w.r.t. DB).

Consumes existing raw sources (participating_orgs, crosswalk_organizations,
organizations_current, historical_organizations, records_current,
historical_arbitrations) and prior /app/memory/*.csv reports, and produces:

  1. ORGANIZATION_PARTICIPATION_SOURCE_RECORDS.csv (175 raw evidence rows)
  2. ORGANIZATION_COHORT_PARTICIPATIONS_UNIFIED.csv (118 unified org×cohort rows)
  3. ORGANIZATION_UNIFIED_REGISTRY.csv                (118 unified organizations)
  4. CROSS_COHORT_CANDIDATES.csv                      (name-similarity across cohorts)
  5. LOVABLE_57_ORG_QUALITY.csv                       (per-Lovable-org quality metrics)
  6. PROPOSED_AUDIT_LOG_ENTRIES.csv                   (dry-run audit-log inserts)
  7. UNIFIED_AUDIT_REPORT.md                          (Arabic RTL report)

Never modifies any collection.  Only reads and writes files under /app/memory/.

Adopted decisions (per user, Iteration 13 review):
  - 118 unified organizations (56 EXACT + 1 PROBABLE + 61 LEGACY_ONLY)
  - PROBABLE_NAME_VARIANT for صندوق الشهداء ↔ صندوق الشهداء والمصابين والأسرى والمفقودين
    is APPROVED (proposed audit-log entry — not yet applied to DB).
  - 175 remains as the source-records count, never used as an org or participation count.
"""
import asyncio
import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")

from db import coll

MEMORY = Path("/app/memory")


def norm(s: str) -> str:
    if not s:
        return ""
    v = unicodedata.normalize("NFKC", s).strip()
    v = re.sub(r"[\u064b-\u065f\u0670]+", "", v)
    v = v.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي").replace("ة", "ه")
    v = re.sub(r"[\s\u200f\u200e]+", "", v)
    return v


def tokens(s: str) -> set:
    """Return significant tokens after stripping common noise words."""
    if not s:
        return set()
    v = unicodedata.normalize("NFKC", s).strip()
    v = re.sub(r"[\u064b-\u065f\u0670]+", "", v)
    v = v.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي").replace("ة", "ه")
    stop = {"جمعيه", "مؤسسه", "شركه", "لجنه", "هيئه", "وزاره", "امانه",
            "الاهليه", "التعاونيه", "الخيريه", "الاجتماعيه", "التنمويه",
            "في", "من", "الى", "لل", "بال", "ال", "بـ", "لـ", "و", "أ"}
    toks = {t for t in v.split() if t and t not in stop and len(t) >= 2}
    return toks


def similarity(a: str, b: str):
    """Return (ratio, jaccard, shared_tokens)."""
    if not a or not b:
        return 0.0, 0.0, set()
    an = norm(a)
    bn = norm(b)
    ratio = SequenceMatcher(None, an, bn).ratio()
    ta, tb = tokens(a), tokens(b)
    jaccard = len(ta & tb) / max(1, len(ta | tb)) if (ta or tb) else 0.0
    return ratio, jaccard, ta & tb


def canon_id_for_leg(lid, cw_by_legacy):
    cw = cw_by_legacy.get(lid)
    if cw and cw.get("match_status") in ("EXACT_NORMALIZED", "PROBABLE_NAME_VARIANT"):
        return cw["current_org_id"]
    return lid


async def main():
    # ---------- Load raw sources ----------
    lov_orgs = {r["organization_id"]: r async for r in coll("organizations_current").find({}, {"_id": 0})}
    leg_orgs = {r["legacy_org_id"]: r async for r in coll("historical_organizations").find({}, {"_id": 0})}
    cw_orgs = [x async for x in coll("crosswalk_organizations").find({}, {"_id": 0})]

    cw_by_current = {c["current_org_id"]: c for c in cw_orgs if c.get("current_org_id")}
    cw_by_legacy = {c["legacy_org_id"]: c for c in cw_orgs if c.get("legacy_org_id")}

    # Family/version counts
    fam_by_org = Counter()
    async for f in coll("canonical_submission_families").find({}, {"organization_id": 1, "_id": 0}):
        if f.get("organization_id"):
            fam_by_org[f["organization_id"]] += 1
    ver_by_org = Counter()
    async for c in coll("canonical_submissions").find({}, {"organization_id": 1, "_id": 0}):
        if c.get("organization_id"):
            ver_by_org[c["organization_id"]] += 1
    ver_by_legacy = Counter()
    async for c in coll("canonical_submissions").find(
        {"primary_source": "legacy"}, {"organization_id": 1, "_id": 0}
    ):
        if c.get("organization_id"):
            ver_by_legacy[c["organization_id"]] += 1

    lov_rows_by_org = Counter()
    lov_rows_detail = defaultdict(list)
    async for r in coll("records_current").find(
        {}, {"organization_id": 1, "model_url": 1, "model_id": 1, "model_name": 1,
             "evaluation": 1, "work_hours": 1, "notes": 1, "first_submitted_at_iso": 1,
             "last_modified_at_iso": 1, "_id": 0}
    ):
        oid = r.get("organization_id")
        if oid:
            lov_rows_by_org[oid] += 1
            lov_rows_detail[oid].append(r)
    leg_rows_by_org = Counter()
    async for r in coll("historical_arbitrations").find({}, {"legacy_org_id": 1, "_id": 0}):
        if r.get("legacy_org_id"):
            leg_rows_by_org[r["legacy_org_id"]] += 1

    # ---------- 1) SOURCE_RECORDS.csv (175 raw evidence rows) ----------
    # We simply mirror the existing ORGANIZATION_COHORT_PARTICIPATIONS.csv structure
    # but rename to make the two-tier model explicit.
    source_records = []
    for lid, leg in leg_orgs.items():
        canon_id = canon_id_for_leg(lid, cw_by_legacy)
        canon_name = (cw_by_legacy.get(lid, {}).get("current_organization_name")
                      or leg.get("organization_name"))
        source_records.append({
            "source_record_id": f"SRC-LEG-{lid}",
            "canonical_org_id": canon_id,
            "canonical_org_name": canon_name,
            "cohort": leg.get("cohort"),
            "source_side": "legacy",
            "source_org_id": lid,
            "name_as_written": leg.get("organization_name"),
            "normalized_name": norm(leg.get("organization_name", "")),
            "source_files": leg.get("source_files") or "",
            "source_rows": leg.get("source_rows") or "",
            "consultant_names": leg.get("consultants") or "",
            "evaluator_names": leg.get("evaluators") or "",
            "roster_status": leg.get("roster_status") or "",
            "records_count": leg_rows_by_org.get(lid, 0),
        })
    for lid, lov in lov_orgs.items():
        cw = cw_by_current.get(lid)
        canon_id = lid
        inferred_cohort = ""
        if cw and cw.get("match_status") in ("EXACT_NORMALIZED", "PROBABLE_NAME_VARIANT"):
            inferred_cohort = cw.get("legacy_cohort") or ""
        source_records.append({
            "source_record_id": f"SRC-LOV-{lid}",
            "canonical_org_id": canon_id,
            "canonical_org_name": lov.get("organization_name"),
            "cohort": inferred_cohort or "UNKNOWN",
            "source_side": "lovable",
            "source_org_id": lid,
            "name_as_written": lov.get("organization_name"),
            "normalized_name": norm(lov.get("organization_name", "")),
            "source_files": "lovable_current",
            "source_rows": "",
            "consultant_names": lov.get("consultant_names") or "",
            "evaluator_names": lov.get("evaluator_name") or "",
            "roster_status": "",
            "records_count": lov_rows_by_org.get(lid, 0),
        })

    src_out = MEMORY / "ORGANIZATION_PARTICIPATION_SOURCE_RECORDS.csv"
    with src_out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(source_records[0].keys()))
        w.writeheader()
        for r in source_records:
            w.writerow(r)

    # ---------- 2) UNIFIED PARTICIPATIONS (118 rows) ----------
    unified = {}  # key=(canon_id, cohort) → dict
    for r in source_records:
        key = (r["canonical_org_id"], str(r["cohort"]))
        if key not in unified:
            unified[key] = {
                "unified_participation_id": f"PART-{r['canonical_org_id']}-C{r['cohort']}",
                "canonical_org_id": r["canonical_org_id"],
                "canonical_org_name": r["canonical_org_name"],
                "cohort": r["cohort"],
                "cohort_label": f"دفعة {r['cohort']}" if r["cohort"] != "UNKNOWN" else "دفعة غير معروفة",
                "aliases": set(),
                "legacy_org_ids": set(),
                "lovable_org_ids": set(),
                "sides": set(),
                "source_record_ids": [],
                "consultant_names": set(),
                "evaluator_names": set(),
                "roster_status": set(),
                "records_count": 0,
                "participation_evidence": [],
                "cohort_confidence": "HIGH",
                "requires_review": False,
            }
        u = unified[key]
        u["aliases"].add(r["name_as_written"])
        u["sides"].add(r["source_side"])
        u["source_record_ids"].append(r["source_record_id"])
        if r["source_side"] == "legacy":
            u["legacy_org_ids"].add(r["source_org_id"])
            u["participation_evidence"].append(f"legacy_org_id={r['source_org_id']}")
        else:
            u["lovable_org_ids"].add(r["source_org_id"])
            u["participation_evidence"].append(f"lovable_org_id={r['source_org_id']}")
        for c in re.split(r"[|,،]", str(r.get("consultant_names") or "")):
            c = c.strip().strip('"').strip("[").strip("]")
            if c:
                u["consultant_names"].add(c)
        for c in re.split(r"[|,،]", str(r.get("evaluator_names") or "")):
            c = c.strip().strip('"').strip("[").strip("]")
            if c:
                u["evaluator_names"].add(c)
        if r["roster_status"]:
            u["roster_status"].add(r["roster_status"])
        u["records_count"] += int(r["records_count"] or 0)
        # confidence: any lovable-only side alone → MEDIUM
        if r["source_side"] == "lovable" and r["cohort"] == "UNKNOWN":
            u["cohort_confidence"] = "UNKNOWN"
            u["requires_review"] = True

    # For each unified row, if we have both legacy and lovable evidence → HIGH
    for u in unified.values():
        if "legacy" in u["sides"] and "lovable" in u["sides"]:
            u["cohort_confidence"] = "HIGH (Legacy roster + Lovable evidence)"
        elif "legacy" in u["sides"]:
            u["cohort_confidence"] = "HIGH (Legacy roster)"
        elif "lovable" in u["sides"] and u["cohort"] != "UNKNOWN":
            u["cohort_confidence"] = "MEDIUM (Lovable inferred via crosswalk)"

    unified_rows = []
    for u in unified.values():
        unified_rows.append({
            "unified_participation_id": u["unified_participation_id"],
            "canonical_org_id": u["canonical_org_id"],
            "canonical_org_name": u["canonical_org_name"],
            "cohort": u["cohort"],
            "cohort_label": u["cohort_label"],
            "aliases": " | ".join(sorted(u["aliases"])),
            "sources": "+".join(sorted(u["sides"])),
            "legacy_org_ids": " | ".join(sorted(u["legacy_org_ids"])),
            "lovable_org_ids": " | ".join(sorted(u["lovable_org_ids"])),
            "source_record_ids": " | ".join(u["source_record_ids"]),
            "consultant_names": " | ".join(sorted(u["consultant_names"])),
            "evaluator_names": " | ".join(sorted(u["evaluator_names"])),
            "roster_status": " | ".join(sorted(u["roster_status"])),
            "records_count": u["records_count"],
            "model_family_count": fam_by_org.get(u["canonical_org_id"], 0),
            "model_version_count": ver_by_org.get(u["canonical_org_id"], 0),
            "participation_evidence": " | ".join(u["participation_evidence"]),
            "cohort_confidence": u["cohort_confidence"],
            "requires_review": "true" if u["requires_review"] else "false",
        })

    # Sort by cohort then canonical id
    def _sort_key(r):
        try:
            c = int(r["cohort"])
        except (ValueError, TypeError):
            c = 99
        return (c, r["canonical_org_id"])

    unified_rows.sort(key=_sort_key)

    unified_out = MEMORY / "ORGANIZATION_COHORT_PARTICIPATIONS_UNIFIED.csv"
    with unified_out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(unified_rows[0].keys()))
        w.writeheader()
        for r in unified_rows:
            w.writerow(r)

    # ---------- 3) UNIFIED_REGISTRY.csv (118 unified organizations) ----------
    reg = {}  # canonical_org_id → dict
    for r in source_records:
        cid = r["canonical_org_id"]
        if cid not in reg:
            reg[cid] = {
                "canonical_org_id": cid,
                "canonical_org_name": r["canonical_org_name"],
                "aliases": set(),
                "legacy_org_ids": set(),
                "lovable_org_ids": set(),
                "cohorts": set(),
                "source_record_ids": [],
                "consultant_names": set(),
                "evaluator_names": set(),
                "roster_status": set(),
            }
        entry = reg[cid]
        entry["aliases"].add(r["name_as_written"])
        entry["cohorts"].add(str(r["cohort"]))
        entry["source_record_ids"].append(r["source_record_id"])
        if r["source_side"] == "legacy":
            entry["legacy_org_ids"].add(r["source_org_id"])
        else:
            entry["lovable_org_ids"].add(r["source_org_id"])
        for c in re.split(r"[|,،]", str(r.get("consultant_names") or "")):
            c = c.strip().strip('"').strip("[").strip("]")
            if c:
                entry["consultant_names"].add(c)
        for c in re.split(r"[|,،]", str(r.get("evaluator_names") or "")):
            c = c.strip().strip('"').strip("[").strip("]")
            if c:
                entry["evaluator_names"].add(c)
        if r["roster_status"]:
            entry["roster_status"].add(r["roster_status"])

    # Determine unification status per org
    def _status(entry):
        if entry["legacy_org_ids"] and entry["lovable_org_ids"]:
            leg_ids = entry["legacy_org_ids"]
            # PROBABLE if any crosswalk is PROBABLE_NAME_VARIANT
            probable = any(cw_by_legacy.get(lid, {}).get("match_status") == "PROBABLE_NAME_VARIANT"
                           for lid in leg_ids)
            return "UNIFIED_PROBABLE_HUMAN_APPROVED" if probable else "UNIFIED_EXACT"
        if entry["legacy_org_ids"]:
            return "LEGACY_ONLY"
        return "LOVABLE_ONLY"

    reg_rows = []
    for cid, entry in reg.items():
        st = _status(entry)
        reg_rows.append({
            "canonical_org_id": cid,
            "canonical_org_name": entry["canonical_org_name"],
            "unification_status": st,
            "unification_reason": {
                "UNIFIED_EXACT": "EXACT_NORMALIZED name match (score=1.0)",
                "UNIFIED_PROBABLE_HUMAN_APPROVED": "abbreviated_legacy_name_matches_full_current_official_name",
                "LEGACY_ONLY": "no Lovable peer",
                "LOVABLE_ONLY": "no Legacy peer",
            }[st],
            "aliases": " | ".join(sorted(entry["aliases"])),
            "legacy_org_ids": " | ".join(sorted(entry["legacy_org_ids"])),
            "lovable_org_ids": " | ".join(sorted(entry["lovable_org_ids"])),
            "cohorts_participated": " | ".join(sorted(entry["cohorts"])),
            "cohort_count": len([x for x in entry["cohorts"] if x != "UNKNOWN"]),
            "source_record_count": len(entry["source_record_ids"]),
            "source_record_ids": " | ".join(entry["source_record_ids"]),
            "consultant_names": " | ".join(sorted(entry["consultant_names"])),
            "evaluator_names": " | ".join(sorted(entry["evaluator_names"])),
            "roster_status": " | ".join(sorted(entry["roster_status"])),
            "model_family_count": fam_by_org.get(cid, 0),
            "model_version_count": ver_by_org.get(cid, 0),
            "lovable_row_count": sum(lov_rows_by_org.get(x, 0) for x in entry["lovable_org_ids"]),
            "legacy_row_count": sum(leg_rows_by_org.get(x, 0) for x in entry["legacy_org_ids"]),
            "requires_human_review": "false" if st != "UNIFIED_PROBABLE_HUMAN_APPROVED" else "false (approved)",
        })
    reg_rows.sort(key=lambda r: r["canonical_org_id"])
    reg_out = MEMORY / "ORGANIZATION_UNIFIED_REGISTRY.csv"
    with reg_out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(reg_rows[0].keys()))
        w.writeheader()
        for r in reg_rows:
            w.writerow(r)

    # ---------- 4) CROSS_COHORT_CANDIDATES.csv ----------
    # Compare every canonical org against every other in a DIFFERENT cohort.
    ratio_threshold = 0.72
    jaccard_threshold = 0.30
    candidates = []
    entries = [(cid, e) for cid, e in reg.items()]
    for i, (cid_a, ea) in enumerate(entries):
        cohs_a = {c for c in ea["cohorts"] if c and c != "UNKNOWN"}
        if not cohs_a:
            continue
        # Use the canonical name + all aliases for comparison
        names_a = list(ea["aliases"]) or [ea["canonical_org_name"]]
        for cid_b, eb in entries[i + 1:]:
            cohs_b = {c for c in eb["cohorts"] if c and c != "UNKNOWN"}
            if not cohs_b or cohs_a & cohs_b:
                # Same cohort → not a cross-cohort candidate.
                continue
            names_b = list(eb["aliases"]) or [eb["canonical_org_name"]]
            best_ratio, best_jac, best_shared = 0.0, 0.0, set()
            best_pair = ("", "")
            for na in names_a:
                for nb in names_b:
                    r, j, s = similarity(na, nb)
                    if r > best_ratio or (r == best_ratio and j > best_jac):
                        best_ratio, best_jac, best_shared, best_pair = r, j, s, (na, nb)
            if best_ratio < ratio_threshold and best_jac < jaccard_threshold:
                continue
            # Reason patterns
            reason = []
            if best_ratio >= 0.95:
                reason.append("near_identical_after_normalization")
            if best_jac >= 0.5:
                reason.append("high_token_overlap")
            if len(best_shared) >= 2:
                reason.append("multi_token_overlap")
            # abbreviation heuristic
            if best_pair[0] and best_pair[1]:
                na_n = norm(best_pair[0])
                nb_n = norm(best_pair[1])
                if na_n in nb_n or nb_n in na_n:
                    reason.append("one_name_substring_of_other")
                if abs(len(na_n) - len(nb_n)) >= 6:
                    reason.append("possible_abbreviation_vs_official")
            candidates.append({
                "candidate_pair_id": f"XC-{cid_a}--{cid_b}",
                "org_a_canonical_id": cid_a,
                "org_a_name": best_pair[0] or ea["canonical_org_name"],
                "org_a_cohorts": " | ".join(sorted(cohs_a)),
                "org_b_canonical_id": cid_b,
                "org_b_name": best_pair[1] or eb["canonical_org_name"],
                "org_b_cohorts": " | ".join(sorted(cohs_b)),
                "similarity_ratio": round(best_ratio, 4),
                "jaccard": round(best_jac, 4),
                "shared_tokens": " | ".join(sorted(best_shared)) if best_shared else "",
                "similarity_reason": " ; ".join(reason) or "moderate_similarity",
                "consultant_a": " | ".join(sorted(ea["consultant_names"])),
                "consultant_b": " | ".join(sorted(eb["consultant_names"])),
                "evaluator_a": " | ".join(sorted(ea["evaluator_names"])),
                "evaluator_b": " | ".join(sorted(eb["evaluator_names"])),
                "auto_decision": "DO_NOT_AUTO_MERGE",
                "recommended_action": "HUMAN_REVIEW_REQUIRED",
            })
    # Sort by highest similarity first
    candidates.sort(key=lambda r: (-r["similarity_ratio"], -r["jaccard"]))
    xc_out = MEMORY / "CROSS_COHORT_CANDIDATES.csv"
    if not candidates:
        # Force at least one row so the file is present
        candidates = [{
            "candidate_pair_id": "-",
            "org_a_canonical_id": "-",
            "org_a_name": "لا توجد حالات فوق العتبة",
            "org_a_cohorts": "-",
            "org_b_canonical_id": "-",
            "org_b_name": "-",
            "org_b_cohorts": "-",
            "similarity_ratio": 0,
            "jaccard": 0,
            "shared_tokens": "",
            "similarity_reason": "-",
            "consultant_a": "",
            "consultant_b": "",
            "evaluator_a": "",
            "evaluator_b": "",
            "auto_decision": "DO_NOT_AUTO_MERGE",
            "recommended_action": "-",
        }]
    with xc_out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(candidates[0].keys()))
        w.writeheader()
        for r in candidates:
            w.writerow(r)

    # ---------- 5) LOVABLE_57_ORG_QUALITY.csv ----------
    lov_q = []
    EXPECTED_ROWS = 45
    for lid, lov in lov_orgs.items():
        rows = lov_rows_detail.get(lid, [])
        n_rows = len(rows)
        urls = [str(r.get("model_url") or "").strip() for r in rows]
        empty_links = sum(1 for u in urls if not u)
        non_empty = [u for u in urls if u]
        unique_links = len(set(non_empty))
        duplicate_links = len(non_empty) - unique_links
        hours = 0.0
        for r in rows:
            try:
                hours += float(r.get("work_hours") or 0)
            except (TypeError, ValueError):
                pass
        notes_count = sum(1 for r in rows if r.get("notes"))
        eval_values = Counter((r.get("evaluation") or "").strip() for r in rows)
        approved_flag = eval_values.get("مقبول", 0)
        content_verified = 0  # we do not fetch google file contents in this iteration
        completed = 0
        # Statuses per user's request
        statuses = []
        statuses.append(f"ROW_EXISTS={n_rows}")
        statuses.append(f"LINK_EXISTS_CONTENT_NOT_VERIFIED={approved_flag}")
        statuses.append(f"CONTENT_VERIFIED={content_verified}")
        statuses.append(f"COMPLETED={completed}")
        statuses.append(f"APPROVED={approved_flag} (raw 'مقبول' — NOT independently verified)")

        lov_q.append({
            "lovable_org_id": lid,
            "canonical_org_name": lov.get("organization_name"),
            "expected_rows": EXPECTED_ROWS,
            "actual_rows": n_rows,
            "rows_match_expected": "true" if n_rows == EXPECTED_ROWS else "false",
            "unique_links": unique_links,
            "duplicate_links": duplicate_links,
            "empty_links": empty_links,
            "sum_work_hours": round(hours, 2),
            "notes_count": notes_count,
            "evaluation_values": " | ".join(f"{k}={v}" for k, v in eval_values.items()),
            "row_exists_count": n_rows,
            "link_exists_content_not_verified_count": approved_flag,
            "content_verified_count": content_verified,
            "completed_count": completed,
            "approved_count_raw": approved_flag,
            "graduation_claim": "NOT_GRADUATED_BY_ROW_COUNT_OR_APPROVAL",
            "audit_note": "Row/link presence does NOT prove content completeness. "
                          "Google file contents were NOT fetched or validated.",
            "recommended_status": "LINK_EXISTS_CONTENT_NOT_VERIFIED",
            "statuses_summary": " ; ".join(statuses),
        })
    lov_q.sort(key=lambda r: r["lovable_org_id"])
    lovq_out = MEMORY / "LOVABLE_57_ORG_QUALITY.csv"
    with lovq_out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lov_q[0].keys()))
        w.writeheader()
        for r in lov_q:
            w.writerow(r)

    # ---------- 6) PROPOSED_AUDIT_LOG_ENTRIES.csv (dry-run) ----------
    audit_entries = [{
        "proposed_entry_id": "AUDIT-XCW-001",
        "action_type": "APPROVE_PROBABLE_NAME_VARIANT_MERGE",
        "canonical_org_id": "ORG-A08-02",
        "canonical_org_name": "صندوق الشهداء والمصابين والأسرى والمفقودين",
        "member_ids": "ORG-A08-02 | LEG-ORG-B4-035",
        "member_names": "صندوق الشهداء والمصابين والأسرى والمفقودين | صندوق الشهداء",
        "cohort": "4",
        "reason_code": "abbreviated_legacy_name_matches_full_current_official_name",
        "similarity_score": "score=0.9064, jaccard=0.4",
        "consultant": "وديع الحربي",
        "evaluator": "محمد العبدالجبار",
        "human_reviewer": "المالك (Iteration 13 review, 2026-07-31)",
        "status": "PROPOSED_NOT_APPLIED",
        "applies_to_collections": "participating_orgs, crosswalk_organizations (match_status column only)",
        "does_not_touch": "source_records, canonical_submissions, canonical_submission_families",
    }]
    ale_out = MEMORY / "PROPOSED_AUDIT_LOG_ENTRIES.csv"
    with ale_out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(audit_entries[0].keys()))
        w.writeheader()
        for r in audit_entries:
            w.writerow(r)

    # ---------- 7) UNIFIED_AUDIT_REPORT.md ----------
    unique_orgs = len(reg)
    n_exact = sum(1 for r in reg_rows if r["unification_status"] == "UNIFIED_EXACT")
    n_probable = sum(1 for r in reg_rows if r["unification_status"] == "UNIFIED_PROBABLE_HUMAN_APPROVED")
    n_legacy_only = sum(1 for r in reg_rows if r["unification_status"] == "LEGACY_ONLY")
    n_lovable_only = sum(1 for r in reg_rows if r["unification_status"] == "LOVABLE_ONLY")

    cohort_dist = Counter()
    for r in unified_rows:
        try:
            cohort_dist[int(r["cohort"])] += 1
        except (ValueError, TypeError):
            cohort_dist["UNKNOWN"] += 1

    md = [
        "# التدقيق الموحد — تسليمات Iteration 13.1 (قراءة فقط)\n",
        "_تاريخ: 2026-07-31 — لا تعديل على قاعدة البيانات. جميع الملفات في `/app/memory/`._\n\n",
        "## القرارات المُعتمَدة (بناءً على مراجعة المالك)\n",
        "- **118 جمعية موحدة** هي العدد الرسمي. الـ175 صف مصدر داخلي فقط.\n",
        "- **PROBABLE_NAME_VARIANT** لـ «صندوق الشهداء ↔ صندوق الشهداء والمصابين والأسرى والمفقودين» تمّت الموافقة عليه بشريًا — مُسجَّل كإدخال قيد التنفيذ في `PROPOSED_AUDIT_LOG_ENTRIES.csv` ولن يُنفَّذ على قاعدة البيانات حتى إشعارك.\n",
        "- «مقبول» في Lovable = **LINK_EXISTS_CONTENT_NOT_VERIFIED**، ليس دليل تخرّج.\n\n",
        "## المؤشرات (بعد الاعتماد)\n",
        "| المؤشر | القيمة |\n|---|---:|\n",
        f"| صفوف مصادر الجهات (ORGANIZATION_PARTICIPATION_SOURCE_RECORDS) | {len(source_records)} |\n",
        f"| جمعيات موحدة (ORGANIZATION_UNIFIED_REGISTRY) | {unique_orgs} |\n",
        f"| مشاركات موحدة org × cohort (ORGANIZATION_COHORT_PARTICIPATIONS_UNIFIED) | {len(unified_rows)} |\n",
        f"| UNIFIED_EXACT | {n_exact} |\n| UNIFIED_PROBABLE_HUMAN_APPROVED | {n_probable} |\n",
        f"| LEGACY_ONLY | {n_legacy_only} |\n| LOVABLE_ONLY | {n_lovable_only} |\n\n",
        "## توزيع الدفعات (المشاركات الموحدة)\n",
        "| الدفعة | عدد الجمعيات |\n|---|---:|\n",
    ]
    for k in [1, 2, 3, 4]:
        md.append(f"| {k} | {cohort_dist.get(k, 0)} |\n")
    if cohort_dist.get("UNKNOWN"):
        md.append(f"| UNKNOWN | {cohort_dist['UNKNOWN']} |\n")
    md.append(f"| **الإجمالي** | **{sum(cohort_dist.values())}** |\n\n")

    md += [
        "## احتمال مشاركة عبر دفعات — مرشحون للمراجعة\n",
        f"- عدد الأزواج التي فوق العتبة (ratio≥{ratio_threshold} أو jaccard≥{jaccard_threshold}): **{len(candidates) if candidates and candidates[0]['candidate_pair_id']!='-' else 0}**.\n",
        "- لن تُدمج تلقائيًا. القرار بشري فقط.\n",
        "- الملف: `CROSS_COHORT_CANDIDATES.csv`.\n\n",
        "## جودة الـ57 جهة Lovable\n",
        "- الملف: `LOVABLE_57_ORG_QUALITY.csv` — 57 صف، عمود لكل مؤشر.\n",
        "- تصنيف كل جمعية حاليًا: `LINK_EXISTS_CONTENT_NOT_VERIFIED`. لم يُفحص أي محتوى ملف Google.\n",
        "- لا يُدَّعى تخرّج أي جهة استنادًا إلى وجود 45 صفًا أو قيمة «مقبول».\n\n",
        "## تأكيد سلامة البيانات\n",
        "- لم تُعدَّل أي مجموعة (`source_records`, `historical_organizations`, `organizations_current`, `crosswalk_organizations`, `participating_orgs`, `canonical_submissions`, `canonical_submission_families`).\n",
        "- كل الكتابة إلى `/app/memory/*.csv` و `PARTICIPATING_ORGANIZATIONS_REVIEW.xlsx`.\n",
        "- الـ175 صف الأصلية محفوظة في `ORGANIZATION_PARTICIPATION_SOURCE_RECORDS.csv` كطبقة أدلة.\n\n",
        "## قائمة الملفات المُنتَجة في هذه التسليمة\n",
        "- `ORGANIZATION_PARTICIPATION_SOURCE_RECORDS.csv` — 175 صف مصدر.\n",
        "- `ORGANIZATION_COHORT_PARTICIPATIONS_UNIFIED.csv` — 118 مشاركة موحدة.\n",
        "- `ORGANIZATION_UNIFIED_REGISTRY.csv` — 118 جمعية موحدة.\n",
        "- `CROSS_COHORT_CANDIDATES.csv` — مرشحو التطابق عبر الدفعات.\n",
        "- `LOVABLE_57_ORG_QUALITY.csv` — جودة الـ57 جهة Lovable.\n",
        "- `PROPOSED_AUDIT_LOG_ENTRIES.csv` — إدخال دمج «صندوق الشهداء» المُقترَح.\n",
        "- `PARTICIPATING_ORGANIZATIONS_REVIEW.xlsx` — كتاب Excel محدَّث بجميع الأوراق.\n",
    ]

    (MEMORY / "UNIFIED_AUDIT_REPORT.md").write_text("".join(md), encoding="utf-8")

    print("=== Iteration 13.1 unified deliverables ===")
    print(f"source_records:            {len(source_records)}")
    print(f"unified participations:    {len(unified_rows)}")
    print(f"unified registry (orgs):   {unique_orgs}")
    print(f"cohort distribution:       {dict(cohort_dist)}")
    print(f"cross-cohort candidates:   {len(candidates)}")
    print(f"lovable quality rows:      {len(lov_q)}")
    print(f"proposed audit entries:    {len(audit_entries)}")


if __name__ == "__main__":
    asyncio.run(main())
