import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "@/lib/api";
import { num } from "@/lib/util";

const DECISION_TONE = {
  APPROVED: "border-edGreen text-edGreen-700 bg-edGreen-50",
  REJECTED: "border-edGray-200 text-edGray-700 bg-white",
  NEEDS_IMPROVEMENT: "border-orange text-orange bg-orange-50",
  PENDING: "border-orange text-orange bg-white",
};

export default function EvaluatorDetail() {
  const { name } = useParams();
  const [fams, setFams] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [versions, setVersions] = useState({});

  useEffect(() => {
    api.get(`/admin/canonical/families?evaluator=${encodeURIComponent(name)}&limit=500`)
       .then((r) => setFams(r.data));
  }, [name]);

  const toggle = async (fid) => {
    setExpanded((e) => ({ ...e, [fid]: !e[fid] }));
    if (!versions[fid]) {
      const { data } = await api.get(`/admin/canonical/families/${fid}`);
      setVersions((v) => ({ ...v, [fid]: data.versions || [] }));
    }
  };

  if (!fams) return <div className="text-edGray-700">…جارٍ التحميل</div>;

  // Group families by organization
  const byOrg = {};
  for (const f of fams.items || []) {
    const oid = f.organization_id || "unknown";
    if (!byOrg[oid]) byOrg[oid] = { org_id: oid, org_name: f.organization_name, families: [] };
    byOrg[oid].families.push(f);
  }
  const orgs = Object.values(byOrg).sort((a, b) => (a.org_name || "").localeCompare(b.org_name || ""));

  const withReview = (fams.items || []).filter((f) => f.has_review_required).length;

  return (
    <div data-testid="evaluator-detail">
      <div className="text-sm mb-3">
        <Link to="/admin/evaluators" className="text-turquoise-700 hover:underline">← المحكمون</Link>
      </div>

      <div className="border-b border-edGray-200 pb-6 mb-6">
        <div className="stat-label mb-1">محكّم</div>
        <h1 className="text-3xl font-bold" data-testid="evaluator-name">{name}</h1>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
          <Stat label="الجهات" v={orgs.length} tone="turquoise" />
          <Stat label="رحلات النماذج" v={fams.total} />
          <Stat label="تحتاج مراجعة" v={withReview} tone="orange" />
          <Stat label="أحدث المخرجات" v={fams.total} />
        </div>
      </div>

      <p className="text-sm text-edGray-700 mb-4">
        المسار: <b>المحكم</b> ← <b>الجهة</b> ← <b>رحلة النموذج</b> ← <b>النسخ</b> ← <b>القرارات</b>. الجهة تظهر مرة واحدة، والنسخ التاريخية والحالية داخل الخط الزمني.
      </p>

      {orgs.map((o) => (
        <div key={o.org_id} className="mb-6 border border-edGray-200 bg-white rounded-md" data-testid={`org-${o.org_id}`}>
          <div className="flex items-center justify-between p-4 border-b border-edGray-200 bg-ivory-100">
            <div>
              <Link to={`/admin/organizations/${o.org_id}`} className="font-semibold text-navy hover:text-turquoise-700">
                {o.org_name}
              </Link>
              <div className="text-xs num text-edGray-700 mt-1">{o.org_id}</div>
            </div>
            <div className="text-sm text-edGray-700 num">{o.families.length} رحلة</div>
          </div>
          <div className="divide-y divide-edGray-200">
            {o.families.map((f) => (
              <div key={f.family_id} className="p-3" data-testid={`fam-${f.family_id}`}>
                <div className="flex items-baseline justify-between gap-3 flex-wrap">
                  <div className="min-w-0">
                    <div className="text-navy font-medium truncate">{f.model_name}</div>
                    <div className="text-xs num text-edGray-700">{f.family_id} · {f.version_count} نسخة</div>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`pill ${DECISION_TONE[f.latest_decision || "PENDING"]}`}>{f.latest_decision_ar}</span>
                    {f.has_review_required && <span className="pill border-orange text-orange bg-orange-50">تحتاج مراجعة</span>}
                    <span className="text-xs num text-edGray-700 min-w-[85px] text-left">{(f.latest_date || "").slice(0, 10) || "—"}</span>
                    <button onClick={() => toggle(f.family_id)} className="btn-outline text-xs" data-testid={`expand-${f.family_id}`}>
                      {expanded[f.family_id] ? "طيّ" : "الخط الزمني"}
                    </button>
                    <Link to={`/admin/family/${f.family_id}`} className="text-turquoise-700 hover:underline text-xs">فتح ↗</Link>
                  </div>
                </div>
                {expanded[f.family_id] && (
                  <div className="mt-3 border-r-2 border-turquoise-200 pr-3 space-y-1.5" data-testid={`timeline-${f.family_id}`}>
                    {(versions[f.family_id] || []).map((v, i) => {
                      const evName = v.evaluator_name || "";
                      const mismatch = evName && evName !== name;
                      return (
                        <div key={v.canonical_id} className="flex items-center gap-2 text-xs">
                          <span className="text-edGray-700 num min-w-[24px]">#{i + 1}</span>
                          <span className={`pill text-xs ${v.primary_source === "current" ? "border-turquoise-200 text-turquoise-700 bg-turquoise-50" : "border-edGray-200 text-edGray-700 bg-white"}`}>
                            {v.primary_source === "current" ? "حالي" : "تاريخي"}
                          </span>
                          <span className="num text-edGray-700 min-w-[85px]">{(v.submitted_at_iso || v.arbitration_date_iso || "").slice(0, 10) || "—"}</span>
                          <span className={`pill text-xs ${DECISION_TONE[(v.decision_normalized_current || v.decision_normalized_legacy) || "PENDING"]}`}>
                            {v.decision_ar}
                          </span>
                          <span className="text-navy">{evName}</span>
                          {mismatch && (
                            <span className="pill text-[10px] border-orange text-orange bg-orange-50">تحتاج مراجعة — محكم مختلف</span>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}

      {orgs.length === 0 && <div className="text-edGray-700 text-sm py-6 text-center">لا توجد رحلات مرتبطة بهذا المحكّم</div>}
    </div>
  );
}

function Stat({ label, v, tone = "edGray" }) {
  const cls = tone === "turquoise" ? "text-turquoise-700" : tone === "orange" ? "text-orange" : "text-navy";
  return (
    <div className="border border-edGray-200 bg-white rounded-md p-3">
      <div className="stat-label">{label}</div>
      <div className={`text-2xl font-mono font-bold ${cls}`}>{num(v)}</div>
    </div>
  );
}
