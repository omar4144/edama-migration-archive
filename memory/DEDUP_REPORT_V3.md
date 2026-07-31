# تقرير Canonical Deduplication — الإصدار الصارم (v3)

_مُنشأ في: 2026-07-31T19:54:06.320129+00:00 — logic_version: v3_strict_rules_


## 1) قواعد المطابقة الصارمة المطبقة

- **EXACT_CROSS_SOURCE_MATCH**: يتطلب المسار المركب — نفس الجهة + نفس النموذج + نفس المحكم (كلاهما موجود ومتساويان) + التاريخ مطابق تمامًا (نفس اليوم) + القراران متوافقان + لا يوجد دليل على نسخة مختلفة. لا يُمنح EXACT بناءً على الجهة + نوع النموذج فقط.
- **PROBABLE_CROSS_SOURCE_MATCH**: الجهة + النموذج + المحكم + توافق القرار، والفارق الزمني بين 1 و 3 أيام. لا يُدمج تلقائيًا؛ يبقى ككيانين قانونيين مع رابط `probable_link` بانتظار مراجعة بشرية.
- **VERSION_LINKED**: نفس الجهة + نفس النموذج + نفس المحكم مع نمط إعادة إرسال (legacy = «يحتاج لتطوير» أو «غير مكتمل» ← current = «مقبول») والفارق الزمني > 3 أيام. يبقيان ككيانين مرتبطين ولا يُدمجان.
- **REVIEW_REQUIRED**: crosswalk_status = NO_DIRECT_MODEL_MATCH أو اختلاف المحكم أو تعارض القرارات بفارق زمني كبير. لا دمج تلقائي.
- **CURRENT_ONLY**: crosswalk_status = NO_LEGACY_ARBITRATION_RECORD.
- **LEGACY_ONLY**: صف تاريخي لا تشير إليه أي crosswalk row.


## 2) مقارنة قبل/بعد التشديد (كل الـ canonicals — الطرفان معًا)

| المقياس | قبل التشديد (v2) | بعد التشديد (v3) |
| --- | --- | --- |
| Canonicals إجمالي | 4020 | 5038 |
| EXACT_CROSS_SOURCE_MATCH | 1018 | 0 |
| PROBABLE_CROSS_SOURCE_MATCH | 0 | 0 |
| VERSION_LINKED (كلا الطرفين) | 0 | 2201 |
| REVIEW_REQUIRED (كلا الطرفين) | 226 | 560 |
| CURRENT_ONLY | 499 | 499 |
| LEGACY_ONLY | 2277 | 1778 |

### تقسيم على المصدر (current-side / legacy-side)

| match_status | current-side | legacy-side |
| --- | --- | --- |
| EXACT_CROSS_SOURCE_MATCH | 0 | 0 |
| PROBABLE_CROSS_SOURCE_MATCH | 0 | 0 |
| VERSION_LINKED | 894 | 1307 |
| REVIEW_REQUIRED | 350 | 210 |
| CURRENT_ONLY | 499 | 0 |
| LEGACY_ONLY | 0 | 1778 |

### توزيع روابط الأزواج (canonical_links)

| نوع الرابط | عدد الأزواج |
| --- | --- |
| VERSION_LINKED | 1307 |
| REVIEW_REQUIRED | 210 |

## 3) لماذا انهار الرقم القديم؟

