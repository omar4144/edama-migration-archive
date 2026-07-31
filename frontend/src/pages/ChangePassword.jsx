import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import api, { formatApiError } from "@/lib/api";

export default function ChangePassword() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  if (user === null) return null;
  if (user === false) return <Navigate to="/login" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setErr(null);
    if (next !== confirm) { setErr("كلمتا المرور غير متطابقتين"); return; }
    setLoading(true);
    try {
      const { data } = await api.post("/auth/change-password", {
        current_password: current, new_password: next,
      });
      if (data.access_token) localStorage.setItem("edama_access_token", data.access_token);
      await refresh();
      navigate("/", { replace: true });
    } catch (e) {
      setErr(formatApiError(e));
    } finally {
      setLoading(false);
    }
  };

  const forced = !!user.must_change_password;

  return (
    <div className="min-h-screen bg-ivory flex items-center justify-center p-4" data-testid="change-password-page">
      <form onSubmit={submit} className="w-full max-w-md bg-white border border-navy/15 p-6" data-testid="change-password-form">
        <h1 className="text-2xl font-semibold mb-1">تغيير كلمة المرور</h1>
        {forced && (
          <div className="mb-4 border-r-4 border-orange bg-orange-50 px-3 py-2 text-sm" data-testid="forced-notice">
            هذا حساب اختبار — يجب تغيير كلمة المرور قبل الوصول إلى أي مساحة عمل.
          </div>
        )}
        <div className="text-sm text-navy/70 mb-6">
          استخدم 8 أحرف على الأقل مع حروف وأرقام. سيتم إبطال جلساتك السابقة.
        </div>

        <label className="field-label" htmlFor="cur">كلمة المرور الحالية</label>
        <input id="cur" type="password" required autoComplete="current-password"
               className="field-input mb-3" value={current} onChange={(e) => setCurrent(e.target.value)}
               data-testid="current-password" />

        <label className="field-label" htmlFor="new">الجديدة</label>
        <input id="new" type="password" required autoComplete="new-password"
               className="field-input mb-3" value={next} onChange={(e) => setNext(e.target.value)}
               data-testid="new-password" />

        <label className="field-label" htmlFor="conf">تأكيد الجديدة</label>
        <input id="conf" type="password" required autoComplete="new-password"
               className="field-input mb-4" value={confirm} onChange={(e) => setConfirm(e.target.value)}
               data-testid="confirm-password" />

        {err && <div className="mb-4 border-r-4 border-orange bg-orange-50 px-3 py-2 text-sm" data-testid="change-error">{err}</div>}

        <button type="submit" disabled={loading} className="btn-primary w-full justify-center disabled:opacity-50" data-testid="change-submit">
          {loading ? "…جارٍ الحفظ" : "حفظ"}
        </button>
      </form>
    </div>
  );
}
