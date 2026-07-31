import React, { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";

const OPTIONS = ["مقبول", "يحتاج لتطوير", "غير مكتمل"];

export default function EvaluatorQueue() {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ evaluation: "مقبول", work_hours: 0, notes: "" });
  const [err, setErr] = useState(null);
  const [msg, setMsg] = useState(null);
  const [filter, setFilter] = useState("");

  const load = () => api.get("/evaluator/queue").then((r) => setItems(r.data));
  useEffect(() => { load(); }, []);

  const open = (r) => {
    setSelected(r);
    setForm({
      evaluation: OPTIONS.includes(r.evaluation) ? r.evaluation : "مقبول",
      work_hours: r.work_hours || 0,
      notes: r.notes || "",
    });
    setErr(null); setMsg(null);
  };

  const save = async () => {
    setErr(null); setMsg(null);
    try {
      await api.patch(`/evaluator/records/${selected.migration_id}`, {
        evaluation: form.evaluation,
        work_hours: parseFloat(form.work_hours) || 0,
        notes: form.notes || null,
      });
      setMsg("تم تسجيل القرار");
      load();
    } catch (e) {
      setErr(formatApiError(e));
    }
  };

  const filtered = filter ? items.filter((r) => r.evaluation === filter) : items;

  return (
    <div data-testid="evaluator-queue-page">
      <h1 className="text-3xl font-semibold mb-2">قائمة التحكيم</h1>
      <p className="text-navy/70 mb-6">السجلات المسندة إليك ({items.length}). سجّل القرار والساعات لكل نموذج.</p>

      <div className="flex gap-3 mb-4">
        <select className="field-input w-auto" value={filter} onChange={(e) => setFilter(e.target.value)} data-testid="filter-evaluation">
          <option value="">كل التقييمات</option>
          {OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      </div>

      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="eval-queue-table">
          <thead>
            <tr><th>الجهة</th><th>النموذج</th><th>المستشار</th><th>التقييم</th><th>الساعات</th><th></th></tr>
          </thead>
          <tbody>
            {filtered.map((r) => (
              <tr key={r.migration_id}>
                <td className="text-sm">{r.organization_name}</td>
                <td className="text-sm">{r.model_name}</td>
                <td className="text-sm">{r.consultant_name}</td>
                <td className="text-sm">{r.evaluation}</td>
                <td className="num">{r.work_hours}</td>
                <td className="text-left"><button className="btn-outline text-sm" onClick={() => open(r)} data-testid={`decide-${r.migration_id}`}>قرار</button></td>
              </tr>
            ))}
            {filtered.length === 0 && <tr><td colSpan={6} className="text-center text-navy/50 py-6">لا توجد نتائج</td></tr>}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="fixed inset-0 bg-navy/40 flex items-center justify-center p-4 z-50" data-testid="decision-modal">
          <div className="bg-white border border-navy/20 max-w-lg w-full p-6">
            <h2 className="text-xl font-semibold mb-1">تسجيل قرار تحكيم</h2>
            <div className="text-sm text-navy/60 mb-4">{selected.organization_name} · {selected.model_name}</div>
            <label className="field-label">التقييم</label>
            <select className="field-input mb-3" value={form.evaluation} onChange={(e) => setForm({...form, evaluation: e.target.value})} data-testid="decision-eval">
              {OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
            <label className="field-label">ساعات العمل</label>
            <input type="number" step="0.5" min="0" className="field-input mb-3 num" value={form.work_hours} onChange={(e) => setForm({...form, work_hours: e.target.value})} data-testid="decision-hours" />
            <label className="field-label">ملاحظات</label>
            <textarea rows={3} className="field-input mb-4" value={form.notes} onChange={(e) => setForm({...form, notes: e.target.value})} data-testid="decision-notes" />
            {err && <div className="mb-3 border-r-4 border-orange bg-orange-50 px-3 py-2 text-sm">{err}</div>}
            {msg && <div className="mb-3 border-r-4 border-edGreen bg-white px-3 py-2 text-sm text-edGreen">{msg}</div>}
            <div className="flex justify-end gap-2">
              <button className="btn-outline" onClick={() => setSelected(null)} data-testid="decision-close">إغلاق</button>
              <button className="btn-primary" onClick={save} data-testid="decision-save">حفظ</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
