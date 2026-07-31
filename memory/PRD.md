# Edama — Musr'at Idama Unified Platform (V8)

## Original problem statement
Unified RTL Arabic platform consolidating historical Excel + Lovable data. Role-based (Admin/Consultant/Arbitrator) with strict raw-data protection.

## What's been implemented (through Iteration 12)
- **Iterations 1-11**: Auth + dedup v4 (families + decisions), Edama brand identity, full cutover, participating orgs registry, three progressive bulk policies (AUTO_APPROVE_WIDE_GAP_IDENTICAL 392, AUTO_LINK_EVALUATOR_REASSIGNMENT 112, — 12 surfaced as wide_gap_conflicting).
- **Iteration 12 (Review Queue Closure, 2026-07-31)** ✅ current — TWO final policies:
  - **AUTO_ACCEPT_LATEST_LOVABLE_DECISION** (138 families): `wide_gap_conflicting_decisions` → `VERSION_LINKED / latest_lovable_decision_authoritative`. Lovable version is the operational current decision; legacy holds prior context in Timeline. Never overwrites raw.
  - **AUTO_MAP_LEGACY_MODEL_TO_CURRENT** (226 families): `no_direct_model_match_only_org` → `VERSION_LINKED / legacy_model_mapped_to_current`. Lovable defines the current model/decision/evaluator; legacy remains contextual within the org's timeline.
  - Both bulk policies logged as SYSTEM entries in `review_audit_log`.
  - **REVIEW_REQUIRED = 0**. Nav auto-hides «قائمة المراجعة» when count is 0; endpoint + page preserved. AppShell now polls `/admin/canonical/exec-scene` on mount to derive count dynamically.

## Final numbers (verified 2026-07-31 post all policies)
- 45 model_types · **3,521 journeys** · **5,038 versions** · **3,521 latest_outputs** — unchanged
- 2,366 approved · 947 rejected · 35 needs improvement · 138 pending
- **0 review-required** ✅
- VERSION_LINKED breakdown (current-side): 392 auto_approved_identical + 346 resubmission_version_resubmit + 30 completion_then_result + 226 legacy_model_mapped + 138 latest_lovable_authoritative + 75 evaluator_reassignment + 34+3 `_evaluator_reassigned` tagged
- Hours: **1,203 per_model** (Lovable, primary operational) · 1,605 per_org_cohort (archival, collapsed detail)
- 175 candidate orgs, 0 confirmed (admin-driven manual)

## Prioritized backlog (Iteration 12+)

### P1 — Roles and mobile
- **Consultant + Evaluator dashboards** read from `canonical_submission_families`, with the same Timeline pattern.
- **Family Timeline evaluator labels**: legacy row shows «المحكم السابق»; family header shows «المحكم الحالي» from Lovable exclusively.
- **RBAC enforcement**: legacy-only evaluators do NOT see the family in their active work queue; only Lovable evaluator drives assignment.
- **مشاركة رابط الرحلة**: deep link `/admin/family/FAM-000006` + return_url on FamilyDetail.
- **RBAC + Mobile regression** via testing_agent.

### P2 — Backlog (deferred)
- Live Lovable Sync (pending credentials + enrollment_id).
- Reports export.
- Multi-Program support.

## Key files
- Backend: `/app/backend/decisions.py`, `/app/backend/routes/{canonical,participating_orgs}.py`, `/app/backend/migrations/{build_canonical,report_dedup_v4,family_key_audit}.py`
- Frontend: `/app/frontend/src/pages/admin/{ExecutiveScene,ReviewQueue,FamilyDetail,ParticipatingOrgs,UnifiedOrganization,EvaluatorDetail,ModelsHub}.jsx`, `/app/frontend/src/components/layout/AppShell.jsx` (with dynamic review-count nav)
- Reports: `/app/memory/{DEDUP_REPORT_V4,FAMILY_KEY_AUDIT}.md`

## Credentials
Admin: `omarzabarmawi@hotmail.com` — see `/app/memory/test_credentials.md`.
