# التدقيق الموحد — تسليمات Iteration 13.1 (قراءة فقط)
_تاريخ: 2026-07-31 — لا تعديل على قاعدة البيانات. جميع الملفات في `/app/memory/`._

## القرارات المُعتمَدة (بناءً على مراجعة المالك)
- **118 جمعية موحدة** هي العدد الرسمي. الـ175 صف مصدر داخلي فقط.
- **PROBABLE_NAME_VARIANT** لـ «صندوق الشهداء ↔ صندوق الشهداء والمصابين والأسرى والمفقودين» تمّت الموافقة عليه بشريًا — مُسجَّل كإدخال قيد التنفيذ في `PROPOSED_AUDIT_LOG_ENTRIES.csv` ولن يُنفَّذ على قاعدة البيانات حتى إشعارك.
- «مقبول» في Lovable = **LINK_EXISTS_CONTENT_NOT_VERIFIED**، ليس دليل تخرّج.

## المؤشرات (بعد الاعتماد)
| المؤشر | القيمة |
|---|---:|
| صفوف مصادر الجهات (ORGANIZATION_PARTICIPATION_SOURCE_RECORDS) | 175 |
| جمعيات موحدة (ORGANIZATION_UNIFIED_REGISTRY) | 118 |
| مشاركات موحدة org × cohort (ORGANIZATION_COHORT_PARTICIPATIONS_UNIFIED) | 118 |
| UNIFIED_EXACT | 56 |
| UNIFIED_PROBABLE_HUMAN_APPROVED | 1 |
| LEGACY_ONLY | 61 |
| LOVABLE_ONLY | 0 |

## توزيع الدفعات (المشاركات الموحدة)
| الدفعة | عدد الجمعيات |
|---|---:|
| 1 | 24 |
| 2 | 30 |
| 3 | 29 |
| 4 | 35 |
| **الإجمالي** | **118** |

## احتمال مشاركة عبر دفعات — مرشحون للمراجعة
- عدد الأزواج التي فوق العتبة (ratio≥0.72 أو jaccard≥0.3): **96**.
- لن تُدمج تلقائيًا. القرار بشري فقط.
- الملف: `CROSS_COHORT_CANDIDATES.csv`.

## جودة الـ57 جهة Lovable
- الملف: `LOVABLE_57_ORG_QUALITY.csv` — 57 صف، عمود لكل مؤشر.
- تصنيف كل جمعية حاليًا: `LINK_EXISTS_CONTENT_NOT_VERIFIED`. لم يُفحص أي محتوى ملف Google.
- لا يُدَّعى تخرّج أي جهة استنادًا إلى وجود 45 صفًا أو قيمة «مقبول».

## تأكيد سلامة البيانات
- لم تُعدَّل أي مجموعة (`source_records`, `historical_organizations`, `organizations_current`, `crosswalk_organizations`, `participating_orgs`, `canonical_submissions`, `canonical_submission_families`).
- كل الكتابة إلى `/app/memory/*.csv` و `PARTICIPATING_ORGANIZATIONS_REVIEW.xlsx`.
- الـ175 صف الأصلية محفوظة في `ORGANIZATION_PARTICIPATION_SOURCE_RECORDS.csv` كطبقة أدلة.

## قائمة الملفات المُنتَجة في هذه التسليمة
- `ORGANIZATION_PARTICIPATION_SOURCE_RECORDS.csv` — 175 صف مصدر.
- `ORGANIZATION_COHORT_PARTICIPATIONS_UNIFIED.csv` — 118 مشاركة موحدة.
- `ORGANIZATION_UNIFIED_REGISTRY.csv` — 118 جمعية موحدة.
- `CROSS_COHORT_CANDIDATES.csv` — مرشحو التطابق عبر الدفعات.
- `LOVABLE_57_ORG_QUALITY.csv` — جودة الـ57 جهة Lovable.
- `PROPOSED_AUDIT_LOG_ENTRIES.csv` — إدخال دمج «صندوق الشهداء» المُقترَح.
- `PARTICIPATING_ORGANIZATIONS_REVIEW.xlsx` — كتاب Excel محدَّث بجميع الأوراق.
