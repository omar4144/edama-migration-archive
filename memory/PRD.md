# Edama — Musr'at Idama Unified Platform (V8)

## Original problem statement
Unified operational web platform consolidating historical Excel/forms data with current Lovable data. Delivers role-based experiences for Admins, Consultants, and Arbitrators, fully RTL Arabic. Palette: Navy/Turquoise/Ivory.

## What's been implemented
- **Iteration 1-3**: Data ingestion (Lovable + Legacy CSVs → `source_records`), JWT auth + RBAC + write-guards, DQ drill-down center, unified frontend shell.
- **Iteration 4 (v2 dedup)**: Initial canonical layer using archive's crosswalk_records — auto-merged 1018 pairs into EXACT (SHOWN INCORRECT).
- **Iteration 5 (v3 strict, 2026-07-31)**: Introduced strict composite-path rules. Discovered 0 EXACT possible in current data.
- **Iteration 6 (v4 families + decisions, 2026-07-31)** ✅ current:
  - `/app/backend/decisions.py` — correct normalization dictionary (legacy مجاز/غير مجاز/مجاز مع تحفظ ↔ current مقبول/يحتاج لتطوير) with strict separation between `decision_normalized` and `completion_status`.
  - `/app/backend/migrations/build_canonical.py` — reclassifies with new dictionary, builds `canonical_submission_families` collection (Model Journeys grouping legacy + current versions of same org × model).
  - Three separate counts: **families=3521, versions=5038, latest_operational=3521**.
  - Hours strictly separated: **1,203 Lovable per_model** and **1,605 Legacy per_org_cohort**. Never summed.
  - `/app/memory/DEDUP_REPORT_V4.md` — 20 documented family journeys.

## Key discoveries
- All 1517 crosswalk-matched pairs have date-gap > 150 days.
- Legacy `total_arbitration_hours_raw` is at **org×cohort level** (same 100.0 hours stamped on all 47 rows of one org). Safe unit = 1,605.
- Lovable `work_hours` is per-model (mean 0.65h; 1,203 after dedup).
- Legacy uses «مجاز/غير مجاز/مجاز مع تحفظ» decision vocabulary (mجاز مع تحفظ = 0 rows); current uses «مقبول».
- Every current-side record = APPROVED. So APPROVED↔APPROVED wide-gap pairs (392) are re-arbitrations, not versions → REVIEW_REQUIRED / `wide_gap_identical_decision`.
- Legacy has TWO fields: `arbitration_result_raw` (decision) and `evaluation_status` (completion). Also `arbitration_date_iso` is often None; must fall back to `arbitration_date_source_iso`.

## Prioritized backlog

### P0 — Awaiting ownership approval on V4 report
- [x] Correct decision dictionary
- [x] Submission Families
- [x] Three separate counts
- [x] Hours displayed separately
- [x] REVIEW_REQUIRED broken down by reason
- [ ] Ownership review of `/app/memory/DEDUP_REPORT_V4.md`

### P1 — UI Cutover (BLOCKED)
- Endpoints for `families` list + detail + review queue
- Executive Scene numbers: families / versions / latest_operational
- Directories consuming canonical data
- Two hour meters displayed side-by-side (Lovable per_model vs Legacy per_org_cohort)
- Review queue UI showing 868 families needing attention with reason grouping

### P2 — Backlog
- Live Lovable Sync (pending credentials)
- Admin action UI for REVIEW_REQUIRED resolution
- Consultant / Evaluator dashboards using canonical numbers

## Key files
- `/app/backend/decisions.py` — decision vocabulary normalizer
- `/app/backend/migrations/build_canonical.py` — v4 families build
- `/app/backend/migrations/report_dedup_v4.py` — reconciliation + 20 family samples
- `/app/backend/routes/canonical.py` — read-only canonical API (needs update for families)
- `/app/memory/DEDUP_REPORT_V4.md` — the current audit report
- `/app/memory/DEDUP_REPORT_V3.md` — prior report (historical)

## Credentials
Admin: `omarzabarmawi@hotmail.com` — see `/app/memory/test_credentials.md`.
