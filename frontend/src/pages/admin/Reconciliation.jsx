import React, { useEffect, useState } from "react";
import api from "@/lib/api";

const LABELS = {
  records_current: "السجلات الحالية (Lovable)",
  organizations_current: "الجهات الحالية",
  people: "الأشخاص",
  model_definitions: "تعريفات النماذج",
  duplicate_links_current: "مجموعات روابط مكررة (حالية)",
  historical_organizations: "الجهات التاريخية",
  historical_activities: "أنشطة المستشارين (تاريخي)",
  historical_arbitrations: "سجلات التحكيم (تاريخي)",
  historical_duplicate_links: "روابط مكررة (تاريخي)",
  historical_batch_plans: "صفوف خطط الدفعات",
  historical_batch_kpis: "لقطات مؤشرات الدفعات",
  crosswalk_organizations: "مطابقة الجهات",
  crosswalk_models: "مطابقة النماذج",
  crosswalk_records: "مطابقة السجلات",
  assignments: "مقارنة التكليفات",
  work_hours_total: "إجمالي ساعات العمل",
  mappings_pending: "مطابقات معلّقة",
  mappings_approved: "مطابقات معتمدة",
  mappings_rejected: "مطابقات مرفوضة",
};

const EXPECTED_MAP = {
  records_current: "current_lovable_records",
  organizations_current: "current_lovable_organizations",
  people: "people",
  model_definitions: "model_definitions",
  historical_organizations: "legacy_organizations_total",
  historical_activities: "legacy_consultant_activities_total",
  historical_arbitrations: "legacy_arbitration_records_total",
  historical_duplicate_links: "legacy_duplicate_link_groups",
  historical_batch_plans: "batch_plan_rows",
  historical_batch_kpis: "batch_kpi_snapshots",
  work_hours_total: "work_hours_total",
};

function Stat({ label, actual, expected }) {
  const target = expected ?? null;
  const ok = target == null || Number(actual) === Number(target);
  return (
    <div className="border border-navy/15 p-5 bg-white">
      <div className="stat-label">{label}</div>
      <div className="mt-2 flex items-baseline gap-2">
        <div className="stat-value">{Number(actual ?? 0).toLocaleString("en-US")}</div>
        {target != null && (
          <div className={`text-xs num ${ok ? "text-edGreen" : "text-orange"}`}>
            /{Number(target).toLocaleString("en-US")} {ok ? "✓" : "≠"}
          </div>
        )}
      </div>
    </div>
  );
}

export default function Reconciliation() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    api.get("/reconciliation/summary")
      .then((r) => setData(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || e.message));
  }, []);

  if (err) return <div className="text-orange" data-testid="recon-error">{String(err)}</div>;
  if (!data) return <div className="text-navy/60">…جارٍ التحميل</div>;

  const { counts, expected, cohorts, crosswalks, latest_run } = data;
  const orderedKeys = [
    "records_current", "organizations_current", "people", "model_definitions", "work_hours_total",
    "historical_organizations", "historical_activities", "historical_arbitrations",
    "historical_duplicate_links", "historical_batch_plans", "historical_batch_kpis",
  ];

  return (
    <div data-testid="reconciliation-page">
      <div className="flex items-baseline justify-between mb-2">
        <h1 className="text-3xl font-semibold">لوحة المصالحة</h1>
        {latest_run && (
          <div className="text-xs text-navy/60 num" data-testid="last-run-status">
            آخر تشغيل: {latest_run.status} — {latest_run.generated_at?.slice(0, 19)}
          </div>
        )}
      </div>
      <p className="text-navy/70 mb-8 max-w-2xl leading-relaxed">
        مقارنة مباشرة بين الأعداد الفعلية في قاعدة البيانات والأعداد المرجعية من عقد التنفيذ V8. البيانات الخام محفوظة كما هي، ولا يوجد أي دمج تلقائي.
      </p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10" data-testid="stats-grid">
        {orderedKeys.map((k) => (
          <Stat key={k} label={LABELS[k]} actual={counts[k]} expected={expected[EXPECTED_MAP[k]]} />
        ))}
      </div>

      <h2 className="text-xl font-semibold mb-3">تغطية الدفعات (التاريخية)</h2>
      <div className="border border-navy/15 bg-white mb-10 overflow-x-auto">
        <table className="tech-table" data-testid="cohort-table">
          <thead>
            <tr>
              <th>الدفعة</th><th>الجهات</th><th>أنشطة المستشارين</th><th>سجلات التحكيم</th>
            </tr>
          </thead>
          <tbody>
            {[1, 2, 3, 4].map((c) => {
              const o = cohorts.organizations.find((x) => String(x._id) === String(c))?.count ?? 0;
              const a = cohorts.activities.find((x) => String(x._id) === String(c))?.count ?? 0;
              const r = cohorts.arbitrations.find((x) => String(x._id) === String(c))?.count ?? 0;
              return (
                <tr key={c}>
                  <td className="num">{c}</td>
                  <td className="num">{o.toLocaleString("en-US")}</td>
                  <td className="num">{a.toLocaleString("en-US")}</td>
                  <td className="num">{r.toLocaleString("en-US")}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <h2 className="text-xl font-semibold mb-3">حالة المطابقات (Crosswalks)</h2>
      <div className="grid md:grid-cols-2 gap-6 mb-10">
        <CrossBlock title="الجهات" rows={crosswalks.organizations} testid="cw-orgs" />
        <CrossBlock title="النماذج" rows={crosswalks.models} testid="cw-models" />
        <CrossBlock title="السجلات" rows={crosswalks.records} testid="cw-records" />
        <CrossBlock title="تكليف المحكّمين" rows={crosswalks.evaluator_assignments} testid="cw-assign" />
      </div>

      <div className="border-r-4 border-turquoise bg-white p-4" data-testid="review-summary">
        <div className="text-sm text-navy/70">قائمة المراجعة (REVIEW_REQUIRED)</div>
        <div className="mt-1 flex items-baseline gap-4">
          <span className="stat-value">{counts.mappings_pending}</span>
          <span className="text-sm text-navy/60">
            معلّقة · {counts.mappings_approved} معتمدة · {counts.mappings_rejected} مرفوضة
          </span>
        </div>
      </div>
    </div>
  );
}

function CrossBlock({ title, rows, testid }) {
  return (
    <div className="border border-navy/15 bg-white" data-testid={testid}>
      <div className="px-4 py-3 border-b border-navy/10 font-medium">{title}</div>
      <table className="tech-table">
        <tbody>
          {rows.map((r) => (
            <tr key={String(r._id)}>
              <td className="text-navy/80 text-sm">{String(r._id ?? "—")}</td>
              <td className="num text-left w-20">{Number(r.count).toLocaleString("en-US")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
