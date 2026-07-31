# Edama — Musr'at Idama Unified Platform (V8)

## Original problem statement
Unified operational web platform consolidating historical Excel/forms data with current Lovable data. Delivers role-based experiences for Admins, Consultants, and Arbitrators, fully RTL Arabic. Palette: Navy/Turquoise/Ivory.

## What's been implemented
- **Iteration 1-3**: Data ingestion (Lovable + Legacy CSVs → `source_records`), JWT auth + RBAC + write-guards, DQ drill-down center, unified frontend shell (Executive Scene / Directories / Unified Orgs) with no Lovable/Historical tabs.
- **Iteration 4 (v2 dedup)**: Initial canonical layer using archive's `crosswalk_records` — auto-merged 1018 MATCHED pairs into EXACT (LATER SHOWN INCORRECT).
- **Iteration 5 (v3 STRICT dedup, 2026-07-31)**: Rewrote `/app/backend/migrations/build_canonical.py` with ownership's strict contract:
  - EXACT requires composite path (org + model + evaluator + date-exact + decision-compat)
  - PROBABLE requires date-diff 1-3 days
  - VERSION_LINKED for resubmission pattern (legacy "يحتاج لتطوير" → current "مقبول")
  - REVIEW_REQUIRED for evaluator mismatch or NO_DIRECT_MODEL_MATCH
  - Never mutates raw. Never auto-merges cross-source unless composite path fully satisfied.
- Result: **0 EXACT, 0 PROBABLE, 2201 VERSION_LINKED (1307 pairs), 560 REVIEW_REQUIRED, 499 CURRENT_ONLY, 1778 LEGACY_ONLY = 5038 canonicals total.**
- Full 20-sample report + hours reconciliation delivered at `/app/memory/DEDUP_REPORT_V3.md`.

## Key discoveries
- All 1517 crosswalk-matched pairs have date-gap > 150 days → they are **versions** not duplicates.
- Legacy `total_arbitration_hours_raw` is stamped at **org×cohort level** (same 100.0 hours repeats across all 47 model rows of one org) → 75,015 sum is massively inflated; safe unit = 1,605 per-org-cohort.
- Lovable `work_hours` is per-model arbitration effort (mean 0.65h, sum 1,662; deduped 1,203).
- Legacy uses decision labels like "مجاز"/"غير مجاز"/"مجاز مع تحفظ"; current uses "مقبول"/"يحتاج لتطوير". Both must remain visible; never merge naïvely.

## Prioritized backlog

### P0 — Awaiting ownership approval
- [x] Tighten cross-source matching contract (v3 strict rules)
- [x] Generate hours-reconciliation report with 20 documented samples
- [ ] Ownership review of `/app/memory/DEDUP_REPORT_V3.md` and confirmation to proceed with UI cutover

### P1 — UI Cutover (BLOCKED on P0 approval)
- Update `/app/frontend/src/pages/admin/ExecutiveScene.jsx`, `UnifiedOrganization.jsx`, `EvaluatorDetail.jsx`, and directories to consume the new `/api/admin/canonical/*` endpoints.
- Terminology cleanup: "صفوف خام" vs "تسليمات موحدة" vs "تعريفات النماذج (45)".
- Add a **Versions** panel showing legacy → current lifecycle per model.
- Show Hours in the correct unit next to each visualization (Lovable per-model vs Legacy per-org-cohort).

### P2 — Backlog
- Live Lovable Sync (deferred pending credentials).
- Duplicate-review workflow: admin action UI on REVIEW_REQUIRED and PROBABLE pairs.
- Consultant / Evaluator dashboards to use canonical numbers instead of raw counts.

## Key files
- `/app/backend/migrations/build_canonical.py` — v3 strict-rules build
- `/app/backend/migrations/report_dedup_v3.py` — reconciliation + 20-sample report
- `/app/backend/dedup.py` — URL normalization helpers (URL family, dates)
- `/app/backend/routes/canonical.py` — read-only canonical API
- `/app/memory/DEDUP_REPORT_V3.md` — full audit report for ownership

## Credentials
Admin: `omarzabarmawi@hotmail.com` — see `/app/memory/test_credentials.md`.
