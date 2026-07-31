import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { num } from "@/lib/util";

export default function UnifiedOrganizations() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [cohort, setCohort] = useState("");

  useEffect(() => {
    const p = new URLSearchParams();
    if (q) p.append("q", q);
    if (cohort) p.append("cohort", cohort);
    api.get(`/admin/unified/organizations?${p}`).then((r) => setItems(r.data));
  }, [q, cohort]);

  return (
    <div data-testid="unified-orgs">
      <h1 className="text-3xl font-semibold mb-2">الجهات</h1>
      <p className="text-navy/70 mb-6">
        سجل موحّد لكل جهة — يجمع بيانات Lovable الحالية مع سجلها التاريخي عبر مطابقة معتمدة. المصدر شارة داخل التفاصيل.
      </p>

      <div className="flex gap-3 mb-4 flex-wrap">
        <input className="field-input w-64" placeholder="بحث بالاسم…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="org-search" />
        <select className="field-input w-auto" value={cohort} onChange={(e) => setCohort(e.target.value)} data-testid="org-cohort">
          <option value="">كل الدفعات</option>
          {["1","2","3","4"].map((c) => <option key={c} value={c}>دفعة {c}</option>)}
        </select>
      </div>

      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="orgs-table">
          <thead>
            <tr><th>الجهة</th><th>الدفعة</th><th>القطاع</th><th>المحكم</th><th>سجلات حالية</th><th>ساعات</th><th></th></tr>
          </thead>
          <tbody>
            {items.map((o) => (
              <tr key={o.org_id} className="hover:bg-ivory-100">
                <td>
                  <Link to={`/admin/organizations/${o.org_id}`} className="text-navy font-medium hover:text-turquoise" data-testid={`org-${o.org_id}`}>
                    {o.organization_name}
                  </Link>
                  <div className="text-xs num text-navy/50">{o.org_id}{o.source === "legacy_only" && " · تاريخي فقط"}</div>
                </td>
                <td className="num">{o.cohort || "—"}</td>
                <td className="text-xs">{o.sector || "—"}</td>
                <td className="text-xs">{o.evaluator || "—"}</td>
                <td className="num">{num(o.records)}</td>
                <td className="num">{o.hours != null ? num(o.hours, 1) : "—"}</td>
                <td className="text-left">
                  <Link to={`/admin/organizations/${o.org_id}`} className="btn-outline text-xs">فتح</Link>
                </td>
              </tr>
            ))}
            {items.length === 0 && <tr><td colSpan={7} className="text-center text-navy/50 py-6">لا يوجد جهات</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
