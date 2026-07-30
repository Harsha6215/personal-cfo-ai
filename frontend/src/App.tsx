import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ToastProvider } from "@/components/ui/Toast";
import { PageSpinner } from "@/components/ui/Spinner";

// Lazy-load pages — keeps initial bundle small
const Login      = lazy(() => import("@/pages/Login"));
const Dashboard  = lazy(() => import("@/pages/Dashboard"));
const ComingSoon = lazy(() => import("@/pages/ComingSoon"));

export default function App() {
  return (
    <ToastProvider>
      <Suspense fallback={<PageSpinner />}>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<Login />} />

          {/* App shell — all authenticated routes nest inside */}
          <Route element={<AppShell />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/portfolio" element={<ComingSoon />} />
            <Route path="/watchlist" element={<ComingSoon />} />
            <Route path="/research"  element={<ComingSoon />} />
            <Route path="/advisor"   element={<ComingSoon />} />
            <Route path="/goals"     element={<ComingSoon />} />
            <Route path="/settings"  element={<ComingSoon />} />
          </Route>

          {/* Default redirects */}
          <Route path="/"   element={<Navigate to="/dashboard" replace />} />
          <Route path="*"   element={<Navigate to="/login" replace />} />
        </Routes>
      </Suspense>
    </ToastProvider>
  );
}
