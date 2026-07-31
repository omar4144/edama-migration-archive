import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import { num } from "@/lib/util";

const REASON_LABELS = {
  wide_gap_identical_decision: "قراران متطابقان بفارق زمني كبير",
  wide_gap_conflicting_decisions: "قراران متعارضان",
  evaluator_mismatch_cross_source: "اختلاف المحكم بين المصدرين",
  no_direct_model_match_only_org: "تطابق الجهة فقط دون نموذج",
};

export default function ReviewQueue() {
  const [sp, setSp] = useSearchParams();
  const reason = sp.get("reason") || "";
  const [d, setD] = useState(null);

  useEffect(() => {
    const q = reason ? `?reason=${encodeURIComponent(reason)}` : "";
    api.get(`/admin/canonical/review-queue${q}`).then((r) => setD(r.data));
  }, [reason]);

  if (!d) return <div className="text-edGray-700">…جارٍ التحميل</div>;

  return (
    <div data-testid="review-queue-page">
      <div className="mb-6">
        <div className="stat-label mb-2">إدارة السياق · قائمة المراجعة</div>
        <h1 className="text-3xl font-bold">رحلات تحتاج مراجعة</h1>
        <p className="text-edGray-700 mt-2 max-w-3xl">
          قرارات إدارية على مستوى الرحلة تحدد كيف تُعامَل السجلات المتقاطعة قبل احتسابها كحقيقة نهائية. لا تعديل على البيانات الخام.
        </p>
      </div>

      {/* Reason chips */}
      <div className="flex flex-wrap gap-2 mb-6" data-testid="reason-chips">
        <button
          onClick={() => setSp({})}
          className={`px-3 py-1.5 rounded-full text-sm border ${!reason ? "bg-turquoise text-white border-turquoise" : "bg-white text-navy border-edGray-200 hover:border-turquoise"}`}
          data-testid="chip-all"
        >
          الكل ({num(Object.values(d.counts_by_reason || {}).reduce((a, b) => a + b, 0))})
        </button>
        {Object.entries(d.counts_by_reason_ar || {}).map(([k, v]) => (
          <button
            key={k}
            onClick={() => setSp({ reason: k })}
            className={`px-3 py-1.5 rounded-full text-sm border ${reason === k ? "bg-turquoise text-white border-turquoise" : "bg-white text-navy border-edGray-200 hover:border-turquoise"}`}
            data-testid={`chip-${k}`}
          >
            {v.reason_ar} <span className="num opacity-70">({num(v.count)})</span>
          </button>
        ))}
      </div>

      <div className="text-sm text-edGray-700 mb-2 num">إجمالي الرحلات: {num(d.total)}</div>

      {/* Family list */}
      <div className="space-y-2" data-testid="review-family-list">
        {(d.items || []).map((f) => (
          <Link key={f.family_id} to={`/admin/family/${f.family_id}`} className="block bg-white border border-edGray-200 hover:border-orange rounded-md p-4" data-testid={`review-${f.family_id}`}>
            <div className="flex items-baseline justify-between mb-2 gap-3 flex-wrap">
              <div>
                <div className="font-semibold text-navy">{f.organization_name}</div>
                <div className="text-sm text-edGray-700">{f.model_name}</div>
              </div>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="pill border-orange text-orange bg-orange-50">تحتاج مراجعة</span>
                <span className="pill border-edGray-200 text-edGray-700 bg-white num">
                  {f.version_count} نسخة
                </span>
                <span className="text-xs num text-edGray-700">{f.family_id}</span>
              </div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-edGray-700 mt-2">
              <div><span className="text-edGray-700">آخر قرار: </span><span className="text-navy font-medium">{f.latest_decision_ar}</span></div>
              <div><span className="text-edGray-700">آخر تاريخ: </span><span className="num text-navy">{(f.latest_date || "").slice(0, 10) || "—"}</span></div>
              <div><span className="text-edGray-700">المحكم: </span><span className="text-navy">{f.latest_evaluator_name || "—"}</span></div>
              <div><span className="text-edGray-700">الرحلة: </span><span className="text-navy">{f.has_current_version && f.has_legacy_version ? "كاملة" : f.has_current_version ? "حالي فقط" : "تاريخي فقط"}</span></div>
            </div>
          </Link>
        ))}
        {(!d.items || d.items.length === 0) && (
          <div className="text-edGray-700 text-sm py-6 text-center">لا توجد رحلات مطابقة للفلتر الحالي.</div>
        )}
      </div>
    </div>
  );
}
