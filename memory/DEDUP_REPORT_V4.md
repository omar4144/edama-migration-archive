# تقرير Canonical Deduplication — الإصدار الرابع (v4)

_مُنشأ في: 2026-07-31T20:10:35.156318+00:00 — logic_version: v4_families_and_decisions_


## 1) الإضافات الجوهرية على v3

1. **قاموس القرارات الصحيح** (`decisions.py`): فصل تام بين `decision_normalized` و `completion_status`.
   - Legacy: «مجاز» → **APPROVED**، «غير مجاز» → **REJECTED**، «مجاز مع تحفظ» → **APPROVED_WITH_RESERVATION** (غير موجود في البيانات فعليًا)، «يحتاج لتطوير» → **NEEDS_IMPROVEMENT**، «مكتمل/غير مكتمل» → **completion_status** فقط (ليس قرارًا).
   - Current: «مقبول» → **APPROVED**، «يحتاج لتطوير» → **NEEDS_IMPROVEMENT**، «غير مكتمل» → **completion_status = INCOMPLETE** (بلا قرار).
2. **إعادة تصنيف الأزواج** بناءً على القرارات المُطبَّعة. أهم اختلاف عن v3: أزواج legacy=«مجاز» → current=«مقبول» بفارق زمني كبير لم تعد تُصنَّف نُسَخًا (كانت v3 تعتبرها version_resubmit خطأً)؛ الآن REVIEW_REQUIRED بسبب `wide_gap_identical_decision`.
3. **Canonical Submission Families**: جمع كل نسخ نفس (الجهة × تعريف النموذج) في «رحلة» واحدة (`family_id = FAM-######`). الرحلة تحكي: نموذج تاريخي → قرار تاريخي → تحسين → نموذج حالي → قرار جديد.
4. **ثلاثة أرقام منفصلة** بدلاً من رقم واحد مضلل.


## 2) الأرقام الثلاثة الجديدة

| المؤشر | القيمة | تعريفه |
| --- | --- | --- |
| **عدد رحلات/عائلات النماذج** | 3521 | عدد الرحلات المستقلة (org × model). كل رحلة قد تحوي عدة نُسَخ في الزمن. |
| **عدد النسخ (Canonicals)** | 5038 | كل تسليم/تحكيم كنسخة مستقلة بعد إزالة التكرارات الداخلية. |
| **عدد أحدث المخرجات التشغيلية** | 3521 | أحدث نسخة واحدة لكل رحلة (= عدد الرحلات). |

### توزيع الرحلات

| البند | عدد الرحلات | % من الإجمالي |
| --- | --- | --- |
| Full lifecycle (legacy → current) | 1019 | 28.9% |
| Current only (لم يسبقها تحكيم تاريخي) | 724 | 20.6% |
| Legacy only (لا يوجد استلام حالي) | 1778 | 50.5% |
| Rows including at least one REVIEW_REQUIRED | 868 | 24.7% |

### توزيع آخر قرار مطبّع (على مستوى الرحلة)

| القرار | عدد الرحلات |
| --- | --- |
| APPROVED | 2366 |
| REJECTED | 947 |
| PENDING | 138 |
| UNKNOWN | 35 |
| NEEDS_IMPROVEMENT | 35 |

### توزيع آخر حالة اكتمال

| الحالة | عدد الرحلات |
| --- | --- |
| COMPLETE | 3348 |
| UNKNOWN | 138 |
| INCOMPLETE | 35 |

## 3) مقارنة v3 → v4 (على مستوى الـ canonicals)

| match_status | v3 (both sides) | v4 (both sides) | التغيير |
| --- | --- | --- | --- |
| VERSION_LINKED | 2201 | 1137 | -1064 |
| REVIEW_REQUIRED | 560 | 1624 | 1064 |
| EXACT_CROSS_SOURCE_MATCH | 0 | 0 | 0 |
| PROBABLE_CROSS_SOURCE_MATCH | 0 | 0 | 0 |
| CURRENT_ONLY | 499 | 499 | 0 |
| LEGACY_ONLY | 1778 | 1778 | 0 |
| **الإجمالي** | 5038 | 5038 | 0 |

### تفسير النقلة

- في v3 كان كل زوج مرتبط عبر crosswalk (بغض النظر عن معنى القرار) يُصنَّف VERSION_LINKED. النتيجة: 2,201 نسخة موصولة و 560 مراجعة.
- في v4 (بالقاموس الصحيح) فقط الأزواج التي فيها **legacy = REJECTED / NEEDS_IMPROVEMENT / APPROVED_WITH_RESERVATION / (INCOMPLETE completion)** ← current = APPROVED تُصنَّف VERSION_LINKED. هذا يُخرج من فئة النسخ كل الأزواج التي فيها الطرفان APPROVED ومتباعدان زمنيًا (392 زوجًا) ويرسلها إلى **REVIEW_REQUIRED / wide_gap_identical_decision** لأنها إما إعادة تحكيم أو إشكال بيانات.


### توزيع أسباب REVIEW_REQUIRED

