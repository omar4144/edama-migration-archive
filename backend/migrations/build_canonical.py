"""
Canonical deduplication (v2) — uses the archive's pre-computed
`crosswalk_records` (1517 MATCHED_ORG_AND_MODEL pairs) as the authoritative
EXACT cross-source signal, since Lovable regenerates file IDs on migration
so URL-based matching alone is impossible (verified: 0 file_id intersection
between the 2565 current and 3403 legacy raw rows).

Then applies:
  - internal Lovable dedupe via `duplicate_link_group_id`
  - internal legacy dedupe via `historical_duplicate_links` (canonical_url)
  - remaining legacy rows → LEGACY_ONLY
  - crosswalk_status NO_DIRECT_MODEL_MATCH → REVIEW_REQUIRED

Never mutates raw data. Wipes only its derived collections.
"""
from __future__ import annotations
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ["EDAMA_MIGRATION_MODE"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from db import coll, get_db  # noqa: E402
from dedup import normalize_url  # noqa: E402


DERIVED = ("canonical_submissions", "record_crosswalks", "duplicate_groups",
           "canonical_reviews", "dedup_reports")


async def _reset():
    db = get_db()
    for name in DERIVED:
        await db[name].delete_many({})


def _num(v):
    try: return float(v) if v not in (None, "", "None") else None
    except (ValueError, TypeError): return None


async def build():
    await _reset()
    stats = {
        "raw_current": await coll("records_current").count_documents({}),
        "raw_legacy": await coll("historical_arbitrations").count_documents({}),
    }

    # ---------- Load current record duplicate groups (129 groups) ----------
    cur_dup_by_migration: dict[str, str] = {}
    async for g in coll("duplicate_links_current").find({}):
        gid = g.get("duplicate_link_group_id")
        migs = json.loads(g.get("migration_ids") or "[]") if isinstance(g.get("migration_ids"), str) else (g.get("migration_ids") or [])
        for m in migs:
            cur_dup_by_migration[m] = gid

    # ---------- Load legacy duplicate groups (67 groups) ----------
    leg_dup_by_review: dict[str, str] = {}
    async for g in coll("historical_duplicate_links").find({}):
        # legacy dup file has models/organizations but not review_ids directly;
        # match by canonical_url resource_id + org
        rid = g.get("resource_id")
        if not rid:
            continue
        gid = g.get("legacy_duplicate_group_id")
        # Find legacy arbitrations sharing this resource id
        cursor = coll("historical_arbitrations").find(
            {"model_url_resource_id": rid}, {"legacy_review_id": 1, "_id": 0})
        async for r in cursor:
            leg_dup_by_review[r["legacy_review_id"]] = gid

    # ---------- Iterate the crosswalk_records ledger (2565 rows) ----------
    # Track legacy_review_ids consumed by cross-source matches
    used_legacy: set[str] = set()
    canonicals: list[dict] = []
    crosswalks: list[dict] = []
    dupgroups: list[dict] = []
    # Track canonicals we've already emitted for a given Lovable dup group
    emitted_cur_dup: dict[str, str] = {}   # gid → canonical_id
    emitted_leg_dup: dict[str, str] = {}
    counters = {"exact_cross_source": 0, "current_only": 0, "review_required": 0,
                "legacy_only": 0, "internal_dup_current": 0, "internal_dup_legacy": 0}
    seq = 0
    def _cid():
        nonlocal seq
        seq += 1
        return f"CANON-{seq:06d}"

    async def _current_raw(mig):
        r = await coll("records_current").find_one({"migration_id": mig})
        r.pop("_id", None)
        return r

    async def _legacy_raw(rid):
        r = await coll("historical_arbitrations").find_one({"legacy_review_id": rid})
        r.pop("_id", None)
        return r

    async def _evaluator_name(cur):
        pid = cur.get("evaluator_person_id")
        if not pid: return None
        p = await coll("people").find_one({"person_id": pid}, {"person_name": 1, "_id": 0})
        return p.get("person_name") if p else None

    async for cw in coll("crosswalk_records").find({}):
        cw.pop("_id", None)
        mig = cw.get("current_migration_id")
        cur = await _current_raw(mig) if mig else None
        eval_name = await _evaluator_name(cur) if cur else None

        # If part of a Lovable duplicate group and we've already emitted a canonical
        # for that group, just add this row as another crosswalk member.
        cur_gid = cur_dup_by_migration.get(mig) if mig else None
        if cur_gid and cur_gid in emitted_cur_dup:
            cid = emitted_cur_dup[cur_gid]
            crosswalks.append({
                "canonical_id": cid, "source": "current", "raw_id": mig,
                "match_reason": "lovable_duplicate_group",
                "confidence": 95, "evidence": [f"dup_group={cur_gid}"],
            })
            counters["internal_dup_current"] += 1
            continue

        status = cw.get("crosswalk_status")
        cid = _cid()

        if status == "MATCHED_ORG_AND_MODEL" and cw.get("legacy_review_id"):
            leg_id = cw["legacy_review_id"]
            leg = await _legacy_raw(leg_id)
            used_legacy.add(leg_id)
            counters["exact_cross_source"] += 1
            # Legacy-side dup group?
            leg_gid = leg_dup_by_review.get(leg_id)
            member_ids = [mig, leg_id]
            canonicals.append({
                "canonical_id": cid,
                "organization_id": cw.get("current_org_id"),
                "organization_name": cw.get("current_organization_name"),
                "model_definition_id": cw.get("current_model_id"),
                "model_name": cw.get("current_model_name"),
                "evaluator_name": eval_name or cw.get("current_evaluator_name"),
                "consultant_name": cw.get("current_consultant_name"),
                "primary_source": "current", "primary_source_id": mig,
                "linked_legacy_id": leg_id, "linked_cohort": cw.get("legacy_cohort"),
                "url": cw.get("current_model_url"), "legacy_url": cw.get("legacy_model_url"),
                "latest_evaluation": cw.get("current_evaluation"),
                "legacy_evaluation": cw.get("legacy_evaluation_status") or leg.get("arbitration_result_raw"),
                "latest_status": cw.get("current_status"),
                "work_hours_current": _num(cw.get("current_work_hours")),
                "work_hours_legacy": _num(leg.get("total_arbitration_hours_raw")),
                "match_status": "EXACT_CROSS_SOURCE_MATCH",
                "match_reason": "crosswalk_matched_org_and_model",
                "confidence": 100,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
            crosswalks.append({"canonical_id": cid, "source": "current", "raw_id": mig,
                              "match_reason": "crosswalk_matched_org_and_model", "confidence": 100,
                              "evidence": ["archive_pre_matched"]})
            crosswalks.append({"canonical_id": cid, "source": "legacy", "raw_id": leg_id,
                              "match_reason": "crosswalk_matched_org_and_model", "confidence": 100,
                              "evidence": ["archive_pre_matched"]})
            if cur_gid: emitted_cur_dup[cur_gid] = cid
            if leg_gid: emitted_leg_dup[leg_gid] = cid

        elif status == "NO_LEGACY_ARBITRATION_RECORD":
            counters["current_only"] += 1
            canonicals.append({
                "canonical_id": cid,
                "organization_id": cw.get("current_org_id"),
                "organization_name": cw.get("current_organization_name"),
                "model_definition_id": cw.get("current_model_id"),
                "model_name": cw.get("current_model_name"),
                "evaluator_name": eval_name or cw.get("current_evaluator_name"),
                "consultant_name": cw.get("current_consultant_name"),
                "primary_source": "current", "primary_source_id": mig,
                "url": cw.get("current_model_url"),
                "latest_evaluation": cw.get("current_evaluation"),
                "latest_status": cw.get("current_status"),
                "work_hours_current": _num(cw.get("current_work_hours")),
                "match_status": "CURRENT_ONLY",
                "match_reason": "no_legacy_arbitration_record",
                "confidence": 100,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
            crosswalks.append({"canonical_id": cid, "source": "current", "raw_id": mig,
                              "match_reason": "no_legacy_arbitration_record", "confidence": 100,
                              "evidence": []})
            if cur_gid: emitted_cur_dup[cur_gid] = cid

        elif status == "NO_DIRECT_MODEL_MATCH":
            counters["review_required"] += 1
            canonicals.append({
                "canonical_id": cid,
                "organization_id": cw.get("current_org_id"),
                "organization_name": cw.get("current_organization_name"),
                "model_definition_id": cw.get("current_model_id"),
                "model_name": cw.get("current_model_name"),
                "evaluator_name": eval_name or cw.get("current_evaluator_name"),
                "consultant_name": cw.get("current_consultant_name"),
                "primary_source": "current", "primary_source_id": mig,
                "url": cw.get("current_model_url"),
                "latest_evaluation": cw.get("current_evaluation"),
                "match_status": "REVIEW_REQUIRED",
                "match_reason": "no_direct_model_match",
                "confidence": 40,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
            crosswalks.append({"canonical_id": cid, "source": "current", "raw_id": mig,
                              "match_reason": "no_direct_model_match", "confidence": 40,
                              "evidence": [f"raw_model_name={cw.get('current_model_name')}"]})
            if cur_gid: emitted_cur_dup[cur_gid] = cid

    # ---------- LEGACY_ONLY: arbitrations not consumed by crosswalk_records ----------
    async for leg in coll("historical_arbitrations").find({"legacy_review_id": {"$nin": list(used_legacy)}}):
        leg.pop("_id", None)
        leg_id = leg.get("legacy_review_id")
        leg_gid = leg_dup_by_review.get(leg_id)
        if leg_gid and leg_gid in emitted_leg_dup:
            cid = emitted_leg_dup[leg_gid]
            crosswalks.append({"canonical_id": cid, "source": "legacy", "raw_id": leg_id,
                              "match_reason": "legacy_duplicate_group", "confidence": 95,
                              "evidence": [f"dup_group={leg_gid}"]})
            counters["internal_dup_legacy"] += 1
            continue
        counters["legacy_only"] += 1
        cid = _cid()
        canonicals.append({
            "canonical_id": cid,
            "organization_id": leg.get("legacy_org_id"),
            "organization_name": leg.get("organization_name"),
            "model_definition_id": None,
            "model_name": leg.get("model_name"),
            "evaluator_name": leg.get("evaluator_name"),
            "consultant_name": leg.get("consultant_name"),
            "primary_source": "legacy", "primary_source_id": leg_id,
            "linked_cohort": leg.get("cohort"),
            "url": leg.get("model_url_canonical") or leg.get("model_url_hyperlink_target")
                   or leg.get("model_url_displayed") or leg.get("model_url"),
            "latest_evaluation": leg.get("arbitration_result_raw"),
            "legacy_evaluation": leg.get("evaluation_status"),
            "work_hours_legacy": _num(leg.get("total_arbitration_hours_raw")),
            "match_status": "LEGACY_ONLY",
            "match_reason": "no_current_lovable_record",
            "confidence": 100,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        })
        crosswalks.append({"canonical_id": cid, "source": "legacy", "raw_id": leg_id,
                          "match_reason": "no_current_lovable_record", "confidence": 100,
                          "evidence": []})
        if leg_gid: emitted_leg_dup[leg_gid] = cid

    # ---------- Duplicate groups summary ----------
    for gid, cid in emitted_cur_dup.items():
        members = [k for k, v in cur_dup_by_migration.items() if v == gid]
        if len(members) > 1:
            dupgroups.append({"group_id": gid, "canonical_id": cid,
                             "kind": "lovable_duplicate_link", "member_raw_ids": members,
                             "count": len(members), "confidence": 95})
    for gid, cid in emitted_leg_dup.items():
        members = [k for k, v in leg_dup_by_review.items() if v == gid]
        if len(members) > 1:
            dupgroups.append({"group_id": gid, "canonical_id": cid,
                             "kind": "legacy_duplicate_link", "member_raw_ids": members,
                             "count": len(members), "confidence": 95})

    # ---------- Persist ----------
    if canonicals: await coll("canonical_submissions").insert_many(canonicals, ordered=False)
    if crosswalks: await coll("record_crosswalks").insert_many(crosswalks, ordered=False)
    if dupgroups: await coll("duplicate_groups").insert_many(dupgroups, ordered=False)

    db = get_db()
    await db.canonical_submissions.create_index("canonical_id", unique=True)
    await db.canonical_submissions.create_index([("organization_id", 1)])
    await db.canonical_submissions.create_index([("match_status", 1)])
    await db.record_crosswalks.create_index("canonical_id")

    # ---------- Aggregate hours (operational: prefer current, fallback to legacy) ----------
    hours_operational = 0.0
    hours_current_raw = 0.0
    hours_legacy_raw = 0.0
    async for c in coll("canonical_submissions").find({}):
        cur_h = c.get("work_hours_current") or 0
        leg_h = c.get("work_hours_legacy") or 0
        hours_current_raw += cur_h or 0
        hours_legacy_raw += leg_h or 0
        # Operational rule: for EXACT_CROSS_SOURCE_MATCH, keep the CURRENT
        # (Lovable) as authoritative; both raw values preserved on the doc.
        hours_operational += cur_h if cur_h else leg_h

    stats.update({
        "canonical_total": len(canonicals),
        "exact_cross_source": counters["exact_cross_source"],
        "current_only": counters["current_only"],
        "review_required": counters["review_required"],
        "legacy_only": counters["legacy_only"],
        "internal_dup_current": counters["internal_dup_current"],
        "internal_dup_legacy": counters["internal_dup_legacy"],
        "duplicate_groups": len(dupgroups),
        "hours_operational_deduped": round(hours_operational, 1),
        "hours_current_raw_sum": round(hours_current_raw, 1),
        "hours_legacy_raw_sum": round(hours_legacy_raw, 1),
        "raw_sum_naive": stats["raw_current"] + stats["raw_legacy"],  # the wrong 5968
        "reduction_from_naive": stats["raw_current"] + stats["raw_legacy"] - len(canonicals),
    })

    await coll("dedup_reports").insert_one({
        "generated_at": datetime.now(timezone.utc).isoformat(), "stats": stats,
    })
    return stats


async def main():
    stats = await build()
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
