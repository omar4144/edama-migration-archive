"""Unified helpers: URL resolution, record shape, source badge classification."""
from typing import Any


URL_KEYS_PRIORITY = (
    "model_url_canonical",
    "model_url_hyperlink_target",
    "model_url_displayed",
    "model_url",
    "canonical_url",
    "current_model_url",
    "legacy_model_url",
)


def resolve_url(rec: dict | None) -> str | None:
    if not rec:
        return None
    for k in URL_KEYS_PRIORITY:
        v = rec.get(k)
        if v and isinstance(v, str) and v.strip():
            return v.strip()
    return None


def unified_record(rec: dict, kind: str) -> dict:
    """Project either a records_current or historical_arbitrations doc into a
    single unified shape used by the models hub / detail views. `kind` is
    'current' or 'legacy'. Source label is `kind` — treated as a badge inside
    detail views, not as a top-level filter."""
    if kind == "current":
        return {
            "id": rec.get("migration_id"),
            "source": "current",
            "cohort": None,  # current records don't carry cohort — org has it
            "organization_id": rec.get("organization_id"),
            "organization_name": rec.get("organization_name"),
            "model_definition_id": rec.get("model_definition_id"),
            "model_name": rec.get("model_name"),
            "category": rec.get("category"),
            "consultant_name": rec.get("consultant_name"),
            "consultant_person_id": rec.get("consultant_person_id"),
            "evaluator_name": None,  # resolved by caller from person_id
            "evaluator_person_id": rec.get("evaluator_person_id"),
            "status": rec.get("status"),
            "evaluation": rec.get("evaluation"),
            "work_hours": rec.get("work_hours"),
            "notes": rec.get("notes"),
            "submitted_at": rec.get("submitted_at_iso"),
            "decided_at": rec.get("modified_at_iso"),
            "url": resolve_url(rec),
            "url_domain": rec.get("url_domain"),
            "url_check": rec.get("url_check"),
            "duplicate_link_group_id": rec.get("duplicate_link_group_id"),
            "duplicate_use_count": rec.get("duplicate_link_use_count"),
            "verification_status": rec.get("verification_status"),
            "raw_source": {
                "system": rec.get("source_system"),
                "file": rec.get("source_file"),
                "sheet": rec.get("source_sheet"),
                "row": rec.get("source_row_number"),
                "account": rec.get("source_account"),
            },
        }
    # legacy arbitration
    return {
        "id": rec.get("legacy_review_id"),
        "source": "legacy",
        "cohort": rec.get("cohort"),
        "organization_id": rec.get("legacy_org_id"),
        "organization_name": rec.get("organization_name"),
        "model_definition_id": None,
        "model_name": rec.get("model_name"),
        "category": rec.get("category"),
        "consultant_name": rec.get("consultant_name"),
        "consultant_person_id": None,
        "evaluator_name": rec.get("evaluator_name"),
        "evaluator_person_id": None,
        "status": rec.get("evaluation_status"),
        "evaluation": rec.get("arbitration_result") or rec.get("arbitration_result_raw"),
        "work_hours": _num(rec.get("total_arbitration_hours") or rec.get("total_arbitration_hours_raw")),
        "notes": rec.get("note"),
        "submitted_at": None,
        "decided_at": rec.get("arbitration_date_iso") or rec.get("arbitration_date_source_iso"),
        "url": resolve_url(rec),
        "url_domain": rec.get("model_url_domain"),
        "url_check": None,
        "duplicate_link_group_id": None,
        "duplicate_use_count": None,
        "verification_status": None,
        "raw_source": {
            "file": rec.get("source_file"),
            "sheet": rec.get("source_sheet"),
            "row": rec.get("source_row"),
            "cell": rec.get("source_cell_url"),
            "metadata_status": rec.get("metadata_status"),
        },
    }


def _num(v: Any) -> float | None:
    try:
        return float(v) if v not in (None, "", "None") else None
    except (ValueError, TypeError):
        return None
