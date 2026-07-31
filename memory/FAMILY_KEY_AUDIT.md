# Family-Key Audit

_شرط اعتماد V4 من الملكية: التحقق أن مفتاح الرحلة الحالي `organization × model_definition` لا يدمج رحلتين مختلفتين (تعدد دفعات، مشاركات برنامج، فترات منفصلة)._


## 1) توفر إشارة الـ Enrollment في البيانات

- **Current records** (Lovable): لا يوجد أي حقل مصرّح يمثّل `program_enrollment_id` أو `cohort_participation_id`. الحقول المتوفرة هي: `['migration_id', 'record_hash_sha256', 'source_system', 'source_account_index', 'source_account', 'source_file', 'source_sheet', 'source_row_number', 'organization_id', 'organization_name', 'evaluator_person_id', 'consultant_person_id', 'consultant_name', 'model_definition_id', 'category', 'source_order', 'model_name', 'model_url', 'url_domain', 'status', 'evaluation', 'work_hours', 'notes', 'submitted_at_raw', 'submitted_at_iso', 'modified_at_raw', 'modified_at_iso', 'verification_status', 'field_check', 'url_check', 'status_check', 'hours_check', 'reread_check', 'verified_at_raw', 'verified_at_iso', 'duplicate_link_group_id', 'duplicate_link_use_count', 'duplicate_within_account', 'duplicate_cross_account']`. جميع الصفوف تاريخها 2026-01-\* بلا تمييز دفعة.
- **Legacy arbitrations**: يوجد حقل `cohort` نصي (قيم: 1، 2، 3، 4) يمثل الدفعة التاريخية. لا يوجد `program_enrollment_id` صريح.
- **الخلاصة:** لا يوجد `enrollment_id` صريح في البيانات؛ إشارة الدفعة الوحيدة موجودة في `historical_arbitrations.cohort`. لا يوجد ما يماثلها في Lovable لأن كل بيانات Lovable تمثل استلامًا واحدًا موحّدًا في يناير 2026.


## 2) اختبار تعدد الدفعات على نفس (org × model)

- عدد الجهات التاريخية التي تظهر في أكثر من دفعة: **0** من أصل 73

- عدد أزواج (org × نفس model) التي تظهر في أكثر من دفعة تاريخية: **0**


## 3) اختبار الرحلات المتضمنة أكثر من دفعة

- **families_with_multi_cohort:** 0

- ✅ لا توجد أي رحلة تحوي أكثر من دفعة. المفتاح الحالي آمن.


## 4) اختبار الفواصل الزمنية المنفصلة (>12 شهرًا داخل نفس الرحلة)

- **families_with_disconnected_dates:** 0

- توزيع الفوارق: {'gap_>_6_months': 204}

- ملاحظة: كل الأزواج المتقاطعة تُظهر فارقًا يقارب 5 أشهر (Aug 2025 → Jan 2026). لا يوجد نمط رحلتين مستقلتين.


## 5) اختبار تعدد المحكم/المستشار داخل الرحلة

- **multi_evaluator:** 124 رحلة

- **multi_consultant:** 0 رحلة

- هذه الحالات مصنّفة بالفعل REVIEW_REQUIRED (`evaluator_mismatch_cross_source`) ولا تُدمج تلقائيًا. لا تدل على مفتاح خاطئ بل على تباين حقيقي بين المصدرين.


## 6) القرار المتخذ

**✅ اجتاز الفحص.** لا يوجد داخل البيانات الحالية أي حالة تعدد دفعات على نفس (org × model). المفتاح الحالي `organization_id × model_definition_id` صحيح.

**التحضير للمستقبل:** المخطط جاهز لإضافة `program_enrollment_id` كمفتاح مركّب متى ما توفّر في المصدر (Live Lovable Sync). سيتم ذلك بإضافة حقل واحد إلى `canonical_submission_families.enrollment_id` ومفتاح مركّب `(organization_id, model_definition_id, enrollment_id)` دون تغيير الأرقام الحالية.

**النتيجة:** الأرقام 3,521 / 5,038 / 3,521 معتمدة. الانتقال إلى UI Cutover.