- في v2 كان كل صف MATCHED_ORG_AND_MODEL في `crosswalk_records` يُعامَل كـ EXACT ويُدمج تلقائيًا في canonical واحد. هذا كان يُنقص العدد بمقدار 1517 صفًا رغم أن الأزواج تختلف في التاريخ (كل الأزواج البالغة 1517 لها فارق زمني > 7 أيام؛ متوسط الفارق ≈ 155 يومًا) وتختلف في القرار (legacy = «غير مكتمل / يحتاج لتطوير» بينما current = «مقبول»).
- تحت القواعد الصارمة: **0 EXACT**، **0 PROBABLE**، والغالبية الساحقة صنّفت **VERSION_LINKED** (1307 رابط زوج، يمثّلها 894 canonical حالي + 1307 canonical تاريخي = 2201 canonical إجمالي).
- 210 من روابط الأزواج المتبقّية صُنّفت **REVIEW_REQUIRED** بسبب اختلاف المحكم بين المصدرين.
- 228 crosswalk من نوع `NO_DIRECT_MODEL_MATCH` (تطابق الجهة فقط دون نموذج) صنّفت أيضًا **REVIEW_REQUIRED**.
- عدد الـ canonicals إجمالاً ارتفع من 4020 إلى **5038** لأن الدمج التلقائي كان خاطئًا: هذه الـ 1018 canonical من v2 تمثّل في الواقع 2201 canonical (نسختين لكل خط).
- الرقم 3,794 السابق كان "confirmed = EXACT + CURRENT_ONLY + LEGACY_ONLY" وتم إعادة حسابه بالكامل — لم يعد صحيحًا.


## 4) تسوية الساعات — تفصيل كامل

| البند | قيمة | ملاحظة |
| --- | --- | --- |
| Lovable — Raw hours (كل الصفوف) | 1662.0 | 2565 صف؛ متوسط 0.65 س، وسيط 0.5 س — **مستوى النموذج** (تحكيم لكل نموذج) |
| Lovable — بعد داخلي (deduped) | 1203.0 | إلغاء تكرارات المجموعات الداخلية (822 صف مدمج) |
| Legacy — Raw hours (كل الصفوف) | 75015.0 | 3403 صف؛ متوسط 22 س، الحد الأعلى 100 س — **مستوى الجهة × الدفعة** وليس النموذج |
| Legacy — بعد داخلي (deduped naive) | 73395.0 | يزال 108 صف مدمج داخليًا |
| Legacy — بعد dedup على مستوى (org × cohort) | 1605.0 | لأن نفس قيمة الساعات تُطبع على كل صف نموذج من نفس الجهة/الدفعة — القيمة الصحيحة هي واحدة لكل جهة/دفعة |
| Legacy hours removed by cross-source merge | 0.0 | 0 — لأن قواعد EXACT الصارمة لم تجد أي زوج قابل للدمج |
| Final operational hours (تقديري) | 2808.0 | = Lovable deduped + Legacy per-org-cohort. **رقم مؤقت** لأن الوحدتين مختلفتان |

### تحذيرات حرجة

- ساعات Lovable مقاسة **لكل نموذج / لكل تحكيم فردي** (0.5–3 س).
- ساعات Legacy مقاسة **على مستوى الجهة × الدفعة**: نفس قيمة `total_arbitration_hours_raw` تظهر مطبوعة على كل صف نموذج تابع لنفس الجهة/الدفعة. سبب الرقم المضخم 75,015 هو تكرار هذه القيمة عبر عشرات صفوف النموذج لكل جهة.
- **لا يجوز جمع الرقمين naïvely.** الرقم القديم 45,077.5 كان مركبًا من قيم legacy مضخمة + قيم current، لذلك هو مضلل.
- الرقم المرجعي 1,662 (Lovable raw) صحيح لكنه لا يمثل «العمل التشغيلي»، بل مجموع خام قبل حذف المجموعات المكررة داخل Lovable (129 مجموعة، 951 عضوًا). القيمة النظيفة = **1,203 س Lovable + 1,605 س Legacy على مستوى الجهة/الدفعة**.


### إجابة سؤال «مستوى الساعة»

- Lovable: **مستوى النموذج/التحكيم الفردي** — كل صف = ساعات المحكم على نموذج واحد.
- Legacy: **مستوى الجهة × الدفعة** — عمود `total_arbitration_hours` هو مجموع الساعات على مستوى الجهة في الدفعة، وقد نُسخ ميكانيكيًا على كل صف نموذج لتلك الجهة في المصدر الأصلي.


## 5) عيّنات موثّقة (20 مجموعة)


