import React, { useEffect, useState } from "react";
import api from "@/lib/api";

export default function Records() {
  const [data, setData] = useState({ items: [], total: 0 });
  const [status, setStatus] = useState("");
  const [orgs, setOrgs] = useState([]);
  const [orgId, setOrgId] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = 25;

  useEffect(() => {
    api.get("/admin/organizations").then((r) => setOrgs(r.data));
  }, []);

  useEffect(() => {
    const p = new URLSearchParams({ limit, offset });
    if (status) p.append("status", status);
    if (orgId) p.append("org_id", orgId);
    api.get(`/admin/records?${p}`).then((r) => setData(r.data));
  }, [status, orgId, offset]);

  return (
    <div data-testid="records-page">
      <h1 className="text-3xl font-semibold mb-2">السجلات الحالية</h1>
      <p className="text-navy/70 mb-6">
        السجلات المعتمدة من Lovable ({data.total.toLocaleString("en-US")} سجلاً إجمالاً). البحث والتصفية عبر API فقط.
      </p>

      <div className="flex gap-3 mb-4 flex-wrap">
        <select className="field-input w-auto" value={orgId} onChange={(e) => { setOrgId(e.target.value); setOffset(0); }} data-testid="filter-org">
          <option value="">كل الجهات</option>
          {orgs.map((o) => (
            <option key={o.organization_id} value={o.organization_id}>{o.organization_name}</option>
          ))}
        </select>
        <select className="field-input w-auto" value={status} onChange={(e) => { setStatus(e.target.value); setOffset(0); }} data-testid="filter-status">
          <option value="">كل الحالات</option>
          <option value="مقبول">مقبول</option>
          <option value="يحتاج لتطوير">يحتاج لتطوير</option>
          <option value="غير مكتمل">غير مكتمل</option>
        </select>
      </div>

      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="records-table">
          <thead>
            <tr>
              <th>معرف الترحيل</th>
              <th>الجهة</th>
              <th>النموذج</th>
              <th>المحكّم</th>
              <th>الحالة</th>
              <th>الساعات</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((r) => (
              <tr key={r.migration_id}>
                <td className="text-xs num text-navy/60">{r.migration_id}</td>
                <td className="text-sm">{r.organization_name}</td>
                <td className="text-sm">{r.model_name}</td>
                <td className="text-sm">{r.source_account}</td>
                <td className="text-sm">{r.status}</td>
                <td className="num">{r.work_hours}</td>
              </tr>
            ))}
            {data.items.length === 0 && (
              <tr><td colSpan={6} className="text-center text-navy/50 py-6">لا توجد نتائج</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-4 text-sm">
        <div className="text-navy/60 num">
          {offset + 1}–{Math.min(offset + limit, data.total)} من {data.total.toLocaleString("en-US")}
        </div>
        <div className="flex gap-2">
          <button className="btn-outline text-sm disabled:opacity-40" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))} data-testid="prev-page">السابق</button>
          <button className="btn-outline text-sm disabled:opacity-40" disabled={offset + limit >= data.total} onClick={() => setOffset(offset + limit)} data-testid="next-page">التالي</button>
        </div>
      </div>
    </div>
  );
}
