/**
 * Auth API service — Epic 6 Sprint 6.3
 *
 * Handles login, register, Google OAuth, OTP, token refresh, and logout.
 */

const API_BASE = "/api/v1/auth";

export interface UserInfo {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  role: string;
  created_at: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserInfo;
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
  _storeAuth(data);
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

// ── Google OAuth ──────────────────────────────────────────────────────────────
export async function loginWithGoogle(credential: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/google`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: credential }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Google login failed");
  }

  const data: LoginResponse = await res.json();
  _storeAuth(data);
  return data;
}

// ── OTP Login ─────────────────────────────────────────────────────────────────
export async function requestOTP(email: string): Promise<string> {
  const res = await fetch(`${API_BASE}/request-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to send OTP");
  }

  const data = await res.json();
  return data.message;
}

export async function verifyOTP(email: string, otp: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/verify-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, otp }),
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "OTP verification failed");
  }

  const data: LoginResponse = await res.json();
  _storeAuth(data);
  return data;
}

// ── Refresh (with rotation) ───────────────────────────────────────────────────
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
  // Rotation: store both new access and refresh tokens
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return data.access_token;
}

// ── Get current user ──────────────────────────────────────────────────────────
export async function getMe(): Promise<UserInfo> {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) throw new Error("Not authenticated");
  return res.json();
}

// ── Logout ────────────────────────────────────────────────────────────────────
export async function logout(): Promise<void> {
  const token = localStorage.getItem("access_token");

  // Tell backend to blacklist the token
  if (token) {
    try {
      await fetch(`${API_BASE}/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {
      // Ignore errors — clear local state regardless
    }
  }

  _clearAuth();
}

// ── Account Deletion ──────────────────────────────────────────────────────────
export async function deleteAccount(): Promise<string> {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/account`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Account deletion failed");
  }

  const data = await res.json();
  _clearAuth();
  return data.message;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function _storeAuth(data: LoginResponse) {
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  localStorage.setItem("user", JSON.stringify(data.user));
}

function _clearAuth() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
}

export function getStoredToken(): string | null {
  return localStorage.getItem("access_token");
}

export function getStoredUser(): UserInfo | null {
  const raw = localStorage.getItem("user");
  return raw ? JSON.parse(raw) : null;
}

export function isAuthenticated(): boolean {
  return !!localStorage.getItem("access_token");
}
