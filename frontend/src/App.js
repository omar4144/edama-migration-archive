import React from "react";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import AppShell from "@/components/layout/AppShell";
import Login from "@/pages/Login";
import Reconciliation from "@/pages/admin/Reconciliation";
import ReviewQueue from "@/pages/admin/ReviewQueue";
import Organizations from "@/pages/admin/Organizations";
import Records from "@/pages/admin/Records";
import UsersPage from "@/pages/admin/Users";
import AuditLog from "@/pages/admin/AuditLog";
import ConsultantSubmissions from "@/pages/consultant/Submissions";
import ConsultantActivities from "@/pages/consultant/Activities";
import EvaluatorQueue from "@/pages/evaluator/Queue";
import EvaluatorHours from "@/pages/evaluator/Hours";
import NotFound from "@/pages/NotFound";
import "@/index.css";

function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-ivory">
      <div className="text-navy/60 text-sm tracking-wider">…جارٍ التحميل</div>
    </div>
  );
}

function RoleGuard({ roles, children }) {
  const { user } = useAuth();
  if (user === null) return <Loading />;
  if (user === false) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

function RootRedirect() {
  const { user } = useAuth();
  if (user === null) return <Loading />;
  if (user === false) return <Navigate to="/login" replace />;
  if (user.role === "admin") return <Navigate to="/admin/reconciliation" replace />;
  if (user.role === "consultant") return <Navigate to="/consultant/submissions" replace />;
  if (user.role === "evaluator") return <Navigate to="/evaluator/queue" replace />;
  return <Navigate to="/login" replace />;
}

function Shell() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<RootRedirect />} />

          <Route element={<RoleGuard roles={["admin"]}><Shell /></RoleGuard>}>
            <Route path="/admin/reconciliation" element={<Reconciliation />} />
            <Route path="/admin/review-queue" element={<ReviewQueue />} />
            <Route path="/admin/organizations" element={<Organizations />} />
            <Route path="/admin/records" element={<Records />} />
            <Route path="/admin/users" element={<UsersPage />} />
            <Route path="/admin/audit" element={<AuditLog />} />
          </Route>

          <Route element={<RoleGuard roles={["consultant"]}><Shell /></RoleGuard>}>
            <Route path="/consultant/submissions" element={<ConsultantSubmissions />} />
            <Route path="/consultant/activities" element={<ConsultantActivities />} />
          </Route>

          <Route element={<RoleGuard roles={["evaluator"]}><Shell /></RoleGuard>}>
            <Route path="/evaluator/queue" element={<EvaluatorQueue />} />
            <Route path="/evaluator/hours" element={<EvaluatorHours />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
