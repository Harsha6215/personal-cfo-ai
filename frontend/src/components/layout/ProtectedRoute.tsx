import { Navigate } from "react-router-dom";
import { isAuthenticated } from "@/services/auth";

interface Props {
  children: React.ReactNode;
}

/**
 * Route guard that redirects to /login if user is not authenticated.
 * Wrap authenticated routes with this component.
 */
export function ProtectedRoute({ children }: Props) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
