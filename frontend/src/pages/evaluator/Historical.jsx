import React, { useEffect, useState } from "react";
import api from "@/lib/api";

export default function EvaluatorHistorical() {
  const [data, setData] = useState({ items: [], total: 0, evaluator_name: "" });
  const [q, setQ] = useState("");
  const [cohort, setCohort] = useState("");
  const [offset, setOffset] = useState(0);
  const limit = 25;

  useEffect(() => {
    const p = new URLSearchParams({ limit, offset });
    if (q) p.append("q", q);
    if (cohort) p.append("cohort", cohort);
    api.get(`/evaluator/historical-arbitrations?${p}`).then((r) => setData(r.data));
  }, [q, cohort, offset]);

  return (
    <div data-testid="evaluator-historical-page">
      <h1 className="text-3xl font-semibold mb-2">التحكيمات التاريخية</h1>
      <div className="mb-4 border-r-4 border-navy/40 bg-white px-3 py-2 text-sm" data-testid="readonly-notice">
        سياق سابق — <b>للقراءة فقط</b>. لا يمكن تحويل قرار تاريخي إلى قرار حالي تلقائياً.
      </div>
      <p className="text-navy/70 mb-6">
        السجلات المسندة إلى <b>{data.evaluator_name || "—"}</b> في البيانات التاريخية ({data.total.toLocaleString("en-US")} سجل).
      </p>

      <div className="flex gap-3 mb-4 flex-wrap">
        <input className="field-input w-64" placeholder="بحث في اسم الجهة…" value={q} onChange={(e) => { setQ(e.target.value); setOffset(0); }} data-testid="filter-q" />
        <select className="field-input w-auto" value={cohort} onChange={(e) => { setCohort(e.target.value); setOffset(0); }} data-testid="filter-cohort">
          <option value="">كل الدفعات</option>
          <option value="2">دفعة 2</option>
          <option value="3">دفعة 3</option>
          <option value="4">دفعة 4</option>
        </select>
      </div>

      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="historical-table">
          <thead>
            <tr>
              <th>الدفعة</th><th>الجهة</th><th>النموذج</th><th>القرار</th><th>الساعات</th><th>التاريخ</th><th>المصدر</th><th>حالة القالب</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((r) => (
              <tr key={r.legacy_review_id}>
                <td className="num">{r.cohort}</td>
                <td className="text-sm">{r.organization_name}</td>
                <td className="text-sm">{r.model_name || "—"}</td>
                <td className="text-sm">{r.arbitration_result || "—"}</td>
                <td className="num">{r.total_arbitration_hours || "—"}</td>
                <td className="text-xs num text-navy/60">{r.arbitration_date_iso || r.arbitration_date_source_iso || "—"}</td>
                <td className="text-xs num text-navy/50 truncate max-w-[16rem]">{r.source_file || "—"}</td>
                <td>
                  {r.metadata_status === "STALE_OR_MISMATCHED_TEMPLATE_METADATA" ? (
                    <span className="pill-pending" title="بيانات قالب مشبوهة">قالب مشبوه</span>
                  ) : r.metadata_status === "CONSISTENT" ? (
                    <span className="pill-approved">متسق</span>
                  ) : <span className="text-xs text-navy/50">—</span>}
                </td>
              </tr>
            ))}
            {data.items.length === 0 && (
              <tr><td colSpan={8} className="text-center text-navy/50 py-6">لا توجد سجلات مطابقة</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-4 text-sm">
        <div className="text-navy/60 num">{data.total > 0 ? `${offset + 1}–${Math.min(offset + limit, data.total)} من ${data.total.toLocaleString("en-US")}` : "—"}</div>
        <div className="flex gap-2">
          <button className="btn-outline text-sm disabled:opacity-40" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))} data-testid="prev-page">السابق</button>
          <button className="btn-outline text-sm disabled:opacity-40" disabled={offset + limit >= data.total} onClick={() => setOffset(offset + limit)} data-testid="next-page">التالي</button>
        </div>
      </div>
    </div>
  );
}
