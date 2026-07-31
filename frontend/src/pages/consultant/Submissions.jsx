import React, { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";

export default function ConsultantSubmissions() {
  const [items, setItems] = useState([]);
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ model_url: "", notes: "", status: "" });
  const [err, setErr] = useState(null);
  const [msg, setMsg] = useState(null);

  const load = () => api.get("/consultant/submissions").then((r) => setItems(r.data));
  useEffect(() => { load(); }, []);

  const open = (r) => {
    setSelected(r);
    setForm({ model_url: r.model_url || "", notes: r.notes || "", status: r.status || "" });
    setErr(null); setMsg(null);
  };

  const save = async () => {
    setErr(null); setMsg(null);
    try {
      await api.patch(`/consultant/records/${selected.migration_id}`, form);
      setMsg("تم الحفظ");
      load();
    } catch (e) {
      setErr(formatApiError(e));
    }
  };

  return (
    <div data-testid="consultant-submissions-page">
      <h1 className="text-3xl font-semibold mb-2">نماذجي المرسلة</h1>
      <p className="text-navy/70 mb-6">السجلات المرتبطة بحسابك في طبقة Lovable الحالية ({items.length} سجل).</p>

      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="submissions-table">
          <thead>
            <tr><th>الجهة</th><th>النموذج</th><th>الحالة</th><th>الساعات</th><th>الرابط</th><th></th></tr>
          </thead>
          <tbody>
            {items.map((r) => (
              <tr key={r.migration_id}>
                <td className="text-sm">{r.organization_name}</td>
                <td className="text-sm">{r.model_name}</td>
                <td className="text-sm">{r.status}</td>
                <td className="num">{r.work_hours}</td>
                <td className="text-xs num text-navy/60 truncate max-w-xs">
                  {r.model_url ? <a href={r.model_url} target="_blank" rel="noreferrer" className="text-turquoise-600 hover:underline">فتح</a> : "—"}
                </td>
                <td className="text-left"><button className="btn-outline text-sm" onClick={() => open(r)} data-testid={`edit-${r.migration_id}`}>تعديل</button></td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={6} className="text-center text-navy/50 py-6">لا توجد سجلات مرتبطة</td></tr>}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="fixed inset-0 bg-navy/40 flex items-center justify-center p-4 z-50" data-testid="edit-modal">
          <div className="bg-white border border-navy/20 max-w-lg w-full p-6">
            <h2 className="text-xl font-semibold mb-1">تعديل مسودة</h2>
            <div className="text-sm text-navy/60 mb-4">{selected.organization_name} · {selected.model_name}</div>
            <label className="field-label">رابط النموذج</label>
            <input className="field-input mb-3" value={form.model_url} onChange={(e) => setForm({...form, model_url: e.target.value})} data-testid="edit-url" />
            <label className="field-label">الحالة</label>
            <input className="field-input mb-3" value={form.status} onChange={(e) => setForm({...form, status: e.target.value})} data-testid="edit-status" />
            <label className="field-label">ملاحظات</label>
            <textarea rows={3} className="field-input mb-4" value={form.notes} onChange={(e) => setForm({...form, notes: e.target.value})} data-testid="edit-notes" />
            {err && <div className="mb-3 border-r-4 border-orange bg-orange-50 px-3 py-2 text-sm">{err}</div>}
            {msg && <div className="mb-3 border-r-4 border-edGreen bg-white px-3 py-2 text-sm text-edGreen">{msg}</div>}
            <div className="flex justify-end gap-2">
              <button className="btn-outline" onClick={() => setSelected(null)} data-testid="edit-close">إغلاق</button>
              <button className="btn-primary" onClick={save} data-testid="edit-save">حفظ</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
