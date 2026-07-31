/** Frontend helpers shared across the unified layer. */

const URL_KEYS = [
  "url",
  "model_url_canonical",
  "model_url_hyperlink_target",
  "model_url_displayed",
  "model_url",
  "canonical_url",
];

export function resolveUrl(rec) {
  if (!rec) return null;
  for (const k of URL_KEYS) {
    const v = rec[k];
    if (v && typeof v === "string" && v.trim()) return v.trim();
  }
  return null;
}

export function sourceBadge(source) {
  // Small chip inside details ONLY — never a top-level filter for operators.
  const map = {
    current: { label: "Lovable", cls: "border-turquoise-600 text-turquoise-600" },
    legacy: { label: "تاريخي", cls: "border-navy/40 text-navy/70" },
    unified: { label: "موحّد", cls: "border-edGreen text-edGreen" },
    legacy_only: { label: "تاريخي فقط", cls: "border-navy/40 text-navy/70" },
    review_required: { label: "يحتاج مراجعة", cls: "border-orange text-orange" },
  };
  return map[source] || { label: source || "—", cls: "border-navy/25 text-navy/60" };
}

export function evaluationTone(v) {
  if (v === "مقبول" || v === "مجاز") return "text-edGreen";
  if (v === "يحتاج لتطوير") return "text-orange";
  if (v === "غير مكتمل") return "text-orange";
  return "text-navy/70";
}

export function num(v, digits = 0) {
  if (v == null || v === "") return "—";
  const n = Number(v);
  if (Number.isNaN(n)) return String(v);
  return n.toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}
