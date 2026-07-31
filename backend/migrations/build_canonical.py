"""
Canonical deduplication (v3 — strict rules).

Applies the strict matching contract required by ownership:

EXACT_CROSS_SOURCE_MATCH
  Only if the composite path is fully satisfied:
    same organization + same model definition + same evaluator (both present, equal)
    + submitted_at date == arbitration date (exact, YYYY-MM-DD)
    + decisions compatible (equal, or both empty)
    + no evidence of a different version.
  In the current dataset this is expected to be 0 (Lovable timestamps differ
  from legacy arbitration timestamps by ≥150 days).

PROBABLE_CROSS_SOURCE_MATCH
  Same org + model + evaluator + decisions compatible, and date difference is
  1–3 days. Kept as *two separate canonicals* with a `probable_link` cross-ref
  and requires human confirmation before any merge.

VERSION_LINKED
  Same org + model + same evaluator + resubmission pattern:
    legacy decision ∈ {يحتاج لتطوير, غير مكتمل} → current decision = مقبول,
    and date gap > 3 days. Two canonicals, related but never merged.

REVIEW_REQUIRED
  Crosswalk_status = NO_DIRECT_MODEL_MATCH  (name-only match, no legacy peer
  with the same model definition), OR
  Evaluator mismatch across sources, OR
  Conflicting decisions with dates too far apart to be a clear version.
  Never auto-merged.

CURRENT_ONLY
  Crosswalk_status = NO_LEGACY_ARBITRATION_RECORD.

LEGACY_ONLY
  Legacy arbitration row that no crosswalk record points at.

Internal-source deduplication (rows recognised as duplicates *within* a single
source) is preserved from the archive:
  Lovable: duplicate_link_group_id via `duplicate_links_current` (129 groups /
           951 rows → 129 canonicals: reduction 822).
  Legacy:  legacy_duplicate_group_id via `historical_duplicate_links` (66
           groups / 174 rows → 66 canonicals: reduction 108).

Never mutates raw data. Wipes only its own derived collections.
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
from datetime import datetime, timezone, date as _date
from pathlib import Path

os.environ["EDAMA_MIGRATION_MODE"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from db import coll, get_db  # noqa: E402


DERIVED = (
    "canonical_submissions",
    "record_crosswalks",
    "duplicate_groups",
    "canonical_reviews",
    "dedup_reports",
    "canonical_links",  # NEW: probable + version cross-refs
)

# Decision compatibility (Arabic labels used across the archive)
DEC_ACCEPT = "مقبول"
DEC_NEEDS = "يحتاج لتطوير"
DEC_INCOMPLETE = "غير مكتمل"
VERSION_LEGACY_DECISIONS = {DEC_NEEDS, DEC_INCOMPLETE}


def _num(v):
    try:
        return float(v) if v not in (None, "", "None") else None
    except (ValueError, TypeError):
        return None


def _parse_date(s: str | None):
    if not s:
        return None
    try:
        y, m, d = s[:10].split("-")
        return _date(int(y), int(m), int(d))
    except (ValueError, IndexError):
        return None


def _date_diff_days(a: _date | None, b: _date | None):
    if not a or not b:
        return None
    return abs((a - b).days)


def _classify_pair(cw: dict, cur: dict, leg: dict) -> tuple[str, str, int, list[str]]:
    """Return (match_status, match_reason, confidence, evidence_list) for a
    MATCHED_ORG_AND_MODEL crosswalk row after applying the strict contract.
    """
    ev = ["archive_org_and_model_matched"]
    ec = (cw.get("current_evaluator_name") or "").strip()
    el = (cw.get("legacy_evaluator_name") or "").strip()
    cc = (cw.get("current_consultant_name") or "").strip()
    cl = (cw.get("legacy_consultant_name") or "").strip()
    dec_c = (cw.get("current_evaluation") or "").strip()
    dec_l = (cw.get("legacy_evaluation_status") or "").strip()
    cd = _parse_date(cur.get("submitted_at_iso"))
    ld = _parse_date(leg.get("arbitration_date_iso") or leg.get("arbitration_date_source_iso"))
    diff = _date_diff_days(cd, ld)

    # Evaluator gate — required for any cross-source auto-linkage
    evaluator_ok = bool(ec) and bool(el) and ec == el
    if evaluator_ok:
        ev.append(f"evaluator_matched={ec}")
    else:
        ev.append(f"evaluator_mismatch(current='{ec or '∅'}' legacy='{el or '∅'}')")

    # Consultant compatibility (informational; not required to be non-empty)
    if cc and cl:
        ev.append("consultant_matched" if cc == cl else f"consultant_mismatch(current='{cc}' legacy='{cl}')")
    elif cc or cl:
        ev.append(f"consultant_partial(current='{cc or '∅'}' legacy='{cl or '∅'}')")

    # Decision compatibility
    if dec_c and dec_l:
        if dec_c == dec_l:
            decision_state = "same"
        elif dec_l in VERSION_LEGACY_DECISIONS and dec_c == DEC_ACCEPT:
            decision_state = "version_resubmit"
        else:
            decision_state = "conflict"
    else:
        decision_state = "unknown"
    ev.append(f"decision_state={decision_state}(c={dec_c or '∅'},l={dec_l or '∅'})")

    # Date evidence
    ev.append(f"dates(c={cd or '∅'},l={ld or '∅'},diff={diff if diff is not None else '∅'})")

    # ---------- Rule tree ----------
    # 1. Missing date on either side → cannot grant EXACT; degrade further.
    if diff is None:
        if evaluator_ok and decision_state in ("same", "version_resubmit"):
            return ("REVIEW_REQUIRED", "missing_date_no_auto_merge", 45, ev)
        return ("REVIEW_REQUIRED", "missing_date_and_uncertain", 30, ev)

    # 2. Evaluator mismatch → never auto-link cross-source
    if not evaluator_ok:
        return ("REVIEW_REQUIRED", "evaluator_mismatch_cross_source", 25, ev)

    # 3. Resubmission (version) pattern — regardless of date gap size, if legacy
    #    said "يحتاج/غير مكتمل" and current says "مقبول" and dates differ, it's
    #    a lifecycle version, not a duplicate.
    if diff > 3 and decision_state == "version_resubmit":
        return ("VERSION_LINKED", "resubmission_after_needs_improvement", 90, ev)

    # 4. Same date + everything compatible → EXACT candidate (composite path)
    if diff == 0 and decision_state == "same":
        return ("EXACT_CROSS_SOURCE_MATCH", "composite_path_same_date_same_decision", 100, ev)

    # 5. Close date (1–3 days) + compat → PROBABLE, no auto-merge
    if 1 <= diff <= 3 and decision_state in ("same", "version_resubmit"):
        return ("PROBABLE_CROSS_SOURCE_MATCH", "close_dates_compatible_decisions", 70, ev)

    # 6. Long gap + same/conflict decision, no clear version story → REVIEW
    if diff > 3 and decision_state == "conflict":
        return ("REVIEW_REQUIRED", "wide_gap_conflicting_decisions", 40, ev)
    if diff > 3 and decision_state == "same":
        # Same decision but far apart — possibly a re-arbitration or bad data
        return ("REVIEW_REQUIRED", "wide_gap_identical_decision", 50, ev)

    return ("REVIEW_REQUIRED", "unclassified_pair", 40, ev)


async def _reset():
    db = get_db()
    for name in DERIVED:
        await db[name].delete_many({})


async def build():  # noqa: C901
    await _reset()
    db = get_db()

    # ---------- 1. Load raw rows into memory maps (small dataset) ----------
    cur_by_mig: dict[str, dict] = {}
    async for r in coll("records_current").find({}, {"_id": 0}):
        cur_by_mig[r["migration_id"]] = r

    leg_by_rev: dict[str, dict] = {}
    async for r in coll("historical_arbitrations").find({}, {"_id": 0}):
        leg_by_rev[r["legacy_review_id"]] = r

    # ---------- 2. Load internal duplicate group maps ----------
    cur_dup_by_mig: dict[str, str] = {}
    async for g in coll("duplicate_links_current").find({}):
        gid = g.get("duplicate_link_group_id")
        migs = g.get("migration_ids")
        if isinstance(migs, str):
            try:
                migs = json.loads(migs)
            except json.JSONDecodeError:
                migs = []
        for m in (migs or []):
            cur_dup_by_mig[m] = gid

    leg_dup_by_rev: dict[str, str] = {}
    async for g in coll("historical_duplicate_links").find({}):
        rid = g.get("resource_id")
        gid = g.get("legacy_duplicate_group_id")
        if not rid or not gid:
            continue
        async for r in coll("historical_arbitrations").find(
            {"model_url_resource_id": rid}, {"legacy_review_id": 1, "_id": 0}
        ):
            leg_dup_by_rev[r["legacy_review_id"]] = gid

    # ---------- 3. Load crosswalk index (current_migration_id → cw) ----------
    cw_by_mig: dict[str, dict] = {}
    matched_legacy_ids: set[str] = set()
    async for cw in coll("crosswalk_records").find({}, {"_id": 0}):
        mig = cw.get("current_migration_id")
        if mig:
            cw_by_mig[mig] = cw
        if cw.get("crosswalk_status") == "MATCHED_ORG_AND_MODEL" and cw.get("legacy_review_id"):
            matched_legacy_ids.add(cw["legacy_review_id"])

    # Evaluator name resolution — prefer people.person_name via evaluator_person_id
    person_name_by_id: dict[str, str] = {}
    async for p in coll("people").find({}, {"person_id": 1, "person_name": 1, "_id": 0}):
        person_name_by_id[p["person_id"]] = p.get("person_name")

    def _resolve_eval_name(cur: dict) -> str | None:
        return person_name_by_id.get(cur.get("evaluator_person_id"))

    # ---------- 4. Emit CURRENT-side canonicals ----------
    canonicals: list[dict] = []
    crosswalks: list[dict] = []
    links: list[dict] = []
    dupgroups: list[dict] = []

    emitted_cur_dup: dict[str, str] = {}   # dup_group_id → canonical_id
    emitted_leg_dup: dict[str, str] = {}
    cur_mig_to_cid: dict[str, str] = {}
    leg_rev_to_cid: dict[str, str] = {}

    counters = {
        "EXACT_CROSS_SOURCE_MATCH": 0,
        "PROBABLE_CROSS_SOURCE_MATCH": 0,
        "VERSION_LINKED": 0,
        "REVIEW_REQUIRED": 0,
        "CURRENT_ONLY": 0,
        "LEGACY_ONLY": 0,
    }
    internal_dup_current_rows = 0
    internal_dup_legacy_rows = 0
    seq = 0

    def _cid():
        nonlocal seq
        seq += 1
        return f"CANON-{seq:06d}"

    for mig, cur in cur_by_mig.items():
        cur_gid = cur_dup_by_mig.get(mig)
        if cur_gid and cur_gid in emitted_cur_dup:
            cid = emitted_cur_dup[cur_gid]
            crosswalks.append({
                "canonical_id": cid, "source": "current", "raw_id": mig,
                "match_reason": "internal_lovable_duplicate_group",
                "confidence": 95, "evidence": [f"dup_group={cur_gid}"],
            })
            cur_mig_to_cid[mig] = cid
            internal_dup_current_rows += 1
            continue

        cw = cw_by_mig.get(mig) or {}
        status = cw.get("crosswalk_status")
        eval_name = _resolve_eval_name(cur) or cw.get("current_evaluator_name")

        # Baseline canonical fields common to any current-side row
        base = {
            "canonical_id": _cid(),
            "primary_source": "current",
            "primary_source_id": mig,
            "organization_id": cw.get("current_org_id") or cur.get("organization_id"),
            "organization_name": cw.get("current_organization_name") or cur.get("organization_name"),
            "model_definition_id": cw.get("current_model_id") or cur.get("model_definition_id"),
            "model_name": cw.get("current_model_name") or cur.get("model_name"),
            "evaluator_name": eval_name,
            "consultant_name": cw.get("current_consultant_name") or cur.get("consultant_name"),
            "url": cw.get("current_model_url") or cur.get("model_url"),
            "latest_evaluation": cw.get("current_evaluation") or cur.get("evaluation"),
            "latest_status": cw.get("current_status") or cur.get("status"),
            "submitted_at_iso": cur.get("submitted_at_iso"),
            "work_hours_current": _num(cur.get("work_hours")),
            "hours_level_current": "per_model_arbitration",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        cid = base["canonical_id"]
        cur_mig_to_cid[mig] = cid
        if cur_gid:
            emitted_cur_dup[cur_gid] = cid

        if status == "NO_LEGACY_ARBITRATION_RECORD":
            base.update({
                "match_status": "CURRENT_ONLY",
                "match_reason": "no_legacy_arbitration_record",
                "confidence": 100,
            })
            counters["CURRENT_ONLY"] += 1
            crosswalks.append({
                "canonical_id": cid, "source": "current", "raw_id": mig,
                "match_reason": "no_legacy_arbitration_record",
                "confidence": 100, "evidence": [],
            })

        elif status == "NO_DIRECT_MODEL_MATCH":
            base.update({
                "match_status": "REVIEW_REQUIRED",
                "match_reason": "no_direct_model_match_only_org",
                "confidence": 40,
            })
            counters["REVIEW_REQUIRED"] += 1
            crosswalks.append({
                "canonical_id": cid, "source": "current", "raw_id": mig,
                "match_reason": "no_direct_model_match_only_org",
                "confidence": 40, "evidence": [f"raw_model_name={base['model_name']}"],
            })

        elif status == "MATCHED_ORG_AND_MODEL" and cw.get("legacy_review_id"):
            leg_id = cw["legacy_review_id"]
            leg = leg_by_rev.get(leg_id, {})
            match_status, reason, conf, evidence = _classify_pair(cw, cur, leg)
            base.update({
                "match_status": match_status,
                "match_reason": reason,
                "confidence": conf,
                "linked_legacy_id": leg_id,
                "legacy_evaluation": cw.get("legacy_evaluation_status") or leg.get("arbitration_result_raw"),
                "work_hours_legacy": _num(leg.get("total_arbitration_hours_raw")),
                "hours_level_legacy": "org_cohort_total_repeated_per_model_row",
                "legacy_url": cw.get("legacy_model_url"),
                "linked_cohort": cw.get("legacy_cohort"),
            })
            counters[match_status] += 1
            crosswalks.append({
                "canonical_id": cid, "source": "current", "raw_id": mig,
                "match_reason": reason, "confidence": conf, "evidence": evidence,
            })
            # No merge: legacy row will get its own canonical below. We just
            # record a cross-canonical link once both sides exist (later pass).
        else:
            # No crosswalk row for this current record (shouldn't happen — every
            # current row has a crosswalk entry). Fall back to CURRENT_ONLY.
            base.update({
                "match_status": "CURRENT_ONLY",
                "match_reason": "no_crosswalk_row_fallback",
                "confidence": 80,
            })
            counters["CURRENT_ONLY"] += 1
            crosswalks.append({
                "canonical_id": cid, "source": "current", "raw_id": mig,
                "match_reason": "no_crosswalk_row_fallback",
                "confidence": 80, "evidence": [],
            })

        canonicals.append(base)

    # ---------- 5. Emit LEGACY-side canonicals ----------
    for rev_id, leg in leg_by_rev.items():
        leg_gid = leg_dup_by_rev.get(rev_id)
        if leg_gid and leg_gid in emitted_leg_dup:
            cid = emitted_leg_dup[leg_gid]
            crosswalks.append({
                "canonical_id": cid, "source": "legacy", "raw_id": rev_id,
                "match_reason": "internal_legacy_duplicate_group",
                "confidence": 95, "evidence": [f"dup_group={leg_gid}"],
            })
            leg_rev_to_cid[rev_id] = cid
            internal_dup_legacy_rows += 1
            continue

        cid = _cid()
        leg_rev_to_cid[rev_id] = cid
        if leg_gid:
            emitted_leg_dup[leg_gid] = cid

        base = {
            "canonical_id": cid,
            "primary_source": "legacy",
            "primary_source_id": rev_id,
            "organization_id": leg.get("legacy_org_id"),
            "organization_name": leg.get("organization_name"),
            "model_definition_id": None,
            "model_name": leg.get("model_name"),
            "evaluator_name": leg.get("evaluator_name"),
            "consultant_name": leg.get("consultant_name"),
            "url": (leg.get("model_url_canonical")
                    or leg.get("model_url_hyperlink_target")
                    or leg.get("model_url_displayed") or leg.get("model_url")),
            "latest_evaluation": leg.get("arbitration_result_raw"),
            "legacy_evaluation": leg.get("evaluation_status"),
            "work_hours_legacy": _num(leg.get("total_arbitration_hours_raw")),
            "hours_level_legacy": "org_cohort_total_repeated_per_model_row",
            "linked_cohort": leg.get("cohort"),
            "arbitration_date_iso": leg.get("arbitration_date_iso"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if rev_id in matched_legacy_ids:
            # Legacy peer for a MATCHED crosswalk pair. Copy the same
            # match_status (VERSION_LINKED / PROBABLE / EXACT / REVIEW) from
            # the current-side canonical for symmetry.
            # (EXACT would MERGE, but we keep 2 canonicals for auditability
            #  and add a cross-link marking merger-eligibility.)
            base["match_status"] = "_pending_from_current_side"
        else:
            base["match_status"] = "LEGACY_ONLY"
            base["match_reason"] = "no_current_lovable_peer"
            base["confidence"] = 100
            counters["LEGACY_ONLY"] += 1
            crosswalks.append({
                "canonical_id": cid, "source": "legacy", "raw_id": rev_id,
                "match_reason": "no_current_lovable_peer",
                "confidence": 100, "evidence": [],
            })

        canonicals.append(base)

    # ---------- 6. Cross-link matched pairs (VERSION / PROBABLE / EXACT / REVIEW) ----------
    async for cw in coll("crosswalk_records").find({"crosswalk_status": "MATCHED_ORG_AND_MODEL"}, {"_id": 0}):
        mig = cw.get("current_migration_id")
        leg_id = cw.get("legacy_review_id")
        if not mig or not leg_id:
            continue
        cur_cid = cur_mig_to_cid.get(mig)
        leg_cid = leg_rev_to_cid.get(leg_id)
        if not cur_cid or not leg_cid:
            continue
        # Find the current-side canonical to copy its status onto legacy
        cur_can = next((c for c in canonicals if c["canonical_id"] == cur_cid), None)
        if not cur_can:
            continue
        status = cur_can.get("match_status")
        # Update the legacy canonical if still marked pending
        for lc in canonicals:
            if lc["canonical_id"] == leg_cid and lc.get("match_status") == "_pending_from_current_side":
                lc["match_status"] = status
                lc["match_reason"] = cur_can.get("match_reason")
                lc["confidence"] = cur_can.get("confidence")
                lc["linked_current_id"] = mig
                lc["linked_canonical_id"] = cur_cid
                # legacy record shouldn't emit a fresh crosswalk row here — it
                # already has the pair-context on the current-side entry
                crosswalks.append({
                    "canonical_id": leg_cid, "source": "legacy", "raw_id": leg_id,
                    "match_reason": cur_can.get("match_reason"),
                    "confidence": cur_can.get("confidence"),
                    "evidence": ["mirrored_from_current_side_pair"],
                })
                break
        # Persist the pair link
        links.append({
            "link_type": status,  # VERSION_LINKED / PROBABLE / EXACT / REVIEW
            "current_canonical_id": cur_cid,
            "legacy_canonical_id": leg_cid,
            "current_migration_id": mig,
            "legacy_review_id": leg_id,
            "reason": cur_can.get("match_reason"),
            "confidence": cur_can.get("confidence"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

    # Recount legacy sides that just got status inherited (they aren't in
    # counters yet, and CURRENT_ONLY/LEGACY_ONLY are already tallied above).
    for c in canonicals:
        if c.get("match_status") == "_pending_from_current_side":
            # Shouldn't happen — fall back to LEGACY_ONLY
            c["match_status"] = "LEGACY_ONLY"
            c["match_reason"] = "orphaned_after_pair_link"
            c["confidence"] = 60
            counters["LEGACY_ONLY"] += 1

    # ---------- 7. Duplicate-group summary ----------
    for gid, cid in emitted_cur_dup.items():
        members = [k for k, v in cur_dup_by_mig.items() if v == gid]
        if len(members) > 1:
            dupgroups.append({
                "group_id": gid, "canonical_id": cid,
                "kind": "lovable_duplicate_link",
                "member_raw_ids": members, "count": len(members),
                "confidence": 95,
            })
    for gid, cid in emitted_leg_dup.items():
        members = [k for k, v in leg_dup_by_rev.items() if v == gid]
        if len(members) > 1:
            dupgroups.append({
                "group_id": gid, "canonical_id": cid,
                "kind": "legacy_duplicate_link",
                "member_raw_ids": members, "count": len(members),
                "confidence": 95,
            })

    # ---------- 8. Persist ----------
    if canonicals:
        await coll("canonical_submissions").insert_many(canonicals, ordered=False)
    if crosswalks:
        await coll("record_crosswalks").insert_many(crosswalks, ordered=False)
    if dupgroups:
        await coll("duplicate_groups").insert_many(dupgroups, ordered=False)
    if links:
        await coll("canonical_links").insert_many(links, ordered=False)

    await db.canonical_submissions.create_index("canonical_id", unique=True)
    await db.canonical_submissions.create_index([("organization_id", 1)])
    await db.canonical_submissions.create_index([("match_status", 1)])
    await db.canonical_submissions.create_index([("primary_source", 1)])
    await db.record_crosswalks.create_index("canonical_id")
    await db.canonical_links.create_index([("current_canonical_id", 1)])
    await db.canonical_links.create_index([("legacy_canonical_id", 1)])

    # ---------- 9. Hours reconciliation ----------
    # Raw sums (before any dedup)
    raw_current_hours = 0.0
    n_cur_rows_h = 0
    for r in cur_by_mig.values():
        v = _num(r.get("work_hours")) or 0
        raw_current_hours += v
        if v > 0:
            n_cur_rows_h += 1
    raw_legacy_hours = 0.0
    n_leg_rows_h = 0
    for r in leg_by_rev.values():
        v = _num(r.get("total_arbitration_hours_raw")) or 0
        raw_legacy_hours += v
        if v > 0:
            n_leg_rows_h += 1

    # Deduped current hours: one representative per canonical (i.e., all rows
    # within an internal Lovable dup group collapse to one). Since each
    # canonical stores work_hours_current from the primary_source_id row, we
    # simply sum work_hours_current across current-primary canonicals.
    deduped_current_hours = 0.0
    for c in canonicals:
        if c.get("primary_source") == "current":
            deduped_current_hours += c.get("work_hours_current") or 0

    # Legacy: same idea, but legacy hours are ORG×COHORT totals repeated on
    # every row of that org. Two useful figures:
    #   (a) Naïve deduped: sum of the primary row per canonical (this still
    #       over-counts because org×cohort total repeats across models).
    #   (b) Per-(org,cohort) unique: take one representative hour per
    #       (legacy_org_id, cohort).
    deduped_legacy_hours_naive = 0.0
    per_org_cohort: dict[tuple, float] = {}
    for c in canonicals:
        if c.get("primary_source") == "legacy":
            v = c.get("work_hours_legacy") or 0
            deduped_legacy_hours_naive += v
            key = (c.get("organization_id"), c.get("linked_cohort"))
            if key not in per_org_cohort and v:
                per_org_cohort[key] = v
    deduped_legacy_hours_org_cohort = sum(per_org_cohort.values())

    # Legacy hours removed by cross-source merges: only EXACT triggers an actual
    # merge; in our current data that's 0.
    exact_pairs = counters["EXACT_CROSS_SOURCE_MATCH"]
    hours_removed_cross_source = 0.0  # 0 unless EXACT merges are implemented

    stats = {
        "raw_current_rows": len(cur_by_mig),
        "raw_legacy_rows": len(leg_by_rev),
        "raw_sum_naive": len(cur_by_mig) + len(leg_by_rev),
        "internal_dup_current_rows_collapsed": internal_dup_current_rows,
        "internal_dup_legacy_rows_collapsed": internal_dup_legacy_rows,
        "canonical_total": len(canonicals),
        "canonicals_from_current": sum(1 for c in canonicals if c.get("primary_source") == "current"),
        "canonicals_from_legacy": sum(1 for c in canonicals if c.get("primary_source") == "legacy"),
        "by_match_status": dict(counters),
        "cross_source_links_total": len(links),
        # HOURS
        "hours_raw_current_lovable": round(raw_current_hours, 1),
        "hours_raw_legacy": round(raw_legacy_hours, 1),
        "hours_deduped_current_lovable": round(deduped_current_hours, 1),
        "hours_deduped_legacy_naive": round(deduped_legacy_hours_naive, 1),
        "hours_deduped_legacy_per_org_cohort": round(deduped_legacy_hours_org_cohort, 1),
        "hours_removed_cross_source_merges": round(hours_removed_cross_source, 1),
        "hours_final_operational_provisional": round(
            deduped_current_hours + deduped_legacy_hours_org_cohort, 1
        ),
        "hours_notes": {
            "lovable_hours_level": "per_model arbitration effort (mean 0.65h, median 0.5h)",
            "legacy_hours_level": (
                "org × cohort total_arbitration_hours stamped on every model "
                "row (same value repeats across all models of one org in one "
                "cohort); safe unit is per_org_cohort dedup"
            ),
            "warning": (
                "hours_raw_current_lovable and hours_raw_legacy are NOT on the "
                "same unit and MUST NOT be summed naïvely."
            ),
        },
    }

    await coll("dedup_reports").insert_one({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "logic_version": "v3_strict_rules",
        "stats": stats,
    })
    return stats, {
        "cur_by_mig": cur_by_mig,
        "leg_by_rev": leg_by_rev,
        "cur_mig_to_cid": cur_mig_to_cid,
        "leg_rev_to_cid": leg_rev_to_cid,
    }


async def main():
    stats, _ = await build()
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
