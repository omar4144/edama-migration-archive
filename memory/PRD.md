# PRD — Edama · Musr'at Idama V8 · Iteration 3 (Unified Operational Platform)

## Original Problem Statement
Edama V8 — منصة تشغيلية موحّدة لمسرعة الاستدامة تدمج الأرشيف التاريخي مع بيانات Lovable الحالية في تدفّق تشغيلي واحد.

## المبدأ المركزي (Iteration 3)
**كل رقم يفتح سياقه، وكل نموذج يقود إلى أثره.**
المسار الطبيعي: `البرنامج ← الدفعة ← المحكم/المستشار ← الجهة ← النموذج ← القرار ← الأثر`

## القرارات المعمارية الحاسمة
- **لا فصل تشغيلي بين Lovable والتاريخي**: مصدر البيانات شارة داخل التفاصيل، وليس تبويباً أو فلتراً رئيسياً.
- **الجذر `/admin` = المشهد التنفيذي** (وليس لوحة المصالحة).
- **جميع العناصر التقنية** (المصالحة، جودة البيانات، المطابقات، السجلات الخام، سجل التدقيق، المستخدمون) تحت `/admin/data/*` كقسم فرعي «إدارة البيانات» في القائمة.
- **دليل موحّد للأشخاص**: `people` (حاليون) + distinct من `historical_arbitrations.evaluator_name` + `historical_activities.consultant_name` → 13 محكم + 11 مستشار.
- **الجهة الموحّدة**: header + impact strip + نماذج مجمّعة بالفئة (بدلاً من tabs).
- **مركز النماذج**: بحث موحّد يجمع `records_current` + `historical_arbitrations` تحت مخطط `unified_record` واحد.
- **حماية الطبقة التاريخية** (من iteration 2) قائمة بلا تغيير.

## Iteration 3 — الإضافات

### Backend
- `/app/backend/unified.py` — `resolve_url` priority (canonical > hyperlink_target > displayed > model_url) + `unified_record` projection.
- `/app/backend/routes/exec_scene.py` — `/api/admin/exec/scene`: journey totals + cohorts strip + attention list (data-driven).
- `/app/backend/routes/directory.py` — دليل المحكمين والمستشارين الموحّد (union of people + historical distinct names). Detail = cohorts + orgs expandable + real model URLs.
- `/app/backend/routes/models_hub.py` — بحث موحّد مع فلاتر شاملة، URL priority محلولة.
- `/app/backend/routes/unified_org.py` — الجهة الموحّدة (header + records مجمّعة بالفئة، بلا tabs).

### Frontend
- `/app/frontend/src/lib/util.js` — `resolveUrl`, `sourceBadge`, `evaluationTone`, `num`.
- Top-nav horizontal بدلاً من sidebar للأدمن، مع dropdown «إدارة البيانات».
- Mobile drawer شامل لكل العناصر.
- صفحات جديدة: `ExecutiveScene`, `EvaluatorsDirectory`, `EvaluatorDetail`, `ConsultantsDirectory`, `ConsultantDetail`, `ModelsHub`, `UnifiedOrganizations`, `UnifiedOrganization`.
- كل رقم رئيسي = رابط إلى الوجهة المُفلترة.
- كل نموذج له `model_url*` → زر `فتح النموذج ↗` بـ `target="_blank" rel="noopener noreferrer"`.

## الأرقام الحقيقية بعد التوحيد
| Metric | Value |
|---|---:|
| Cohorts | 4 |
| Organizations (unified) | 57 |
| Evaluators (unified) | 13 (5 current + 8 legacy-only) |
| Consultants (unified) | 11 (9 current + 2 legacy-only) |
| Model definitions | 45 |
| Current records (Lovable) | 2,565 |
| Legacy arbitrations | 3,403 |
| Legacy activities | 3,760 |
| Total hours (current + legacy) | 76,677.0 (1,662 current + 75,015 legacy) |
| Batool profile | 507 items (225 current + 282 legacy), 11 orgs, cohort 4 |

## Iteration 1-2 (محفوظة كما هي)
- JWT + bcrypt + refresh + brute-force + must_change_password + password reset + session revocation.
- Historical write-guard (DB proxy + HTTP 405 + audit).
- Data Quality Center + drill-downs.
- Reconciliation report + mapping decisions.
- RBAC + API-layer data isolation + 33/33 pytest passing.

## Backlog (post-iteration 3)
- P1: Program-level (multi-program) support — currently single-program (مسرعة إدامة).
- P1: Impact evidence per cohort (KPIs + evidence attachments).
- P1: Reports export.
- P2: Live Lovable sync via API (currently snapshots).
