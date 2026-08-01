import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { ToastProvider } from "@/components/ui/Toast";
import { PageSpinner } from "@/components/ui/Spinner";

// Lazy-load pages — keeps initial bundle small
const Login         = lazy(() => import("@/pages/Login"));
const Dashboard     = lazy(() => import("@/pages/Dashboard"));
const Import        = lazy(() => import("@/pages/Import"));
const ImportHistory = lazy(() => import("@/pages/ImportHistory"));
const Portfolio     = lazy(() => import("@/pages/Portfolio"));
const ComingSoon    = lazy(() => import("@/pages/ComingSoon"));

export default function App() {
  return (
    <ToastProvider>
      <Suspense fallback={<PageSpinner />}>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<Login />} />

          {/* Protected app shell — all authenticated routes nest inside */}
          <Route
            element={
              <ProtectedRoute>
                <AppShell />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/portfolio" element={<Portfolio />} />
            <Route path="/import"    element={<Import />} />
            <Route path="/imports"   element={<ImportHistory />} />
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
