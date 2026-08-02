import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { login, register, loginWithGoogle, requestOTP, verifyOTP } from "@/services/auth";

type AuthMode = "login" | "register" | "otp-request" | "otp-verify";

// Google Client ID — from env
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";

export default function Login() {
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  // ── Google Identity Services ────────────────────────────────────────────────
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;

    // Load the Google Identity Services script
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.onload = () => {
      window.google?.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleCallback,
      });
      window.google?.accounts.id.renderButton(
        document.getElementById("google-signin-btn"),
        { theme: "filled_black", size: "large", width: "100%", text: "signin_with" }
      );
    };
    document.body.appendChild(script);

    return () => {
      document.body.removeChild(script);
    };
  }, []);

  const handleGoogleCallback = async (response: any) => {
    setLoading(true);
    try {
      await loginWithGoogle(response.credential);
      toast("Welcome to Personal CFO AI", "success");
      navigate("/dashboard");
    } catch (err: any) {
      toast(err.message || "Google login failed", "error");
    } finally {
      setLoading(false);
    }
  };

  // ── Form submission ─────────────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (mode === "register") {
        await register(email, password, fullName || undefined);
        toast("Account created! Logging you in…", "success");
        await login(email, password);
        navigate("/onboarding");
      } else if (mode === "otp-request") {
        await requestOTP(email);
        toast("OTP sent to your email (check server logs in dev)", "success");
        setMode("otp-verify");
      } else if (mode === "otp-verify") {
        await verifyOTP(email, otp);
        toast("Welcome to Personal CFO AI", "success");
        await checkOnboardingAndRedirect();
      } else {
        await login(email, password);
        toast("Welcome to Personal CFO AI", "success");
        await checkOnboardingAndRedirect();
      }
    } catch (err: any) {
      toast(err.message || "Authentication failed", "error");
    } finally {
      setLoading(false);
    }
  };

  const checkOnboardingAndRedirect = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const res = await fetch("/api/v1/onboarding/status", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const status = await res.json();
        if (!status.completed) {
          navigate("/onboarding");
          return;
        }
      }
    } catch {
      // If check fails, just go to dashboard
    }
    navigate("/dashboard");
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-900 p-4">
      {/* Background gradient */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full bg-sky-500/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-sky-500/10 blur-3xl" />
      </div>

      <div className="relative w-full max-w-md">
        {/* Logo */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-sky-500 shadow-lg shadow-sky-500/30">
            <svg className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-white">Personal CFO AI</h1>
          <p className="mt-1 text-sm text-slate-400">Your intelligent finance platform</p>
        </div>

        {/* Card */}
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-8 shadow-2xl">
          <h2 className="mb-6 text-lg font-semibold text-white">
            {mode === "login" && "Sign in"}
            {mode === "register" && "Create account"}
            {mode === "otp-request" && "Passwordless sign in"}
            {mode === "otp-verify" && "Enter verification code"}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            {/* Full name — register only */}
            {mode === "register" && (
              <div>
                <label htmlFor="fullName" className="mb-1.5 block text-sm font-medium text-slate-300">
                  Full name
                </label>
                <input
                  id="fullName"
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="input"
                  placeholder="Harshavardhan Reddy"
                />
              </div>
            )}

            {/* Email — always shown except otp-verify */}
            {mode !== "otp-verify" && (
              <div>
                <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-slate-300">
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input"
                  placeholder="you@example.com"
                />
              </div>
            )}

            {/* OTP verify — show code and email (read-only) */}
            {mode === "otp-verify" && (
              <>
                <div>
                  <label className="mb-1.5 block text-sm font-medium text-slate-300">
                    Email
                  </label>
                  <input
                    type="email"
                    value={email}
                    disabled
                    className="input opacity-60"
                  />
                </div>
                <div>
                  <label htmlFor="otp" className="mb-1.5 block text-sm font-medium text-slate-300">
                    Verification code
                  </label>
                  <input
                    id="otp"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                    className="input text-center text-2xl tracking-widest"
                    placeholder="000000"
                    autoFocus
                  />
                  <p className="mt-1 text-xs text-slate-500">Check your email (or server logs in dev mode)</p>
                </div>
              </>
            )}

            {/* Password — login and register only */}
            {(mode === "login" || mode === "register") && (
              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <label htmlFor="password" className="text-sm font-medium text-slate-300">
                    Password
                  </label>
                  {mode === "login" && (
                    <button
                      type="button"
                      onClick={() => setMode("otp-request")}
                      className="text-xs text-sky-400 hover:text-sky-300"
                    >
                      Use OTP instead
                    </button>
                  )}
                </div>
                <input
                  id="password"
                  type="password"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input"
                  placeholder="••••••••"
                />
                {mode === "register" && (
                  <p className="mt-1 text-xs text-slate-500">Minimum 8 characters</p>
                )}
              </div>
            )}

            <Button type="submit" variant="primary" className="w-full" loading={loading}>
              {loading ? "Please wait…" : (
                mode === "login" ? "Sign in" :
                mode === "register" ? "Create account" :
                mode === "otp-request" ? "Send code" :
                "Verify & sign in"
              )}
            </Button>
          </form>

          {/* Mode switchers */}
          <div className="mt-6 text-center text-sm text-slate-500">
            {mode === "login" && (
              <>
                Don't have an account?{" "}
                <button onClick={() => setMode("register")} className="text-sky-400 hover:text-sky-300">
                  Create one
                </button>
              </>
            )}
            {mode === "register" && (
              <>
                Already have an account?{" "}
                <button onClick={() => setMode("login")} className="text-sky-400 hover:text-sky-300">
                  Sign in
                </button>
              </>
            )}
            {(mode === "otp-request" || mode === "otp-verify") && (
              <button onClick={() => setMode("login")} className="text-sky-400 hover:text-sky-300">
                ← Back to password login
              </button>
            )}
          </div>

          {/* Google Sign-In */}
          {(mode === "login" || mode === "register") && (
            <div className="mt-6">
              <div className="relative flex items-center">
                <div className="flex-grow border-t border-slate-700" />
                <span className="mx-3 text-xs text-slate-500">or continue with</span>
                <div className="flex-grow border-t border-slate-700" />
              </div>

              <div className="mt-4">
                {GOOGLE_CLIENT_ID ? (
                  <div id="google-signin-btn" className="flex justify-center" />
                ) : (
                  <button
                    disabled
                    className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-700/50 px-4 py-2.5 text-sm text-slate-400 opacity-60 cursor-not-allowed"
                  >
                    <GoogleIcon />
                    Google (set VITE_GOOGLE_CLIENT_ID to enable)
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function GoogleIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24">
      <path
        fill="currentColor"
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
      />
      <path
        fill="currentColor"
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
      />
      <path
        fill="currentColor"
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
      />
      <path
        fill="currentColor"
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
      />
    </svg>
  );
}

// Type declarations for Google Identity Services
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: any) => void;
          renderButton: (el: HTMLElement | null, options: any) => void;
          prompt: () => void;
        };
      };
    };
  }
}
