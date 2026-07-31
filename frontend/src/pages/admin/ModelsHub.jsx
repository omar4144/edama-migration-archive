import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import { num, resolveUrl, sourceBadge, evaluationTone } from "@/lib/util";
import { ExternalLink } from "lucide-react";

export default function ModelsHub() {
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState({ items: [], total: 0, total_current: 0, total_legacy: 0 });
  const [detail, setDetail] = useState(null);
  const [offset, setOffset] = useState(0);
  const limit = 50;

  const f = {
    q: params.get("q") || "",
    evaluation: params.get("evaluation") || "",
    category: params.get("category") || "",
    source: params.get("source") || "",
    cohort: params.get("cohort") || "",
    no_url: params.get("no_url") === "true",
  };
  const update = (k, v) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v); else next.delete(k);
    setOffset(0);
    setParams(next);
  };

  useEffect(() => {
    const p = new URLSearchParams({ limit, offset });
    if (f.q) p.append("q", f.q);
    if (f.evaluation) p.append("evaluation", f.evaluation);
    if (f.category) p.append("category", f.category);
    if (f.source) p.append("source", f.source);
    if (f.cohort) p.append("cohort", f.cohort);
    if (f.no_url) p.append("no_url", "true");
    api.get(`/admin/models-hub?${p}`).then((r) => setData(r.data));
    // eslint-disable-next-line
  }, [params.toString(), offset]);

  const openDetail = async (id) => {
    const { data } = await api.get(`/admin/models-hub/${encodeURIComponent(id)}`);
    setDetail(data);
  };

  return (
    <div data-testid="models-hub">
      <h1 className="text-3xl font-semibold mb-2">النماذج والتحكيمات</h1>
      <p className="text-navy/70 mb-6">مركز موحّد للبحث. المصدر شارة داخل التفاصيل، وليس فلترًا رئيسيًا.</p>

      <div className="flex gap-2 flex-wrap mb-4" data-testid="filters">
        <input className="field-input w-64" placeholder="بحث في الجهة أو النموذج…" value={f.q} onChange={(e) => update("q", e.target.value)} data-testid="filter-q" />
        <select className="field-input w-auto" value={f.evaluation} onChange={(e) => update("evaluation", e.target.value)} data-testid="filter-evaluation">
          <option value="">كل القرارات</option>
          <option value="مقبول">مقبول</option>
          <option value="يحتاج لتطوير">يحتاج لتطوير</option>
          <option value="غير مكتمل">غير مكتمل</option>
          <option value="مجاز">مجاز</option>
        </select>
        <select className="field-input w-auto" value={f.category} onChange={(e) => update("category", e.target.value)} data-testid="filter-category">
          <option value="">كل الفئات</option>
          <option value="نماذج المستشار">نماذج المستشار</option>
          <option value="نماذج المنظمة">نماذج المنظمة</option>
          <option value="نماذج المسرعة">نماذج المسرعة</option>
        </select>
        <select className="field-input w-auto" value={f.cohort} onChange={(e) => update("cohort", e.target.value)} data-testid="filter-cohort">
          <option value="">كل الدفعات</option>
          <option value="1">دفعة 1</option>
          <option value="2">دفعة 2</option>
          <option value="3">دفعة 3</option>
          <option value="4">دفعة 4</option>
        </select>
        <select className="field-input w-auto" value={f.source} onChange={(e) => update("source", e.target.value)} data-testid="filter-source">
          <option value="">حالي وتاريخي</option>
          <option value="current">حالي فقط</option>
          <option value="legacy">تاريخي فقط</option>
        </select>
        <label className="flex items-center gap-2 text-sm border border-navy/25 px-3">
          <input type="checkbox" checked={f.no_url} onChange={(e) => update("no_url", e.target.checked ? "true" : "")} data-testid="filter-no-url" />
          بدون رابط
        </label>
      </div>

      <div className="text-sm text-navy/60 mb-2 num" data-testid="total-info">
        {data.total.toLocaleString("en-US")} نتيجة · حالي {data.total_current.toLocaleString("en-US")} · تاريخي {data.total_legacy.toLocaleString("en-US")}
      </div>

      <div className="border border-navy/15 bg-white overflow-x-auto">
        <table className="tech-table" data-testid="models-table">
          <thead>
            <tr>
              <th>النموذج</th><th>الجهة</th><th>الدفعة</th><th>المحكم</th><th>المستشار</th><th>القرار</th><th>الحالة</th><th>الساعات</th><th>الرابط</th><th></th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((r) => {
              const url = resolveUrl(r);
              const src = sourceBadge(r.source);
              return (
                <tr key={r.id} className="hover:bg-ivory-100 cursor-pointer" onClick={() => openDetail(r.id)} data-testid={`row-${r.id}`}>
                  <td className="text-sm">
                    <span className="text-navy">{r.model_name || "—"}</span>
                    <div className="text-xs num text-navy/50 flex items-center gap-1">
                      <span>{r.id}</span>
                      <span className={`pill border text-[10px] ${src.cls}`}>{src.label}</span>
                    </div>
                  </td>
                  <td className="text-sm">
                    {r.organization_id ? (
                      <Link to={`/admin/organizations/${r.organization_id}`} className="hover:text-turquoise" onClick={(e) => e.stopPropagation()}>
                        {r.organization_name}
                      </Link>
                    ) : r.organization_name}
                  </td>
                  <td className="num">{r.cohort || "—"}</td>
                  <td className="text-xs">
                    {r.evaluator_name ? (
                      <Link to={`/admin/evaluators/${encodeURIComponent(r.evaluator_name)}`} className="hover:text-turquoise" onClick={(e) => e.stopPropagation()}>
                        {r.evaluator_name}
                      </Link>
                    ) : "—"}
                  </td>
                  <td className="text-xs">
                    {r.consultant_name ? (
                      <Link to={`/admin/consultants/${encodeURIComponent(r.consultant_name)}`} className="hover:text-turquoise" onClick={(e) => e.stopPropagation()}>
                        {r.consultant_name}
                      </Link>
                    ) : "—"}
                  </td>
                  <td className={`text-sm ${evaluationTone(r.evaluation)}`}>{r.evaluation || "—"}</td>
                  <td className="text-xs">{r.status || "—"}</td>
                  <td className="num">{r.work_hours ?? "—"}</td>
                  <td>
                    {url ? (
                      <a href={url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} className="inline-flex items-center gap-1 text-turquoise-600 hover:underline text-sm" data-testid={`open-${r.id}`}>
                        فتح <ExternalLink size={11} />
                      </a>
                    ) : <span className="text-xs text-navy/40">—</span>}
                  </td>
                  <td className="text-left"><button className="btn-outline text-xs" onClick={(e) => { e.stopPropagation(); openDetail(r.id); }} data-testid={`detail-${r.id}`}>تفاصيل</button></td>
                </tr>
              );
            })}
            {data.items.length === 0 && <tr><td colSpan={10} className="text-center text-navy/50 py-6">لا نتائج</td></tr>}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-4 text-sm">
        <div className="text-navy/60 num">{data.total > 0 ? `${offset + 1}–${Math.min(offset + limit, data.total)} من ${data.total.toLocaleString("en-US")}` : "—"}</div>
        <div className="flex gap-2">
          <button className="btn-outline text-sm disabled:opacity-40" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - limit))} data-testid="prev-page">السابق</button>
          <button className="btn-outline text-sm disabled:opacity-40" disabled={offset + limit >= data.total} onClick={() => setOffset(offset + limit)} data-testid="next-page">التالي</button>
        </div>
      </div>

      {detail && <RecordPanel r={detail} onClose={() => setDetail(null)} />}
    </div>
  );
}