### عيّنة 1 — جمعية المشي والجري — Lovable side of a version pair

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000001 | CANON-003064 |
| Raw ID | BATOOL-A1-01 | LEG-REV-01321 |
| الجهة | جمعية المشي والجري | جمعية المشي والجري |
| النموذج | أداة تقييم الجاهزية | أداة تقييم الجاهزية |
| المحكم | بتول الرويلي | بتول الرويلي |
| المستشار | نجود السيد | نجود السيد |
| التاريخ | 2026-01-18 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 0.5 | 15 |
| URL | https://docs.google.com/spreadsheets/d/1OAJIlQgd3xpZkSqmuNCX4ZUjmNYr22Nf/edit?us | — |
| **Match status** | VERSION_LINKED | VERSION_LINKED |
| Match reason | resubmission_after_needs_improvement | resubmission_after_needs_improvement |
| Confidence | 90 | 90 |
| **التصنيف النهائي** | Version (not duplicate) | Version (not duplicate) |

### عيّنة 2 — جمعية المشي والجري — Lovable side of a version pair

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000002 | CANON-003061 |
| Raw ID | BATOOL-A1-02 | LEG-REV-01318 |
| الجهة | جمعية المشي والجري | جمعية المشي والجري |
| النموذج | التقييم الذاتي للجهة | التقييم الذاتي للجهة |
| المحكم | بتول الرويلي | بتول الرويلي |
| المستشار | نجود السيد | نجود السيد |
| التاريخ | 2026-01-18 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 1.0 | 15 |
| URL | https://cnp.kfupm.edu.sa/edama/edamasurvey9/submitted.php?submissionID=150ba1da7 | — |
| **Match status** | VERSION_LINKED | VERSION_LINKED |
| Match reason | resubmission_after_needs_improvement | resubmission_after_needs_improvement |
| Confidence | 90 | 90 |
| **التصنيف النهائي** | Version (not duplicate) | Version (not duplicate) |

### عيّنة 3 — جمعية المشي والجري — Lovable side of a version pair

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000003 | CANON-003062 |
| Raw ID | BATOOL-A1-03 | LEG-REV-01319 |
| الجهة | جمعية المشي والجري | جمعية المشي والجري |
| النموذج | تقرير لقاء التعارف | تقرير لقاء التعارف |
| المحكم | بتول الرويلي | بتول الرويلي |
| المستشار | نجود السيد | نجود السيد |
| التاريخ | 2026-01-18 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 1.0 | 15 |
| URL | https://docs.google.com/document/d/1KR2GtatIES-olpn6A0HcBAx2NOql3IkC/edit | — |
| **Match status** | VERSION_LINKED | VERSION_LINKED |
| Match reason | resubmission_after_needs_improvement | resubmission_after_needs_improvement |
| Confidence | 90 | 90 |
| **التصنيف النهائي** | Version (not duplicate) | Version (not duplicate) |

### عيّنة 4 — جمعية المشي والجري — Lovable side of a version pair

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000004 | CANON-003063 |
| Raw ID | BATOOL-A1-04 | LEG-REV-01320 |
| الجهة | جمعية المشي والجري | جمعية المشي والجري |
| النموذج | تقرير ورش العمل مع مجلس الإدارة (أو من يقوم مقامهم) والإدارات الموازية | تقرير ورش العمل مع مجلس الإدارة (أو من يقوم مقامهم) والإدارات الموازية |
| المحكم | بتول الرويلي | بتول الرويلي |
| المستشار | نجود السيد | نجود السيد |
| التاريخ | 2026-01-18 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 1.0 | 15 |
| URL | https://docs.google.com/document/d/1jMVRqQ3-CgdUHGiEZpqRxxElg9LO5Y14/edit?usp=sh | — |
| **Match status** | VERSION_LINKED | VERSION_LINKED |
| Match reason | resubmission_after_needs_improvement | resubmission_after_needs_improvement |
| Confidence | 90 | 90 |
| **التصنيف النهائي** | Version (not duplicate) | Version (not duplicate) |

