import React, { useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") || "";
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ok, setOk] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr(null);
    if (!token) { setErr("رمز غير موجود في الرابط"); return; }
    if (next !== confirm) { setErr("كلمتا المرور غير متطابقتين"); return; }
    setLoading(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: next });
      setOk(true);
      setTimeout(() => navigate("/login", { replace: true }), 2000);
    } catch (e) {
      setErr(formatApiError(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ivory flex items-center justify-center p-4" data-testid="reset-page">
      <div className="w-full max-w-md bg-white border border-navy/15 p-6">
        <h1 className="text-2xl font-semibold mb-1">إعادة تعيين كلمة المرور</h1>
        <p className="text-sm text-navy/70 mb-6">اختر كلمة مرور جديدة قوية (8+ أحرف، حروف وأرقام).</p>

        {ok ? (
          <div className="border-r-4 border-edGreen bg-white px-3 py-3 text-sm" data-testid="reset-done">
            تم تحديث كلمة المرور بنجاح. سيتم توجيهك لتسجيل الدخول…
          </div>
        ) : (
          <form onSubmit={submit} data-testid="reset-form">
            <label className="field-label">الجديدة</label>
            <input type="password" required className="field-input mb-3" value={next} onChange={(e) => setNext(e.target.value)} data-testid="reset-new" />
            <label className="field-label">تأكيد الجديدة</label>
            <input type="password" required className="field-input mb-4" value={confirm} onChange={(e) => setConfirm(e.target.value)} data-testid="reset-confirm" />
            {err && <div className="mb-3 border-r-4 border-orange bg-orange-50 px-3 py-2 text-sm" data-testid="reset-error">{err}</div>}
            <button type="submit" disabled={loading} className="btn-primary w-full justify-center disabled:opacity-50" data-testid="reset-submit">
              {loading ? "…جارٍ الحفظ" : "تعيين"}
            </button>
            <div className="mt-4 text-sm text-navy/60"><Link to="/login" className="hover:underline">العودة</Link></div>
          </form>
        )}
      </div>
    </div>
  );
}
