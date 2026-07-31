import React, { useEffect, useState } from "react";
import api from "@/lib/api";

const SEV_STYLE = {
  HIGH: "text-orange border-orange bg-orange-50",
  MEDIUM: "text-navy border-navy/40 bg-white",
  LOW: "text-navy/70 border-navy/25 bg-white",
  OK: "text-edGreen border-edGreen bg-white",
};

export default function DataQuality() {
  const [data, setData] = useState(null);
  const [signal, setSignal] = useState(null);
  const [drill, setDrill] = useState({ items: [], total: 0, collection: "" });
  const [offset, setOffset] = useState(0);
  const limit = 25;

  useEffect(() => { api.get("/admin/dq/summary").then((r) => setData(r.data)); }, []);

  useEffect(() => {
    if (!signal) return;
    const p = new URLSearchParams({ limit, offset });
    api.get(`/admin/dq/affected/${signal.id}?${p}`).then((r) => setDrill(r.data));
  }, [signal, offset]);

  if (!data) return <div className="text-navy/60">…جارٍ التحميل</div>;

  return (
    <div data-testid="dq-page">
      <h1 className="text-3xl font-semibold mb-2">مركز جودة البيانات</h1>
      <p className="text-navy/70 mb-6 max-w-2xl leading-relaxed">
        16 فحص جودة + 108 ملف مصدر. المسار: <span className="num">المصدر الخام ← التطبيع ← المطابقة ← المراجعة ← الاعتماد</span>. البيانات الخام لا تُعدَّل — يُتخذ القرار على طبقة المطابقة/المراجعة.
      </p>

      <h2 className="text-xl font-semibold mb-3">فحوصات المصادر (Static)</h2>
      <div className="border border-navy/15 bg-white overflow-x-auto mb-8">
        <table className="tech-table" data-testid="static-checks-table">
          <thead>
            <tr><th>الفحص</th><th>المتوقع</th><th>الفعلي</th><th>الحالة</th><th>ملاحظات</th></tr>
          </thead>
          <tbody>
            {data.checks.map((c, i) => (
              <tr key={i}>
                <td className="text-sm">{c.check}</td>
                <td className="num">{c.expected}</td>
                <td className="num">{c.actual}</td>
                <td>
                  <span className={c.status === "PASS" ? "pill-approved" : "pill-pending"}>{c.status}</span>
                </td>
                <td className="text-xs text-navy/60">{c.notes || ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="text-xl font-semibold mb-3">إشارات حية (Drill-down)</h2>
      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="signals-table">
          <thead>
            <tr><th>الفحص</th><th>السجلات المتأثرة</th><th>الخطورة</th><th>الإجراء المقترح</th><th></th></tr>
          </thead>
          <tbody>
            {data.signals.map((s) => (
              <tr key={s.id}>
                <td className="text-sm">{s.label}</td>
                <td className="num">{Number(s.affected).toLocaleString("en-US")}</td>
                <td><span className={`pill border ${SEV_STYLE[s.severity] || SEV_STYLE.LOW}`}>{s.severity}</span></td>
                <td className="text-xs text-navy/70">{s.action}</td>
                <td className="text-left">
                  {s.affected > 0 && s.severity !== "OK" && (
                    <button className="btn-outline text-sm" onClick={() => { setSignal(s); setOffset(0); }} data-testid={`drill-${s.id}`}>
                      عرض السجلات
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {signal && (
        <div className="fixed inset-0 bg-navy/40 flex items-center justify-center p-4 z-50" data-testid="dq-drill-modal">
          <div className="bg-white border border-navy/20 max-w-5xl w-full max-h-[85vh] overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-navy/10 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold">{signal.label}</h3>
                <div className="text-xs text-navy/60 num">{drill.collection} · {drill.total.toLocaleString("en-US")} سجلاً</div>
              </div>
              <button className="btn-outline text-sm" onClick={() => setSignal(null)} data-testid="drill-close">إغلاق</button>
            </div>
            <div className="overflow-x-auto overflow-y-auto flex-1">
              <table className="tech-table">
                <thead>
                  <tr>
                    <th>الدفعة</th><th>الجهة</th><th>النموذج/النشاط</th><th>حقول متأثرة</th><th>المصدر</th>
                  </tr>
                </thead>
                <tbody>
                  {drill.items.map((r, i) => (
                    <tr key={i}>
                      <td className="num">{r.cohort || r.legacy_cohort || "—"}</td>
                      <td className="text-sm">{r.organization_name || r.current_organization_name || "—"}</td>
                      <td className="text-sm">{r.model_name || r.activity || r.current_model_name || "—"}</td>
                      <td className="text-xs text-navy/60">{r.metadata_status || r.source_name_status || r.crosswalk_status || ""}</td>
                      <td className="text-xs num text-navy/50 truncate max-w-xs">{r.source_file || r.source_sheet || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="px-6 py-3 border-t border-navy/10 flex items-center justify-between text-sm">
              <div className="text-navy/60 num">{offset + 1}–{Math.min(offset + limit, drill.total)} من {drill.total.toLocaleString("en-US")}</div>
              <div className="flex gap-2">
                <button className="btn-outline text-sm disabled:opacity-40" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))} data-testid="drill-prev">السابق</button>
                <button className="btn-outline text-sm disabled:opacity-40" disabled={offset + limit >= drill.total} onClick={() => setOffset(offset + limit)} data-testid="drill-next">التالي</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