### عيّنة 5 — جمعية المشي والجري — Lovable side of a version pair

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000005 | CANON-003060 |
| Raw ID | BATOOL-A1-05 | LEG-REV-01317 |
| الجهة | جمعية المشي والجري | جمعية المشي والجري |
| النموذج | نموذج التقرير العام عن المنظمة | نموذج التقرير العام عن المنظمة |
| المحكم | بتول الرويلي | بتول الرويلي |
| المستشار | نجود السيد | نجود السيد |
| التاريخ | 2026-01-18 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 0.5 | 15 |
| URL | https://docs.google.com/document/d/1PQKnJSu43xFEF_Qq9crQZSS4-MwtUR25/edit?usp=sh | — |
| **Match status** | VERSION_LINKED | VERSION_LINKED |
| Match reason | resubmission_after_needs_improvement | resubmission_after_needs_improvement |
| Confidence | 90 | 90 |
| **التصنيف النهائي** | Version (not duplicate) | Version (not duplicate) |

### عيّنة 6 — مؤسسة الاميرة العنود — بتول الرويلي كمحكم

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000030 | CANON-002876 |
| Raw ID | BATOOL-A2-01 | LEG-REV-01133 |
| الجهة | مؤسسة الاميرة العنود | مؤسسة الاميرة العنود |
| النموذج | أداة تقييم الجاهزية | أداة تقييم الجاهزية |
| المحكم | بتول الرويلي | بتول الرويلي |
| المستشار | نجود السيد | نجود السيد |
| التاريخ | 2026-01-18 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 0.5 | 15 |
| URL | https://docs.google.com/spreadsheets/d/1pnq89Th-GVFRsgLv1m6NaDvS8bTjP0JY/edit?gi | — |
| **Match status** | VERSION_LINKED | VERSION_LINKED |
| Match reason | resubmission_after_needs_improvement | resubmission_after_needs_improvement |
| Confidence | 90 | 90 |
| **التصنيف النهائي** | Version (not duplicate) | Version (not duplicate) |

### عيّنة 7 — مؤسسة الاميرة العنود — بتول الرويلي كمحكم

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000031 | CANON-002873 |
| Raw ID | BATOOL-A2-02 | LEG-REV-01130 |
| الجهة | مؤسسة الاميرة العنود | مؤسسة الاميرة العنود |
| النموذج | التقييم الذاتي للجهة | التقييم الذاتي للجهة |
| المحكم | بتول الرويلي | بتول الرويلي |
| المستشار | نجود السيد | نجود السيد |
| التاريخ | 2026-01-18 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 1.0 | 15 |
| URL | https://cnp.kfupm.edu.sa/edama/edamasurvey9/submitted.php?submissionID=990f53117 | — |
| **Match status** | VERSION_LINKED | VERSION_LINKED |
| Match reason | resubmission_after_needs_improvement | resubmission_after_needs_improvement |
| Confidence | 90 | 90 |
| **التصنيف النهائي** | Version (not duplicate) | Version (not duplicate) |

### عيّنة 8 — مؤسسة الاميرة العنود — بتول الرويلي كمحكم

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000032 | CANON-002874 |
| Raw ID | BATOOL-A2-03 | LEG-REV-01131 |
| الجهة | مؤسسة الاميرة العنود | مؤسسة الاميرة العنود |
| النموذج | تقرير لقاء التعارف | تقرير لقاء التعارف |
| المحكم | بتول الرويلي | بتول الرويلي |
| المستشار | نجود السيد | نجود السيد |
| التاريخ | 2026-01-18 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 1.0 | 15 |
| URL | https://docs.google.com/document/d/1lrR6pZq8-7INVAWNhdTsICA5AKJy63p9/edit | — |
| **Match status** | VERSION_LINKED | VERSION_LINKED |
| Match reason | resubmission_after_needs_improvement | resubmission_after_needs_improvement |
| Confidence | 90 | 90 |
| **التصنيف النهائي** | Version (not duplicate) | Version (not duplicate) |

