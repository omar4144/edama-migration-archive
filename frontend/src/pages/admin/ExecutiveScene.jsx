import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { num } from "@/lib/util";

const SEV_STYLE = {
  HIGH: "border-orange text-orange bg-orange-50",
  MEDIUM: "border-navy/40 text-navy bg-white",
  LOW: "border-navy/25 text-navy/70 bg-white",
};

export default function ExecutiveScene() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/admin/exec/scene").then((r) => setD(r.data)); }, []);
  if (!d) return <div className="text-navy/60">…جارٍ التحميل</div>;
  const t = d.totals;

  return (
    <div data-testid="exec-scene-page">
      <div className="mb-8">
        <div className="stat-label mb-2">المشهد التنفيذي · مسرعة إدامة</div>
        <h1 className="text-3xl md:text-4xl font-semibold leading-tight">أين وصلت المسرعة اليوم؟</h1>
        <p className="text-navy/70 mt-3 max-w-3xl leading-relaxed">
          كل رقم في هذا المشهد يفتح سياقه الكامل. اتبع المسار الطبيعي:
          <span className="mx-2 num text-navy">البرنامج ← الدفعة ← المحكم/المستشار ← الجهة ← النموذج ← القرار ← الأثر</span>
        </p>
      </div>

      {/* Journey strip — clickable steps */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2 mb-10" data-testid="journey-strip">
        <Step to="/admin/cohorts" label="الدفعات" value={t.cohorts} icon="P" />
        <Arrow />
        <Step to="/admin/organizations" label="الجهات" value={t.organizations} icon="O" />
        <Arrow />
        <Step to="/admin/evaluators" label="المحكمون" value={t.evaluators} icon="M" sub={`${t.evaluators_current} حالي`} />
        <Step to="/admin/consultants" label="المستشارون" value={t.consultants} icon="C" sub={`${t.consultants_current} حالي`} />
        <Step to="/admin/models-hub" label="النماذج" value={t.models_defined} icon="F" />
      </div>

      {/* Decisions & impact — links to filtered models hub */}
      <h2 className="text-xl font-semibold mb-3">القرارات والأثر</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-10">
        <TileLink to={`/admin/models-hub?evaluation=${encodeURIComponent("مقبول")}`} label="مقبول" value={t.accepted} tone="edGreen" testid="tile-accepted" />
        <TileLink to={`/admin/models-hub?evaluation=${encodeURIComponent("يحتاج لتطوير")}`} label="يحتاج تطوير" value={t.needs_dev} tone="orange" testid="tile-needs-dev" />
        <TileLink to={`/admin/models-hub?evaluation=${encodeURIComponent("غير مكتمل")}`} label="غير مكتمل" value={t.incomplete} tone="orange" testid="tile-incomplete" />
        <TileLink to={`/admin/models-hub?source=legacy`} label="تحكيمات تاريخية" value={t.arbitrations_legacy} testid="tile-legacy-arb" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
        <TileLink to="/admin/models-hub" label="نماذج مسلّمة (حالي)" value={t.records_current} testid="tile-records-current" />
        <div className="border border-navy/15 bg-white p-5">
          <div className="stat-label">ساعات العمل والتحكيم</div>
          <div className="mt-2 flex items-baseline gap-3">
            <div className="stat-value">{num(t.hours_total, 1)}</div>
            <div className="text-xs num text-navy/60">حالي {num(t.hours_current, 1)} · قديم {num(t.hours_legacy, 1)}</div>
          </div>
        </div>
        <TileLink to={`/admin/models-hub?source=legacy&evaluation=${encodeURIComponent("غير مكتمل")}`} label="تحكيم مفتوح (تاريخي)" value={t.open_legacy} tone="orange" testid="tile-open-legacy" />
      </div>

      {/* Cohorts strip — clickable */}
      <h2 className="text-xl font-semibold mb-3">الدفعات الأربع</h2>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-10" data-testid="cohorts-mini">
        {d.cohorts.map((c) => (
          <Link key={c.cohort} to={`/admin/cohorts/${c.cohort}`} className="block bg-white border border-navy/15 hover:border-turquoise p-4" data-testid={`cohort-${c.cohort}`}>
            <div className="flex items-baseline justify-between mb-3">
              <div className="stat-label">دفعة</div>
              <div className="text-3xl font-mono">{c.cohort}</div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-right text-sm">
              <MiniRow k="جهات" v={c.organizations} />
              <MiniRow k="محكمين" v={c.evaluators} />
              <MiniRow k="مستشارين" v={c.consultants} />
              <MiniRow k="تحكيمات" v={c.arbitrations} />
            </div>
          </Link>
        ))}
      </div>

      {/* Attention list */}
      {d.attention.length > 0 && (
        <>
          <h2 className="text-xl font-semibold mb-3">يحتاج تدخّلاً الآن</h2>
          <div className="space-y-2" data-testid="attention-list">
            {d.attention.map((a, i) => (
              <Link key={i} to={a.target} className={`block border-r-4 p-4 ${SEV_STYLE[a.severity]}`} data-testid={`attention-${i}`}>
                <div className="flex items-center justify-between">
                  <span className="text-sm">{a.message}</span>
                  <span className="text-xs num opacity-60">{a.severity}</span>
                </div>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function Step({ to, label, value, icon, sub }) {
  return (
    <Link to={to} className="block bg-white border border-navy/15 hover:border-turquoise p-3 text-center" data-testid={`step-${label}`}>
      <div className="w-8 h-8 mx-auto mb-2 border-2 border-turquoise flex items-center justify-center">
        <span className="text-turquoise font-mono font-bold">{icon}</span>
      </div>
      <div className="stat-label mb-1">{label}</div>
      <div className="text-2xl font-mono text-navy">{num(value)}</div>
      {sub && <div className="text-[10px] text-navy/50 mt-1 num">{sub}</div>}
    </Link>
  );
}

function Arrow() {
  return <div className="hidden lg:flex items-center justify-center text-turquoise/40 text-xl">←</div>;
}

function TileLink({ to, label, value, tone = "navy", testid }) {
  const cls = tone === "edGreen" ? "text-edGreen" : tone === "orange" ? "text-orange" : "text-navy";
  return (
    <Link to={to} className="block border border-navy/15 bg-white hover:border-turquoise p-5" data-testid={testid}>
      <div className="stat-label">{label}</div>
      <div className={`mt-2 text-3xl font-mono font-medium ${cls}`}>{num(value)}</div>
    </Link>
  );
}

function MiniRow({ k, v }) {
  return (
    <div className="flex justify-between border-b border-navy/10 py-1">
      <span className="text-navy/60 text-xs">{k}</span>
      <span className="num">{num(v)}</span>
    </div>
  );
}
