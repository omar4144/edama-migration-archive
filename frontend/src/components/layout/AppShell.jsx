import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Menu, X, ChevronDown } from "lucide-react";

const PRIMARY = [
  { to: "/admin", label: "المشهد التنفيذي", testid: "nav-exec", end: true },
  { to: "/admin/cohorts", label: "الدفعات", testid: "nav-cohorts" },
  { to: "/admin/organizations", label: "الجهات", testid: "nav-orgs" },
  { to: "/admin/evaluators", label: "المحكمون", testid: "nav-evaluators" },
  { to: "/admin/consultants", label: "المستشارون", testid: "nav-consultants" },
  { to: "/admin/models-hub", label: "النماذج والتحكيمات", testid: "nav-models" },
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

  const handleLogout = async () => { await logout(); navigate("/login", { replace: true }); };
  const closeMenu = () => setMenuOpen(false);

  const isAdmin = user?.role === "admin";
  const secondary = isAdmin ? SECONDARY : [];
  const primary = isAdmin ? PRIMARY : user?.role === "consultant" ? CONSULTANT_NAV : EVALUATOR_NAV;

  return (
    <div className="min-h-screen bg-ivory text-navy" data-testid="app-shell">
      <header className="bg-navy text-ivory border-b border-navy/60 sticky top-0 z-40">
        <div className="max-w-[1400px] mx-auto px-4 md:px-6 py-3 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              className="lg:hidden text-ivory p-1 border border-ivory/30"
              onClick={() => setMenuOpen(!menuOpen)}
              aria-label={menuOpen ? "إغلاق القائمة" : "فتح القائمة"}
              data-testid="mobile-menu-toggle"
            >
              {menuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
            <div className="w-9 h-9 border-2 border-turquoise flex items-center justify-center shrink-0">
              <span className="text-turquoise font-bold text-lg">إ</span>
            </div>
            <div className="leading-tight">
              <div className="font-semibold text-base md:text-lg">مسرعة إدامة</div>
              <div className="text-xs text-ivory/70 tracking-wider hidden sm:block">Edama · V8</div>
            </div>
          </div>

          {/* Top nav — inline on lg+ */}
          {isAdmin && (
            <nav className="hidden lg:flex items-center gap-1 flex-1 justify-center" data-testid="top-nav">
              {PRIMARY.map((it) => (
                <NavLink
                  key={it.to} to={it.to} end={it.end}
                  className={({ isActive }) => `px-3 py-2 text-sm border-b-2 transition-colors ${isActive ? "border-turquoise text-ivory font-medium" : "border-transparent text-ivory/70 hover:text-ivory"}`}
                  data-testid={it.testid}
                >
                  {it.label}
                </NavLink>
              ))}
              <div className="relative">
                <button
                  className="px-3 py-2 text-sm flex items-center gap-1 text-ivory/70 hover:text-ivory"
                  onClick={() => setDataOpen(!dataOpen)}
                  data-testid="nav-data-toggle"
                >
                  إدارة البيانات <ChevronDown size={14} />
                </button>
                {dataOpen && (
                  <div className="absolute top-full left-0 mt-1 bg-navy border border-ivory/20 min-w-[220px] z-50" onMouseLeave={() => setDataOpen(false)} data-testid="data-menu">
                    {SECONDARY.map((it) => (
                      <NavLink
                        key={it.to} to={it.to}
                        onClick={() => setDataOpen(false)}
                        className={({ isActive }) => `block px-4 py-2.5 text-sm ${isActive ? "bg-navy-700 text-ivory" : "text-ivory/80 hover:bg-navy-700"}`}
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
              <div className="text-sm font-medium" data-testid="user-name">{user?.name_ar}</div>
              <div className="text-xs text-ivory/60" data-testid="user-role">{ROLE_LABEL[user?.role]}</div>
            </div>
            <button onClick={handleLogout} className="text-sm border border-ivory/40 hover:border-ivory px-3 py-1.5 text-ivory" data-testid="logout-button">خروج</button>
          </div>
        </div>
      </header>

      {/* Mobile / consultant / evaluator side nav */}
      <div className="max-w-[1400px] mx-auto flex">
        {!isAdmin && (
          <aside className="hidden md:block w-64 shrink-0 border-l border-navy/15 min-h-[calc(100vh-73px)] py-6">
            <nav className="flex flex-col" data-testid="sidebar-nav">
              {primary.map((it) => (
                <NavLink key={it.to} to={it.to} data-testid={it.testid}
                  className={({ isActive }) => `px-6 py-3 border-r-4 text-sm ${isActive ? "border-turquoise bg-white text-navy font-medium" : "border-transparent text-navy/70 hover:text-navy hover:bg-white/60"}`}>
                  {it.label}
                </NavLink>
              ))}
            </nav>
          </aside>
        )}

        {menuOpen && (
          <div className="lg:hidden fixed inset-0 bg-navy/50 z-40" onClick={closeMenu}>
            <aside className="absolute right-0 top-0 bottom-0 w-72 bg-ivory border-l border-navy/15 py-4 overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="mobile-drawer">
              <nav className="flex flex-col">
                {(isAdmin ? [...PRIMARY, ...SECONDARY] : primary).map((it) => (
                  <NavLink key={it.to} to={it.to} onClick={closeMenu} end={it.end} data-testid={`m-${it.testid}`}
                    className={({ isActive }) => `px-6 py-3 border-r-4 text-sm ${isActive ? "border-turquoise bg-white text-navy font-medium" : "border-transparent text-navy/70"}`}>
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
