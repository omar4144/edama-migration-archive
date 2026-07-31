import React, { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { num } from "@/lib/util";

const STATUS_OPTIONS = [
  { k: "PENDING_REVIEW", ar: "تحتاج مراجعة", tone: "orange" },
  { k: "CONFIRMED_PARTICIPANT", ar: "مشاركة مؤكدة", tone: "edGreen" },
  { k: "EXCLUDED", ar: "مستبعدة", tone: "edGray" },
  { k: "WITHDRAWN", ar: "منسحبة", tone: "edGray" },
  { k: "REPLACED", ar: "استبدلت", tone: "edGray" },
  { k: "DUPLICATE_CANDIDATE", ar: "مشتبه تكرارها", tone: "orange" },
];

const ACTIONS = [
  { key: "CONFIRMED_PARTICIPANT", label: "تأكيد كمشاركة" },
  { key: "EXCLUDED", label: "استبعاد (سبب إلزامي)" },
  { key: "WITHDRAWN", label: "تسجيل انسحاب" },
  { key: "REPLACED", label: "استبدال بجهة" },
  { key: "DUPLICATE_CANDIDATE", label: "ترشيح كتكرار" },
  { key: "PENDING_REVIEW", label: "إعادة للمراجعة" },
];

export default function ParticipatingOrgs() {
  const [sp, setSp] = useSearchParams();
  const [d, setD] = useState(null);
  const [selection, setSelection] = useState({});
  const [openOrg, setOpenOrg] = useState(null);
  const [note, setNote] = useState("");
  const [target, setTarget] = useState("");
  const [busy, setBusy] = useState(null);
  const [msg, setMsg] = useState(null);
  const [confirmBulk, setConfirmBulk] = useState(false);

  const load = () => {
    const p = new URLSearchParams();
    for (const [k, v] of sp.entries()) p.set(k, v);
    api.get(`/admin/participating-orgs?${p}`).then((r) => setD(r.data));
  };
  useEffect(() => { load(); }, [sp.toString()]);
  const set = (k, v) => { const n = new URLSearchParams(sp); if (v) n.set(k, v); else n.delete(k); setSp(n); };

  const toggleSel = (oid) => setSelection((s) => ({ ...s, [oid]: !s[oid] }));
  const selIds = Object.entries(selection).filter(([, v]) => v).map(([k]) => k);

  const applyDecision = async (oid, status) => {
    setBusy(oid + status); setMsg(null);
    try {
      const body = { status, note };
      if (status === "REPLACED") body.replaced_by_org_id = target;
      if (status === "DUPLICATE_CANDIDATE") body.duplicate_of_org_id = target;
      await api.post(`/admin/participating-orgs/${oid}/decision`, body);
      setMsg(`تم تحديث ${oid} → ${status}`);
      setOpenOrg(null); setNote(""); setTarget("");
      load();
    } catch (e) { setMsg(formatApiError(e)); }
    finally { setBusy(null); }
  };

  const bulkConfirm = async () => {
    if (selIds.length === 0) return;
    setBusy("bulk"); setMsg(null);
    try {
      const { data } = await api.post("/admin/participating-orgs/bulk-confirm", { org_ids: selIds });
      setMsg(`تم تأكيد ${data.confirmed} جهة`);
      setSelection({}); setConfirmBulk(false);
      load();
    } catch (e) { setMsg(formatApiError(e)); }
    finally { setBusy(null); }
  };

  if (!d) return <div className="text-edGray-700">…جارٍ التحميل</div>;

  return (
    <div data-testid="participating-orgs-page">
      <div className="mb-6">
        <div className="stat-label mb-2">إدارة السياق · سجل الجمعيات المشاركة</div>
        <h1 className="text-3xl font-bold">الجمعيات المرشحة للمشاركة</h1>
        <p className="text-edGray-700 mt-2 max-w-3xl">
          راجع الجهات المرشحة من جميع المصادر واعتمد المشاركة يدويًا. العدد الرسمي مشتق فقط من الجهات المؤكدة. لا تعديل على البيانات الخام.
        </p>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2 mb-6" data-testid="metrics">
        <Metric label="إجمالي المرشحة" v={d.total} tone="edGray" />
        <Metric label="مؤكدة" v={d.counts_by_status.CONFIRMED_PARTICIPANT || 0} tone="edGreen" />
        <Metric label="تحتاج مراجعة" v={d.counts_by_status.PENDING_REVIEW || 0} tone="orange" />
        <Metric label="مستبعدة" v={d.counts_by_status.EXCLUDED || 0} tone="edGray" />
        <Metric label="منسحبة" v={d.counts_by_status.WITHDRAWN || 0} tone="edGray" />
        <Metric label="استبدلت" v={d.counts_by_status.REPLACED || 0} tone="edGray" />
        <Metric label="مشتبه تكرارها" v={d.counts_by_status.DUPLICATE_CANDIDATE || 0} tone="orange" />
      </div>

      <div className="border border-turquoise-200 bg-turquoise-50/40 rounded-md p-4 mb-6" data-testid="official-counter">
        <div className="stat-label">المؤشر الرسمي: الجهات المشاركة المؤكدة</div>
        <div className="text-4xl font-mono font-bold text-turquoise-700 mt-1 num">
          {num(d.official_confirmed_count)}
        </div>
        <div className="text-xs text-edGray-700 mt-1">
          {num(d.counts_by_status.PENDING_REVIEW || 0)} جهة ما زالت تحتاج مراجعة
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-4" data-testid="filters">
        <input className="field-input w-64" placeholder="بحث بالاسم أو المعرف…" value={sp.get("q") || ""} onChange={(e) => set("q", e.target.value)} data-testid="filter-q" />
        <select className="field-input w-auto" value={sp.get("status") || ""} onChange={(e) => set("status", e.target.value)} data-testid="filter-status">
          <option value="">كل الحالات</option>
          {STATUS_OPTIONS.map((s) => <option key={s.k} value={s.k}>{s.ar}</option>)}
        </select>
        <select className="field-input w-auto" value={sp.get("cohort") || ""} onChange={(e) => set("cohort", e.target.value)} data-testid="filter-cohort">
          <option value="">كل الدفعات</option>
          <option value="1">دفعة 1</option><option value="2">دفعة 2</option><option value="3">دفعة 3</option><option value="4">دفعة 4</option>
        </select>
        <select className="field-input w-auto" value={sp.get("source") || ""} onChange={(e) => set("source", e.target.value)} data-testid="filter-source">
          <option value="">كل المصادر</option>
          <option value="current">Lovable حالي</option>
          <option value="legacy">تاريخي</option>
          <option value="crosswalk_matched">Crosswalk موحد</option>
        </select>
      </div>

      {selIds.length > 0 && (
        <div className="border border-turquoise-200 bg-white rounded-md p-3 mb-4 flex items-center justify-between" data-testid="bulk-bar">
          <span className="text-sm">تم اختيار <span className="num font-semibold">{selIds.length}</span> جهة</span>
          <div className="flex gap-2">
            <button className="btn-outline text-sm" onClick={() => setSelection({})}>مسح</button>
            {!confirmBulk ? (
              <button className="btn-primary text-sm" onClick={() => setConfirmBulk(true)} data-testid="bulk-confirm-start">تأكيد كمشاركة</button>
            ) : (
              <button className="btn-primary text-sm" onClick={bulkConfirm} disabled={busy === "bulk"} data-testid="bulk-confirm-final">
                {busy === "bulk" ? "…" : `تأكيد ${selIds.length} جهة نهائيًا`}
              </button>
            )}
          </div>
        </div>
      )}

      {msg && <div className="text-sm mb-4 text-turquoise-700" data-testid="msg">{msg}</div>}

      <div className="text-sm text-edGray-700 mb-2 num">إجمالي المطابقين: {num(d.total)}</div>

      <div className="space-y-2" data-testid="org-list">
        {(d.items || []).map((o) => (
          <div key={o.org_id} className="bg-white border border-edGray-200 rounded-md" data-testid={`org-${o.org_id}`}>
            <div className="p-4 flex items-start gap-3">
              <input type="checkbox" checked={!!selection[o.org_id]} onChange={() => toggleSel(o.org_id)} className="mt-1" data-testid={`sel-${o.org_id}`} />
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline justify-between gap-3 flex-wrap">
                  <div>
                    <Link to={`/admin/organizations/${o.org_id}`} className="font-semibold text-navy hover:text-turquoise">{o.canonical_name}</Link>
                    <div className="text-xs num text-edGray-700 mt-1">{o.org_id}{o.linked_legacy_id ? ` · تاريخي: ${o.linked_legacy_id}` : ""}</div>
                  </div>
                  <StatusBadge status={o.participation_review_status} />
                </div>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-3 text-xs">
                  <Field k="الدفعات" v={o.cohorts?.length ? o.cohorts.join("، ") : "—"} />
                  <Field k="المصادر" v={o.sources?.join("، ") || "—"} />
                  <Field k="رحلات النماذج" v={num(o.families_count)} />
                  <Field k="النسخ" v={num(o.versions_count)} />
                  <Field k="فيها مراجعة" v={o.families_review > 0 ? `${num(o.families_review)} رحلة` : "لا"} />
                </div>
                {o.alt_names?.length > 1 && (
                  <div className="text-xs text-edGray-700 mt-2">
                    أسماء بديلة: {o.alt_names.slice(0, 4).join(" · ")}
                    {o.alt_names.length > 4 ? " …" : ""}
                  </div>
                )}
                {o.participation_notes && (
                  <div className="text-xs text-edGray-700 mt-1">ملاحظة: {o.participation_notes}</div>
                )}
                <div className="mt-3 flex gap-2 flex-wrap">
                  <button onClick={() => setOpenOrg(openOrg === o.org_id ? null : o.org_id)} className="btn-outline text-xs" data-testid={`toggle-${o.org_id}`}>
                    {openOrg === o.org_id ? "إغلاق" : "قرار المراجعة"}
                  </button>
                  <Link to={`/admin/organizations/${o.org_id}`} className="btn-outline text-xs">فتح الجهة</Link>
                </div>
                {openOrg === o.org_id && (
                  <div className="mt-3 border-t border-edGray-200 pt-3 space-y-2" data-testid={`actions-${o.org_id}`}>
                    <textarea className="field-input" rows={2} placeholder="سبب/ملاحظة (إلزامية عند الاستبعاد أو الانسحاب)" value={note} onChange={(e) => setNote(e.target.value)} data-testid={`note-${o.org_id}`} />
                    <input className="field-input" placeholder="معرف الجهة البديلة/الأصلية (عند الاستبدال/التكرار)" value={target} onChange={(e) => setTarget(e.target.value)} data-testid={`target-${o.org_id}`} />
                    <div className="flex flex-wrap gap-2">
                      {ACTIONS.map((a) => (
                        <button key={a.key} onClick={() => applyDecision(o.org_id, a.key)}
                                disabled={busy === (o.org_id + a.key)}
                                className="btn-outline text-xs" data-testid={`act-${o.org_id}-${a.key}`}>
                          {busy === (o.org_id + a.key) ? "…" : a.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const cfg = STATUS_OPTIONS.find((s) => s.k === status) || STATUS_OPTIONS[0];
  const toneCls = {
    orange: "border-orange text-orange bg-orange-50",
    edGreen: "border-edGreen text-edGreen-700 bg-edGreen-50",
    edGray: "border-edGray-200 text-edGray-700 bg-white",
  }[cfg.tone];
  return <span className={`pill ${toneCls}`}>{cfg.ar}</span>;
}
function Metric({ label, v, tone }) {
  const cls = tone === "edGreen" ? "text-edGreen-700" : tone === "orange" ? "text-orange" : "text-navy";
  return (
    <div className="border border-edGray-200 bg-white rounded-md p-3">
      <div className="stat-label">{label}</div>
      <div className={`text-2xl font-mono font-bold ${cls}`}>{num(v)}</div>
    </div>
  );
}
function Field({ k, v }) {
  return <div><span className="text-edGray-700">{k}: </span><span className="text-navy">{v}</span></div>;
}
