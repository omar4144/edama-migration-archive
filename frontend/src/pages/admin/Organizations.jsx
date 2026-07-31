import React, { useEffect, useState } from "react";
import api from "@/lib/api";

export default function Organizations() {
  const [scope, setScope] = useState("current");
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");

  useEffect(() => {
    const path = scope === "current"
      ? `/admin/organizations${q ? `?q=${encodeURIComponent(q)}` : ""}`
      : `/admin/organizations/historical`;
    api.get(path).then((r) => setItems(r.data));
  }, [scope, q]);

  return (
    <div data-testid="orgs-page">
      <h1 className="text-3xl font-semibold mb-2">الجهات</h1>
      <p className="text-navy/70 mb-6">
        عرض منفصل للطبقتين. البيانات التاريخية للقراءة فقط ولا تُدمج مع الحالية.
      </p>

      <div className="flex gap-3 mb-4">
        <div className="flex border border-navy/25" role="tablist">
          <button
            className={`px-4 py-2 text-sm ${scope === "current" ? "bg-navy text-ivory" : "bg-white text-navy"}`}
            onClick={() => setScope("current")}
            data-testid="tab-current"
          >
            حالي (Lovable)
          </button>
          <button
            className={`px-4 py-2 text-sm ${scope === "legacy" ? "bg-navy text-ivory" : "bg-white text-navy"}`}
            onClick={() => setScope("legacy")}
            data-testid="tab-legacy"
          >
            تاريخي
          </button>
        </div>
        {scope === "current" && (
          <input className="field-input w-64" placeholder="بحث بالاسم…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="orgs-search" />
        )}
      </div>

      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="orgs-table">
          <thead>
            <tr>
              <th>المعرف</th>
              <th>الاسم</th>
              {scope === "current" ? (
                <>
                  <th>المحكّم</th>
                  <th>المستشار</th>
                  <th>السجلات</th>
                  <th>الساعات</th>
                  <th></th>
                </>
              ) : (
                <>
                  <th>الدفعة</th>
                  <th>المستشار</th>
                  <th>المحكّم</th>
                  <th></th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {items.map((o) => (
              <tr key={o.organization_id || o.legacy_org_id}>
                <td className="num text-xs text-navy/60">{o.organization_id || o.legacy_org_id}</td>
                <td>{o.organization_name}</td>
                {scope === "current" ? (
                  <>
                    <td className="text-sm">{o.evaluator_name}</td>
                    <td className="text-sm">{Array.isArray(o.consultant_names) ? o.consultant_names.join("، ") : (o.consultant_names || "").replaceAll('"', "").replaceAll("[", "").replaceAll("]", "")}</td>
                    <td className="num">{o.record_count}</td>
                    <td className="num">{o.work_hours}</td>
                    <td className="text-left">
                      <a href={`/admin/organizations/${o.organization_id}/journey`} className="btn-outline text-sm" data-testid={`journey-${o.organization_id}`}>رحلة</a>
                    </td>
                  </>
                ) : (
                  <>
                    <td className="num">{o.cohort}</td>
                    <td className="text-sm">{o.consultants}</td>
                    <td className="text-sm">{o.evaluators}</td>
                    <td></td>
                  </>
                )}
              </tr>
            ))}
            {items.length === 0 && (
              <tr><td colSpan={6} className="text-center text-navy/50 py-6">لا توجد بيانات</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
