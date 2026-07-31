import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Menu, X } from "lucide-react";

const NAV = {
  admin: [
    { to: "/admin/reconciliation", label: "لوحة المصالحة", testid: "nav-reconciliation" },
    { to: "/admin/review-queue", label: "قائمة المراجعة", testid: "nav-review-queue" },
    { to: "/admin/cohorts", label: "خريطة الدفعات", testid: "nav-cohorts" },
    { to: "/admin/organizations", label: "الجهات", testid: "nav-orgs" },
    { to: "/admin/records", label: "السجلات الحالية", testid: "nav-records" },
    { to: "/admin/data-quality", label: "مركز جودة البيانات", testid: "nav-dq" },
    { to: "/admin/users", label: "المستخدمون", testid: "nav-users" },
    { to: "/admin/audit", label: "سجل التدقيق", testid: "nav-audit" },
  ],
  consultant: [
    { to: "/consultant/submissions", label: "نماذجي المرسلة", testid: "nav-submissions" },
    { to: "/consultant/activities", label: "الأنشطة التاريخية", testid: "nav-activities" },
  ],
  evaluator: [
    { to: "/evaluator/queue", label: "قائمة التحكيم", testid: "nav-eval-queue" },
    { to: "/evaluator/hours", label: "ساعات العمل", testid: "nav-eval-hours" },
    { to: "/evaluator/historical", label: "التحكيمات التاريخية", testid: "nav-eval-historical" },
  ],
};

const ROLE_LABEL = { admin: "إدارة السياق", consultant: "مستشار", evaluator: "محكّم" };

export default function AppShell({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const items = user?.role ? NAV[user.role] || [] : [];

  const handleLogout = async () => {
    await logout();
    navigate("/login", { replace: true });
  };

  const closeMenu = () => setMenuOpen(false);

  return (
    <div className="min-h-screen bg-ivory text-navy" data-testid="app-shell">
      <header className="bg-navy text-ivory border-b border-navy/60 sticky top-0 z-40">
        <div className="max-w-[1400px] mx-auto px-4 md:px-6 py-3 md:py-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              className="md:hidden text-ivory p-1 border border-ivory/30"
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
          <div className="flex items-center gap-3 md:gap-4">
            <div className="text-right hidden md:block leading-tight">
              <div className="text-sm font-medium" data-testid="user-name">{user?.name_ar}</div>
              <div className="text-xs text-ivory/60" data-testid="user-role">{ROLE_LABEL[user?.role]}</div>
            </div>
            <button
              onClick={handleLogout}
              className="text-sm border border-ivory/40 hover:border-ivory px-3 py-1.5 text-ivory"
              data-testid="logout-button"
            >
              خروج
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-[1400px] mx-auto flex">
        {/* Sidebar — desktop */}
        <aside className="hidden md:block w-64 shrink-0 border-l border-navy/15 min-h-[calc(100vh-73px)] py-6">
          <nav className="flex flex-col" data-testid="sidebar-nav">
            {items.map((it) => (
              <NavLink
                key={it.to}
                to={it.to}
                data-testid={it.testid}
                className={({ isActive }) =>
                  `px-6 py-3 border-r-4 text-sm ${
                    isActive
                      ? "border-turquoise bg-white text-navy font-medium"
                      : "border-transparent text-navy/70 hover:text-navy hover:bg-white/60"
                  }`
                }
              >
                {it.label}
              </NavLink>
            ))}
          </nav>
        </aside>

        {/* Mobile drawer */}
        {menuOpen && (
          <div className="md:hidden fixed inset-0 bg-navy/50 z-40" onClick={closeMenu}>
            <aside
              className="absolute right-0 top-0 bottom-0 w-72 bg-ivory border-l border-navy/15 py-6"
              onClick={(e) => e.stopPropagation()}
              data-testid="mobile-drawer"
            >
              <nav className="flex flex-col">
                {items.map((it) => (
                  <NavLink
                    key={it.to}
                    to={it.to}
                    onClick={closeMenu}
                    data-testid={`m-${it.testid}`}
                    className={({ isActive }) =>
                      `px-6 py-3 border-r-4 text-sm ${
                        isActive
                          ? "border-turquoise bg-white text-navy font-medium"
                          : "border-transparent text-navy/70"
                      }`
                    }
                  >
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
