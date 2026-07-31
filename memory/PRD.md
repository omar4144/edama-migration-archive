# Edama — Musr'at Idama Unified Platform (V8)

## Original problem statement
Unified operational web platform consolidating historical Excel/forms data with current Lovable data. Delivers role-based experiences for Admins, Consultants, and Arbitrators, fully RTL Arabic.

## What's been implemented
- **Iterations 1-3**: Ingestion + JWT auth + RBAC + DQ + unified frontend shell.
- **Iteration 4 (v2 dedup)**: Initial canonical layer — auto-merged 1018 pairs into EXACT (shown INCORRECT).
- **Iteration 5 (v3 strict)**: Composite-path rules. Discovered 0 legitimate EXACT.
- **Iteration 6 (v4 families + decisions, 2026-07-31)**:
  - `/app/backend/decisions.py` — correct legacy vocabulary (مجاز=APPROVED, غير مجاز=REJECTED, مجاز مع تحفظ=APPROVED_WITH_RESERVATION) with strict separation between `decision_normalized` and `completion_status`.
  - Reclassification: 0 EXACT / 0 PROBABLE / **1,137 VERSION_LINKED (both sides)** / **1,624 REVIEW_REQUIRED (both sides)** / 499 CURRENT_ONLY / 1,778 LEGACY_ONLY.
  - New `canonical_submission_families` collection — grouping (org × model) journeys.
  - **Three counts**: families=3,521 / versions=5,038 / latest_operational=3,521.
  - Hours strictly separated: 1,203 Lovable per_model / 1,605 Legacy per_org_cohort.
  - `/app/memory/DEDUP_REPORT_V4.md` — 20 documented family journeys + full reconciliation.
- **Iteration 7 (brand identity, 2026-07-31)** ✅ current:
  - Official **Edama logo** installed at `/app/frontend/public/edama-logo.png` (mark) and `edama-logo-full.png` (with EDAMA ACCELERATOR tagline). Extracted from the corporate PowerPoint.
  - Exact palette: **Turquoise #30BEBC**, **Green #88C656**, **Gray #939598**, Ivory #FBFAF6.
  - Font stack: **"Somar Sans" → SOMAR → Tahoma → system-ui** (matches identity guide spec).
  - Chevron backdrop echoing the logo's arrow motif on auth pages; turquoise+green ribbon under the app header.
  - Updated AppShell header (white, logo image), Login (two-pane with new stats 3,521/5,038/1,203), ForgotPassword, ChangePassword.

## Key discoveries
- All 1517 crosswalk-matched pairs have date-gap > 150 days.
- Legacy `total_arbitration_hours_raw` is at **org×cohort level** (repeated on every model row).
- Legacy uses «مجاز/غير مجاز» vocabulary; current always «مقبول». APPROVED↔APPROVED wide-gap = 392 REVIEW_REQUIRED (`wide_gap_identical_decision`).
- Legacy `arbitration_date_iso` often None → fall back to `arbitration_date_source_iso`.

## Prioritized backlog

### P0 — Awaiting ownership approval on V4 report
- [x] Correct decision dictionary
- [x] Submission Families
- [x] Three separate counts
- [x] Hours displayed separately
- [x] REVIEW_REQUIRED broken down by reason
- [x] Brand identity applied (logo, palette, fonts, chevron motif)
- [ ] Ownership review of `/app/memory/DEDUP_REPORT_V4.md`
- [ ] Ownership decision on REVIEW_REQUIRED display strategy (Q4)
- [ ] Ownership decision on terminology (Q5: "عدد النماذج" = families?)

### P1 — UI Cutover (BLOCKED on P0 approval)
- Executive Scene / Directories consume `families`, `versions`, `latest_operational` from new endpoints.
- Two hour meters side-by-side (Lovable per_model vs Legacy per_org_cohort).
- Review queue UI (868 families) with reason grouping.
- Backend endpoints for families list/detail/review queue.

### P2 — Backlog
- Live Lovable Sync (pending credentials).
- Admin action UI for REVIEW_REQUIRED resolution.

## Key files
- `/app/backend/decisions.py` — decision vocabulary normalizer
- `/app/backend/migrations/build_canonical.py` — v4 families build
- `/app/backend/migrations/report_dedup_v4.py` — report generator
- `/app/frontend/public/edama-logo.png`, `edama-logo-full.png` — official brand assets
- `/app/frontend/tailwind.config.js`, `/app/frontend/src/index.css` — brand palette + font stack
- `/app/frontend/src/components/layout/AppShell.jsx` — header with real logo + chevron ribbon
- `/app/memory/DEDUP_REPORT_V4.md` — current audit report (516 lines, 20 family samples)

## Credentials
Admin: `omarzabarmawi@hotmail.com` — see `/app/memory/test_credentials.md`.
