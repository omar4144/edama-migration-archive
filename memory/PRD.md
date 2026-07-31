# Edama — Musr'at Idama Unified Platform (V8)

## Original problem statement
Unified RTL Arabic platform consolidating historical Excel + Lovable data. Role-based (Admin/Consultant/Arbitrator) with strict raw-data protection.

## What's been implemented (through Iteration 13)
- **Iterations 1-11**: Auth, dedup v4 with correct decision vocabulary + families + Edama brand identity + full UI cutover + participating orgs registry + 4 bulk auto-linking policies.
- **Iteration 12 (Review Queue Closure)**: AUTO_ACCEPT_LATEST_LOVABLE_DECISION (138) + AUTO_MAP_LEGACY_MODEL_TO_CURRENT (226) → REVIEW_REQUIRED = 0.
- **Iteration 13 (Participating Orgs Audit, 2026-07-31)** ✅ current — READ-ONLY, no data modification:
  - Root cause of the 175 number identified: `175 = 57 (Lovable) + 118 (Legacy)` — direct sum, `crosswalk_organizations` was not applied during participating_orgs seed.
  - 4 audit artifacts produced under `/app/memory/`:
    - `PARTICIPATING_ORGANIZATIONS_AUDIT.md` — full report (158 lines).
    - `PARTICIPATING_ORGANIZATIONS_175_AUDIT.csv` — 1 row per registry candidate (175).
    - `ORGANIZATION_MATCH_GROUPS.csv` — 118 proposed unified organizations (56 EXACT + 1 PROBABLE + 61 LEGACY_ONLY, plus LOVABLE_ONLY).
    - `ORGANIZATION_COHORT_PARTICIPATIONS.csv` — 175 org × cohort participations.
  - Three separate counts distinguished: raw source rows (175), org×cohort participations (175), unique orgs after crosswalk (**119 EXACT-only, 118 EXACT+PROBABLE**).
  - Multi-cohort orgs detected after normalization + crosswalk: **0** — Family-Key `org × model_definition` remains safe. Adding cohort to key would not split any of the 3,521 journeys.
  - Lovable «مقبول» flagged as `LINK_EXISTS_CONTENT_NOT_VERIFIED` — the row/link presence does not verify Google file content.
  - Verified by testing_agent (iteration_5.json): all counts match, no writes to DB, 175 participating_orgs still all PENDING_REVIEW.

## Prioritized backlog

### P0 — Awaiting ownership decision on 175 audit
- Confirm which unique-org number to adopt: **119** (EXACT only, safe) vs **118** (EXACT + 1 PROBABLE).
- Confirm whether participating_orgs seed should be re-run to APPLY the crosswalk (merging 57 pairs), or whether to keep 175 as candidates and add a "resolve to X" review step.
- Decide the operational meaning of Lovable «مقبول»: does it count as pending verification vs approved?

### P1 — Deferred (Iteration 12 continuation)
- Consultant + Evaluator dashboards read from `canonical_submission_families`.
- Family Timeline evaluator labels («المحكم السابق» / «المحكم الحالي»).
- RBAC enforcement for legacy-only evaluators.
- مشاركة رابط الرحلة deep-link button.
- RBAC + Mobile regression via testing_agent.

### P2 — Backlog
- Live Lovable Sync (pending credentials).
- Reports export.
- Multi-Program support.

## Key numbers (2026-07-31)
- 45 model_types · 3,521 journeys · 5,038 versions · 0 review-required.
- Hours: 1,203 per_model (primary) · 1,605 per_org_cohort (archival).
- Participating orgs candidates: **175** = 57 + 118 raw sum; proposed unique: 119 (EXACT-only) or 118 (with 1 PROBABLE); 0 confirmed pending your review.

## Key files
- Backend: `/app/backend/{decisions.py,routes/{canonical,participating_orgs}.py,migrations/{build_canonical,report_dedup_v4,family_key_audit,participating_orgs_audit}.py}`
- Frontend: `/app/frontend/src/{components/layout/AppShell.jsx,pages/admin/{ExecutiveScene,ReviewQueue,FamilyDetail,ParticipatingOrgs,UnifiedOrganization,EvaluatorDetail,ModelsHub}.jsx}`
- Reports: `/app/memory/{DEDUP_REPORT_V4,FAMILY_KEY_AUDIT,PARTICIPATING_ORGANIZATIONS_AUDIT}.md`, CSVs in `/app/memory/`
- Test report: `/app/test_reports/iteration_5.json`

## Credentials
Admin: `omarzabarmawi@hotmail.com` — see `/app/memory/test_credentials.md`.
