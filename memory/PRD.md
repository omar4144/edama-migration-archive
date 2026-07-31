# Edama — Musr'at Idama Unified Platform (V8)

## Original problem statement
Unified RTL Arabic platform consolidating historical Excel + Lovable data. Role-based (Admin/Consultant/Arbitrator) with strict raw-data protection.

## What's been implemented
- **Iterations 1-8**: Auth, dedup v4 (families + decisions), Edama brand identity, first cutover (Executive Scene, Review Queue, Family Detail).
- **Iteration 9**: Participating orgs registry (175 candidates, 0 hardcoded), Family-view for org/evaluator, ModelsHub with Latest Outputs default (3,521) + toggle to All Versions (5,038).
- **Iteration 10 policy (2026-07-31)** ✅ current:
  - **AUTO_APPROVE_WIDE_GAP_IDENTICAL** bulk rule applied. All pairs with (same org + same model + same evaluator + same normalized decision) are now `VERSION_LINKED / auto_approved_identical_after_wide_gap` — wide date gap alone is no longer a review trigger.
  - Bulk decision logged as SYSTEM entry in `review_audit_log` (`kind=bulk_policy_applied`, `previous_reason=wide_gap_identical_decision`, `affected canonicals=812`, `~392 families`).
  - **Review queue dropped from 868 → 476 families** = 226 no_direct_model + 124 evaluator_mismatch + 126 wide_gap_conflicting.
  - Total families **3,521 unchanged**, total canonicals **5,038 unchanged**. Both versions remain in every family's Timeline; no raw record touched.
  - Executive Scene hours re-styled: **1,203 h per_model** is the *primary operational meter* (Lovable). The 1,605 h legacy value is moved into a collapsible `<details>` labelled «ساعات تاريخية تقديرية للجهات» with clarification «قيمة أرشيفية على مستوى الجهة والدفعة (~15 س / جهة×دفعة)، لا تُستخدم كمؤشر تشغيلي». Never summed with Lovable.
  - Canonical route dictionary updated: Arabic label for `auto_approved_identical_after_wide_gap`.

## Key numbers (2026-07-31 post-policy)
- 45 model_types · 3,521 journeys · 5,038 versions · 3,521 latest_outputs
- 2,366 approved · 947 rejected · 35 needs improvement · 138 pending
- **476 review-required journeys** (was 868)
- Hours: 1,203 per_model (primary) — 1,605 per_org_cohort (secondary archival only)
- 175 candidate orgs, 0 confirmed (admin-driven manual)

## Prioritized backlog

### P1 — Iteration 10 remainder
- **Consultant + Evaluator role dashboards** consume `canonical_submission_families` instead of raw records.
- **مشاركة رابط الرحلة**: "نسخ رابط الرحلة" button on FamilyDetail — deep link `/admin/family/{fid}` with return_url after login.
- **Full RBAC + Mobile testing_agent regression** across new pages.

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
