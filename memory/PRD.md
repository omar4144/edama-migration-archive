# Edama — Musr'at Idama Unified Platform (V8)

## Original problem statement
Unified RTL Arabic platform consolidating historical Excel + Lovable data. Role-based (Admin/Consultant/Arbitrator) with strict raw-data protection.

## What's been implemented
- **Iterations 1-5**: Ingestion + JWT + RBAC + DQ + shell + strict v3 dedup.
- **Iteration 6 (v4 families, 2026-07-31)**: correct decision vocabulary (`decisions.py`), `canonical_submission_families` collection, three counts, hours split.
- **Iteration 7 (brand identity, 2026-07-31)**: official Edama logo installed, palette Turquoise #30BEBC / Green #88C656 / Gray #939598, Somar Sans + Tahoma font stack, chevron ribbon.
- **Iteration 8 (Family-Key audit + UI Cutover, 2026-07-31)** ✅ current:
  - **Family-Key audit passed** (`/app/memory/FAMILY_KEY_AUDIT.md`): 0 orgs in multiple cohorts, 0 disconnected journeys → key `organization × model_definition` validated. Future-ready for `enrollment_id`.
  - Backend `/app/backend/routes/canonical.py` extended: `/exec-scene`, `/families`, `/families/{id}`, `/review-queue`, `/review-queue/{fid}/decision`, `/submissions?family_id=…`. Arabic reason/decision/status labels included.
  - Frontend Executive Scene rewritten with **exact v4 numbers** (45 / 3,521 / 5,038 / 3,521 / 2,366 / 868 / 35 / 138 / 947), review reason chips, **two separate hour meters** (1,203 per-model + 1,605 per-org-cohort — never summed).
  - New **Review Queue** page with reason filters (wide_gap_identical, wide_gap_conflict, evaluator_mismatch, no_direct_model).
  - New **Family Detail** page showing version timeline (legacy → قرار → current → قرار جديد) + 6 review actions (link_as_versions / keep_separate / select_evaluator / select_model / defer / reopen) → audit-logged.
  - Nav updated: «قائمة المراجعة» primary + «رحلات النماذج» renamed.

## Key discoveries
- All 1517 cross-source pairs have >150-day gap → versions, not duplicates.
- Legacy hours are per-org-cohort (repeated on rows); current hours are per-model.
- Legacy uses «مجاز/غير مجاز»; current always «مقبول». APPROVED↔APPROVED wide-gap (392 canonicals inside 812 review scope) is re-arbitration → REVIEW_REQUIRED.
- Family key `org × model_definition` is safe: no org appears in >1 cohort in this dataset.

## Backlog

### P1 — Polish and full cutover
- Refactor UnifiedOrganization page to show families (one row per model) instead of Current/Legacy split, with expandable version timeline per family.
- Refactor EvaluatorDetail: org appears once, families under it.
- Refactor ModelsHub default view = Latest Outputs (3,521 rows, one per family), with "إظهار جميع النسخ" toggle to show 5,038.
- Consultant + Evaluator dashboards to use canonical family numbers.

### P2 — Backlog
- Live Lovable Sync (pending credentials + enrollment_id availability).
- Share-link for a family journey.
- Full RBAC re-test suite + mobile pass.

## Key files
- `/app/backend/decisions.py`, `/app/backend/migrations/build_canonical.py`, `/app/backend/migrations/report_dedup_v4.py`, `/app/backend/migrations/family_key_audit.py`
- `/app/backend/routes/canonical.py` — all v4 endpoints
- `/app/frontend/src/pages/admin/ExecutiveScene.jsx`, `ReviewQueue.jsx`, `FamilyDetail.jsx`
- `/app/memory/DEDUP_REPORT_V4.md`, `/app/memory/FAMILY_KEY_AUDIT.md`

## Credentials
Admin: `omarzabarmawi@hotmail.com` — see `/app/memory/test_credentials.md`.
