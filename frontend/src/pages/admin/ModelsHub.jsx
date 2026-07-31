import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import { num } from "@/lib/util";

const DECISION_TONE = {
  APPROVED: "border-edGreen text-edGreen-700 bg-edGreen-50",
  REJECTED: "border-edGray-200 text-edGray-700 bg-white",
  NEEDS_IMPROVEMENT: "border-orange text-orange bg-orange-50",
  PENDING: "border-orange text-orange bg-white",
};

export default function ModelsHub() {
  const [sp, setSp] = useSearchParams();
  const view = sp.get("view") || "latest";  // latest | versions
  const [data, setData] = useState(null);
  const limit = 100;
  const offset = parseInt(sp.get("offset") || "0", 10);

  useEffect(() => {
    const p = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (sp.get("latest_decision")) p.set("latest_decision", sp.get("latest_decision"));
    if (sp.get("has_review") === "true") p.set("has_review", "true");
    if (sp.get("lifecycle")) p.set("lifecycle", sp.get("lifecycle"));
    if (sp.get("evaluator")) p.set("evaluator", sp.get("evaluator"));
    if (sp.get("org_id")) p.set("org_id", sp.get("org_id"));
    const path = view === "versions"
      ? `/admin/canonical/submissions?${p}${sp.get("match_status") ? "&match_status=" + sp.get("match_status") : ""}`
      : `/admin/canonical/families?${p}`;
    api.get(path).then((r) => setData(r.data));
  }, [sp.toString(), view]);

  const set = (k, v) => {
    const n = new URLSearchParams(sp);
    if (v) n.set(k, v); else n.delete(k);
    n.delete("offset");
    setSp(n);
  };

  if (!data) return <div className="text-edGray-700">…جارٍ التحميل</div>;

  return (
    <div data-testid="models-hub">
      <div className="mb-4">
        <div className="stat-label mb-2">مركز رحلات النماذج</div>
        <h1 className="text-3xl font-bold">
          {view === "versions" ? "جميع النسخ" : "أحدث المخرجات"}
        </h1>
      </div>

      {/* View toggle */}
      <div className="flex flex-wrap gap-2 mb-4" data-testid="view-toggle">
        <button
          onClick={() => set("view", "latest")}
          className={`px-4 py-2 rounded-md text-sm border ${view === "latest" ? "bg-turquoise text-white border-turquoise" : "bg-white text-navy border-edGray-200 hover:border-turquoise"}`}
          data-testid="view-latest"
        >
          أحدث المخرجات <span className="num opacity-70">(3,521)</span>
        </button>
        <button
          onClick={() => set("view", "versions")}
          className={`px-4 py-2 rounded-md text-sm border ${view === "versions" ? "bg-turquoise text-white border-turquoise" : "bg-white text-navy border-edGray-200 hover:border-turquoise"}`}
          data-testid="view-versions"
        >
          جميع النسخ <span className="num opacity-70">(5,038)</span>
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-4" data-testid="filters">
        {view === "latest" && (
          <>
            <select className="field-input w-auto" value={sp.get("latest_decision") || ""} onChange={(e) => set("latest_decision", e.target.value)} data-testid="filter-decision">
              <option value="">كل القرارات</option>
              <option value="APPROVED">معتمد</option>
              <option value="REJECTED">مرفوض</option>
              <option value="NEEDS_IMPROVEMENT">يحتاج تطوير</option>
              <option value="PENDING">معلّق</option>
            </select>
            <select className="field-input w-auto" value={sp.get("has_review") || ""} onChange={(e) => set("has_review", e.target.value)} data-testid="filter-review">
              <option value="">كل حالات المراجعة</option>
              <option value="true">تحتاج مراجعة فقط</option>
            </select>
            <select className="field-input w-auto" value={sp.get("lifecycle") || ""} onChange={(e) => set("lifecycle", e.target.value)} data-testid="filter-lifecycle">
              <option value="">كل الرحلات</option>
              <option value="full">كاملة (تاريخي → حالي)</option>
              <option value="current_only">حالي فقط</option>
              <option value="legacy_only">تاريخي فقط</option>
            </select>
          </>
        )}
        {view === "versions" && (
          <select className="field-input w-auto" value={sp.get("match_status") || ""} onChange={(e) => set("match_status", e.target.value)} data-testid="filter-status">
            <option value="">كل الحالات</option>
            <option value="VERSION_LINKED">نسخ مرتبطة</option>
            <option value="REVIEW_REQUIRED">تحتاج مراجعة</option>
            <option value="CURRENT_ONLY">حالي فقط</option>
            <option value="LEGACY_ONLY">تاريخي فقط</option>
          </select>
        )}
      </div>

      <div className="text-sm text-edGray-700 mb-2 num">إجمالي: {num(data.total)}</div>

      <div className="border border-edGray-200 bg-white rounded-md overflow-x-auto">
        <table className="tech-table">
          <thead>
            {view === "latest" ? (
              <tr>
                <th>النموذج</th><th>الجهة</th><th>آخر قرار</th><th>عدد النسخ</th>
                <th>المحكم</th><th>آخر تاريخ</th><th>مراجعة</th><th></th>
              </tr>
            ) : (
              <tr>
                <th>Canonical</th><th>الجهة</th><th>النموذج</th><th>المصدر</th>
                <th>القرار</th><th>الحالة</th><th>التاريخ</th><th></th>
              </tr>
            )}
          </thead>
          <tbody>
            {view === "latest" && (data.items || []).map((f) => (
              <tr key={f.family_id} className="hover:bg-turquoise-50/40" data-testid={`row-${f.family_id}`}>
                <td className="text-sm">
                  <div>{f.model_name}</div>
                  <div className="text-xs num text-edGray-700">{f.family_id}</div>
                </td>
                <td>
                  <Link to={`/admin/organizations/${f.organization_id}`} className="text-navy hover:text-turquoise-700">
                    {f.organization_name}
                  </Link>
                </td>
                <td><span className={`pill text-xs ${DECISION_TONE[f.latest_decision || "PENDING"]}`}>{f.latest_decision_ar}</span></td>
                <td className="num">{f.version_count}</td>
                <td className="text-sm">{f.latest_evaluator_name || "—"}</td>
                <td className="text-xs num text-edGray-700">{(f.latest_date || "").slice(0, 10) || "—"}</td>
                <td>{f.has_review_required ? <span className="pill text-xs border-orange text-orange bg-orange-50">مراجعة</span> : "—"}</td>
                <td><Link to={`/admin/family/${f.family_id}`} className="btn-outline text-xs">فتح</Link></td>
              </tr>
            ))}
            {view === "versions" && (data.items || []).map((c) => (
              <tr key={c.canonical_id} className="hover:bg-turquoise-50/40" data-testid={`row-${c.canonical_id}`}>
                <td className="text-xs num text-edGray-700">{c.canonical_id}</td>
                <td className="text-sm">
                  <Link to={`/admin/organizations/${c.organization_id}`} className="text-navy hover:text-turquoise-700">
                    {c.organization_name}
                  </Link>
                </td>
                <td className="text-sm">{c.model_name}</td>
                <td>
                  <span className={`pill text-xs ${c.primary_source === "current" ? "border-turquoise-200 text-turquoise-700 bg-turquoise-50" : "border-edGray-200 text-edGray-700 bg-white"}`}>
                    {c.primary_source === "current" ? "حالي" : "تاريخي"}
                  </span>
                </td>
                <td className="text-xs">{c.raw_evaluation_current || c.raw_evaluation_legacy || "—"}</td>
                <td className="text-xs">{c.match_status}</td>
                <td className="text-xs num text-edGray-700">{(c.submitted_at_iso || c.arbitration_date_iso || "").slice(0, 10) || "—"}</td>
                <td>{c.family_id && <Link to={`/admin/family/${c.family_id}`} className="btn-outline text-xs">فتح الرحلة</Link>}</td>
              </tr>
            ))}
            {(data.items || []).length === 0 && <tr><td colSpan={8} className="text-center text-edGray-700 py-6">لا نتائج</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-4 text-sm">
        <div className="text-edGray-700 num">
          {data.total > 0 ? `${offset + 1}–${Math.min(offset + limit, data.total)} من ${num(data.total)}` : "—"}
        </div>
        <div className="flex gap-2">
          <button className="btn-outline text-sm disabled:opacity-40" disabled={offset === 0}
                  onClick={() => set("offset", String(Math.max(0, offset - limit)))} data-testid="prev-page">السابق</button>
          <button className="btn-outline text-sm disabled:opacity-40" disabled={offset + limit >= data.total}
                  onClick={() => set("offset", String(offset + limit))} data-testid="next-page">التالي</button>
        </div>
      </div>
    </div>
  );
}
