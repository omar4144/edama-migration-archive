import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "@/lib/api";

export default function CohortDetail() {
  const { cohort } = useParams();
  const [data, setData] = useState(null);
  useEffect(() => { api.get(`/admin/cohorts/${cohort}`).then((r) => setData(r.data)); }, [cohort]);

  if (!data) return <div className="text-navy/60">…جارٍ التحميل</div>;

  return (
    <div data-testid="cohort-detail-page">
      <div className="text-sm mb-2">
        <Link to="/admin/cohorts" className="text-turquoise-600 hover:underline">← خريطة الدفعات</Link>
      </div>
      <h1 className="text-3xl font-semibold mb-2">عالم الدفعة <span className="num">{cohort}</span></h1>
      <p className="text-navy/70 mb-6">جميع الجهات المشاركة، بأنشطتها التاريخية وسجلات تحكيمها. كل جهة قابلة للفتح كرحلة كاملة.</p>

      {data.kpi_snapshot && (
        <div className="border border-navy/15 bg-white p-4 mb-6" data-testid="kpi-snapshot">
          <div className="stat-label mb-2">لقطة مؤشرات هذه الدفعة</div>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4 text-right">
            <KpiCell label="فرص تطوعية" v={data.kpi_snapshot["فرص تطوعية معلنة"]} />
            <KpiCell label="متطوعين" v={data.kpi_snapshot["عدد متطوعين مستقطبين"]} />
            <KpiCell label="ساعات تطوعية" v={data.kpi_snapshot["عدد الساعات التطوعية"]} />
            <KpiCell label="أنشطة" v={data.kpi_snapshot["عدد الانشطة"]} />
            <KpiCell label="منجزة" v={data.kpi_snapshot["اجمالي الانشطة المنجزة"]} />
            <KpiCell label="جهات" v={data.kpi_snapshot["عدد الجهات المشاركة"]} />
          </div>
        </div>
      )}

      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="cohort-orgs-table">
          <thead>
            <tr><th>الجهة</th><th>المستشار</th><th>المحكّم</th><th>أنشطة</th><th>تحكيمات</th><th></th></tr>
          </thead>
          <tbody>
            {data.organizations.map((o) => (
              <tr key={o.legacy_org_id}>
                <td className="text-sm">{o.organization_name}</td>
                <td className="text-sm">{o.consultants || "—"}</td>
                <td className="text-sm">{o.evaluators || "—"}</td>
                <td className="num">{o.activity_count}</td>
                <td className="num">{o.arbitration_count}</td>
                <td className="text-left">
                  <span className="text-xs num text-navy/50">{o.legacy_org_id}</span>
                </td>
              </tr>
            ))}
            {data.organizations.length === 0 && (
              <tr><td colSpan={6} className="text-center text-navy/50 py-6">لا توجد جهات</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function KpiCell({ label, v }) {
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className="num text-lg">{v == null || v === "" ? "—" : v}</div>
    </div>
  );
}