| السبب | العدد | ملاحظة |
| --- | --- | --- |
| wide_gap_identical_decision | 392 | كلا الطرفين APPROVED لكن التاريخان بعيدان؛ إعادة تحكيم أو خلل مصدر |
| no_direct_model_match_only_org | 226 | crosswalk = NO_DIRECT_MODEL_MATCH — تطابق جهة فقط |
| wide_gap_conflicting_decisions | 126 | قراران متعارضان دون نمط نسخة واضح |
| evaluator_mismatch_cross_source | 124 | اختلاف المحكم بين المصدرين |
| **الإجمالي (current-side)** | 868 |  |

## 4) الساعات — لا تُجمع أبدًا كرقم واحد

| البند | قيمة | الوحدة |
| --- | --- | --- |
| Raw Lovable hours | 1662.0 | per_model |
| **Lovable after internal dedup** | 1203.0 | **per_model** — القيمة التشغيلية النظيفة |
| Raw Legacy hours | 75015.0 | org × cohort مكررة |
| Legacy after internal dedup (naive) | 73395.0 | org × cohort لا تزال مكررة |
| **Legacy per (org × cohort) unique** | 1605.0 | **org × cohort** — القيمة الصحيحة |

**قاعدة عرض إلزامية:** الواجهة يجب أن تعرض:
- «ساعات تحكيم النماذج الحالية بعد التنظيف: **1203 س** (لكل نموذج)»
- «ساعات الجهات والدفعات التاريخية: **1605 س** (لكل جهة/دفعة)»
- ❌ لا رقم موحّد يجمعهما. ❌ لا Final operational hours.


## 5) عيّنات موثّقة — 20 رحلة (Submission Families)

لكل رحلة: بيانات الرحلة العامة، ثم جدول النسخ مرتبة زمنيًا يوضّح الانتقال من التحكيم التاريخي إلى الاستلام الحالي بقرار مطبّع.


### رحلة 1 — جمعية المشي والجري

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000001 |
| الجهة | جمعية المشي والجري |
| النموذج | أداة تقييم الجاهزية |
| Model definition ID | MODEL-001 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-003064 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-000001 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 2 — جمعية المشي والجري

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000002 |
| الجهة | جمعية المشي والجري |
| النموذج | التقييم الذاتي للجهة |
| Model definition ID | MODEL-002 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-003061 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-000002 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 3 — جمعية المشي والجري

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000003 |
| الجهة | جمعية المشي والجري |
| النموذج | تقرير لقاء التعارف |
| Model definition ID | MODEL-003 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-003062 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-000003 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 4 — جمعية المشي والجري

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000004 |
| الجهة | جمعية المشي والجري |
| النموذج | تقرير ورش العمل مع مجلس الإدارة (أو من يقوم مقامهم) والإدارات الموازية |
| Model definition ID | MODEL-004 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-003063 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-000004 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 5 — جمعية المشي والجري

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000005 |
| الجهة | جمعية المشي والجري |
| النموذج | نموذج التقرير العام عن المنظمة |
| Model definition ID | MODEL-005 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-003060 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-000005 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 6 — مؤسسة الاميرة العنود

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000030 |
| الجهة | مؤسسة الاميرة العنود |
| النموذج | أداة تقييم الجاهزية |
| Model definition ID | MODEL-001 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-002876 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-000030 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 7 — مؤسسة الاميرة العنود

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000031 |
| الجهة | مؤسسة الاميرة العنود |
| النموذج | التقييم الذاتي للجهة |
| Model definition ID | MODEL-002 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-002873 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-000031 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 8 — مؤسسة الاميرة العنود

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000032 |
| الجهة | مؤسسة الاميرة العنود |
| النموذج | تقرير لقاء التعارف |
| Model definition ID | MODEL-003 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-002874 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-000032 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 9 — مؤسسة الاميرة العنود

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000033 |
| الجهة | مؤسسة الاميرة العنود |
| النموذج | تقرير ورش العمل مع مجلس الإدارة (أو من يقوم مقامهم) والإدارات الموازية |
| Model definition ID | MODEL-004 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-002875 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-000033 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 10 — مؤسسة الاميرة العنود

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000034 |
| الجهة | مؤسسة الاميرة العنود |
| النموذج | نموذج التقرير العام عن المنظمة |
| Model definition ID | MODEL-005 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-002872 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-000034 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 11 — رحلة كاملة (REJECTED → APPROVED)

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000006 |
| الجهة | جمعية المشي والجري |
| النموذج | نموذج تقرير متابعة التشغيل وإغلاق التأسيس |
| Model definition ID | MODEL-006 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-19 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-003066 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-000006 | current | 2026-01-19 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 12 — رحلة كاملة (REJECTED → APPROVED)

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000007 |
| الجهة | جمعية المشي والجري |
| النموذج | نموذج خطة سد الفجوات |
| Model definition ID | MODEL-007 |
| عدد النسخ | 5 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-002830 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-002924 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 3 | CANON-003018 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 4 | CANON-003065 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 5 | CANON-000007 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 13 — رحلة كاملة (REJECTED → APPROVED)

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000008 |
| الجهة | جمعية المشي والجري |
| النموذج | أداة إدارة الفرص التطوعية |
| Model definition ID | MODEL-008 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-21 |
| يحتاج مراجعة؟ | لا |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-003085 | legacy | 2025-08-16 | غير مجاز | REJECTED | COMPLETE | VERSION_LINKED | resubmission_version_resubmit |
| 2 | CANON-000008 | current | 2026-01-21 | مقبول | APPROVED | COMPLETE | VERSION_LINKED | resubmission_version_resubmit |

