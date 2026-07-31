import React, { useEffect, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import api from "@/lib/api";
import { Menu, X, ChevronDown } from "lucide-react";

const PRIMARY_BASE = [
  { to: "/admin", label: "المشهد التنفيذي", testid: "nav-exec", end: true },
  { to: "/admin/participating-organizations", label: "سجل الجمعيات", testid: "nav-participating" },
  { to: "/admin/organizations", label: "الجهات", testid: "nav-orgs" },
  { to: "/admin/evaluators", label: "المحكمون", testid: "nav-evaluators" },
  { to: "/admin/consultants", label: "المستشارون", testid: "nav-consultants" },
  { to: "/admin/models-hub", label: "رحلات النماذج", testid: "nav-models" },
];

const SECONDARY = [
  { to: "/admin/data/reconciliation", label: "المصالحة", testid: "nav-recon" },
  { to: "/admin/data/mappings", label: "قائمة المطابقات", testid: "nav-mappings" },
  { to: "/admin/data/quality", label: "جودة البيانات", testid: "nav-dq" },
  { to: "/admin/data/records", label: "السجلات الخام", testid: "nav-records" },
  { to: "/admin/data/audit", label: "سجل التدقيق", testid: "nav-audit" },
  { to: "/admin/data/users", label: "المستخدمون والصلاحيات", testid: "nav-users" },
];

const CONSULTANT_NAV = [
  { to: "/consultant/submissions", label: "نماذجي المرسلة", testid: "nav-submissions" },
  { to: "/consultant/activities", label: "الأنشطة التاريخية", testid: "nav-activities" },
];

const EVALUATOR_NAV = [
  { to: "/evaluator/queue", label: "قائمة التحكيم", testid: "nav-eval-queue" },
  { to: "/evaluator/hours", label: "ساعات العمل", testid: "nav-eval-hours" },
  { to: "/evaluator/historical", label: "التحكيمات التاريخية", testid: "nav-eval-historical" },
];

const ROLE_LABEL = { admin: "إدارة السياق", consultant: "مستشار", evaluator: "محكّم" };

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [dataOpen, setDataOpen] = useState(false);
  const [reviewCount, setReviewCount] = useState(0);

  useEffect(() => {
    if (user?.role !== "admin") return;
    api.get("/admin/canonical/exec-scene")
       .then((r) => setReviewCount(r.data?.terminology?.review_required_journeys || 0))
       .catch(() => {});
  }, [user?.role]);

  const handleLogout = async () => { await logout(); navigate("/login", { replace: true }); };
  const closeMenu = () => setMenuOpen(false);

  const isAdmin = user?.role === "admin";
  const secondary = isAdmin ? SECONDARY : [];
  const PRIMARY = isAdmin && reviewCount > 0
    ? [PRIMARY_BASE[0], { to: "/admin/review-queue", label: `قائمة المراجعة (${reviewCount})`, testid: "nav-review" }, ...PRIMARY_BASE.slice(1)]
    : PRIMARY_BASE;
  const primary = isAdmin ? PRIMARY : user?.role === "consultant" ? CONSULTANT_NAV : EVALUATOR_NAV;

  return (
    <div className="min-h-screen bg-ivory text-navy" data-testid="app-shell">
      <header className="bg-white border-b border-edGray-200 sticky top-0 z-40 shadow-[0_1px_0_0_rgba(48,190,188,0.08)]">
        <div className="max-w-[1400px] mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              className="lg:hidden text-navy p-1 border border-edGray-200 rounded"
              onClick={() => setMenuOpen(!menuOpen)}
              aria-label={menuOpen ? "إغلاق القائمة" : "فتح القائمة"}
              data-testid="mobile-menu-toggle"
            >
              {menuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
            <img
              src="/edama-logo.png"
              alt="مسرعة إدامة — Edama Accelerator"
              className="h-11 md:h-12 w-auto select-none"
              draggable={false}
              data-testid="edama-brand-logo"
            />
            <div className="hidden md:block leading-tight border-r border-edGray-200 pr-3 mr-1">
              <div className="text-[11px] uppercase tracking-[0.18em] text-edGray-700 font-semibold">EDAMA ACCELERATOR</div>
              <div className="text-xs text-edGray-700">منصة إدارة التحكيمات والنماذج</div>
            </div>
          </div>

          {isAdmin && (
            <nav className="hidden lg:flex items-center gap-1 flex-1 justify-center" data-testid="top-nav">
              {PRIMARY.map((it) => (
                <NavLink
                  key={it.to} to={it.to} end={it.end}
                  className={({ isActive }) => `px-3 py-2 text-sm border-b-2 transition-colors ${isActive ? "border-turquoise text-turquoise font-semibold" : "border-transparent text-navy/75 hover:text-turquoise"}`}
                  data-testid={it.testid}
                >
                  {it.label}
                </NavLink>
              ))}
              <div className="relative">
                <button
                  className="px-3 py-2 text-sm flex items-center gap-1 text-navy/75 hover:text-turquoise"
                  onClick={() => setDataOpen(!dataOpen)}
                  data-testid="nav-data-toggle"
                >
                  إدارة البيانات <ChevronDown size={14} />
                </button>
                {dataOpen && (
                  <div className="absolute top-full right-0 mt-1 bg-white border border-edGray-200 rounded-md shadow-lg min-w-[220px] z-50" onMouseLeave={() => setDataOpen(false)} data-testid="data-menu">
                    {SECONDARY.map((it) => (
                      <NavLink
                        key={it.to} to={it.to}
                        onClick={() => setDataOpen(false)}
                        className={({ isActive }) => `block px-4 py-2.5 text-sm ${isActive ? "bg-turquoise-50 text-turquoise-700 font-semibold" : "text-navy/80 hover:bg-turquoise-50/60"}`}
                        data-testid={it.testid}
                      >
                        {it.label}
                      </NavLink>
                    ))}
                  </div>
                )}
              </div>
            </nav>
          )}

          <div className="flex items-center gap-3">
            <div className="text-right hidden md:block leading-tight">
              <div className="text-sm font-semibold text-navy" data-testid="user-name">{user?.name_ar}</div>
              <div className="text-xs text-edGray-700" data-testid="user-role">{ROLE_LABEL[user?.role]}</div>
            </div>
            <button onClick={handleLogout} className="text-sm border border-edGray-200 hover:border-turquoise hover:text-turquoise px-3 py-1.5 rounded-md text-navy transition-colors" data-testid="logout-button">خروج</button>
          </div>
        </div>
        <div className="edama-chevron-strip" aria-hidden="true" />
      </header>

      <div className="max-w-[1400px] mx-auto flex">
        {!isAdmin && (
          <aside className="hidden md:block w-64 shrink-0 border-l border-edGray-200 min-h-[calc(100vh-79px)] py-6 bg-white/40">
            <nav className="flex flex-col" data-testid="sidebar-nav">
              {primary.map((it) => (
                <NavLink key={it.to} to={it.to} data-testid={it.testid}
                  className={({ isActive }) => `px-6 py-3 border-r-4 text-sm transition-colors ${isActive ? "border-turquoise bg-white text-turquoise-700 font-semibold" : "border-transparent text-navy/75 hover:text-turquoise hover:bg-white/60"}`}>
                  {it.label}
                </NavLink>
              ))}
            </nav>
          </aside>
        )}

        {menuOpen && (
          <div className="lg:hidden fixed inset-0 bg-navy/40 z-40" onClick={closeMenu}>
            <aside className="absolute right-0 top-0 bottom-0 w-72 bg-white border-l border-edGray-200 py-4 overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="mobile-drawer">
              <div className="px-6 pb-4 mb-2 border-b border-edGray-200">
                <img src="/edama-logo.png" alt="مسرعة إدامة" className="h-10 w-auto" />
              </div>
              <nav className="flex flex-col">
                {(isAdmin ? [...PRIMARY, ...SECONDARY] : primary).map((it) => (
                  <NavLink key={it.to} to={it.to} onClick={closeMenu} end={it.end} data-testid={`m-${it.testid}`}
                    className={({ isActive }) => `px-6 py-3 border-r-4 text-sm ${isActive ? "border-turquoise bg-turquoise-50 text-turquoise-700 font-semibold" : "border-transparent text-navy/75"}`}>
                    {it.label}
                  </NavLink>
                ))}
              </nav>
            </aside>
          </div>
        )}

        <main className="flex-1 min-w-0 px-4 md:px-8 py-6 md:py-8">{children}</main>
      </div>
    </div>
  );
}
