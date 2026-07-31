"""
Real data importer for the Edama archive.
Reads CSV/JSON sources into MongoDB, preserving raw fields.

Idempotent: re-running clears prior imported collections then reloads.
Never mutates the source archive. Historical collections are populated as
immutable snapshots (write-once semantics enforced by the app layer).
"""
from __future__ import annotations
import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Enable migration mode BEFORE importing db so the immutable guard is bypassed.
os.environ["EDAMA_MIGRATION_MODE"] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from db import coll, ensure_indexes, get_db  # noqa: E402


ARCHIVE = Path(os.environ.get("ARCHIVE_ROOT", "/app/data/archive"))
NORM = ARCHIVE / "Edama_Dashboard_Normalized_Data"
LOV = ARCHIVE / "lovable_current"


# --- reference targets from summary.json (contract-locked) --------------
EXPECTED = {
    "current_lovable_records": 2565,
    "current_lovable_organizations": 57,
    "people": 17,
    "model_definitions": 45,
    "work_hours_total": 1662.0,
    "legacy_organizations_total": 118,
    "legacy_consultant_activities_total": 3760,
    "legacy_arbitration_records_total": 3403,
    "legacy_duplicate_link_groups": 67,
    "batch_plan_rows": 120,
    "batch_kpi_snapshots": 4,
    "org_crosswalk_exact": 56,
    "org_crosswalk_legacy_only": 61,
    "org_crosswalk_probable": 1,
    "model_crosswalk_direct": 41,
    "model_crosswalk_candidate": 3,
    "record_crosswalk_matched": 1517,
    "record_crosswalk_no_model": 228,
    "record_crosswalk_no_legacy": 820,
}


def _read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _strip_empty(rec: dict) -> dict:
    """Normalize empty strings to None (keep raw structure otherwise)."""
    return {k: (v if v != "" else None) for k, v in rec.items()}


async def _wipe_and_load(name: str, rows: list[dict], *, extra_fields: dict | None = None) -> int:
    if not rows:
        return 0
    docs = []
    for r in rows:
        d = _strip_empty(r)
        if extra_fields:
            d.update(extra_fields)
        docs.append(d)
    c = coll(name)
    await c.delete_many({})
    if docs:
        await c.insert_many(docs, ordered=False)
    return len(docs)


async def load_lovable_current():
    """Authoritative current state from Lovable."""
    counts = {}

    # People (17)
    counts["people"] = await _wipe_and_load(
        "people", _read_csv(LOV / "people.csv"),
        extra_fields={"source_system": "lovable"},
    )

    # Model definitions (45)
    counts["model_definitions"] = await _wipe_and_load(
        "model_definitions", _read_csv(LOV / "model_catalog.csv"),
    )

    # Organizations (57)
    counts["organizations_current"] = await _wipe_and_load(
        "organizations_current", _read_csv(LOV / "organizations.csv"),
    )

    # Records (2565) — read JSON for typed fields
    with open(LOV / "edama_records.jsonl", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]
    for r in records:
        # Preserve raw. Coerce numeric fields softly.
        try:
            r["work_hours"] = float(r.get("work_hours") or 0)
        except (ValueError, TypeError):
            r["work_hours_raw"] = r.get("work_hours")
            r["work_hours"] = 0.0
    await coll("records_current").delete_many({})
    if records:
        await coll("records_current").insert_many(records, ordered=False)
    counts["records_current"] = len(records)

    # Duplicate links (current, 129 groups)
    counts["duplicate_links_current"] = await _wipe_and_load(
        "duplicate_links_current", _read_csv(LOV / "duplicate_links.csv"),
    )

    return counts


async def load_historical():
    """Immutable historical operational layer."""
    counts = {}

    counts["historical_organizations"] = await _wipe_and_load(
        "historical_organizations", _read_csv(NORM / "legacy_organizations.csv"),
    )
    counts["historical_activities"] = await _wipe_and_load(
        "historical_activities", _read_csv(NORM / "consultant_activities.csv"),
    )
    counts["historical_arbitrations"] = await _wipe_and_load(
        "historical_arbitrations", _read_csv(NORM / "legacy_arbitration_records.csv"),
    )
    counts["historical_duplicate_links"] = await _wipe_and_load(
        "historical_duplicate_links", _read_csv(NORM / "legacy_duplicate_links.csv"),
    )
    counts["historical_batch_plans"] = await _wipe_and_load(
        "historical_batch_plans", _read_csv(NORM / "batch_plans.csv"),
    )
    counts["historical_batch_kpis"] = await _wipe_and_load(
        "historical_batch_kpis", _read_csv(NORM / "batch_kpis.csv"),
    )
    return counts


async def load_crosswalks():
    counts = {}
    counts["crosswalk_organizations"] = await _wipe_and_load(
        "crosswalk_organizations", _read_csv(NORM / "organization_crosswalk.csv"),
    )
    counts["crosswalk_models"] = await _wipe_and_load(
        "crosswalk_models", _read_csv(NORM / "model_crosswalk.csv"),
    )
    counts["crosswalk_records"] = await _wipe_and_load(
        "crosswalk_records", _read_csv(NORM / "current_record_crosswalk.csv"),
    )
    counts["assignments"] = await _wipe_and_load(
        "assignments", _read_csv(NORM / "assignment_comparison.csv"),
    )
    counts["source_inventory"] = await _wipe_and_load(
        "source_inventory", _read_csv(NORM / "source_inventory.csv"),
    )
    counts["quality_checks"] = await _wipe_and_load(
        "quality_checks", _read_csv(NORM / "quality_checks.csv"),
    )
    return counts


