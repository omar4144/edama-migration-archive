import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "@/lib/api";
import { num } from "@/lib/util";

export default function ConsultantDetail() {
  const { name } = useParams();
  const [d, setD] = useState(null);
  useEffect(() => { api.get(`/admin/directory/consultants/${encodeURIComponent(name)}`).then((r) => setD(r.data)); }, [name]);
  if (!d) return <div className="text-navy/60">…جارٍ التحميل</div>;
  const t = d.totals;
  return (
    <div data-testid="consultant-detail">
      <div className="text-sm mb-3"><Link to="/admin/consultants" className="text-turquoise-600 hover:underline">← المستشارون</Link></div>
      <div className="border-b border-navy/15 pb-6 mb-8">
        <h1 className="text-3xl font-semibold" data-testid="cons-name">{d.name}</h1>
        {d.has_current_account
          ? <div className="text-xs text-edGreen num mt-1">حساب مربوط · {d.person_id}</div>
          : <div className="text-xs text-navy/50 mt-1">تاريخي — لا يوجد حساب حالي</div>}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-6">
          <Stat label="الجهات" v={t.orgs} />
          <Stat label="نماذج حالية" v={t.current_records} />
          <Stat label="أنشطة تاريخية" v={t.legacy_activities} />
          <Stat label="الساعات" v={t.hours} digits={1} />
          <Stat label="الدفعات" v={t.cohorts_participated.length} sub={t.cohorts_participated.join("، ") || "—"} />
        </div>
      </div>

      {d.current.orgs.length > 0 && (
        <>
          <h2 className="text-xl font-semibold mb-3">الحالي — الجهات</h2>
          <div className="border border-navy/15 bg-white overflow-x-auto mb-8">
            <table className="tech-table">
              <thead><tr><th>الجهة</th><th>نماذج</th><th>مقبول</th><th>تطوير</th><th>ساعات</th></tr></thead>
              <tbody>
                {d.current.orgs.map((o) => (
                  <tr key={o.org_id}>
                    <td><Link to={`/admin/organizations/${o.org_id}`} className="text-navy hover:text-turquoise" data-testid={`cons-org-${o.org_id}`}>{o.organization_name}</Link></td>
                    <td className="num">{o.models}</td>
                    <td className="num text-edGreen">{o.accepted}</td>
                    <td className="num text-orange">{o.needs_dev}</td>
                    <td className="num">{num(o.hours, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {d.legacy_by_cohort.map((c) => (
        <div key={c.cohort} className="mb-6 border border-navy/15 bg-white">
          <div className="px-4 py-3 border-b border-navy/10 bg-ivory-100 flex items-center gap-6 text-sm">
            <span className="font-medium">دفعة <span className="num">{c.cohort}</span></span>
            <span><span className="stat-label">أنشطة</span> <span className="num">{c.activities}</span></span>
            <span><span className="stat-label">جهات</span> <span className="num">{c.orgs}</span></span>
          </div>
          <div className="grid md:grid-cols-2 divide-x divide-navy/10">
            <div className="p-4">
              <div className="stat-label mb-2">حالات الإنجاز</div>
              {Object.entries(c.completion).map(([k,v]) => (
                <div key={k} className="flex justify-between text-sm border-b border-navy/10 py-1">
                  <span>{k}</span><span className="num">{v}</span>
                </div>
              ))}
            </div>
            <div className="p-4">
              <div className="stat-label mb-2">المراحل</div>
              {Object.entries(c.stages).slice(0, 8).map(([k,v]) => (
                <div key={k} className="flex justify-between text-sm border-b border-navy/10 py-1">
                  <span className="truncate">{k}</span><span className="num">{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
function Stat({ label, v, digits=0, sub }) {
  return <div><div className="stat-label">{label}</div><div className="stat-value">{num(v, digits)}</div>{sub && <div className="text-xs text-navy/50 mt-1">{sub}</div>}</div>;
}
