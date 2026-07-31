# Edama — Musr'at Idama Unified Platform (V8)

## Original problem statement
Unified RTL Arabic platform consolidating historical Excel + Lovable data. Role-based (Admin/Consultant/Arbitrator) with strict raw-data protection.

## What's been implemented (through Iteration 11)
- **Iterations 1-9**: Auth + dedup v4 (families + decisions), brand identity, cutover (Executive Scene / Review Queue / Family Detail / Participating Orgs), Family-view for org/evaluator/models-hub.
- **Iteration 10 policy (AUTO_APPROVE_WIDE_GAP_IDENTICAL)**: 392 families auto-VERSION_LINKED when everything but the date matches. Review drop: 868 → 476.
- **Iteration 11 policy (AUTO_LINK_EVALUATOR_REASSIGNMENT, 2026-07-31)** ✅ current:
  - Evaluator mismatch is no longer a review trigger by itself. Legacy evaluator = المحكم السابق (preserved on that version); Lovable evaluator = المحكم الحالي (drives current assignment/queue).
  - `_evaluator_reassigned` suffix appears on `version_resubmit` and `close_dates_compatible_decisions` reasons when evaluators differ. `auto_linked_evaluator_reassignment` reason for same-decision cases.
  - Bulk SYSTEM audit log entry added: `action=AUTO_LINK_EVALUATOR_REASSIGNMENT`, `previous_reason=evaluator_mismatch_cross_source`, `new_status=VERSION_LINKED`.
  - **Result: 364 families need review** (was 476). Breakdown: 226 `no_direct_model_match_only_org` + 138 `wide_gap_conflicting_decisions`. 12 additional wide_gap_conflicting cases surfaced (they were hidden behind the previous evaluator-mismatch hard gate — now correctly reviewed because their decisions truly conflict).
  - Version distribution enriched: 346 resubmission_version_resubmit + 30 resubmission_completion_then_result + 392 auto_approved_identical + 75 auto_linked_evaluator_reassignment + 34+3 `_evaluator_reassigned` tagged variants.
  - Raw data untouched. Every version stays in its family Timeline with its original evaluator.

## Key numbers (2026-07-31 post-policy)
- 45 model_types · **3,521 journeys** · **5,038 versions** · 3,521 latest_outputs
- 2,366 approved · 947 rejected · 35 needs improvement · 138 pending
- **364 review-required journeys** (dynamic, never hardcoded)
- Hours: **1,203 per_model (Lovable, primary operational)** · 1,605 per_org_cohort (archival only, collapsed in UI)

## Prioritized backlog

### P1 — Iteration 10/11 remainder
- **Consultant + Evaluator role dashboards** read from `canonical_submission_families`.
- **Family Timeline evaluator display**: label legacy row as «المحكم السابق»; header shows current Lovable evaluator.
- **RBAC enforcement**: ensure legacy-only evaluators do NOT see the family in their active queue; Lovable evaluator drives assignment.
- **مشاركة رابط الرحلة**: deep link + return_url button on FamilyDetail.
- **Full RBAC + Mobile regression via testing_agent** across all admin pages.

### P2 — Backlog (deferred)
- Live Lovable Sync (pending credentials + enrollment_id availability).
- Reports export.
- Multi-Program support.

## Key files
- Backend: `/app/backend/decisions.py`, `/app/backend/routes/{canonical,participating_orgs}.py`, `/app/backend/migrations/{build_canonical,report_dedup_v4,family_key_audit}.py`
- Frontend: `/app/frontend/src/pages/admin/{ExecutiveScene,ReviewQueue,FamilyDetail,ParticipatingOrgs,UnifiedOrganization,EvaluatorDetail,ModelsHub}.jsx`
- Reports: `/app/memory/{DEDUP_REPORT_V4,FAMILY_KEY_AUDIT}.md`

## Credentials
Admin: `omarzabarmawi@hotmail.com` — see `/app/memory/test_credentials.md`.
