import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "@/lib/api";

export default function OrganizationJourney() {
  const { orgId } = useParams();
  const [data, setData] = useState(null);
  useEffect(() => { api.get(`/admin/organizations/${orgId}/journey`).then((r) => setData(r.data)); }, [orgId]);

  if (!data) return <div className="text-navy/60">…جارٍ التحميل</div>;

  const { current, crosswalk, legacy, records, record_count, legacy_activities_count, legacy_arbitrations_count, assignment } = data;

  // Group records by category → model
  const byCategory = records.reduce((acc, r) => {
    (acc[r.category] = acc[r.category] || []).push(r);
    return acc;
  }, {});

  return (
    <div data-testid="org-journey-page">
      <div className="text-sm mb-2">
        <Link to="/admin/organizations" className="text-turquoise-600 hover:underline">← الجهات</Link>
      </div>
      <h1 className="text-3xl font-semibold mb-1">{current.organization_name}</h1>
      <div className="text-xs num text-navy/50 mb-6">{current.organization_id}</div>

      {/* Journey: Cohort → Org → Consultant → Model → Arbitration → Impact */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-8" data-testid="journey-strip">
        <Step label="الدفعة" value={legacy?.cohort || "—"} />
        <Step label="الجهة" value={record_count > 0 ? "حاضرة" : "—"} />
        <Step label="المستشار" value={JSON.parse(current.consultant_names || '["—"]').join("، ")} />
        <Step label="النماذج" value={record_count} num />
        <Step label="التحكيمات التاريخية" value={legacy_arbitrations_count} num />
        <Step label="الساعات" value={current.work_hours} num />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="border border-navy/15 bg-white p-5" data-testid="current-panel">
          <h2 className="text-lg font-semibold mb-3">الحالي (Lovable)</h2>
          <dl className="text-sm space-y-2">
            <Row k="المحكّم" v={current.evaluator_name} />
            <Row k="السجلات" v={current.record_count} num />
            <Row k="ساعات العمل" v={current.work_hours} num />
            <Row k="الملاحظات" v={current.notes_count} num />
            <Row k="مجموعات روابط مكررة" v={current.duplicate_link_groups} num />
            <Row k="أول إرسال" v={current.first_submitted_at_iso?.slice(0, 10)} />
            <Row k="آخر تعديل" v={current.last_modified_at_iso?.slice(0, 10)} />
          </dl>
        </div>

        <div className="border border-navy/15 bg-white p-5" data-testid="legacy-panel">
          <h2 className="text-lg font-semibold mb-3">التاريخي</h2>
          {legacy ? (
            <dl className="text-sm space-y-2">
              <Row k="معرف تاريخي" v={legacy.legacy_org_id} mono />
              <Row k="الدفعة" v={legacy.cohort} num />
              <Row k="المستشار" v={legacy.consultants} />
              <Row k="المحكّم" v={legacy.evaluators} />
              <Row k="القطاع" v={legacy.sector} />
              <Row k="الأنشطة التاريخية" v={legacy_activities_count} num />
              <Row k="التحكيمات التاريخية" v={legacy_arbitrations_count} num />
            </dl>
          ) : (
            <div className="text-sm text-navy/60">لا يوجد نظير تاريخي مؤكد. Crosswalk: <span className="num">{crosswalk?.match_status || "—"}</span></div>
          )}
          {crosswalk?.match_status === "PROBABLE_NAME_VARIANT" && (
            <div className="mt-4 border-r-4 border-orange bg-orange-50 px-3 py-2 text-sm">
              مطابقة مرجّحة — تحتاج اعتماد بشري (درجة: <span className="num">{crosswalk.match_score}</span>)
            </div>
          )}
        </div>
      </div>

      {assignment && assignment.evaluator_assignment_status === "CHANGED" && (
        <div className="border-r-4 border-orange bg-white p-4 mb-8" data-testid="assign-changed">
          <div className="text-sm">تكليف المحكّم تغيّر عن الدفعة التاريخية:</div>
          <div className="num text-sm mt-1">
            <span className="text-navy/60">تاريخي:</span> {assignment.legacy_evaluator} → <span className="text-navy/60">حالي:</span> {assignment.current_evaluator}
          </div>
        </div>
      )}

      <h2 className="text-xl font-semibold mb-3">النماذج (حالي)</h2>
      {Object.entries(byCategory).map(([cat, rows]) => (
        <div key={cat} className="border border-navy/15 bg-white mb-4 overflow-x-auto">
          <div className="px-4 py-3 border-b border-navy/10 font-medium">{cat} — <span className="num">{rows.length}</span></div>
          <table className="tech-table">
            <thead>
              <tr><th>النموذج</th><th>الحالة</th><th>التقييم</th><th>الساعات</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.migration_id}>
                  <td className="text-sm">{r.model_name}</td>
                  <td className="text-sm">{r.status}</td>
                  <td className="text-sm">{r.evaluation}</td>
                  <td className="num">{r.work_hours}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  );
}

function Step({ label, value, num }) {
  return (
    <div className="border border-navy/15 bg-white p-3">
      <div className="stat-label text-[10px]">{label}</div>
      <div className={num ? "num text-lg" : "text-sm"}>{value ?? "—"}</div>
    </div>
  );
}

function Row({ k, v, num, mono }) {
  return (
    <div className="flex justify-between border-b border-navy/10 py-1.5">
      <dt className="text-navy/60">{k}</dt>
      <dd className={num || mono ? "num text-navy" : "text-navy"}>{v ?? "—"}</dd>
    </div>
  );
}
