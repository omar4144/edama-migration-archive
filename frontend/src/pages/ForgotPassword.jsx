import React, { useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/forgot-password", { email: email.trim().toLowerCase() });
    } catch {}
    // Never disclose whether the email is registered.
    setDone(true);
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-ivory flex items-center justify-center p-4" data-testid="forgot-page">
      <div className="w-full max-w-md bg-white border border-navy/15 p-6">
        <h1 className="text-2xl font-semibold mb-1">استعادة كلمة المرور</h1>
        <p className="text-sm text-navy/70 mb-6">أدخل بريدك؛ إن كان مسجلاً، سترسل رابط إعادة التعيين خلال دقائق.</p>

        {done ? (
          <div className="border-r-4 border-turquoise bg-white px-3 py-3 text-sm" data-testid="forgot-done">
            إذا كان البريد مسجلاً في المنصة، فسيصلك رابط لإعادة التعيين. راجع صندوق الوارد.
            <div className="mt-3"><Link to="/login" className="text-turquoise-600 hover:underline">العودة لتسجيل الدخول</Link></div>
          </div>
        ) : (
          <form onSubmit={submit} data-testid="forgot-form">
            <label className="field-label">البريد الإلكتروني</label>
            <input type="email" required className="field-input mb-4" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="forgot-email" />
            <button type="submit" disabled={loading} className="btn-primary w-full justify-center disabled:opacity-50" data-testid="forgot-submit">
              {loading ? "…جارٍ الإرسال" : "إرسال"}
            </button>
            <div className="mt-4 text-sm text-navy/60"><Link to="/login" className="hover:underline">العودة</Link></div>
          </form>
        )}
      </div>
    </div>
  );
}