### عيّنة 9 — مؤسسة الاميرة العنود — بتول الرويلي كمحكم

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000033 | CANON-002875 |
| Raw ID | BATOOL-A2-04 | LEG-REV-01132 |
| الجهة | مؤسسة الاميرة العنود | مؤسسة الاميرة العنود |
| النموذج | تقرير ورش العمل مع مجلس الإدارة (أو من يقوم مقامهم) والإدارات الموازية | تقرير ورش العمل مع مجلس الإدارة (أو من يقوم مقامهم) والإدارات الموازية |
| المحكم | بتول الرويلي | بتول الرويلي |
| المستشار | نجود السيد | نجود السيد |
| التاريخ | 2026-01-18 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 1.0 | 15 |
| URL | https://docs.google.com/document/d/1QLGrD3I7kF-Ib4K9hkIyGyukGDo8fzOX/edit | — |
| **Match status** | VERSION_LINKED | VERSION_LINKED |
| Match reason | resubmission_after_needs_improvement | resubmission_after_needs_improvement |
| Confidence | 90 | 90 |
| **التصنيف النهائي** | Version (not duplicate) | Version (not duplicate) |

### عيّنة 10 — مؤسسة الاميرة العنود — بتول الرويلي كمحكم

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000034 | CANON-002872 |
| Raw ID | BATOOL-A2-05 | LEG-REV-01129 |
| الجهة | مؤسسة الاميرة العنود | مؤسسة الاميرة العنود |
| النموذج | نموذج التقرير العام عن المنظمة | نموذج التقرير العام عن المنظمة |
| المحكم | بتول الرويلي | بتول الرويلي |
| المستشار | نجود السيد | نجود السيد |
| التاريخ | 2026-01-18 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 1.0 | 15 |
| URL | https://docs.google.com/document/d/1OhQjEsnlqvgtZRtnL-URPyNr75Xnce1P/edit | — |
| **Match status** | VERSION_LINKED | VERSION_LINKED |
| Match reason | resubmission_after_needs_improvement | resubmission_after_needs_improvement |
| Confidence | 90 | 90 |
| **التصنيف النهائي** | Version (not duplicate) | Version (not duplicate) |

### عيّنة 11 — إعادة إرسال — Version pair (جهة أخرى)

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000035 | CANON-002878 |
| Raw ID | BATOOL-A2-06 | LEG-REV-01135 |
| الجهة | مؤسسة الاميرة العنود | مؤسسة الاميرة العنود |
| النموذج | نموذج تقرير متابعة التشغيل وإغلاق التأسيس | نموذج تقرير متابعة التشغيل وإغلاق التأسيس |
| المحكم | بتول الرويلي | بتول الرويلي |
| المستشار | نجود السيد | نجود السيد |
| التاريخ | 2026-01-18 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 0.5 | 15 |
| URL | https://docs.google.com/document/d/1eCrE4o6mhp9-TSQ1k2VoRysjEqI0k38C/edit?usp=sh | — |
| **Match status** | VERSION_LINKED | VERSION_LINKED |
| Match reason | resubmission_after_needs_improvement | resubmission_after_needs_improvement |
| Confidence | 90 | 90 |
| **التصنيف النهائي** | Version (not duplicate) | Version (not duplicate) |

### عيّنة 12 — إعادة إرسال — Version pair (جهة أخرى)

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000036 | CANON-002877 |
| Raw ID | BATOOL-A2-07 | LEG-REV-01134 |
| الجهة | مؤسسة الاميرة العنود | مؤسسة الاميرة العنود |
| النموذج | نموذج خطة سد الفجوات | نموذج خطة سد الفجوات |
| المحكم | بتول الرويلي | بتول الرويلي |
| المستشار | نجود السيد | نجود السيد |
| التاريخ | 2026-01-18 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 0.5 | 15 |
| URL | https://docs.google.com/spreadsheets/d/1oKwy8KnGGwfj0djUSgFlwc4EjEL3M9SO/edit?us | — |
| **Match status** | VERSION_LINKED | VERSION_LINKED |
| Match reason | resubmission_after_needs_improvement | resubmission_after_needs_improvement |
| Confidence | 90 | 90 |
| **التصنيف النهائي** | Version (not duplicate) | Version (not duplicate) |

