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
      <div className="hidden md:flex flex-col justify-between w-1/2 bg-navy text-ivory p-12">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 border-2 border-turquoise flex items-center justify-center">
            <span className="text-turquoise font-bold text-xl">إ</span>
          </div>
          <div>
            <div className="font-semibold text-xl">مسرعة إدامة</div>
            <div className="text-sm text-ivory/60 tracking-wider">Musr'at Idama · V8</div>
          </div>
        </div>
        <div>
          <h1 className="text-4xl font-semibold leading-tight mb-4">منصة موحّدة لمصالحة السياق</h1>
          <p className="text-ivory/70 leading-relaxed max-w-md">
            دمج البيانات التاريخية والحالية لمسرعة الاستدامة عبر طبقة ترحيل ثابتة ولوحة قرارات مطابقة موثّقة.
          </p>
          <div className="mt-8 grid grid-cols-3 gap-6 text-right">
            <div><div className="stat-value">2,565</div><div className="stat-label mt-1">سجل حالي</div></div>
            <div><div className="stat-value">3,403</div><div className="stat-label mt-1">تحكيم تاريخي</div></div>
            <div><div className="stat-value">118</div><div className="stat-label mt-1">جهة تاريخية</div></div>
          </div>
        </div>
        <div className="text-xs text-ivory/40 tracking-wider">© مسرعة إدامة · طبقة V8</div>
      </div>

      <div className="flex-1 flex items-center justify-center px-6">
        <form onSubmit={submit} className="w-full max-w-sm" data-testid="login-form">
          <h2 className="text-2xl font-semibold mb-1">تسجيل الدخول</h2>
          <p className="text-sm text-navy/60 mb-8">استخدم بريد المؤسسة وكلمة المرور المخصصة.</p>

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
        </form>
      </div>
    </div>
  );
}
