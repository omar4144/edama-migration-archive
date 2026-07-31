import React, { useCallback, useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";

const KIND_LABEL = {
  organization_probable_match: "جهة — مطابقة اسم مرجّحة",
  model_evolved_schema: "نموذج — تطوّر مخطط",
  evaluator_assignment_changed: "تغيّر تكليف المحكّم",
};

export default function ReviewQueue() {
  const [status, setStatus] = useState("pending");
  const [kind, setKind] = useState("");
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [note, setNote] = useState("");
  const [err, setErr] = useState(null);

  const load = useCallback(() => {
    setErr(null);
    const params = new URLSearchParams({ status });
    if (kind) params.append("kind", kind);
    api.get(`/reconciliation/mappings?${params}`)
      .then((r) => setItems(r.data))
      .catch((e) => setErr(formatApiError(e)));
  }, [status, kind]);

  useEffect(() => { load(); }, [load]);

  const decide = async (decision) => {
    if (!selected) return;
    try {
      await api.post(`/reconciliation/mappings/${encodeURIComponent(selected.key)}`,
        { decision, note: note || null });
      setSelected(null);
      setNote("");
      load();
    } catch (e) {
      setErr(formatApiError(e));
    }
  };

  return (
    <div data-testid="review-queue-page">
      <h1 className="text-3xl font-semibold mb-2">قائمة المراجعة</h1>
      <p className="text-navy/70 mb-6 max-w-2xl leading-relaxed">
        كل عنصر يحمل حالة REVIEW_REQUIRED ولن يُدمج آلياً. الاعتماد بشري صريح، مع تسجيل كامل في سجل التدقيق.
      </p>

      <div className="flex gap-3 mb-4" data-testid="filters">
        <select className="field-input w-auto" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="filter-status">
          <option value="pending">معلّقة</option>
          <option value="approved">معتمدة</option>
          <option value="rejected">مرفوضة</option>
        </select>
        <select className="field-input w-auto" value={kind} onChange={(e) => setKind(e.target.value)} data-testid="filter-kind">
          <option value="">كل الأنواع</option>
          <option value="organization_probable_match">جهة — مرجّحة</option>
          <option value="model_evolved_schema">نموذج — تطوّر</option>
          <option value="evaluator_assignment_changed">تكليف محكّم</option>
        </select>
      </div>

      {err && <div className="mb-3 border-r-4 border-orange bg-orange-50 px-3 py-2 text-sm">{err}</div>}

      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="mappings-table">
          <thead>
            <tr>
              <th>النوع</th>
              <th>الحالي</th>
              <th>التاريخي</th>
              <th>سياق</th>
              <th className="text-left">إجراء</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 && (
              <tr><td colSpan={5} className="text-center text-navy/50 py-6">لا توجد عناصر</td></tr>
            )}
            {items.map((it) => (
              <tr key={it.key} className={status === "pending" ? "review-required" : ""} data-testid={`row-${it.key}`}>
                <td className="text-sm">{KIND_LABEL[it.kind] || it.kind}</td>
                <td className="text-sm">
                  {it.current_name || it.organization_name || it.current_evaluator || "—"}
                  {it.current_id && <div className="text-xs num text-navy/50">{it.current_id}</div>}
                </td>
                <td className="text-sm">
                  {it.legacy_name || it.legacy_evaluator || "—"}
                  {it.legacy_id && <div className="text-xs num text-navy/50">{it.legacy_id}</div>}
                </td>
                <td className="text-sm text-navy/70">
                  {it.score != null && <div>درجة: <span className="num">{it.score}</span></div>}
                  {it.cohort && <div>دفعة: <span className="num">{it.cohort}</span></div>}
                  {it.relationship && <div>{it.relationship}</div>}
                </td>
                <td className="text-left">
                  {status === "pending" ? (
                    <button className="btn-outline text-sm" onClick={() => setSelected(it)} data-testid={`decide-${it.key}`}>
                      قرار
                    </button>
                  ) : (
                    <span className={it.status === "approved" ? "pill-approved" : "pill-rejected"}>
                      {it.status === "approved" ? "معتمدة" : "مرفوضة"}
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="fixed inset-0 bg-navy/40 flex items-center justify-center p-4 z-50" data-testid="decision-modal">
          <div className="bg-white border border-navy/20 max-w-lg w-full p-6">
            <h2 className="text-xl font-semibold mb-2">قرار مطابقة</h2>
            <div className="text-sm text-navy/70 mb-4">{KIND_LABEL[selected.kind]}</div>
            <div className="border border-navy/15 p-3 mb-3">
              <div className="text-xs text-navy/50 mb-1">الحالي</div>
              <div>{selected.current_name || selected.organization_name || selected.current_evaluator}</div>
            </div>
            <div className="border border-navy/15 p-3 mb-4">
              <div className="text-xs text-navy/50 mb-1">التاريخي</div>
              <div>{selected.legacy_name || selected.legacy_evaluator}</div>
            </div>
            <label className="field-label">ملاحظة (اختياري)</label>
            <textarea rows={3} className="field-input mb-4" value={note} onChange={(e) => setNote(e.target.value)} data-testid="decision-note" />
            <div className="flex justify-end gap-2">
              <button className="btn-outline" onClick={() => { setSelected(null); setNote(""); }} data-testid="decision-cancel">إلغاء</button>
              <button className="btn-danger" onClick={() => decide("rejected")} data-testid="decision-reject">رفض</button>
              <button className="btn-primary" onClick={() => decide("approved")} data-testid="decision-approve">اعتماد</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
