// ── Navigation ────────────────────────────────────────────────────────────────
export interface NavItem {
  label: string;
  path: string;
  icon: string;          // Heroicon name (outline)
  badge?: string | number;
  children?: NavItem[];
}

// ── User / Auth ───────────────────────────────────────────────────────────────
export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// ── Theme ─────────────────────────────────────────────────────────────────────
export type Theme = "light" | "dark" | "system";

// ── API ───────────────────────────────────────────────────────────────────────
export interface ApiError {
  error: string;
  message: string;
  request_id: string;
}

export interface HealthResponse {
  status: string;
  service: string;
}
