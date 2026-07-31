# PRD — Edama V8 · Iteration 4 (Canonical Deduplication Layer)

## Context
User rejected 5,968 as «إجمالي النماذج والتحكيمات» — that's a naive `2565+3403` sum of raw source rows without cross-source dedup. Iteration 4 builds a canonical layer BEFORE any UI change (per user instruction).

## Deliverables (backend-only, no UI change yet)
- `/app/backend/dedup.py` — URL normalization (Google Docs file-id extraction), scoring helper
- `/app/backend/migrations/build_canonical.py` — canonicalization pass (idempotent)
- `/app/backend/routes/canonical.py` — `/api/admin/canonical/{report,submissions,submissions/{id}}`

## Method
Verified: 0 file_id intersection between 2,565 current URLs and 324 legacy URLs (Lovable regenerates file IDs on migration). So URL-only matching cannot work cross-source. Uses the archive's pre-computed `crosswalk_records` (1,517 MATCHED_ORG_AND_MODEL pairs) as EXACT signal. Applies Lovable's `duplicate_link_group_id` (129 groups) and legacy `historical_duplicate_links.resource_id` (67 groups) for internal dedup.

Raw data NEVER modified. Derived collections: canonical_submissions, record_crosswalks, duplicate_groups, canonical_reviews, dedup_reports.

## Real Numbers (Reconciliation Report)
| Metric | Value |
|---|---:|
| Raw current (Lovable) | 2,565 |
| Raw legacy (arbitrations) | 3,403 |
| Naive sum (misleading) | 5,968 |
| **Canonical total (after dedup)** | **4,020** |
| ↳ EXACT_CROSS_SOURCE_MATCH | 1,018 |
| ↳ CURRENT_ONLY | 499 |
| ↳ REVIEW_REQUIRED | 226 |
| ↳ LEGACY_ONLY | 2,277 |
| Internal Lovable dupes folded | 822 |
| Internal legacy dupes folded | 108 |
| Duplicate groups | 195 |
| **Reduction from naive** | **1,948** |
| Hours (operational, deduped, Lovable-authoritative) | 45,077.5 |
| Hours raw current | 1,062.5 |
| Hours raw legacy | 73,395.0 |

## Sample verification (20 groups reported to user)
- 5 EXACT matches for جمعية المشي والجري (BATOOL-A1-01…05 ↔ LEG-REV-01317…01321) — بتول الرويلي
- 5 EXACT matches for بتول الرويلي in مؤسسة الاميرة العنود (BATOOL-A2-01…05 ↔ LEG-REV-01129…01133)
- 5 CURRENT_ONLY samples (جمعية البر لقرى جنوب مكة — سارة بالخير)
- 5 LEGACY_ONLY samples (جمعية نبتون للتاهيل الطبي — أحمد خواجي)

## Testing
- iter4: **25/25 PASS** — endpoint contract, sample content, RBAC, historical-guard regression, reconciliation counts regression, idempotency
- iter3: 27/27 regression PASS
- iter2: 30/33 PASS (1 unrelated data drift: pending_mappings 9→8, from an earlier accepted mapping — not caused by this iteration)

## Next Iteration (awaits user approval)
1. Replace 5,968 in Executive Scene with `stats.canonical_total` (4,020) + tooltip explaining dedup
2. Drilldown from canonical count → /api/admin/canonical/submissions filtered lists
3. Per-org unified page: show canonical count + versions + source occurrences (not raw sum)
4. Evaluator/Consultant pages: collapse to canonical models per org
5. Hours: use `hours_operational_deduped` (45,077.5) with breakdown

**No UI numbers were changed in iteration 4 per user's explicit instruction.**
