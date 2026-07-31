"""
Canonical deduplication (v4 — Submission Families).

Adds on top of v3 strict rules:
  - Correct decision vocabulary via `decisions.py`
    (المجاز/غير مجاز/مجاز مع تحفظ mapped to APPROVED/REJECTED/APPROVED_WITH_RESERVATION;
     مقبول/يحتاج لتطوير are current; غير مكتمل/مكتمل are completion, NOT decisions).
  - `decision_normalized` and `completion_status` stored separately.
  - `canonical_submission_families` collection: groups canonicals belonging to
    the same (organization, model_definition) journey — legacy attempts +
    later current submission(s) chained under one family, with:
        family_id, organization_id, model_definition_id/model_key,
        versions[canonical_ids sorted by date],
        latest_canonical_id / latest_decision / latest_completion_status,
        earliest_arbitration_date / latest_submission_date,
        version_count, has_review_required.

Never mutates raw data. Wipes only its own derived collections.
"""
from __future__ import annotations
import asyncio
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone, date as _date
from pathlib import Path

os.environ["EDAMA_MIGRATION_MODE"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from db import coll, get_db  # noqa: E402
from decisions import (  # noqa: E402
    normalize_current, normalize_legacy, classify_decision_transition,
    DECISION_APPROVED, DECISION_REJECTED, DECISION_NEEDS_IMPROVEMENT,
    DECISION_APPROVED_RESERVED,
    COMPLETION_INCOMPLETE,
)


DERIVED = (
    "canonical_submissions",
    "record_crosswalks",
    "duplicate_groups",
    "canonical_reviews",
    "dedup_reports",
    "canonical_links",
    "canonical_submission_families",  # NEW
)


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


_MODEL_KEY_STRIP = re.compile(r"[\s\u200f\u200e\u064b-\u065f]+")


def _model_key(model_id: str | None, model_name: str | None) -> str:
    """Family key component for the model side. Uses model_definition_id
    when available; falls back to a normalized Arabic name."""
    if model_id:
        return f"MID:{model_id}"
    if not model_name:
        return "MID:UNKNOWN"
    v = unicodedata.normalize("NFKC", model_name).strip()
    # Strip diacritics (tashkil range) & collapse whitespace
    v = _MODEL_KEY_STRIP.sub(" ", v)
    v = re.sub(r"\s+", " ", v).strip()
    return f"MNAME:{v}"


def _classify_pair(cw: dict, cur: dict, leg: dict) -> tuple[str, str, int, list[str], dict]:
    """Return (match_status, match_reason, confidence, evidence_list, extras)
    for a MATCHED_ORG_AND_MODEL crosswalk row.

    `extras` carries decision_normalized / completion_status for both sides so
    the caller can store them on the canonical.
    """
    ev = ["archive_org_and_model_matched"]
    ec = (cw.get("current_evaluator_name") or "").strip()
    el = (cw.get("legacy_evaluator_name") or "").strip()
    cc = (cw.get("current_consultant_name") or "").strip()
    cl = (cw.get("legacy_consultant_name") or "").strip()

    cur_dec, cur_comp = normalize_current(cur.get("evaluation"))
    leg_dec, leg_comp = normalize_legacy(
        leg.get("arbitration_result_raw"),
        leg.get("evaluation_status"),
    )
    trans = classify_decision_transition(leg_dec, leg_comp, cur_dec, cur_comp)

    cd = _parse_date(cur.get("submitted_at_iso"))
    ld = _parse_date(leg.get("arbitration_date_iso") or leg.get("arbitration_date_source_iso"))
    diff = _date_diff_days(cd, ld)

    evaluator_ok = bool(ec) and bool(el) and ec == el
    if evaluator_ok:
        ev.append(f"evaluator_matched={ec}")
    else:
        ev.append(f"evaluator_mismatch(current='{ec or '∅'}' legacy='{el or '∅'}')")

    if cc and cl:
        ev.append("consultant_matched" if cc == cl else f"consultant_mismatch(current='{cc}' legacy='{cl}')")
    elif cc or cl:
        ev.append(f"consultant_partial(current='{cc or '∅'}' legacy='{cl or '∅'}')")

    ev.append(f"decision_transition={trans}(c={cur_dec or ('completion:' + (cur_comp or '∅'))},l={leg_dec or ('completion:' + (leg_comp or '∅'))})")
    ev.append(f"dates(c={cd or '∅'},l={ld or '∅'},diff={diff if diff is not None else '∅'})")

    extras = {
        "decision_normalized_current": cur_dec,
        "decision_normalized_legacy": leg_dec,
        "completion_status_current": cur_comp,
        "completion_status_legacy": leg_comp,
        "decision_transition": trans,
    }

    # ---------- Rule tree ----------
    if diff is None:
        if evaluator_ok and trans in ("same_decision", "version_resubmit", "completion_then_result"):
            return ("REVIEW_REQUIRED", "missing_date_no_auto_merge", 45, ev, extras)
        return ("REVIEW_REQUIRED", "missing_date_and_uncertain", 30, ev, extras)

    if not evaluator_ok:
        # Bulk policy AUTO_LINK_EVALUATOR_REASSIGNMENT: evaluator differing
        # across the two sources is NOT a review trigger on its own — it is a
        # re-assignment of arbiter over time. The Lovable evaluator is the
        # current operational assignment; the legacy evaluator is preserved in
        # the timeline as "المحكم السابق". We downgrade the gate to a soft
        # signal that flavors the reason string in every downstream branch.
        evaluator_tag = "_evaluator_reassigned"
    else:
        evaluator_tag = ""

    # Version pattern (regardless of date-gap size) — resubmission after a
    # negative outcome, or completion→arbitration transition.
    if diff > 3 and trans in ("version_resubmit", "completion_then_result"):
        return ("VERSION_LINKED", f"resubmission_{trans}{evaluator_tag}", 90, ev, extras)

    if diff == 0 and trans == "same_decision" and evaluator_ok:
        return ("EXACT_CROSS_SOURCE_MATCH", "composite_path_same_date_same_decision", 100, ev, extras)

    if 1 <= diff <= 3 and trans in ("same_decision", "version_resubmit", "completion_then_result"):
        return ("PROBABLE_CROSS_SOURCE_MATCH", f"close_dates_compatible_decisions{evaluator_tag}", 70, ev, extras)

    if diff > 3 and trans == "conflict":
        # Wide-gap conflicting decisions remain review-worthy — the disagreement
        # itself is the problem, not the evaluator assignment.
        return ("REVIEW_REQUIRED", "wide_gap_conflicting_decisions", 40, ev, extras)
    if diff > 3 and trans == "same_decision":
        # Bulk policies applied here:
        #   AUTO_APPROVE_WIDE_GAP_IDENTICAL (same evaluator + same decision)
        #   AUTO_LINK_EVALUATOR_REASSIGNMENT (different evaluator + same decision)
        if evaluator_ok:
            return ("VERSION_LINKED", "auto_approved_identical_after_wide_gap", 85, ev, extras)
        return ("VERSION_LINKED", "auto_linked_evaluator_reassignment", 80, ev, extras)
    if trans == "unknown":
        return ("REVIEW_REQUIRED", "unknown_decision_state", 35, ev, extras)

    return ("REVIEW_REQUIRED", "unclassified_pair", 40, ev, extras)


async def _reset():
    db = get_db()
    for name in DERIVED:
        await db[name].delete_many({})


async def build():  # noqa: C901
    await _reset()
    db = get_db()

    # ---------- 1. Raw rows ----------
    cur_by_mig: dict[str, dict] = {}
    async for r in coll("records_current").find({}, {"_id": 0}):
        cur_by_mig[r["migration_id"]] = r
    leg_by_rev: dict[str, dict] = {}
    async for r in coll("historical_arbitrations").find({}, {"_id": 0}):
        leg_by_rev[r["legacy_review_id"]] = r

    # ---------- 2. Internal dup maps ----------
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

    # ---------- 3. Crosswalk index ----------
    cw_by_mig: dict[str, dict] = {}
    matched_legacy_ids: set[str] = set()
    async for cw in coll("crosswalk_records").find({}, {"_id": 0}):
        mig = cw.get("current_migration_id")
        if mig:
            cw_by_mig[mig] = cw
        if cw.get("crosswalk_status") == "MATCHED_ORG_AND_MODEL" and cw.get("legacy_review_id"):
            matched_legacy_ids.add(cw["legacy_review_id"])

    person_name_by_id: dict[str, str] = {}
    async for p in coll("people").find({}, {"person_id": 1, "person_name": 1, "_id": 0}):
        person_name_by_id[p["person_id"]] = p.get("person_name")

    def _resolve_eval_name(cur: dict) -> str | None:
        return person_name_by_id.get(cur.get("evaluator_person_id"))

    # ---------- 4. CURRENT-side canonicals ----------
    canonicals: list[dict] = []
    crosswalks: list[dict] = []
    links: list[dict] = []
    dupgroups: list[dict] = []

    emitted_cur_dup: dict[str, str] = {}
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
    review_reason_counts: dict[str, int] = {}
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
        cur_dec, cur_comp = normalize_current(cur.get("evaluation"))

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
            "raw_evaluation_current": cw.get("current_evaluation") or cur.get("evaluation"),
            "decision_normalized_current": cur_dec,
            "completion_status_current": cur_comp,
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
            review_reason_counts["no_direct_model_match_only_org"] = \
                review_reason_counts.get("no_direct_model_match_only_org", 0) + 1
            crosswalks.append({
                "canonical_id": cid, "source": "current", "raw_id": mig,
                "match_reason": "no_direct_model_match_only_org",
                "confidence": 40, "evidence": [f"raw_model_name={base['model_name']}"],
            })

        elif status == "MATCHED_ORG_AND_MODEL" and cw.get("legacy_review_id"):
            leg_id = cw["legacy_review_id"]
            leg = leg_by_rev.get(leg_id, {})
            match_status, reason, conf, evidence, extras = _classify_pair(cw, cur, leg)
            base.update({
                "match_status": match_status,
                "match_reason": reason,
                "confidence": conf,
                "linked_legacy_id": leg_id,
                "raw_evaluation_legacy": leg.get("arbitration_result_raw"),
                "raw_evaluation_status_legacy": leg.get("evaluation_status"),
                "decision_normalized_legacy": extras["decision_normalized_legacy"],
                "completion_status_legacy": extras["completion_status_legacy"],
                "decision_transition": extras["decision_transition"],
                "work_hours_legacy": _num(leg.get("total_arbitration_hours_raw")),
                "hours_level_legacy": "org_cohort_total_repeated_per_model_row",
                "legacy_url": cw.get("legacy_model_url"),
                "linked_cohort": cw.get("legacy_cohort"),
            })
            counters[match_status] += 1
            if match_status == "REVIEW_REQUIRED":
                review_reason_counts[reason] = review_reason_counts.get(reason, 0) + 1
            crosswalks.append({
                "canonical_id": cid, "source": "current", "raw_id": mig,
                "match_reason": reason, "confidence": conf, "evidence": evidence,
            })
        else:
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

    # ---------- 5. LEGACY-side canonicals ----------
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

        leg_dec, leg_comp = normalize_legacy(
            leg.get("arbitration_result_raw"), leg.get("evaluation_status")
        )
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
            "raw_evaluation_legacy": leg.get("arbitration_result_raw"),
            "raw_evaluation_status_legacy": leg.get("evaluation_status"),
            "decision_normalized_legacy": leg_dec,
            "completion_status_legacy": leg_comp,
            "work_hours_legacy": _num(leg.get("total_arbitration_hours_raw")),
            "hours_level_legacy": "org_cohort_total_repeated_per_model_row",
            "linked_cohort": leg.get("cohort"),
            "arbitration_date_iso": (leg.get("arbitration_date_iso")
                                     or leg.get("arbitration_date_source_iso")),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        if rev_id in matched_legacy_ids:
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

    # ---------- 6. Cross-link matched pairs ----------
    canonicals_by_cid = {c["canonical_id"]: c for c in canonicals}
    async for cw in coll("crosswalk_records").find({"crosswalk_status": "MATCHED_ORG_AND_MODEL"}, {"_id": 0}):
        mig = cw.get("current_migration_id")
        leg_id = cw.get("legacy_review_id")
        if not mig or not leg_id:
            continue
        cur_cid = cur_mig_to_cid.get(mig)
        leg_cid = leg_rev_to_cid.get(leg_id)
        if not cur_cid or not leg_cid:
            continue
        cur_can = canonicals_by_cid.get(cur_cid)
        if not cur_can:
            continue
        status = cur_can.get("match_status")
        reason = cur_can.get("match_reason")
        conf = cur_can.get("confidence")

        leg_can = canonicals_by_cid.get(leg_cid)
        if leg_can and leg_can.get("match_status") == "_pending_from_current_side":
            leg_can["match_status"] = status
            leg_can["match_reason"] = reason
            leg_can["confidence"] = conf
            leg_can["decision_transition"] = cur_can.get("decision_transition")
            leg_can["linked_current_id"] = mig
            leg_can["linked_canonical_id"] = cur_cid
            crosswalks.append({
                "canonical_id": leg_cid, "source": "legacy", "raw_id": leg_id,
                "match_reason": reason, "confidence": conf,
                "evidence": ["mirrored_from_current_side_pair"],
            })
        links.append({
            "link_type": status,
            "current_canonical_id": cur_cid,
            "legacy_canonical_id": leg_cid,
            "current_migration_id": mig,
            "legacy_review_id": leg_id,
            "reason": reason,
            "confidence": conf,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

    for c in canonicals:
        if c.get("match_status") == "_pending_from_current_side":
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

    # ---------- 8. Submission Families ----------
    #
    # Family = distinct (organization_id, model_key) journey. Includes:
    #   - legacy version(s) attempted for that (org, model)
    #   - the later current submission(s)
    #   - version links binding them into one lifeline
    #
    # Family key derivation:
    #   * current-side canonical: MID:<model_definition_id>
    #   * legacy peer (via link): inherits current's MID
    #   * pure legacy canonical: MNAME:<normalized model_name>
    #
    # After grouping, we detect family_key collisions between (MID) and
    # (MNAME) families of the same org — if a MNAME family shares model_name
    # with a MID family already collected, we fold it in.
    fam_current_side: dict[tuple, dict] = {}
    fam_legacy_only: dict[tuple, dict] = {}

    # First pass — current-side canonicals establish MID families
    for c in canonicals:
        if c.get("primary_source") != "current":
            continue
        key = (c.get("organization_id"),
               _model_key(c.get("model_definition_id"), c.get("model_name")))
        fam = fam_current_side.setdefault(key, {
            "organization_id": c.get("organization_id"),
            "organization_name": c.get("organization_name"),
            "model_definition_id": c.get("model_definition_id"),
            "model_key": key[1],
            "model_name": c.get("model_name"),
            "canonical_ids": [],
        })
        fam["canonical_ids"].append(c["canonical_id"])

    # Second pass — legacy canonicals. If linked to a current canonical, join
    # its family; else form legacy-only families.
    for c in canonicals:
        if c.get("primary_source") != "legacy":
            continue
        cid = c["canonical_id"]
        # linked_canonical_id set during pair-link if this legacy was matched
        linked = c.get("linked_canonical_id")
        joined = False
        if linked:
            # Find the current-side family that contains linked
            for key, fam in fam_current_side.items():
                if linked in fam["canonical_ids"]:
                    fam["canonical_ids"].append(cid)
                    joined = True
                    break
        if joined:
            continue
        key = (c.get("organization_id"),
               _model_key(None, c.get("model_name")))
        fam = fam_legacy_only.setdefault(key, {
            "organization_id": c.get("organization_id"),
            "organization_name": c.get("organization_name"),
            "model_definition_id": None,
            "model_key": key[1],
            "model_name": c.get("model_name"),
            "canonical_ids": [],
        })
        fam["canonical_ids"].append(cid)

    # Optional 3rd pass: fold legacy-only families into current-side families
    # if same (org, model_name normalized) appears — legacy peers whose model
    # wasn't matched by crosswalk but obviously share the same model.
    # Build lookup: (org, MNAME:x) → current-side family_key
    cur_by_name: dict[tuple, tuple] = {}
    for key, fam in fam_current_side.items():
        norm = _model_key(None, fam.get("model_name"))
        cur_by_name.setdefault((fam["organization_id"], norm), key)
    merged_legacy_keys = []
    for lkey, lfam in list(fam_legacy_only.items()):
        alt = cur_by_name.get(lkey)
        if alt:
            fam_current_side[alt]["canonical_ids"].extend(lfam["canonical_ids"])
            merged_legacy_keys.append(lkey)
    for k in merged_legacy_keys:
        fam_legacy_only.pop(k, None)

    # Now materialize family docs with lifecycle info
    families: list[dict] = []
    fam_seq = 0

    def _fid():
        nonlocal fam_seq
        fam_seq += 1
        return f"FAM-{fam_seq:06d}"

    canonicals_by_cid = {c["canonical_id"]: c for c in canonicals}
    for fam in list(fam_current_side.values()) + list(fam_legacy_only.values()):
        cids = fam["canonical_ids"]
        cans = [canonicals_by_cid[c] for c in cids]
        # Sort by best available timestamp
        def _sort_key(x):
            return (
                x.get("submitted_at_iso") or x.get("arbitration_date_iso") or "",
                x.get("canonical_id"),
            )
        cans.sort(key=_sort_key)
        latest = cans[-1]
        earliest = cans[0]
        version_count = len(cans)
        has_review = any(c.get("match_status") == "REVIEW_REQUIRED" for c in cans)
        has_current = any(c.get("primary_source") == "current" for c in cans)
        has_legacy = any(c.get("primary_source") == "legacy" for c in cans)
        distinct_dates = sorted({
            (c.get("submitted_at_iso") or c.get("arbitration_date_iso") or "")[:10]
            for c in cans if (c.get("submitted_at_iso") or c.get("arbitration_date_iso"))
        })
        # Latest OPERATIONAL result: prefer the latest current-side canonical
        cur_cans = [c for c in cans if c.get("primary_source") == "current"]
        latest_current = cur_cans[-1] if cur_cans else None
        families.append({
            "family_id": _fid(),
            "organization_id": fam["organization_id"],
            "organization_name": fam["organization_name"],
            "model_definition_id": fam["model_definition_id"],
            "model_key": fam["model_key"],
            "model_name": fam["model_name"],
            "version_canonical_ids": [c["canonical_id"] for c in cans],
            "version_count": version_count,
            "has_current_version": has_current,
            "has_legacy_version": has_legacy,
            "has_review_required": has_review,
            "earliest_date": (earliest.get("submitted_at_iso") or earliest.get("arbitration_date_iso") or None),
            "latest_date": (latest.get("submitted_at_iso") or latest.get("arbitration_date_iso") or None),
            "distinct_dates": distinct_dates,
            "latest_canonical_id": (latest_current or latest).get("canonical_id"),
            "latest_decision": ((latest_current or latest).get("decision_normalized_current")
                                or (latest_current or latest).get("decision_normalized_legacy")),
            "latest_completion_status": ((latest_current or latest).get("completion_status_current")
                                         or (latest_current or latest).get("completion_status_legacy")),
            "latest_evaluator_name": (latest_current or latest).get("evaluator_name"),
            "latest_hours_current": (latest_current or {}).get("work_hours_current"),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })

    # Assign family_id back into each canonical
    for f in families:
        for cid in f["version_canonical_ids"]:
            can = canonicals_by_cid.get(cid)
            if can:
                can["family_id"] = f["family_id"]

    # ---------- 9. Persist ----------
    if canonicals:
        await coll("canonical_submissions").insert_many(canonicals, ordered=False)
    if crosswalks:
        await coll("record_crosswalks").insert_many(crosswalks, ordered=False)
    if dupgroups:
        await coll("duplicate_groups").insert_many(dupgroups, ordered=False)
    if links:
        await coll("canonical_links").insert_many(links, ordered=False)
    if families:
        await coll("canonical_submission_families").insert_many(families, ordered=False)

    await db.canonical_submissions.create_index("canonical_id", unique=True)
    await db.canonical_submissions.create_index([("organization_id", 1)])
    await db.canonical_submissions.create_index([("match_status", 1)])
    await db.canonical_submissions.create_index([("primary_source", 1)])
    await db.canonical_submissions.create_index([("family_id", 1)])
    await db.record_crosswalks.create_index("canonical_id")
    await db.canonical_links.create_index([("current_canonical_id", 1)])
    await db.canonical_links.create_index([("legacy_canonical_id", 1)])
    await db.canonical_submission_families.create_index("family_id", unique=True)
    await db.canonical_submission_families.create_index([("organization_id", 1)])
    await db.canonical_submission_families.create_index([("model_definition_id", 1)])

    # ---------- 10. Hours reconciliation ----------
    raw_current_hours = sum((_num(r.get("work_hours")) or 0) for r in cur_by_mig.values())
    raw_legacy_hours = sum((_num(r.get("total_arbitration_hours_raw")) or 0) for r in leg_by_rev.values())

    deduped_current_hours = sum(
        (c.get("work_hours_current") or 0) for c in canonicals
        if c.get("primary_source") == "current"
    )
    deduped_legacy_hours_naive = sum(
        (c.get("work_hours_legacy") or 0) for c in canonicals
        if c.get("primary_source") == "legacy"
    )
    per_org_cohort: dict[tuple, float] = {}
    for c in canonicals:
        if c.get("primary_source") == "legacy":
            v = c.get("work_hours_legacy") or 0
            key = (c.get("organization_id"), c.get("linked_cohort"))
            if v and key not in per_org_cohort:
                per_org_cohort[key] = v
    deduped_legacy_hours_org_cohort = sum(per_org_cohort.values())

    # ---------- 11. Three-count summary ----------
    counts_three = {
        "families_count": len(families),
        "versions_count": len(canonicals),
        "latest_operational_count": len(families),  # one latest per family
    }

    # Distribution of latest_decision across families
    latest_decision_dist: dict[str, int] = {}
    latest_completion_dist: dict[str, int] = {}
    for f in families:
        d = f.get("latest_decision") or "UNKNOWN"
        latest_decision_dist[d] = latest_decision_dist.get(d, 0) + 1
        c = f.get("latest_completion_status") or "UNKNOWN"
        latest_completion_dist[c] = latest_completion_dist.get(c, 0) + 1

    families_with_lifecycle = sum(
        1 for f in families if f["has_current_version"] and f["has_legacy_version"]
    )
    families_current_only = sum(1 for f in families if f["has_current_version"] and not f["has_legacy_version"])
    families_legacy_only = sum(1 for f in families if f["has_legacy_version"] and not f["has_current_version"])
    families_with_review = sum(1 for f in families if f["has_review_required"])

    stats = {
        "logic_version": "v4_families_and_decisions",
        "raw_current_rows": len(cur_by_mig),
        "raw_legacy_rows": len(leg_by_rev),
        "raw_sum_naive": len(cur_by_mig) + len(leg_by_rev),
        "internal_dup_current_rows_collapsed": internal_dup_current_rows,
        "internal_dup_legacy_rows_collapsed": internal_dup_legacy_rows,
        "canonical_total": len(canonicals),
        "canonicals_from_current": sum(1 for c in canonicals if c.get("primary_source") == "current"),
        "canonicals_from_legacy": sum(1 for c in canonicals if c.get("primary_source") == "legacy"),
        "by_match_status_current_side": dict(counters),
        "review_required_by_reason": review_reason_counts,
        "cross_source_links_total": len(links),
        "counts_three": counts_three,
        "families_with_full_lifecycle_legacy_and_current": families_with_lifecycle,
        "families_current_only": families_current_only,
        "families_legacy_only": families_legacy_only,
        "families_with_any_review_required": families_with_review,
        "latest_decision_distribution": latest_decision_dist,
        "latest_completion_distribution": latest_completion_dist,
        "hours_raw_current_lovable": round(raw_current_hours, 1),
        "hours_raw_legacy": round(raw_legacy_hours, 1),
        "hours_deduped_current_lovable_per_model": round(deduped_current_hours, 1),
        "hours_deduped_legacy_naive": round(deduped_legacy_hours_naive, 1),
        "hours_deduped_legacy_per_org_cohort": round(deduped_legacy_hours_org_cohort, 1),
        "hours_notes": {
            "lovable_hours_level": "per_model arbitration effort (mean 0.65h, median 0.5h)",
            "legacy_hours_level": (
                "org × cohort total_arbitration_hours stamped on every model row"
            ),
            "warning": (
                "Never sum current-hours + legacy-hours — different measurement units."
            ),
        },
    }

    await coll("dedup_reports").insert_one({
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "logic_version": "v4_families_and_decisions",
        "policy_applied": "AUTO_APPROVE_WIDE_GAP_IDENTICAL",
        "stats": stats,
    })

    # Bulk-decision audit entry (not attributed to any user — bulk rule)
    await coll("review_audit_log").insert_one({
        "at": datetime.now(timezone.utc).isoformat(),
        "kind": "bulk_policy_applied",
        "action": "AUTO_APPROVE_WIDE_GAP_IDENTICAL",
        "policy_reason": "same_org_model_normalized_decision — wide date gap alone is not a review trigger",
        "previous_reason": "wide_gap_identical_decision",
        "previous_status": "REVIEW_REQUIRED",
        "new_status": "VERSION_LINKED",
        "new_reason": "auto_approved_identical_after_wide_gap",
        "actor_email": "SYSTEM",
        "actor_id": None,
    })
    await coll("review_audit_log").insert_one({
        "at": datetime.now(timezone.utc).isoformat(),
        "kind": "bulk_policy_applied",
        "action": "AUTO_LINK_EVALUATOR_REASSIGNMENT",
        "policy_reason": "lovable_evaluator_is_current_assignment — evaluator differing alone is not a review trigger",
        "previous_reason": "evaluator_mismatch_cross_source",
        "previous_status": "REVIEW_REQUIRED",
        "new_status": "VERSION_LINKED",
        "new_reason": "auto_linked_evaluator_reassignment (+ _evaluator_reassigned suffix on version_resubmit/completion_then_result)",
        "actor_email": "SYSTEM",
        "actor_id": None,
    })
    return stats


async def main():
    stats = await build()
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
