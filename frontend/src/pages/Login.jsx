import React, { useState } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export default function Login() {
  const { user, login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(false);

  if (user && user !== false) return <Navigate to="/" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setErr(null);
    setLoading(true);
    try {
      await login(email.trim().toLowerCase(), password);
    } catch (e) {
      setErr(e?.response?.data?.detail || "بيانات الدخول غير صحيحة");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ivory text-navy flex" data-testid="login-page">
      <div className="hidden md:flex flex-col justify-between w-1/2 bg-white p-12 relative overflow-hidden">
        <div className="absolute inset-0 edama-chevron-bg opacity-70 pointer-events-none" aria-hidden="true" />
        <div className="absolute inset-x-0 top-0 edama-chevron-strip" aria-hidden="true" />
        <div className="relative flex items-center gap-4">
          <img src="/edama-logo-full.png" alt="مسرعة إدامة — Edama Accelerator" className="h-20 w-auto" draggable={false} />
        </div>
        <div className="relative">
          <h1 className="text-4xl font-bold leading-tight mb-4 text-navy">منصة موحّدة لمصالحة السياق</h1>
          <p className="text-edGray-700 leading-relaxed max-w-md">
            دمج البيانات التاريخية والحالية لمسرعة الاستدامة عبر طبقة ترحيل ثابتة ولوحة قرارات مطابقة موثّقة.
          </p>
          <div className="mt-8 grid grid-cols-3 gap-6 text-right">
            <div>
              <div className="stat-value text-turquoise">3,521</div>
              <div className="stat-label mt-1">رحلة نماذج</div>
            </div>
            <div>
              <div className="stat-value text-edGreen-600">5,038</div>
              <div className="stat-label mt-1">نسخة موحّدة</div>
            </div>
            <div>
              <div className="stat-value text-navy">1,203<span className="text-sm text-edGray-700"> س</span></div>
              <div className="stat-label mt-1">تحكيم Lovable</div>
            </div>
          </div>
        </div>
        <div className="relative text-xs text-edGray-700 tracking-[0.18em] font-semibold">© EDAMA ACCELERATOR</div>
      </div>

      <div className="flex-1 flex items-center justify-center px-6 bg-ivory">
        <form onSubmit={submit} className="w-full max-w-sm" data-testid="login-form">
          <div className="md:hidden mb-6 flex justify-center">
            <img src="/edama-logo-full.png" alt="مسرعة إدامة" className="h-16 w-auto" />
          </div>
          <h2 className="text-2xl font-bold mb-1 text-navy">تسجيل الدخول</h2>
          <p className="text-sm text-edGray-700 mb-8">استخدم بريد المؤسسة وكلمة المرور المخصصة.</p>

          <label className="field-label" htmlFor="email">البريد الإلكتروني</label>
          <input
            id="email"
            data-testid="login-email"
            type="email"
            required
            autoComplete="email"
            className="field-input mb-4"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <label className="field-label" htmlFor="password">كلمة المرور</label>
          <input
            id="password"
            data-testid="login-password"
            type="password"
            required
            autoComplete="current-password"
            className="field-input mb-6"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {err && (
            <div className="mb-4 border-r-4 border-orange bg-orange-50 text-navy px-3 py-2 text-sm" data-testid="login-error">
              {err}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full justify-center disabled:opacity-50"
            data-testid="login-submit"
          >
            {loading ? "…جارٍ التحقق" : "دخول"}
          </button>
          <div className="mt-4 text-sm text-navy/60 text-center">
            <a href="/forgot-password" className="hover:underline" data-testid="forgot-link">نسيت كلمة المرور؟</a>
          </div>
        </form>
      </div>
    </div>
  );
}
