# PRD — Edama · Musr'at Idama V8 · Final Finish

## Original Problem Statement
Edama V8 — منصة تشغيلية موحّدة لمسرعة الاستدامة تدمج الأرشيف التاريخي (Excel/forms) مع بيانات Lovable الحالية، بتجربة V8 (Navy/Turquoise/Ivory/Orange) RTL كاملة لثلاثة أدوار: إدارة السياق، المستشار، المحكّم.

## Non-Negotiables
- بيانات حقيقية فقط من `omar4144/edama-migration-archive` — لا بيانات وهمية.
- الطبقة التاريخية **immutable على مستوى DB + HTTP + Audit** (defense in depth).
- JWT + bcrypt + refresh + RBAC + عزل بيانات على API (لا إخفاء واجهة فقط).
- مصطلح `المحكّم / Evaluator` فقط.
- لا LLM، لا PDF export، لا merge تلقائي.
- تجربة V8 كتجربة تشغيلية مترابطة (الدفعة ← الجهة ← المستشار ← النموذج ← التحكيم ← الأثر) — ليس palette فقط.

## Contract-Locked Counts (verified)
| Item | Target | Actual |
|---|---:|---:|
| Lovable records | 2,565 | ✓ |
| Lovable orgs | 57 | ✓ |
| People | 17 | ✓ |
| Model definitions | 45 | ✓ |
| Work hours total | 1,662.0 | ✓ |
| Legacy orgs (24/30/29/35) | 118 | ✓ |
| Legacy activities (0/1200/1160/1400) | 3,760 | ✓ |
| Legacy arbitrations (0/1382/1081/940) | 3,403 | ✓ |
| Legacy duplicate link groups | 67 | ✓ |
| Batch plan rows | 120 | ✓ |
| Batch KPI snapshots | 4 | ✓ |
| REVIEW_REQUIRED mappings | 9 | ✓ |
| template_metadata_stale | 2,336 | ✓ |
| activity_name_variant | 960 | ✓ |
| activity_row_sheet_mismatch | 80 | ✓ |

## What's Been Implemented

### Iteration 1 (Foundation)
- FastAPI + React + MongoDB scaffold, RTL, IBM Plex Sans Arabic, V8 palette
- JWT (bcrypt, httpOnly cookies + Bearer fallback), RBAC, brute-force lockout
- Real archive import: 12 CSV/JSON → MongoDB, contract counts verified 10/10
- Admin: reconciliation dashboard + review queue + records/orgs/users/audit
- Consultant: submissions + draft edit + historical activities
- Evaluator: assigned queue + decision recorder + hours summary
- Testing: 20/20 pytest

### Iteration 2 (Final Finish — P0)
- **Historical write-guard (defense in depth)**: DB-layer `ImmutableCollection` proxy blocks writes on 12 historical/crosswalk/source collections + HTTP-layer PATCH/DELETE endpoints return 405 + every attempt logged as `historical_write_blocked` in `audit_log`.
- **Force password change**: HTTP 428 on all operational endpoints if `must_change_password=true`. `/auth/me`, `/auth/logout`, `/auth/change-password` remain accessible. Rotates cookies + bumps `pw_version` → old tokens revoked with 401 "Session revoked". Frontend does hard reload after success to eliminate race.
- **Password reset**: `/auth/forgot-password` (SHA256 tokens, 1h TTL, 3/hour rate-limit, no user enumeration, dev mail sink). `/auth/reset-password` (weak → 422, reuse → 400, expired → 400, invalidates all sessions on success).
- **Evaluator historical viewer**: `/api/evaluator/historical-arbitrations` — scoped to logged-in person's name (Batool → 282), read-only notice, search/cohort/pagination, isolation verified.
- **Data Quality Center**: `/api/admin/dq/summary` — 16 static checks + 7 live signals (template_metadata_stale=2336, etc). `/api/admin/dq/affected/{signal_id}` — drill-down to real affected rows.
- **V8 experience**: Cohort map (خريطة الدفعات) with data-driven progress bars, Cohort world (عالم الدفعة) with KPI snapshot + per-org counts, Organization journey (رحلة الجهة) with Cohort→Org→Consultant→Model→Arbitration→Impact strip + current/legacy panels + assignment-changed banner.
- **Session revocation via pw_version**: all previously-issued tokens invalidated on any password change/reset.
- **Password strength**: 8+ chars, letters + digits enforced.
- **Mobile responsive AppShell**: hamburger drawer, viewport-aware header, tested 390×780.
- **Security**: `test_credentials.md` excluded via `.gitignore`; secrets only in `.env`.
- Testing: **33/33 pytest** on iteration 2 (backend) + all P0 frontend flows verified.

## Test Accounts (preview env only — not for production)
See `/app/memory/test_credentials.md` (gitignored). All non-owner accounts flagged `must_change_password=true`.

## Backlog

### P1 (post-Final-Finish)
- Live Lovable API sync (currently: snapshot-based)
- Consultant/Evaluator time-series trends (data-driven chart)
- Export reconciliation report as JSON/CSV
- Session revocation UI (active sessions list + revoke)
- Program/cohort management (create/edit)

### P2
- Full accessibility audit + keyboard shortcut layer
- dev_mail_sink.log rotation
- SMTP integration when credentials provided (structure ready — set RESET_URL_BASE + env-based provider)

## Notes
- Two P0.2 tests are stateful (each run flips `must_change_password`); serial pytest + restore helper documented in testing agent report.
- Historical collections are protected at DB-proxy layer; migration script uses `EDAMA_MIGRATION_MODE=1` bypass — the ONLY way to write historical.
