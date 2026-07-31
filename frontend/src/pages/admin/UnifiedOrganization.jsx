import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "@/lib/api";
import { num } from "@/lib/util";

const DECISION_TONE = {
  APPROVED: "border-edGreen text-edGreen-700 bg-edGreen-50",
  REJECTED: "border-edGray-200 text-edGray-700 bg-white",
  NEEDS_IMPROVEMENT: "border-orange text-orange bg-orange-50",
  APPROVED_WITH_RESERVATION: "border-turquoise-200 text-turquoise-700 bg-turquoise-50",
  PENDING: "border-orange text-orange bg-white",
};

export default function UnifiedOrganization() {
  const { orgId } = useParams();
  const [fams, setFams] = useState(null);
  const [porg, setPorg] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [versions, setVersions] = useState({});

  useEffect(() => {
    api.get(`/admin/canonical/families?org_id=${orgId}&limit=500`).then((r) => setFams(r.data));
    api.get(`/admin/participating-orgs?q=${orgId}`).then((r) => {
      setPorg((r.data.items || []).find((x) => x.org_id === orgId));
    });
  }, [orgId]);

  const toggle = async (fid) => {
    setExpanded((e) => ({ ...e, [fid]: !e[fid] }));
    if (!versions[fid]) {
      const { data } = await api.get(`/admin/canonical/families/${fid}`);
      setVersions((v) => ({ ...v, [fid]: data.versions || [] }));
    }
  };

  if (!fams) return <div className="text-edGray-700">…جارٍ التحميل</div>;
  const orgName = fams.items?.[0]?.organization_name || porg?.canonical_name || orgId;
  const total = fams.total || 0;
  const withReview = fams.items?.filter((f) => f.has_review_required).length || 0;

  return (
    <div data-testid="unified-org">
      <div className="text-sm mb-3">
        <Link to="/admin/participating-organizations" className="text-turquoise-700 hover:underline">← سجل الجمعيات</Link>
      </div>

      <div className="border-b border-edGray-200 pb-6 mb-6">
        <h1 className="text-3xl font-bold" data-testid="org-name">{orgName}</h1>
        <div className="text-xs num text-edGray-700 mt-1">
          {orgId}
          {porg?.linked_legacy_id && ` · تاريخي: ${porg.linked_legacy_id}`}
        </div>
        {porg && (
          <div className="mt-3 flex flex-wrap gap-2 items-center">
            <ParticipationBadge status={porg.participation_review_status} />
            {porg.cohorts?.length > 0 && (
              <span className="pill border-edGray-200 text-edGray-700 bg-white">
                الدفعات: {porg.cohorts.join("، ")}
              </span>
            )}
            {porg.sources?.map((s) => (
              <span key={s} className="pill border-edGray-200 text-edGray-700 bg-white text-xs">{s}</span>
            ))}
          </div>
        )}

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
          <Stat label="رحلات النماذج" v={total} tone="turquoise" />
          <Stat label="تحتاج مراجعة" v={withReview} tone="orange" />
          <Stat label="أنواع مصادر" v={porg?.sources?.length || 0} />
          <Stat label="نسخ إجمالاً" v={porg?.versions_count || 0} />
        </div>
      </div>

      <h2 className="text-lg font-bold mb-3">رحلات النماذج (صف واحد لكل نموذج)</h2>
      <div className="border border-edGray-200 rounded-md bg-white overflow-x-auto" data-testid="families-list">
        <table className="tech-table">
          <thead>
            <tr>
              <th>النموذج</th>
              <th>آخر قرار</th>
              <th>حالة الاكتمال</th>
              <th>عدد النسخ</th>
              <th>المحكم الأحدث</th>
              <th>آخر تاريخ</th>
              <th>حالة المراجعة</th>
              <th>الرابط الأحدث</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(fams.items || []).map((f) => (
              <React.Fragment key={f.family_id}>
                <tr className="hover:bg-turquoise-50/40" data-testid={`fam-row-${f.family_id}`}>
                  <td className="text-sm">
                    <div className="text-navy">{f.model_name}</div>
                    <div className="text-xs num text-edGray-700">{f.family_id}</div>
                  </td>
                  <td>
                    <span className={`pill ${DECISION_TONE[f.latest_decision || "PENDING"]}`}>
                      {f.latest_decision_ar}
                    </span>
                  </td>
                  <td className="text-xs">{f.latest_completion_status || "—"}</td>
                  <td className="num">{f.version_count}</td>
                  <td className="text-sm">{f.latest_evaluator_name || "—"}</td>
                  <td className="text-xs num text-edGray-700">{(f.latest_date || "").slice(0, 10) || "—"}</td>
                  <td>
                    {f.has_review_required
                      ? <span className="pill border-orange text-orange bg-orange-50">تحتاج مراجعة</span>
                      : <span className="text-xs text-edGreen-700">مؤكدة</span>}
                  </td>
                  <td>
                    <Link to={`/admin/family/${f.family_id}`} className="text-turquoise-700 hover:underline text-sm" data-testid={`open-fam-${f.family_id}`}>
                      فتح الرحلة ↗
                    </Link>
                  </td>
                  <td>
                    <button onClick={() => toggle(f.family_id)} className="btn-outline text-xs" data-testid={`expand-${f.family_id}`}>
                      {expanded[f.family_id] ? "طيّ" : "توسيع"}
                    </button>
                  </td>
                </tr>
                {expanded[f.family_id] && (
                  <tr className="bg-ivory-100">
                    <td colSpan={9} className="px-4 py-3">
                      <div className="text-xs text-edGray-700 mb-2">خط زمني للنسخ (صعوديًا):</div>
                      <div className="space-y-2">
                        {(versions[f.family_id] || []).map((v, i) => (
                          <div key={v.canonical_id} className="flex items-center gap-3 text-sm border-r-2 border-turquoise-200 pr-3">
                            <span className="stat-label">#{i + 1}</span>
                            <span className={`pill text-xs ${v.primary_source === "current" ? "border-turquoise-200 text-turquoise-700 bg-turquoise-50" : "border-edGray-200 text-edGray-700 bg-white"}`}>
                              {v.primary_source === "current" ? "حالي" : "تاريخي"}
                            </span>
                            <span className="text-xs num text-edGray-700 min-w-[85px]">{(v.submitted_at_iso || v.arbitration_date_iso || "").slice(0, 10) || "—"}</span>
                            <span className={`pill text-xs ${DECISION_TONE[(v.decision_normalized_current || v.decision_normalized_legacy) || "PENDING"]}`}>
                              {v.decision_ar || "—"}
                            </span>
                            <span className="text-xs text-edGray-700">{v.evaluator_name || "—"}</span>
                            {v.url && (
                              <a href={v.url} target="_blank" rel="noopener noreferrer" className="text-turquoise-700 hover:underline text-xs">
                                رابط ↗
                              </a>
                            )}
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
            {total === 0 && <tr><td colSpan={9} className="text-center text-edGray-700 py-6">لا توجد رحلات نماذج لهذه الجهة</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ParticipationBadge({ status }) {
  const map = {
    CONFIRMED_PARTICIPANT: { ar: "مشاركة مؤكدة", cls: "border-edGreen text-edGreen-700 bg-edGreen-50" },
    PENDING_REVIEW: { ar: "تحتاج مراجعة", cls: "border-orange text-orange bg-orange-50" },
    EXCLUDED: { ar: "مستبعدة", cls: "border-edGray-200 text-edGray-700 bg-white" },
    WITHDRAWN: { ar: "منسحبة", cls: "border-edGray-200 text-edGray-700 bg-white" },
    REPLACED: { ar: "استبدلت", cls: "border-edGray-200 text-edGray-700 bg-white" },
    DUPLICATE_CANDIDATE: { ar: "مشتبه تكرارها", cls: "border-orange text-orange bg-orange-50" },
  }[status] || { ar: status, cls: "border-edGray-200 text-edGray-700 bg-white" };
  return <span className={`pill ${map.cls}`}>{map.ar}</span>;
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
