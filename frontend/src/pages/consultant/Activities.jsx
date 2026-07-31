import React, { useEffect, useState } from "react";
import api from "@/lib/api";

export default function ConsultantActivities() {
  const [items, setItems] = useState([]);
  useEffect(() => {
    api.get("/consultant/activities").then((r) => setItems(r.data));
  }, []);
  return (
    <div data-testid="consultant-activities-page">
      <h1 className="text-3xl font-semibold mb-2">الأنشطة التاريخية</h1>
      <p className="text-navy/70 mb-6">
        الأنشطة من ملفات الأرشيف التاريخي المرتبطة باسمك ({items.length} نشاط). للقراءة فقط.
      </p>
      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="activities-table">
          <thead>
            <tr><th>الدفعة</th><th>الجهة</th><th>المرحلة</th><th>النشاط</th><th>النسبة</th><th>الحالة</th></tr>
          </thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.legacy_activity_id}>
                <td className="num">{a.cohort}</td>
                <td className="text-sm">{a.organization_name}</td>
                <td className="text-sm text-navy/70">{a.stage}</td>
                <td className="text-sm">{a.activity}</td>
                <td className="num">{a.completion_ratio}</td>
                <td className="text-sm">{a.completion_status}</td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={6} className="text-center text-navy/50 py-6">لا توجد أنشطة مرتبطة</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
