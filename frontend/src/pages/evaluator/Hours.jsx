import React, { useEffect, useState } from "react";
import api from "@/lib/api";

export default function EvaluatorHours() {
  const [data, setData] = useState(null);
  useEffect(() => { api.get("/evaluator/hours-summary").then((r) => setData(r.data)); }, []);
  if (!data) return <div className="text-navy/60">…جارٍ التحميل</div>;
  return (
    <div data-testid="evaluator-hours-page">
      <h1 className="text-3xl font-semibold mb-2">ساعات العمل</h1>
      <p className="text-navy/70 mb-6">ملخص إجمالي وموزّع على الجهات المسندة إليك.</p>

      <div className="border border-navy/15 bg-white p-5 mb-6 inline-block">
        <div className="stat-label">الإجمالي</div>
        <div className="stat-value" data-testid="total-hours">{Number(data.total_hours).toLocaleString("en-US", { maximumFractionDigits: 1 })}</div>
      </div>

      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="hours-table">
          <thead>
            <tr><th>الجهة</th><th>السجلات</th><th>الساعات</th></tr>
          </thead>
          <tbody>
            {data.by_organization.map((r) => (
              <tr key={r._id}>
                <td className="text-xs num text-navy/60">{r._id}</td>
                <td className="num">{r.records}</td>
                <td className="num">{Number(r.hours).toLocaleString("en-US", { maximumFractionDigits: 1 })}</td>
              </tr>
            ))}
            {data.by_organization.length === 0 && <tr><td colSpan={3} className="text-center text-navy/50 py-6">لا توجد بيانات</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
