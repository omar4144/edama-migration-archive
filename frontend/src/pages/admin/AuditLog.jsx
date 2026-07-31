import React, { useEffect, useState } from "react";
import api from "@/lib/api";

export default function AuditLog() {
  const [items, setItems] = useState([]);
  useEffect(() => {
    api.get("/reconciliation/audit-log?limit=200").then((r) => setItems(r.data));
  }, []);
  return (
    <div data-testid="audit-page">
      <h1 className="text-3xl font-semibold mb-2">سجل التدقيق</h1>
      <p className="text-navy/70 mb-6">جميع القرارات والتعديلات مسجّلة بترتيب زمني.</p>
      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="audit-table">
          <thead>
            <tr><th>الوقت</th><th>المستخدم</th><th>الإجراء</th><th>الكيان</th><th>ملاحظات</th></tr>
          </thead>
          <tbody>
            {items.map((r, i) => (
              <tr key={i}>
                <td className="text-xs num text-navy/60">{r.created_at?.slice(0, 19)}</td>
                <td className="text-sm">{r.user_email}</td>
                <td className="text-sm">{r.action}</td>
                <td className="text-xs num text-navy/60">{r.entity_key || r.entity || "—"}</td>
                <td className="text-xs text-navy/70">{r.after?.note || ""}</td>
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={5} className="text-center text-navy/50 py-6">لا يوجد سجل بعد</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
