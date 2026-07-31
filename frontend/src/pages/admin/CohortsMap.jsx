import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "@/lib/api";

export default function CohortsMap() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get("/admin/cohorts").then((r) => setItems(r.data)); }, []);
  const maxOrgs = Math.max(1, ...items.map((c) => c.organizations));

  return (
    <div data-testid="cohorts-page">
      <h1 className="text-3xl font-semibold mb-2">خريطة الدفعات</h1>
      <p className="text-navy/70 mb-8 max-w-2xl leading-relaxed">
        الدفعات الأربع للمسرعة. ادخل الدفعة للاطلاع على عالمها الكامل: الجهات، الأنشطة، والتحكيمات التاريخية.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="cohorts-grid">
        {items.map((c) => (
          <Link
            key={c.cohort}
            to={`/admin/cohorts/${c.cohort}`}
            className="block bg-white border border-navy/15 hover:border-turquoise p-6 transition-colors"
            data-testid={`cohort-${c.cohort}`}
          >
            <div className="flex items-baseline justify-between mb-4">
              <div>
                <div className="stat-label">الدفعة</div>
                <div className="text-4xl font-mono font-medium text-navy">{c.cohort}</div>
              </div>
              <div className="text-right">
                <div className="stat-label">الجهات</div>
                <div className="text-3xl font-mono text-turquoise">{c.organizations}</div>
              </div>
            </div>
            {/* Data-driven progress bar (no timers, no arbitrary transitions) */}
            <div className="h-1 bg-navy/10">
              <div
                className="h-1 bg-turquoise"
                style={{ width: `${(c.organizations / maxOrgs) * 100}%` }}
              />
            </div>
            <div className="grid grid-cols-3 gap-3 mt-4 text-right">
              <div>
                <div className="stat-label">أنشطة</div>
                <div className="num text-lg">{c.activities.toLocaleString("en-US")}</div>
              </div>
              <div>
                <div className="stat-label">تحكيمات</div>
                <div className="num text-lg">{c.arbitrations.toLocaleString("en-US")}</div>
              </div>
              <div>
                <div className="stat-label">خطط</div>
                <div className="num text-lg">{c.batch_plan_rows}</div>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
