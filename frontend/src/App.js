import React from "react";
import { BrowserRouter, Routes, Route, Navigate, Outlet } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import AppShell from "@/components/layout/AppShell";
import Login from "@/pages/Login";
import ChangePassword from "@/pages/ChangePassword";
import ForgotPassword from "@/pages/ForgotPassword";
import ResetPassword from "@/pages/ResetPassword";
import ExecutiveScene from "@/pages/admin/ExecutiveScene";
import Reconciliation from "@/pages/admin/Reconciliation";
import ReviewQueue from "@/pages/admin/ReviewQueue";
import Records from "@/pages/admin/Records";
import UsersPage from "@/pages/admin/Users";
import AuditLog from "@/pages/admin/AuditLog";
import DataQuality from "@/pages/admin/DataQuality";
import CohortsMap from "@/pages/admin/CohortsMap";
import CohortDetail from "@/pages/admin/CohortDetail";
import UnifiedOrganizations from "@/pages/admin/UnifiedOrganizations";
import UnifiedOrganization from "@/pages/admin/UnifiedOrganization";
import EvaluatorsDirectory from "@/pages/admin/EvaluatorsDirectory";
import EvaluatorDetail from "@/pages/admin/EvaluatorDetail";
import ConsultantsDirectory from "@/pages/admin/ConsultantsDirectory";
import ConsultantDetail from "@/pages/admin/ConsultantDetail";
import ModelsHub from "@/pages/admin/ModelsHub";
import ConsultantSubmissions from "@/pages/consultant/Submissions";
import ConsultantActivities from "@/pages/consultant/Activities";
import EvaluatorQueue from "@/pages/evaluator/Queue";
import EvaluatorHours from "@/pages/evaluator/Hours";
import EvaluatorHistorical from "@/pages/evaluator/Historical";
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
  if (user.must_change_password) return <Navigate to="/change-password" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

function RootRedirect() {
  const { user } = useAuth();
  if (user === null) return <Loading />;
  if (user === false) return <Navigate to="/login" replace />;
  if (user.must_change_password) return <Navigate to="/change-password" replace />;
  if (user.role === "admin") return <Navigate to="/admin" replace />;
  if (user.role === "consultant") return <Navigate to="/consultant/submissions" replace />;
  if (user.role === "evaluator") return <Navigate to="/evaluator/queue" replace />;
  return <Navigate to="/login" replace />;
}

function Shell() { return <AppShell><Outlet /></AppShell>; }

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/change-password" element={<ChangePassword />} />
          <Route path="/" element={<RootRedirect />} />

          <Route element={<RoleGuard roles={["admin"]}><Shell /></RoleGuard>}>
            {/* Primary operational layer */}
            <Route path="/admin" element={<ExecutiveScene />} />
            <Route path="/admin/cohorts" element={<CohortsMap />} />
            <Route path="/admin/cohorts/:cohort" element={<CohortDetail />} />
            <Route path="/admin/organizations" element={<UnifiedOrganizations />} />
            <Route path="/admin/organizations/:orgId" element={<UnifiedOrganization />} />
            <Route path="/admin/evaluators" element={<EvaluatorsDirectory />} />
            <Route path="/admin/evaluators/:name" element={<EvaluatorDetail />} />
            <Route path="/admin/consultants" element={<ConsultantsDirectory />} />
            <Route path="/admin/consultants/:name" element={<ConsultantDetail />} />
            <Route path="/admin/models-hub" element={<ModelsHub />} />
            {/* Data management (secondary) */}
            <Route path="/admin/data/reconciliation" element={<Reconciliation />} />
            <Route path="/admin/data/mappings" element={<ReviewQueue />} />
            <Route path="/admin/data/quality" element={<DataQuality />} />
            <Route path="/admin/data/records" element={<Records />} />
            <Route path="/admin/data/users" element={<UsersPage />} />
            <Route path="/admin/data/audit" element={<AuditLog />} />
          </Route>

          <Route element={<RoleGuard roles={["consultant"]}><Shell /></RoleGuard>}>
            <Route path="/consultant/submissions" element={<ConsultantSubmissions />} />
            <Route path="/consultant/activities" element={<ConsultantActivities />} />
          </Route>

          <Route element={<RoleGuard roles={["evaluator"]}><Shell /></RoleGuard>}>
            <Route path="/evaluator/queue" element={<EvaluatorQueue />} />
            <Route path="/evaluator/hours" element={<EvaluatorHours />} />
            <Route path="/evaluator/historical" element={<EvaluatorHistorical />} />
          </Route>

          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
