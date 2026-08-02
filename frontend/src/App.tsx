import { lazy, Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { ToastProvider } from "@/components/ui/Toast";
import { PageSpinner } from "@/components/ui/Spinner";

// Lazy-load pages — keeps initial bundle small
const Login         = lazy(() => import("@/pages/Login"));
const Onboarding    = lazy(() => import("@/pages/Onboarding"));
const Dashboard     = lazy(() => import("@/pages/Dashboard"));
const Import        = lazy(() => import("@/pages/Import"));
const ImportHistory = lazy(() => import("@/pages/ImportHistory"));
const Portfolio     = lazy(() => import("@/pages/Portfolio"));
const StockDetail   = lazy(() => import("@/pages/StockDetail"));
const Watchlist     = lazy(() => import("@/pages/Watchlist"));
const Research      = lazy(() => import("@/pages/Research"));
const Advisor       = lazy(() => import("@/pages/Advisor"));
const Goals         = lazy(() => import("@/pages/Goals"));
const ComingSoon    = lazy(() => import("@/pages/ComingSoon"));

export default function App() {
  return (
    <ToastProvider>
      <Suspense fallback={<PageSpinner />}>
        <Routes>
          {/* Public */}
          <Route path="/login" element={<Login />} />
          <Route path="/onboarding" element={<ProtectedRoute><Onboarding /></ProtectedRoute>} />

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
            <Route path="/stock/:ticker" element={<StockDetail />} />
            <Route path="/import"    element={<Import />} />
            <Route path="/imports"   element={<ImportHistory />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/research"  element={<Research />} />
            <Route path="/advisor"   element={<Advisor />} />
            <Route path="/goals"     element={<Goals />} />
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
