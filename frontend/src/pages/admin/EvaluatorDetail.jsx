import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "@/lib/api";
import { num, resolveUrl, sourceBadge, evaluationTone } from "@/lib/util";
import { ExternalLink } from "lucide-react";

export default function EvaluatorDetail() {
  const { name } = useParams();
  const [d, setD] = useState(null);
  const [expandOrg, setExpandOrg] = useState(null);
  const [orgModels, setOrgModels] = useState({});

  useEffect(() => {
    api.get(`/admin/directory/evaluators/${encodeURIComponent(name)}`).then((r) => setD(r.data));
  }, [name]);

  const toggleOrg = async (orgId) => {
    if (expandOrg === orgId) { setExpandOrg(null); return; }
    setExpandOrg(orgId);
    if (!orgModels[orgId]) {
      const { data } = await api.get(`/admin/directory/evaluators/${encodeURIComponent(name)}/organization/${orgId}`);
      setOrgModels((m) => ({ ...m, [orgId]: data }));
    }
  };

  if (!d) return <div className="text-navy/60">…جارٍ التحميل</div>;
  const t = d.totals;

  return (
    <div data-testid="evaluator-detail">
      <div className="text-sm mb-3">
        <Link to="/admin/evaluators" className="text-turquoise-600 hover:underline">← المحكمون</Link>
      </div>

      <div className="border-b border-navy/15 pb-6 mb-8">
        <div className="flex items-baseline justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-3xl font-semibold" data-testid="evaluator-name">{d.name}</h1>
            {d.has_current_account ? (
              <div className="text-xs text-edGreen num mt-1">حساب مربوط · {d.person_id}</div>
            ) : (
              <div className="text-xs text-navy/50 mt-1">تاريخي — لا يوجد حساب حالي</div>
            )}
          </div>
          <div className="text-xs num text-navy/60">دفعات: {t.cohorts_participated.join("، ") || "—"}</div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mt-6" data-testid="eval-totals">
          <Stat label="الجهات" v={t.orgs} />
          <Stat label="النماذج والتحكيمات" v={t.arbitrations} />
          <Stat label="حالي" v={t.current_records} />
          <Stat label="تاريخي" v={t.legacy_arbitrations} />
          <Stat label="الساعات" v={t.hours} digits={1} />
          <Stat label="القرارات" v={Object.keys(d.decisions).length} sub={Object.entries(d.decisions).slice(0,2).map(([k,v])=>`${k}: ${v}`).join(" · ")} />
        </div>
      </div>

      {/* Current bucket */}
      {d.current.orgs.length > 0 && (
        <>
          <h2 className="text-xl font-semibold mb-3">الحالي — الجهات المسندة</h2>
          <div className="border border-navy/15 bg-white mb-8">
            {d.current.orgs.map((o) => (
              <div key={o.org_id} className="border-b border-navy/10 last:border-b-0">
                <button className="w-full flex items-center justify-between px-4 py-3 hover:bg-ivory-100" onClick={() => toggleOrg(o.org_id)} data-testid={`org-${o.org_id}`}>
                  <div className="text-right">
                    <Link to={`/admin/organizations/${o.org_id}`} className="text-navy font-medium hover:text-turquoise" onClick={(e) => e.stopPropagation()}>
                      {o.organization_name}
                    </Link>
                    <div className="text-xs num text-navy/50">{o.org_id}</div>
                  </div>
                  <div className="flex items-center gap-6 text-sm">
                    <span><span className="stat-label">نماذج</span> <span className="num">{o.models}</span></span>
                    <span><span className="stat-label">مقبول</span> <span className="num text-edGreen">{o.accepted}</span></span>
                    <span><span className="stat-label">تطوير</span> <span className="num text-orange">{o.needs_dev}</span></span>
                    <span><span className="stat-label">ساعات</span> <span className="num">{num(o.hours,1)}</span></span>
                  </div>
                </button>
                {expandOrg === o.org_id && orgModels[o.org_id] && (
                  <div className="bg-ivory-100 px-4 py-3">
                    <ModelList items={orgModels[o.org_id]} testid={`models-${o.org_id}`} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}

      {/* Legacy by cohort */}
      {d.legacy_by_cohort.map((c) => (
        <div key={c.cohort} className="mb-8">
          <h2 className="text-xl font-semibold mb-3">دفعة <span className="num">{c.cohort}</span> — تاريخي</h2>
          <div className="border border-navy/15 bg-white">
            <div className="px-4 py-3 border-b border-navy/10 flex items-center gap-6 text-sm bg-ivory-100">
              <span><span className="stat-label">جهات</span> <span className="num">{c.orgs.length}</span></span>
              <span><span className="stat-label">تحكيمات</span> <span className="num">{c.arbitrations}</span></span>
              <span><span className="stat-label">ساعات</span> <span className="num">{num(c.hours,1)}</span></span>
              <span className="text-xs text-navy/60">القرارات: {Object.entries(c.decisions).map(([k,v])=>`${k}: ${v}`).join(" · ")}</span>
            </div>
            {c.orgs.map((o) => (
              <div key={o.org_id} className="border-b border-navy/10 last:border-b-0">
                <button className="w-full flex items-center justify-between px-4 py-3 hover:bg-ivory-100" onClick={() => toggleOrg(o.org_id)} data-testid={`legorg-${o.org_id}`}>
                  <div className="text-right">
                    <Link to={`/admin/organizations/${o.org_id}`} className="text-navy hover:text-turquoise" onClick={(e) => e.stopPropagation()}>
                      {o.organization_name}
                    </Link>
                    <div className="text-xs num text-navy/50">{o.org_id}</div>
                  </div>
                  <div className="text-sm"><span className="stat-label">نماذج</span> <span className="num">{o.models}</span></div>
                </button>
                {expandOrg === o.org_id && orgModels[o.org_id] && (
                  <div className="bg-ivory-100 px-4 py-3">
                    <ModelList items={orgModels[o.org_id]} testid={`legmodels-${o.org_id}`} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

export function ModelList({ items, testid }) {
  if (!items || items.length === 0) return <div className="text-sm text-navy/50">لا توجد نماذج</div>;
  return (
    <table className="tech-table" data-testid={testid}>
      <thead>
        <tr><th>النموذج</th><th>القرار</th><th>الحالة</th><th>الساعات</th><th>التاريخ</th><th>المصدر</th><th>الرابط</th></tr>
      </thead>
      <tbody>
        {items.map((m) => {
          const url = resolveUrl(m);
          const src = sourceBadge(m.source);
          return (
            <tr key={m.id}>
              <td className="text-sm">{m.model_name || "—"}</td>
              <td className={`text-sm ${evaluationTone(m.evaluation)}`}>{m.evaluation || "—"}</td>
              <td className="text-sm">{m.status || "—"}</td>
              <td className="num">{m.work_hours ?? "—"}</td>
              <td className="text-xs num text-navy/60">{(m.decided_at || m.submitted_at || "").slice(0,10) || "—"}</td>
              <td><span className={`pill border ${src.cls}`}>{src.label}</span></td>
              <td>
                {url ? (
                  <a href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-turquoise-600 hover:underline text-sm" data-testid={`open-${m.id}`}>
                    فتح النموذج <ExternalLink size={12} />
                  </a>
                ) : <span className="text-xs text-navy/40">الرابط غير متوفر</span>}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function Stat({ label, v, digits = 0, sub }) {
  return (
    <div>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{num(v, digits)}</div>
      {sub && <div className="text-xs text-navy/50 mt-1">{sub}</div>}
    </div>
  );
}
