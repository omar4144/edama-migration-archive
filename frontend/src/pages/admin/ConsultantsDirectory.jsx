import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";
import { num } from "@/lib/util";

export default function ConsultantsDirectory() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  useEffect(() => { api.get("/admin/directory/consultants").then((r) => setItems(r.data)); }, []);
  const filtered = q ? items.filter((e) => e.name.toLowerCase().includes(q.toLowerCase())) : items;

  return (
    <div data-testid="consultants-directory">
      <h1 className="text-3xl font-semibold mb-2">المستشارون</h1>
      <p className="text-navy/70 mb-6">دليل موحّد لجميع المستشارين — الحاليون والتاريخيون. اضغط اسم لفتح ملفه الكامل.</p>

      <div className="mb-4">
        <input className="field-input w-64" placeholder="بحث بالاسم…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="cons-search" />
      </div>

      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="consultants-table">
          <thead>
            <tr><th>الاسم</th><th>الدفعات</th><th>نماذج حالية</th><th>أنشطة تاريخية</th><th>الجهات</th><th>الساعات</th><th>الحساب</th></tr>
          </thead>
          <tbody>
            {filtered.map((e) => (
              <tr key={e.name} className="hover:bg-ivory-100">
                <td>
                  <Link to={`/admin/consultants/${encodeURIComponent(e.name)}`} className="text-navy font-medium hover:text-turquoise" data-testid={`cons-${e.name}`}>
                    {e.name}
                  </Link>
                </td>
                <td className="num text-xs">{e.legacy_cohorts.length > 0 ? e.legacy_cohorts.join("، ") : "—"}</td>
                <td className="num">{num(e.current_records)}</td>
                <td className="num">{num(e.legacy_activities)}</td>
                <td className="num">{num(e.current_orgs)}</td>
                <td className="num">{num(e.current_hours, 1)}</td>
                <td>{e.has_current_account
                  ? <span className="text-xs text-edGreen">حساب مربوط</span>
                  : <span className="text-xs text-navy/50">تاريخي فقط</span>}</td>
              </tr>
            ))}
            {filtered.length === 0 && <tr><td colSpan={7} className="text-center text-navy/50 py-6">لا يوجد نتائج</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