### عيّنة 13 — إعادة إرسال — Version pair (جهة أخرى)

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000037 | CANON-002897 |
| Raw ID | BATOOL-A2-08 | LEG-REV-01154 |
| الجهة | مؤسسة الاميرة العنود | مؤسسة الاميرة العنود |
| النموذج | أداة إدارة الفرص التطوعية | أداة إدارة الفرص التطوعية |
| المحكم | بتول الرويلي | بتول الرويلي |
| المستشار | نجود السيد | نجود السيد |
| التاريخ | 2026-01-18 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | غير مجاز |
| Hours | 1.0 | 15 |
| URL | https://docs.google.com/spreadsheets/d/1uV1qQmsl5QWOcPEC9YFXwTxX9_yW9l92/edit?us | — |
| **Match status** | VERSION_LINKED | VERSION_LINKED |
| Match reason | resubmission_after_needs_improvement | resubmission_after_needs_improvement |
| Confidence | 90 | 90 |
| **التصنيف النهائي** | Version (not duplicate) | Version (not duplicate) |

### عيّنة 14 — REVIEW — اختلاف المحكم بين المصدرين

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000473 | CANON-001936 |
| Raw ID | HASAN-A1-01 | LEG-REV-00193 |
| الجهة | جمعية أفق لتطوير العمل الخيري والتطوعي | جمعية أفق لتطوير العمل الخيري والتطوعي |
| النموذج | أداة تقييم الجاهزية | أداة تقييم الجاهزية |
| المحكم | د. حسن ابو كافته | أحمد خواجي |
| المستشار | ظافر القرني | ظافر القرني |
| التاريخ | 2026-01-28 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 0.5 | 15 |
| URL | https://docs.google.com/spreadsheets/d/1RER2N11apWboLnK82VktCff5ommQXDwt/edit?us | — |
| **Match status** | REVIEW_REQUIRED | REVIEW_REQUIRED |
| Match reason | evaluator_mismatch_cross_source | evaluator_mismatch_cross_source |
| Confidence | 25 | 25 |
| **التصنيف النهائي** | Review required | Review required |

### عيّنة 15 — REVIEW — اختلاف المحكم بين المصدرين

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000474 | CANON-001933 |
| Raw ID | HASAN-A1-02 | LEG-REV-00190 |
| الجهة | جمعية أفق لتطوير العمل الخيري والتطوعي | جمعية أفق لتطوير العمل الخيري والتطوعي |
| النموذج | التقييم الذاتي للجهة | التقييم الذاتي للجهة |
| المحكم | د. حسن ابو كافته | أحمد خواجي |
| المستشار | ظافر القرني | ظافر القرني |
| التاريخ | 2026-01-28 | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | مقبول | مجاز |
| Hours | 0.5 | 15 |
| URL | https://cnp.kfupm.edu.sa/edama/edamasurvey9/submitted.php?submissionID=99688f16d | — |
| **Match status** | REVIEW_REQUIRED | REVIEW_REQUIRED |
| Match reason | evaluator_mismatch_cross_source | evaluator_mismatch_cross_source |
| Confidence | 25 | 25 |
| **التصنيف النهائي** | Review required | Review required |

### عيّنة 16 — REVIEW — لا يوجد نموذج مطابق (تطابق الجهة فقط)

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000010 | — |
| Raw ID | BATOOL-A1-10 | — |
| الجهة | جمعية المشي والجري | جمعية المشي والجري |
| النموذج | الدليل الإرشادي لإنشاء وإدارة الفرق التطوعية | الدليل الإرشادي لإنشاء وإدارة الفرق التطوعية |
| المحكم | بتول الرويلي | — |
| المستشار | نجود السيد | — |
| التاريخ | 2026-01-18 | — |
| Resource ID | — | — |
| Decision/Status | مقبول | — |
| Hours | 1.0 | — |
| URL | https://drive.google.com/file/d/1pqYEruag2RVAx2rfUz_ZO41nVUkIdrzZ/view?usp=drive | — |
| **Match status** | REVIEW_REQUIRED | REVIEW_REQUIRED |
| Match reason | no_direct_model_match_only_org | no_direct_model_match_only_org |
| Confidence | 40 | 40 |
| **التصنيف النهائي** | Review required | Review required |

