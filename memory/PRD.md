# PRD — Edama · Musr'at Idama V8

## Original Problem Statement
Edama — Musr'at Idama Unified Platform (V8). A unified, experience-led operational web platform for the Sustainability Accelerator (مسرعة إدامة) that consolidates historical Excel/forms data with current Lovable data, and delivers role-based experiences for Admins (إدارة السياق), Consultants (مستشار), and Evaluators / المحكم — fully RTL/Arabic, per the V8 Implementation Contract.

## Non-Negotiable Constraints
- Real archive data only (omar4144/edama-migration-archive). **No seed/dummy data.**
- Contract-locked reconciliation counts MUST match exactly.
- Historical layer is IMMUTABLE. Crosswalks are advisory. Probable matches → REVIEW_REQUIRED queue with human decisions.
- JWT (bcrypt, access + refresh tokens), RBAC on API, data isolation at API layer.
- Terminology: `evaluator / المحكّم` (not "arbitrator").
- No LLM / no AI mapping suggestions / no PDF export in this phase.
- V8 experience: Navy · Turquoise · Ivory · Orange, RTL, IBM Plex Sans Arabic, no shadows, no glassmorphism, no card carpets.

## Reference Counts (from Edama_Dashboard_Integration_Report + summary.json)
| Item | Target |
|---|---:|
| current_lovable_records | 2,565 |
| current_lovable_organizations | 57 |
| people | 17 |
| model_definitions | 45 |
| work_hours_total | 1,662.0 |
| duplicate_link_groups (current) | 129 |
| legacy_organizations | 118 (24/30/29/35) |
| legacy_consultant_activities | 3,760 |
| legacy_arbitration_records | 3,403 |
| legacy_duplicate_link_groups | 67 |
| batch_plan_rows | 120 |
| batch_kpi_snapshots | 4 |
| REVIEW_REQUIRED queue | 9 (1 org + 3 model + 5 evaluator) |

## User Personas
- **إدارة السياق (Admin/Owner)** — full oversight, reconciliation dashboard, mapping decisions, users & permissions, audit log.
- **مستشار (Consultant)** — own submissions list, draft editor (model_url/notes/status), historical activities view.
- **محكّم (Evaluator)** — review queue for assigned records, decision recorder (تقييم + ساعات + ملاحظات), hours summary.

## Architecture
- **Backend**: FastAPI + Motor (MongoDB async) + PyJWT + bcrypt. Routes under `/api/{auth,reconciliation,admin,consultant,evaluator}`.
- **Frontend**: React 19 + Tailwind + shadcn/ui primitives + IBM Plex Sans Arabic. RTL `<html dir="rtl" lang="ar">`. AuthProvider + RoleGuard.
- **DB**: MongoDB collections — `users`, `login_attempts`, `audit_log`, `people`, `model_definitions`, `organizations_current`, `records_current`, `duplicate_links_current`, `historical_*` (immutable), `crosswalk_*`, `assignments`, `mappings` (REVIEW_REQUIRED), `quality_checks`, `source_inventory`, `migration_runs`.
- **Migration**: `/app/backend/migrations/import_archive.py` — reads CSV/JSON from `/app/data/archive/`, preserves raw fields, verifies counts against contract targets, builds review queue from crosswalks with no auto-merge.

## What's Been Implemented (2026-07-31)
- Foundation: FastAPI + React scaffold, RTL base theme, V8 palette tokens, IBM Plex Sans Arabic.
- Auth (JWT + bcrypt): login, logout, me, refresh, change-password. httpOnly cookies (secure, SameSite=none) + Bearer fallback. Brute-force lockout (5 failures / 15 min, email-only identifier). RBAC via `require_role()` dependency.
- Data model + migration: All 12 archive CSVs + JSONL imported. Contract counts VERIFIED PASS 10/10.
- Reconciliation console: live counts vs targets, cohort table (24/30/29/35 · 0/1200/1160/1400 · 0/1382/1081/940), crosswalk status breakdowns, latest run summary.
- Review queue: 9 items (1 org probable + 3 model evolved + 5 evaluator changed). Approve/reject with optional note. Every decision → audit_log.
- Admin: organizations (current + historical tabs), records browser (org + status + pagination), users management with person linking, audit log viewer.
- Consultant workspace: own submissions (person_id filter), draft editor (model_url/notes/status), historical activities.
- Evaluator workspace: assigned records queue, decision recorder (evaluation, work_hours, notes), hours summary by organization.
- Data isolation VERIFIED at API layer (403 on cross-role access) — no UI-only hiding.
- Testing: 20/20 pytest cases pass; frontend flows verified via testing subagent.

## Test Credentials (test env only)
See `/app/memory/test_credentials.md`.

## P0 Backlog (deferred by explicit user direction)
- Password reset flow (forgot-password + reset-password endpoints wired to Resend integration)
- Historical arbitration record viewer for evaluators (immutable, view-only)
- Full data quality dashboard page (template metadata status, source inventory drill-down)
- Immutable-write guard middleware for `historical_*` collections
- Program/cohort management page (create/edit cohorts)

## P1 Backlog
- Consultant/Evaluator hour trends over time (line chart, data-driven only)
- Export reconciliation report as JSON/CSV
- Password change enforcement flow on first login (must_change_password already flagged on server)
- Session revocation / active sessions list
- Deployment build + production URL

## P2 Backlog
- Batch KPI cohort dashboard visualisations
- Full accessibility audit + keyboard shortcut layer
- Lovable API live sync (currently: snapshot-based)

## Known Notes
- Console shows a single 401 from initial `/auth/me` bootstrap on the login page — harmless, cosmetic only.
- Historical collections are protected by convention (only the migration script writes to them). Enforcement via app-level guard is on the P0 backlog.
