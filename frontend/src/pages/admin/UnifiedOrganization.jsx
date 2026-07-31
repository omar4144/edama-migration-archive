import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "@/lib/api";
import { num, resolveUrl, sourceBadge, evaluationTone } from "@/lib/util";
import { ExternalLink } from "lucide-react";

export default function UnifiedOrganization() {
  const { orgId } = useParams();
  const [d, setD] = useState(null);
  const [expandedCat, setExpandedCat] = useState({});

  useEffect(() => { api.get(`/admin/unified/organizations/${orgId}`).then((r) => setD(r.data)); }, [orgId]);
  if (!d) return <div className="text-navy/60">…جارٍ التحميل</div>;

  const h = d.header;
  const t = d.totals;
  const byCategory = d.records.reduce((acc, r) => {
    const k = r.category || "بدون فئة";
    (acc[k] = acc[k] || []).push(r);
    return acc;
  }, {});

  return (
    <div data-testid="unified-org">
      <div className="text-sm mb-3">
        <Link to="/admin/organizations" className="text-turquoise-600 hover:underline">← الجهات</Link>
      </div>

      {/* Header */}
      <div className="border-b border-navy/15 pb-6 mb-8">
        <h1 className="text-3xl font-semibold" data-testid="org-name">{h.organization_name}</h1>
        <div className="text-xs num text-navy/50 mt-1 flex items-center gap-3 flex-wrap">
          <span>{h.org_id}</span>
          {h.linked_legacy_id && h.linked_legacy_id !== h.org_id && <span>· تاريخي: {h.linked_legacy_id}</span>}
          {h.match_status && <span className={`pill border ${h.match_status === "PROBABLE_NAME_VARIANT" ? "border-orange text-orange" : "border-edGreen text-edGreen"}`}>{h.match_status}</span>}
        </div>

        {/* Journey strip */}
        <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mt-6" data-testid="org-journey-strip">
          <Cell label="الدفعة" v={h.cohort} mono />
          <Cell label="القطاع" v={h.sector} />
          <Cell label="المنطقة" v={h.region} />
          <Cell label="المحكم" v={h.evaluator} link={h.evaluator ? `/admin/evaluators/${encodeURIComponent(h.evaluator.split(",")[0].trim())}` : null} />
          <Cell label="المستشار" v={h.consultants.join("، ") || "—"} />
          <Cell label="حالة" v={h.roster_status} />
        </div>
      </div>

      {/* Impact strip */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-8" data-testid="impact-strip">
        <Stat label="النماذج" v={t.records} />
        <Stat label="حالي" v={t.current} />
        <Stat label="تحكيمات تاريخية" v={t.legacy_arbitrations} />
        <Stat label="أنشطة تاريخية" v={t.legacy_activities} />
        <Stat label="مقبول" v={t.accepted} tone="text-edGreen" />
        <Stat label="ساعات" v={t.hours} digits={1} />
      </div>
      {(t.needs_dev + t.incomplete) > 0 && (
        <div className="mb-8 border-r-4 border-orange bg-orange-50 px-4 py-3 text-sm" data-testid="attention-inline">
          يحتاج تدخّل: <span className="num">{t.needs_dev}</span> نموذج بحاجة تطوير · <span className="num">{t.incomplete}</span> غير مكتمل
        </div>
      )}

      {/* Records grouped by category */}
      {Object.entries(byCategory).map(([cat, rows]) => {
        const open = expandedCat[cat] !== false;
        const accepted = rows.filter((r) => r.evaluation === "مقبول").length;
        return (
          <div key={cat} className="border border-navy/15 bg-white mb-4" data-testid={`cat-${cat}`}>
            <button
              className="w-full flex items-center justify-between px-4 py-3 border-b border-navy/10 bg-ivory-100 hover:bg-ivory"
              onClick={() => setExpandedCat({ ...expandedCat, [cat]: !open })}
            >
              <div className="text-right">
                <div className="font-medium">{cat}</div>
                <div className="text-xs text-navy/60 num">{rows.length} نموذج · مقبول {accepted}</div>
              </div>
              <span className="text-navy/40 text-lg">{open ? "−" : "+"}</span>
            </button>
            {open && (
              <table className="tech-table">
                <thead>
                  <tr><th>النموذج</th><th>القرار</th><th>الحالة</th><th>الساعات</th><th>التاريخ</th><th>المصدر</th><th>الرابط</th></tr>
                </thead>
                <tbody>
                  {rows.map((r) => {
                    const url = resolveUrl(r);
                    const src = sourceBadge(r.source);
                    return (
                      <tr key={r.id}>
                        <td className="text-sm">
                          <div>{r.model_name || "—"}</div>
                          <div className="text-xs num text-navy/50">{r.id}</div>
                        </td>
                        <td className={`text-sm ${evaluationTone(r.evaluation)}`}>{r.evaluation || "—"}</td>
                        <td className="text-sm">{r.status || "—"}</td>
                        <td className="num">{r.work_hours ?? "—"}</td>
                        <td className="text-xs num text-navy/60">{(r.decided_at || r.submitted_at || "").slice(0,10) || "—"}</td>
                        <td><span className={`pill border ${src.cls}`}>{src.label}</span></td>
                        <td>
                          {url ? (
                            <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-turquoise-600 hover:underline text-sm" data-testid={`open-${r.id}`}>
                              فتح ↗
                            </a>
                          ) : <span className="text-xs text-navy/40">—</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        );
      })}
    </div>
  );
}

function Cell({ label, v, mono, link }) {
  return (
    <div className="border border-navy/15 bg-white p-3">
      <div className="stat-label mb-1">{label}</div>
      {link && v ? (
        <Link to={link} className={`${mono ? "num" : ""} text-navy hover:text-turquoise`}>{v}</Link>
      ) : (
        <div className={`${mono ? "num" : "text-sm"}`}>{v ?? "—"}</div>
      )}
    </div>
  );
}
function Stat({ label, v, tone = "text-navy", digits = 0 }) {
  return (
    <div className="border border-navy/15 bg-white p-3">
      <div className="stat-label">{label}</div>
      <div className={`text-2xl font-mono ${tone}`}>{num(v, digits)}</div>
    </div>
  );
}