function RecordPanel({ r, onClose }) {
  const url = resolveUrl(r);
  const src = sourceBadge(r.source);
  return (
    <div className="fixed inset-0 bg-navy/40 flex items-center justify-center p-4 z-50" onClick={onClose} data-testid="record-panel">
      <div className="bg-white border border-navy/20 max-w-2xl w-full max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="px-6 py-4 border-b border-navy/10 flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className={`pill border ${src.cls}`}>{src.label}</span>
              <span className="num text-xs text-navy/50">{r.id}</span>
            </div>
            <h3 className="text-lg font-semibold">{r.model_name}</h3>
            <div className="text-sm text-navy/70">{r.organization_name}</div>
          </div>
          <button className="btn-outline text-sm" onClick={onClose} data-testid="detail-close">إغلاق</button>
        </div>
        <div className="px-6 py-4 space-y-2 text-sm">
          <Row k="الفئة" v={r.category} />
          <Row k="المحكم" v={r.evaluator_name} link={r.evaluator_name ? `/admin/evaluators/${encodeURIComponent(r.evaluator_name)}` : null} />
          <Row k="المستشار" v={r.consultant_name} link={r.consultant_name ? `/admin/consultants/${encodeURIComponent(r.consultant_name)}` : null} />
          <Row k="الحالة" v={r.status} />
          <Row k="القرار" v={r.evaluation} tone={evaluationTone(r.evaluation)} />
          <Row k="الساعات" v={r.work_hours} mono />
          <Row k="تاريخ الإرسال" v={(r.submitted_at || "").slice(0,19)} mono />
          <Row k="تاريخ القرار" v={(r.decided_at || "").slice(0,19)} mono />
          <Row k="ملاحظات" v={r.notes} />
          <Row k="الجهة" v={r.organization_name} link={r.organization_id ? `/admin/organizations/${r.organization_id}` : null} />
          <Row k="الدفعة" v={r.cohort} mono />
          {r.duplicate_link_group_id && (
            <Row k="مجموعة تكرار" v={`${r.duplicate_link_group_id} · استخدامات ${r.duplicate_use_count}`} mono />
          )}
          <Row k="التحقق الآلي" v={r.verification_status} />
        </div>
        <div className="px-6 py-4 border-t border-navy/10 flex items-center justify-between">
          <div className="text-xs num text-navy/50">
            {r.raw_source?.file || ""} {r.raw_source?.sheet ? `· ${r.raw_source.sheet}` : ""}
          </div>
          {url ? (
            <a href={url} target="_blank" rel="noopener noreferrer" className="btn-primary text-sm" data-testid="detail-open-url">
              فتح النموذج ↗
            </a>
          ) : <span className="text-xs text-navy/50">الرابط غير متوفر</span>}
        </div>
      </div>
    </div>
  );
}

function Row({ k, v, mono, tone, link }) {
  if (v == null || v === "") v = "—";
  const cls = `${tone || ""} ${mono ? "num" : ""}`.trim();
  return (
    <div className="flex justify-between border-b border-navy/10 pb-1.5">
      <span className="text-navy/60">{k}</span>
      {link && v !== "—"
        ? <Link to={link} className={`${cls} hover:text-turquoise`}>{v}</Link>
        : <span className={cls}>{v}</span>}
    </div>
  );
}