### رحلة 14 — مراجعة — wide_gap_identical_decision (كلاهما مجاز)

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000016 |
| الجهة | جمعية المشي والجري |
| النموذج | دليل المتطوع |
| Model definition ID | MODEL-016 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-003076 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-000016 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 15 — مراجعة — wide_gap_identical_decision (كلاهما مجاز)

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000036 |
| الجهة | مؤسسة الاميرة العنود |
| النموذج | نموذج خطة سد الفجوات |
| Model definition ID | MODEL-007 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-002877 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |
| 2 | CANON-000036 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | wide_gap_identical_decision |

### رحلة 16 — مراجعة — evaluator_mismatch_cross_source

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000480 |
| الجهة | جمعية أفق لتطوير العمل الخيري والتطوعي |
| النموذج | أداة إدارة الفرص التطوعية |
| Model definition ID | MODEL-008 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-28 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-001957 | legacy | 2025-08-16 | غير مجاز | REJECTED | COMPLETE | REVIEW_REQUIRED | evaluator_mismatch_cross_source |
| 2 | CANON-000480 | current | 2026-01-28 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | evaluator_mismatch_cross_source |

### رحلة 17 — مراجعة — evaluator_mismatch_cross_source

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000484 |
| الجهة | جمعية أفق لتطوير العمل الخيري والتطوعي |
| النموذج | الميثاق الأخلاقي للمتطوع |
| Model definition ID | MODEL-012 |
| عدد النسخ | 2 |
| الرحلة | legacy + current |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-26 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-001947 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | REVIEW_REQUIRED | evaluator_mismatch_cross_source |
| 2 | CANON-000484 | current | 2026-01-26 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | evaluator_mismatch_cross_source |

### رحلة 18 — Current only — لا نسخة تاريخية

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000010 |
| الجهة | جمعية المشي والجري |
| النموذج | الدليل الإرشادي لإنشاء وإدارة الفرق التطوعية |
| Model definition ID | MODEL-010 |
| عدد النسخ | 1 |
| الرحلة | current only |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-18 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-000010 | current | 2026-01-18 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | no_direct_model_match_only_org |

### رحلة 19 — Current only — لا نسخة تاريخية

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-000014 |
| الجهة | جمعية المشي والجري |
| النموذج | بطاقات الوصف الوظيفي |
| Model definition ID | MODEL-014 |
| عدد النسخ | 1 |
| الرحلة | current only |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2026-01-21 |
| يحتاج مراجعة؟ | نعم |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-000014 | current | 2026-01-21 | مقبول | APPROVED | COMPLETE | REVIEW_REQUIRED | no_direct_model_match_only_org |

### رحلة 20 — Legacy only — لا استلام حالي

| الحقل | قيمة |
| --- | --- |
| Family ID | FAM-001744 |
| الجهة | جمعية نبتون للتاهيل الطبي |
| النموذج | نموذج التقرير العام عن المنظمة |
| Model definition ID | MNAME (بلا معرف) |
| عدد النسخ | 1 |
| الرحلة | legacy only |
| آخر قرار مطبّع | APPROVED |
| آخر حالة اكتمال | COMPLETE |
| آخر تاريخ | 2025-08-16 |
| يحتاج مراجعة؟ | لا |

| # | canonical_id | source | التاريخ | raw decision | decision (normalized) | completion | match_status | match_reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | CANON-001744 | legacy | 2025-08-16 | مجاز | APPROVED | COMPLETE | LEGACY_ONLY | no_current_lovable_peer |

## 6) القرار المطلوب من الملكية

الأرقام الرسمية المقترحة للاعتماد التالي:
- **عدد رحلات/عائلات النماذج (Model Journeys):** 3,521
- **عدد النسخ (Canonicals):** 5,038
- **عدد أحدث المخرجات التشغيلية:** 3,521
- **رحلات كاملة (تاريخية + حالية):** 1,019
- **رحلات في المراجعة:** 868
- **الساعات:** 1,203 س Lovable per_model | 1,605 س Legacy per_org_cohort — لا جمع.

**البنود المفتوحة قبل UI Cutover:**
1. اعتمد قاموس القرارات ونتائج التصنيف الجديدة.
2. اعتمد الأرقام الثلاثة.
3. اعتمد قاعدة عرض الساعات بشكل منفصل (بدون رقم موحّد).
4. حدد كيف يجب أن تظهر REVIEW_REQUIRED (868 رحلة) في الواجهة — قائمة عمل للمشرف؟ مراجعة إلزامية قبل الإحصائيات؟
5. حدد ماذا نُظهر «كنموذج»: `families` (3,521) أم `latest_operational` (3,521 — نفس القيمة)، وماذا نُظهر «كنسخ»: 5,038.
