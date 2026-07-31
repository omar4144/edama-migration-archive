import React, { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";

const ROLE_LABEL = { admin: "إدارة السياق", consultant: "مستشار", evaluator: "محكّم" };

export default function Users() {
  const [users, setUsers] = useState([]);
  const [people, setPeople] = useState([]);
  const [form, setForm] = useState({ email: "", password: "", name_ar: "", role: "consultant", person_id: "" });
  const [err, setErr] = useState(null);
  const [msg, setMsg] = useState(null);

  const load = () => api.get("/admin/users").then((r) => setUsers(r.data));

  useEffect(() => {
    load();
    api.get("/admin/people").then((r) => setPeople(r.data));
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setErr(null); setMsg(null);
    try {
      await api.post("/admin/users", {
        ...form,
        person_id: form.person_id || null,
      });
      setForm({ email: "", password: "", name_ar: "", role: "consultant", person_id: "" });
      setMsg("تم إنشاء المستخدم");
      load();
    } catch (e) {
      setErr(formatApiError(e));
    }
  };

  return (
    <div data-testid="users-page">
      <h1 className="text-3xl font-semibold mb-2">المستخدمون والصلاحيات</h1>
      <p className="text-navy/70 mb-6">إنشاء وربط الحسابات بالأشخاص الحقيقيين من طبقة Lovable.</p>

      <div className="grid md:grid-cols-3 gap-6">
        <form onSubmit={submit} className="border border-navy/15 bg-white p-5" data-testid="create-user-form">
          <h2 className="text-lg font-semibold mb-3">إضافة مستخدم</h2>
          <label className="field-label">البريد</label>
          <input required type="email" className="field-input mb-3" value={form.email} onChange={(e) => setForm({...form, email: e.target.value})} data-testid="new-email" />
          <label className="field-label">كلمة المرور المبدئية</label>
          <input required type="text" className="field-input mb-3" value={form.password} onChange={(e) => setForm({...form, password: e.target.value})} data-testid="new-password" />
          <label className="field-label">الاسم (عربي)</label>
          <input className="field-input mb-3" value={form.name_ar} onChange={(e) => setForm({...form, name_ar: e.target.value})} data-testid="new-name" />
          <label className="field-label">الدور</label>
          <select className="field-input mb-3" value={form.role} onChange={(e) => setForm({...form, role: e.target.value, person_id: ""})} data-testid="new-role">
            <option value="admin">إدارة السياق</option>
            <option value="consultant">مستشار</option>
            <option value="evaluator">محكّم</option>
          </select>
          {form.role !== "admin" && (
            <>
              <label className="field-label">ربط بشخص</label>
              <select className="field-input mb-3" value={form.person_id} onChange={(e) => setForm({...form, person_id: e.target.value})} data-testid="new-person">
                <option value="">— بدون ربط —</option>
                {people.filter((p) => p.role === form.role).map((p) => (
                  <option key={p.person_id} value={p.person_id}>{p.person_name}</option>
                ))}
              </select>
            </>
          )}
          {err && <div className="mb-3 border-r-4 border-orange bg-orange-50 px-3 py-2 text-sm">{err}</div>}
          {msg && <div className="mb-3 border-r-4 border-edGreen bg-white px-3 py-2 text-sm text-edGreen">{msg}</div>}
          <button type="submit" className="btn-primary w-full justify-center" data-testid="create-user-submit">إنشاء</button>
        </form>

        <div className="md:col-span-2 border border-navy/15 bg-white overflow-x-auto">
          <table className="tech-table" data-testid="users-table">
            <thead>
              <tr>
                <th>البريد</th><th>الاسم</th><th>الدور</th><th>ربط</th><th>تغيير كلمة المرور</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="text-sm">{u.email}</td>
                  <td className="text-sm">{u.name_ar}</td>
                  <td className="text-sm">{ROLE_LABEL[u.role]}</td>
                  <td className="text-xs num text-navy/60">{u.person_id || "—"}</td>
                  <td>{u.must_change_password ? <span className="pill-pending">مطلوب</span> : <span className="pill-approved">تم</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
