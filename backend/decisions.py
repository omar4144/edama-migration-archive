"""
Correct decision-vocabulary normalization for Edama.

Legacy (historical arbitration) uses:
  - «مجاز»            → APPROVED
  - «غير مجاز»        → REJECTED
  - «مجاز مع تحفظ»   → APPROVED_WITH_RESERVATION

Current (Lovable) uses:
  - «مقبول»          → APPROVED
  - «يحتاج لتطوير»    → NEEDS_IMPROVEMENT
  - «غير مكتمل»       → NOT a decision — a completion status (INCOMPLETE)

`decision_normalized` and `completion_status` are strictly separated.

- decision_normalized ∈ {APPROVED, APPROVED_WITH_RESERVATION,
                         NEEDS_IMPROVEMENT, REJECTED, PENDING, None}
- completion_status  ∈ {COMPLETE, INCOMPLETE, None}
"""
from __future__ import annotations
from typing import Optional


DECISION_APPROVED = "APPROVED"
DECISION_APPROVED_RESERVED = "APPROVED_WITH_RESERVATION"
DECISION_NEEDS_IMPROVEMENT = "NEEDS_IMPROVEMENT"
DECISION_REJECTED = "REJECTED"
DECISION_PENDING = "PENDING"

COMPLETION_COMPLETE = "COMPLETE"
COMPLETION_INCOMPLETE = "INCOMPLETE"


def _clean(s: Optional[str]) -> str:
    return (s or "").strip()


def normalize_current(evaluation: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Return (decision_normalized, completion_status) for a Lovable row's
    `evaluation` field."""
    v = _clean(evaluation)
    if not v:
        return (None, None)
    if v == "مقبول":
        return (DECISION_APPROVED, COMPLETION_COMPLETE)
    if v == "يحتاج لتطوير":
        return (DECISION_NEEDS_IMPROVEMENT, COMPLETION_COMPLETE)
    if v == "غير مكتمل":
        # This is a completion status, not a decision.
        return (None, COMPLETION_INCOMPLETE)
    # Unknown / free-text
    return (DECISION_PENDING, None)


def normalize_legacy(arbitration_result_raw: Optional[str],
                     evaluation_status: Optional[str] = None
                     ) -> tuple[Optional[str], Optional[str]]:
    """Return (decision_normalized, completion_status) for a legacy
    arbitration row.

    Primary vocabulary comes from `arbitration_result_raw` (the arbitration
    decision itself). `evaluation_status` occasionally carries the same
    verdict but sometimes uses different labels — fall back only if the
    primary is empty.
    """
    v = _clean(arbitration_result_raw)
    if not v:
        v = _clean(evaluation_status)
    if not v:
        return (None, None)
    if v == "مجاز":
        return (DECISION_APPROVED, COMPLETION_COMPLETE)
    if v == "غير مجاز":
        return (DECISION_REJECTED, COMPLETION_COMPLETE)
    if v == "مجاز مع تحفظ":
        return (DECISION_APPROVED_RESERVED, COMPLETION_COMPLETE)
    if v == "غير مكتمل":
        return (None, COMPLETION_INCOMPLETE)
    if v == "يحتاج لتطوير":
        return (DECISION_NEEDS_IMPROVEMENT, COMPLETION_COMPLETE)
    if v == "مقبول":
        return (DECISION_APPROVED, COMPLETION_COMPLETE)
    # Unknown / free-text
    return (DECISION_PENDING, None)


# Decisions that plausibly precede a "resubmission after fix" — i.e., a
# canonical VERSION relationship where a later current submission is likely
# the improved version of an earlier legacy attempt.
VERSION_TRIGGER_DECISIONS = {
    DECISION_REJECTED,
    DECISION_NEEDS_IMPROVEMENT,
    DECISION_APPROVED_RESERVED,  # reservation to resolve → resubmit
}


def classify_decision_transition(legacy_dec: Optional[str],
                                 legacy_completion: Optional[str],
                                 current_dec: Optional[str],
                                 current_completion: Optional[str]) -> str:
    """Return a decision-transition tag used by the pair classifier.

    - 'same_decision'          — identical normalized decisions
    - 'version_resubmit'       — legacy negative outcome → current APPROVED
    - 'completion_then_result' — legacy INCOMPLETE → current has a real decision
    - 'conflict'               — different decisions, no clear version pattern
    - 'unknown'                — at least one side is empty/PENDING
    """
    if not legacy_dec and legacy_completion == COMPLETION_INCOMPLETE \
            and current_dec in (DECISION_APPROVED,
                                DECISION_APPROVED_RESERVED,
                                DECISION_NEEDS_IMPROVEMENT):
        return "completion_then_result"
    if not legacy_dec or not current_dec:
        return "unknown"
    if legacy_dec == current_dec:
        return "same_decision"
    if legacy_dec in VERSION_TRIGGER_DECISIONS and current_dec == DECISION_APPROVED:
        return "version_resubmit"
    return "conflict"
