import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { num } from "@/lib/util";

const DECISION_TONE = {
  APPROVED: "border-edGreen text-edGreen-700 bg-edGreen-50",
  REJECTED: "border-edGray-200 text-edGray-700 bg-white",
  NEEDS_IMPROVEMENT: "border-orange text-orange bg-orange-50",
  APPROVED_WITH_RESERVATION: "border-turquoise-200 text-turquoise-700 bg-turquoise-50",
  PENDING: "border-orange text-orange bg-white",
  UNKNOWN: "border-edGray-200 text-edGray-700 bg-white",
};

const ACTIONS = [
  { key: "link_as_versions", label: "ربط كسلسلة نسخ" },
  { key: "keep_separate", label: "إبقاء كسجلين منفصلين" },
  { key: "select_evaluator", label: "اعتماد محكم واحد" },
  { key: "select_model", label: "اعتماد تعريف نموذج" },
  { key: "defer", label: "تأجيل القرار" },
  { key: "reopen", label: "إعادة فتح المراجعة" },
];

export default function FamilyDetail() {
  const { familyId } = useParams();
  const [f, setF] = useState(null);
  const [err, setErr] = useState(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(null);
  const [msg, setMsg] = useState(null);

  const load = () => api.get(`/admin/canonical/families/${familyId}`).then((r) => setF(r.data));
  useEffect(() => { load(); }, [familyId]);

  const applyAction = async (action) => {
    setErr(null); setMsg(null); setBusy(action);
    try {
      const { data } = await api.post(`/admin/canonical/review-queue/${familyId}/decision`, { action, note });
      setMsg(`تم تسجيل القرار: ${action} في ${data.at}`);
      await load();
    } catch (e) { setErr(formatApiError(e)); }
    finally { setBusy(null); }
  };

  if (!f) return <div className="text-edGray-700">…جارٍ التحميل</div>;

  return (
    <div data-testid="family-detail-page">
      <div className="text-sm mb-3">
        <Link to="/admin/review-queue" className="text-turquoise-700 hover:underline">← قائمة المراجعة</Link>
      </div>

      <div className="border-b border-edGray-200 pb-6 mb-6">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <div className="stat-label mb-1">رحلة نموذج · {f.family_id}</div>
            <h1 className="text-2xl md:text-3xl font-bold text-navy">{f.organization_name}</h1>
            <div className="text-edGray-700 mt-1">{f.model_name}</div>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className={`pill ${DECISION_TONE[f.latest_decision || "UNKNOWN"]}`}>
              آخر قرار: {f.latest_decision_ar}
            </span>
            {f.has_review_required && <span className="pill border-orange text-orange bg-orange-50">تحتاج مراجعة</span>}
            <span className="pill border-edGray-200 text-edGray-700 bg-white num">{f.version_count} نسخة</span>
          </div>
        </div>
      </div>

      {/* Version timeline */}
      <h2 className="text-lg font-bold mb-3">الخط الزمني للنسخ</h2>
      <div className="space-y-3 mb-8" data-testid="version-timeline">
        {(f.versions || []).map((v, i) => (
          <div key={v.canonical_id} className={`bg-white border rounded-md p-4 ${v.match_status === "REVIEW_REQUIRED" ? "border-r-4 border-orange" : "border-edGray-200"}`} data-testid={`version-${i}`}>
            <div className="flex items-baseline justify-between gap-3 flex-wrap">
              <div className="flex items-baseline gap-3">
                <span className="stat-label">نسخة {i + 1} · {v.primary_source === "current" ? "حالي (Lovable)" : "تاريخي"}</span>
                <span className="text-xs num text-edGray-700">{v.canonical_id}</span>
              </div>
              <span className="text-sm num text-edGray-700">
                {(v.submitted_at_iso || v.arbitration_date_iso || "").slice(0, 10) || "—"}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mt-3 text-sm">
              <div>
                <div className="stat-label">القرار الخام</div>
                <div className="text-navy">{v.raw_evaluation_current || v.raw_evaluation_legacy || "—"}</div>
              </div>
              <div>
                <div className="stat-label">القرار المطبّع</div>
                <span className={`pill ${DECISION_TONE[(v.decision_normalized_current || v.decision_normalized_legacy) || "UNKNOWN"]}`}>
                  {v.decision_ar}
                </span>
              </div>
              <div>
                <div className="stat-label">حالة الاكتمال</div>
                <div className="text-navy">{v.completion_status_current || v.completion_status_legacy || "—"}</div>
              </div>
              <div>
                <div className="stat-label">المحكم / المستشار</div>
                <div className="text-navy text-sm">{v.evaluator_name || "—"} · {v.consultant_name || "—"}</div>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-3 text-sm">
              <div>
                <div className="stat-label">الحالة</div>
                <div className="text-navy">{v.match_status_ar}</div>
                <div className="text-xs text-edGray-700 mt-1">{v.match_reason_ar}</div>
              </div>
              <div>
                <div className="stat-label">الساعات</div>
                <div className="text-navy num">
                  {v.primary_source === "current"
                    ? `${v.work_hours_current ?? 0} س (لكل نموذج)`
                    : `${v.work_hours_legacy ?? 0} س (لكل جهة × دفعة)`}
                </div>
              </div>
              <div>
                <div className="stat-label">الرابط</div>
                {v.url ? (
                  <a href={v.url} target="_blank" rel="noopener noreferrer" className="text-turquoise-700 hover:underline text-sm" data-testid={`link-${i}`}>
                    فتح ↗
                  </a>
                ) : <span className="text-edGray-700 text-sm">—</span>}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Review actions */}
      {f.has_review_required && (
        <div className="border border-orange rounded-md p-5 bg-orange-50/40" data-testid="review-actions">
          <h2 className="text-lg font-bold mb-2">قرار المراجعة</h2>
          <p className="text-sm text-edGray-700 mb-3">
            سيُسجَّل القرار في سجل التدقيق مع صاحبه ووقته وسببه، ويعاد حساب الرحلة idempotently. البيانات الخام لا تتغيّر.
          </p>
          <label className="field-label">ملاحظة إدارية (اختياري)</label>
          <textarea className="field-input mb-4" rows={2} value={note} onChange={(e) => setNote(e.target.value)} data-testid="review-note" />
          <div className="flex flex-wrap gap-2">
            {ACTIONS.map((a) => (
              <button key={a.key} onClick={() => applyAction(a.key)} disabled={busy === a.key}
                      className="btn-outline disabled:opacity-50"
                      data-testid={`action-${a.key}`}>
                {busy === a.key ? "…جارٍ الحفظ" : a.label}
              </button>
            ))}
          </div>
          {msg && <div className="mt-3 text-sm text-edGreen-700" data-testid="review-msg">{msg}</div>}
          {err && <div className="mt-3 text-sm text-orange" data-testid="review-err">{err}</div>}
        </div>
      )}

      {!f.has_review_required && f.review_action && (
        <div className="border border-edGreen-200 bg-edGreen-50/40 rounded-md p-4" data-testid="review-resolved">
          تم تطبيق: <b>{f.review_action}</b> · <span className="text-edGray-700 text-sm">{f.review_action_at?.slice(0, 19)?.replace("T", " ")}</span>
          <button onClick={() => applyAction("reopen")} className="mr-4 text-sm text-turquoise-700 hover:underline">إعادة فتح</button>
        </div>
      )}
    </div>
  );
}
