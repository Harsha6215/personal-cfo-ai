/**
 * Auth API service.
 * Handles login, register, token refresh, and logout.
 */

const API_BASE = "/api/v1/auth";

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: {
    id: string;
    email: string;
    full_name: string | null;
    is_active: boolean;
    created_at: string;
  };
}

export interface RegisterResponse {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
}

// ── Login ─────────────────────────────────────────────────────────────────────
export async function login(email: string, password: string): Promise<LoginResponse> {
  // FastAPI's OAuth2PasswordRequestForm expects form-urlencoded
  const body = new URLSearchParams();
  body.append("username", email);
  body.append("password", password);

  const res = await fetch(`${API_BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Login failed");
  }

  const data: LoginResponse = await res.json();

  // Store tokens
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  localStorage.setItem("user", JSON.stringify(data.user));

  return data;
}

// ── Register ──────────────────────────────────────────────────────────────────
export async function register(
  email: string,
  password: string,
  fullName?: string
): Promise<RegisterResponse> {
  const res = await fetch(`${API_BASE}/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Registration failed");
  }

  return res.json();
}

// ── Refresh ───────────────────────────────────────────────────────────────────
export async function refreshToken(): Promise<string> {
  const refresh = localStorage.getItem("refresh_token");
  if (!refresh) throw new Error("No refresh token");

  const res = await fetch(`${API_BASE}/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });

  if (!res.ok) {
    logout();
    throw new Error("Token refresh failed");
  }

  const data = await res.json();
  localStorage.setItem("access_token", data.access_token);
  return data.access_token;
}

// ── Get current user ──────────────────────────────────────────────────────────
export async function getMe() {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) throw new Error("Not authenticated");
  return res.json();
}

// ── Logout ────────────────────────────────────────────────────────────────────
export function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
}

// ── Helpers ───────────────────────────────────────────────────────────────────
export function getStoredToken(): string | null {
  return localStorage.getItem("access_token");
}

export function getStoredUser() {
  const raw = localStorage.getItem("user");
  return raw ? JSON.parse(raw) : null;
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem("access_token");
}
