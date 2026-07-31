# Edama — Musr'at Idama Unified Platform (V8)

## Original problem statement
Unified RTL Arabic platform consolidating historical Excel + Lovable data. Role-based (Admin/Consultant/Arbitrator) with strict raw-data protection.

## What's been implemented
- **Iterations 1-7**: Auth, RBAC, DQ, v4 dedup with families + decisions, Edama brand identity.
- **Iteration 8**: Family-Key audit + UI Cutover: Executive Scene v4 numbers, Review Queue, Family Detail with 6 actions.
- **Iteration 9 (Participating Orgs + Journeys, 2026-07-31)** ✅ current:
  - New backend `/app/backend/routes/participating_orgs.py` — candidate orgs auto-seeded from all sources (current + legacy + crosswalk), with 6 review statuses (PENDING_REVIEW / CONFIRMED_PARTICIPANT / EXCLUDED / WITHDRAWN / REPLACED / DUPLICATE_CANDIDATE). Every decision audit-logged. Bulk-confirm supported.
  - **NO hardcoded participating count**: official metric derived only from `CONFIRMED_PARTICIPANT`. Starts at 0 out of 175 candidates.
  - **ParticipatingOrgs.jsx** — full registry page with filters (search / status / cohort / source), per-org review actions (confirm/exclude/withdraw/replace/duplicate/reopen), bulk-confirm bar, alternative names, source badges, family counts, review flags. Never modifies raw.
  - **UnifiedOrganization.jsx rewritten**: one row per family (org × model) with latest_decision, version_count, evaluator, review badge, latest URL. Expandable inline timeline. No Current/Legacy split.
  - **EvaluatorDetail.jsx rewritten**: evaluator → org (once) → family (once) → versions timeline. Evaluator-mismatch badge shows on version rows where evaluator differs.
  - **ModelsHub.jsx rewritten**: default view = Latest Outputs (3,521 families, one row per model). Toggle to All Versions (5,038 canonicals). Filters preserved across toggle.
  - Nav updated: «سجل الجمعيات» primary entry.

## Key numbers
- 45 model_types
- 3,521 model_journeys · 5,038 versions · 3,521 latest_outputs
- 2,366 approved · 947 rejected · 35 needs improvement · 138 pending · 868 review-required journeys
- Hours: 1,203 per_model (Lovable) + 1,605 per_org_cohort (Legacy) — never summed
- 175 candidate orgs → 0 confirmed (yet); admin will confirm manually via /admin/participating-organizations

## Prioritized backlog

### P1 — Polish
- **مشاركة رابط الرحلة**: Add "نسخ رابط الرحلة" button on FamilyDetail (deep link `/admin/family/{fid}` with return_url after login).
- **RBAC + Mobile regression**: full pass with the testing agent on all new pages.
- **Consultant + Evaluator role dashboards** to consume canonical families instead of raw.

### P2 — Backlog (deferred)
- Live Lovable Sync (pending credentials + enrollment_id availability).
- Reports export.
- Multi-Program support.

## Key files
- Backend: `/app/backend/decisions.py`, `/app/backend/routes/canonical.py`, `/app/backend/routes/participating_orgs.py`, `/app/backend/migrations/build_canonical.py`, `family_key_audit.py`
- Frontend: `/app/frontend/src/pages/admin/{ExecutiveScene,ReviewQueue,FamilyDetail,ParticipatingOrgs,UnifiedOrganization,EvaluatorDetail,ModelsHub}.jsx`
- Reports: `/app/memory/DEDUP_REPORT_V4.md`, `FAMILY_KEY_AUDIT.md`

## Credentials
Admin: `omarzabarmawi@hotmail.com` — see `/app/memory/test_credentials.md`.