### عيّنة 17 — CURRENT_ONLY — لا يوجد سجل تاريخي مطابق

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000326 | — |
| Raw ID | SARA-A1-01 | — |
| الجهة | جمعية البر لقرى جنوب مكة | جمعية البر لقرى جنوب مكة |
| النموذج | أداة تقييم الجاهزية | أداة تقييم الجاهزية |
| المحكم | سارة بالخير | — |
| المستشار | عزيز التوخي | — |
| التاريخ | 2026-01-22 | — |
| Resource ID | — | — |
| Decision/Status | مقبول | — |
| Hours | 0.5 | — |
| URL | https://docs.google.com/spreadsheets/d/1xqcaYynXhv-FxQNSQWHYBnLbq8hzgQq4/edit?gi | — |
| **Match status** | CURRENT_ONLY | CURRENT_ONLY |
| Match reason | no_legacy_arbitration_record | no_legacy_arbitration_record |
| Confidence | 100 | 100 |
| **التصنيف النهائي** | Separate (current only) | Separate (current only) |

### عيّنة 18 — CURRENT_ONLY — لا يوجد سجل تاريخي مطابق

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | CANON-000327 | — |
| Raw ID | SARA-A1-02 | — |
| الجهة | جمعية البر لقرى جنوب مكة | جمعية البر لقرى جنوب مكة |
| النموذج | التقييم الذاتي للجهة | التقييم الذاتي للجهة |
| المحكم | سارة بالخير | — |
| المستشار | عزيز التوخي | — |
| التاريخ | 2026-01-22 | — |
| Resource ID | — | — |
| Decision/Status | مقبول | — |
| Hours | 0.5 | — |
| URL | https://drive.google.com/drive/folders/1W5dx_bldtBsDPIoVhoMIqtV4aqqRagK8 | — |
| **Match status** | CURRENT_ONLY | CURRENT_ONLY |
| Match reason | no_legacy_arbitration_record | no_legacy_arbitration_record |
| Confidence | 100 | 100 |
| **التصنيف النهائي** | Separate (current only) | Separate (current only) |

### عيّنة 19 — LEGACY_ONLY — لا يوجد سجل حالي مطابق

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | — | CANON-001744 |
| Raw ID | — | LEG-REV-00001 |
| الجهة | جمعية نبتون للتاهيل الطبي | جمعية نبتون للتاهيل الطبي |
| النموذج | نموذج التقرير العام عن المنظمة | نموذج التقرير العام عن المنظمة |
| المحكم | — | أحمد خواجي |
| المستشار | — | ظافر القرني |
| التاريخ | — | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | — | مجاز |
| Hours | — | 15 |
| URL | — | — |
| **Match status** | LEGACY_ONLY | LEGACY_ONLY |
| Match reason | no_current_lovable_peer | no_current_lovable_peer |
| Confidence | 100 | 100 |
| **التصنيف النهائي** | Separate (legacy only) | Separate (legacy only) |

### عيّنة 20 — LEGACY_ONLY — لا يوجد سجل حالي مطابق

| الحقل | current | legacy |
| --- | --- | --- |
| Canonical ID | — | CANON-001745 |
| Raw ID | — | LEG-REV-00002 |
| الجهة | جمعية نبتون للتاهيل الطبي | جمعية نبتون للتاهيل الطبي |
| النموذج | التقييم الذاتي للجهة | التقييم الذاتي للجهة |
| المحكم | — | أحمد خواجي |
| المستشار | — | ظافر القرني |
| التاريخ | — | 2025-08-16 |
| Resource ID | — | — |
| Decision/Status | — | مجاز |
| Hours | — | 15 |
| URL | — | — |
| **Match status** | LEGACY_ONLY | LEGACY_ONLY |
| Match reason | no_current_lovable_peer | no_current_lovable_peer |
| Confidence | 100 | 100 |
| **التصنيف النهائي** | Separate (legacy only) | Separate (legacy only) |