async def build_review_queue():
    """
    Populate `mappings` collection with all REVIEW_REQUIRED items derived from
    crosswalks. No auto-merge. Every candidate has status='pending'.
    """
    await coll("mappings").delete_many({})
    items = []

    # Organization probable name variants
    async for row in coll("crosswalk_organizations").find(
        {"match_status": "PROBABLE_NAME_VARIANT"}
    ):
        items.append({
            "key": f"org::{row.get('current_org_id')}::{row.get('legacy_org_id')}",
            "kind": "organization_probable_match",
            "status": "pending",
            "current_id": row.get("current_org_id"),
            "current_name": row.get("current_organization_name"),
            "legacy_id": row.get("legacy_org_id"),
            "legacy_name": row.get("legacy_organization_name"),
            "score": row.get("match_score"),
            "cohort": row.get("legacy_cohort"),
            "decision": None,
            "decided_by": None,
            "decided_at": None,
            "note": None,
        })

    # Model evolved-schema candidates
    async for row in coll("crosswalk_models").find(
        {"crosswalk_status": "CANDIDATE_EVOLVED_SCHEMA"}
    ):
        items.append({
            "key": f"model::{row.get('legacy_model_name')}::{row.get('current_model_id')}",
            "kind": "model_evolved_schema",
            "status": "pending",
            "legacy_name": row.get("legacy_model_name"),
            "current_id": row.get("current_model_id"),
            "current_name": row.get("current_model_name"),
            "relationship": row.get("relationship"),
            "notes": row.get("notes"),
            "decision": None,
            "decided_by": None,
            "decided_at": None,
            "note": None,
        })

    # Assignment differences (evaluator changed)
    async for row in coll("assignments").find(
        {"evaluator_assignment_status": "CHANGED"}
    ):
        items.append({
            "key": f"assign::{row.get('current_org_id')}",
            "kind": "evaluator_assignment_changed",
            "status": "pending",
            "current_id": row.get("current_org_id"),
            "organization_name": row.get("organization_name"),
            "current_evaluator": row.get("current_evaluator"),
            "legacy_evaluator": row.get("legacy_evaluator"),
            "cohort": row.get("legacy_cohort"),
            "decision": None,
            "decided_by": None,
            "decided_at": None,
            "note": None,
        })

    if items:
        await coll("mappings").insert_many(items, ordered=False)
    return len(items)


async def verify_counts(counts: dict) -> tuple[list, list]:
    """Compare observed counts vs. contract-locked expected values."""
    checks = [
        ("current_lovable_records", counts.get("records_current")),
        ("current_lovable_organizations", counts.get("organizations_current")),
        ("people", counts.get("people")),
        ("model_definitions", counts.get("model_definitions")),
        ("legacy_organizations_total", counts.get("historical_organizations")),
        ("legacy_consultant_activities_total", counts.get("historical_activities")),
        ("legacy_arbitration_records_total", counts.get("historical_arbitrations")),
        ("legacy_duplicate_link_groups", counts.get("historical_duplicate_links")),
        ("batch_plan_rows", counts.get("historical_batch_plans")),
        ("batch_kpi_snapshots", counts.get("historical_batch_kpis")),
    ]
    passes, fails = [], []
    for key, actual in checks:
        expected = EXPECTED.get(key)
        ok = actual == expected
        (passes if ok else fails).append({
            "check": key, "expected": expected, "actual": actual, "status": "PASS" if ok else "FAIL",
        })
    return passes, fails


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-auth", action="store_true", help="Also seed auth accounts")
    args = parser.parse_args()

    await ensure_indexes()
    counts = {}
    counts.update(await load_lovable_current())
    counts.update(await load_historical())
    counts.update(await load_crosswalks())
    review_count = await build_review_queue()
    counts["mappings_review_queue"] = review_count

    # Sum current work hours from actual records
    pipe = [{"$group": {"_id": None, "total": {"$sum": "$work_hours"}}}]
    agg = await coll("records_current").aggregate(pipe).to_list(1)
    total_hours = float(agg[0]["total"]) if agg else 0.0
    counts["work_hours_total"] = total_hours

    passes, fails = await verify_counts(counts)

    # Persist reconciliation report
    report = {
        "id": f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": counts,
        "expected": EXPECTED,
        "checks_passed": passes,
        "checks_failed": fails,
        "status": "PASS" if not fails else "FAIL",
    }
    await coll("migration_runs").insert_one(report.copy())

    print(json.dumps({
        "counts": counts,
        "checks_passed": len(passes),
        "checks_failed": len(fails),
        "status": report["status"],
        "review_queue_pending": review_count,
        "current_work_hours_total": total_hours,
    }, ensure_ascii=False, indent=2))
    if fails:
        print("\nFAILED CHECKS:")
        print(json.dumps(fails, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
