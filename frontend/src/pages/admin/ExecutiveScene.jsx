import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { num } from "@/lib/util";

export default function ExecutiveScene() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/admin/canonical/exec-scene").then((r) => setD(r.data)); }, []);
  if (!d) return <div className="text-edGray-700">…جارٍ التحميل</div>;
  const t = d.terminology;

  return (
    <div data-testid="exec-scene-page">
      <div className="mb-8">
        <div className="stat-label mb-2">المشهد التنفيذي · مسرعة إدامة</div>
        <h1 className="text-3xl md:text-4xl font-bold leading-tight">أين وصلت المسرعة اليوم؟</h1>
        <p className="text-edGray-700 mt-3 max-w-3xl leading-relaxed">
          كل رقم هنا يفتح سياقه الكامل. الأرقام على مستوى <b>الرحلة الموحّدة</b>: الجهة × النموذج، مع كامل نسخ الرحلة (تاريخي + حالي) تحت رقم واحد.
        </p>
      </div>

      {/* Three headline counters */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6" data-testid="counters">
        <Tile to="/admin/models-hub" label="أنواع النماذج" value={t.model_types} tone="edGray" testid="tile-model-types" />
        <Tile to="/admin/models-hub?view=journeys" label="رحلات النماذج" value={t.model_journeys} tone="turquoise" testid="tile-journeys" />
        <Tile to="/admin/models-hub?view=versions" label="النسخ والتسليمات" value={t.versions_submissions} tone="edGray" testid="tile-versions" />
        <Tile to="/admin/models-hub?view=latest" label="أحدث المخرجات" value={t.latest_outputs} tone="turquoise" testid="tile-latest" />
      </div>

      {/* Latest-decision distribution */}
      <h2 className="text-lg font-bold mb-3">آخر قرار على مستوى الرحلة</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8" data-testid="latest-decisions">
        <Tile to="/admin/models-hub?latest_decision=APPROVED" label="معتمد" value={t.approved_journeys} tone="edGreen" testid="tile-approved" />
        <Tile to="/admin/models-hub?latest_decision=REJECTED" label="مرفوض" value={t.rejected_journeys} tone="edGray" testid="tile-rejected" />
        <Tile to="/admin/models-hub?latest_decision=NEEDS_IMPROVEMENT" label="يحتاج تطوير" value={t.needs_improvement_journeys} tone="orange" testid="tile-needs-dev" />
        <Tile to="/admin/models-hub?latest_decision=PENDING" label="معلّق" value={t.pending_journeys} tone="orange" testid="tile-pending" />
      </div>

      {/* Review required — with reason breakdown */}
      <div className="border-r-4 border-orange bg-orange-50 rounded-md p-5 mb-8" data-testid="review-required-block">
        <div className="flex items-baseline justify-between mb-3 flex-wrap gap-3">
          <div>
            <div className="stat-label text-orange">تحتاج مراجعة</div>
            <div className="text-4xl font-mono font-bold text-orange">{num(t.review_required_journeys)}</div>
            <div className="text-xs text-edGray-700 mt-1">رحلة تحتوي على سجل واحد على الأقل يحتاج قرار إدارة قبل اعتماد الأرقام.</div>
          </div>
          <Link to="/admin/review-queue" className="btn-primary" data-testid="open-review-queue">فتح قائمة المراجعة ↗</Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-4" data-testid="review-reasons">
          {Object.entries(d.review_by_reason_ar || {}).map(([reason_ar, count]) => (
            <div key={reason_ar} className="flex justify-between bg-white border border-orange/40 rounded px-3 py-2 text-sm">
              <span className="text-navy">{reason_ar}</span>
              <span className="num font-semibold text-orange">{num(count)}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Hours — Primary operational (Lovable) + Secondary archival (Legacy) */}
      <h2 className="text-lg font-bold mb-3">ساعات التحكيم المسجلة للنماذج</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4" data-testid="hours-meters">
        <div className="border border-turquoise-200 bg-turquoise-50/40 rounded-md p-5">
          <div className="stat-label">المؤشر التشغيلي الأساسي</div>
          <div className="mt-2 flex items-baseline gap-2">
            <div className="text-4xl font-mono font-bold text-turquoise-700">{num(t.hours_current_per_model, 0)}</div>
            <div className="text-sm text-edGray-700">ساعة</div>
          </div>
          <div className="text-xs text-edGray-700 mt-2">
            الوحدة: <b>لكل نموذج</b> — ساعات محكم فردية مسجّلة في Lovable بعد إزالة التكرارات الداخلية.
          </div>
        </div>
        <details className="border border-edGray-200 bg-white rounded-md p-5" data-testid="legacy-hours-detail">
          <summary className="cursor-pointer">
            <span className="stat-label">ساعات تاريخية تقديرية للجهات</span>
            <span className="mr-2 num text-lg text-edGray-700">{num(t.hours_legacy_per_org_cohort, 0)} ساعة</span>
          </summary>
          <div className="text-xs text-edGray-700 mt-3 leading-relaxed">
            قيمة أرشيفية مسجلة على مستوى الجهة والدفعة (~15 ساعة لكل جهة × دفعة)، وليست ساعات منفصلة لكل نموذج. <b>لا تُستخدم كمؤشر تشغيلي</b> ولا تُجمع مع ساعات Lovable.
          </div>
        </details>
      </div>

      {/* Lifecycle breakdown of the 3,521 journeys */}
      <h2 className="text-lg font-bold mb-3">توزيع الرحلات</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-10" data-testid="lifecycle">
        <Tile to="/admin/models-hub?lifecycle=full" label="رحلات كاملة (تاريخي → حالي)" value={d.family_lifecycle.full_lifecycle} tone="turquoise" testid="tile-full" />
        <Tile to="/admin/models-hub?lifecycle=current_only" label="حالي فقط" value={d.family_lifecycle.current_only} tone="edGray" testid="tile-current-only" />
        <Tile to="/admin/models-hub?lifecycle=legacy_only" label="تاريخي فقط" value={d.family_lifecycle.legacy_only} tone="edGray" testid="tile-legacy-only" />
      </div>

      {/* Cohorts strip */}
      <h2 className="text-lg font-bold mb-3">الدفعات الأربع</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10" data-testid="cohorts-strip">
        {(d.cohorts || []).map((c) => (
          <Link key={c.cohort} to={`/admin/cohorts/${c.cohort}`} className="block bg-white border border-edGray-200 hover:border-turquoise rounded-md p-4">
            <div className="flex items-baseline justify-between mb-3">
              <div className="stat-label">دفعة</div>
              <div className="text-3xl font-mono">{c.cohort}</div>
            </div>
            <div className="text-xs text-edGray-700 flex justify-between">
              <span>جهات</span><span className="num">{num(c.organizations)}</span>
            </div>
            <div className="text-xs text-edGray-700 flex justify-between">
              <span>تحكيمات تاريخية</span><span className="num">{num(c.arbitrations)}</span>
            </div>
          </Link>
        ))}
      </div>

      <div className="text-xs text-edGray-700 border-t border-edGray-200 pt-4">
        منطق التصنيف: <span className="num">{d.logic_version || "v4"}</span> · الأرقام مطابقة عبر المشهد والجهة والمحكم ومركز النماذج.
      </div>
    </div>
  );
}

function Tile({ to, label, value, tone = "edGray", testid }) {
  const toneCls = {
    turquoise: "text-turquoise-700 border-turquoise-200 hover:border-turquoise",
    edGreen: "text-edGreen-700 border-edGreen-200 hover:border-edGreen",
    orange: "text-orange border-orange/30 hover:border-orange",
    edGray: "text-navy border-edGray-200 hover:border-turquoise",
  }[tone];
  return (
    <Link to={to} className={`block bg-white border rounded-md p-5 transition-colors ${toneCls}`} data-testid={testid}>
      <div className="stat-label">{label}</div>
      <div className={`mt-2 text-3xl font-mono font-bold ${tone === "edGray" ? "text-navy" : ""}`}>{num(value)}</div>
    </Link>
  );
}
