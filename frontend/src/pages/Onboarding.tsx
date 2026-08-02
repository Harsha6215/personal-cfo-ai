import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { getStoredToken } from "@/services/auth";

// Steps
import { RiskStep } from "@/components/onboarding/RiskStep";
import { GoalsStep } from "@/components/onboarding/GoalsStep";
import { ProfileStep } from "@/components/onboarding/ProfileStep";
import { UploadStep } from "@/components/onboarding/UploadStep";
import { DoctorResult } from "@/components/onboarding/DoctorResult";

const API_BASE = "/api/v1/onboarding";

export interface OnboardingData {
  risk_appetite: string | null;
  investment_horizon: string | null;
  monthly_income: number | null;
  age: number | null;
  primary_goals: string[];
  experience_level: string | null;
}

const STEPS = ["Welcome", "Risk", "Goals", "Profile", "Upload", "Doctor"];

export default function Onboarding() {
  const [step, setStep] = useState(0);
  const [data, setData] = useState<OnboardingData>({
    risk_appetite: null,
    investment_horizon: null,
    monthly_income: null,
    age: null,
    primary_goals: [],
    experience_level: null,
  });
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  // Load existing profile on mount
  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    const token = getStoredToken();
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE}/profile`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const profile = await res.json();
        setData({
          risk_appetite: profile.risk_appetite,
          investment_horizon: profile.investment_horizon,
          monthly_income: profile.monthly_income,
          age: profile.age,
          primary_goals: profile.primary_goals || [],
          experience_level: profile.experience_level,
        });
        if (profile.onboarding_completed_at) {
          navigate("/dashboard");
        } else if (profile.onboarding_step > 0) {
          setStep(profile.onboarding_step);
        }
      }
    } catch {
      // Ignore — fresh start
    }
  };

  const saveProgress = async (stepNum: number, extraData?: Partial<OnboardingData>) => {
    const token = getStoredToken();
    if (!token) return;

    const updatePayload = { ...extraData, onboarding_step: stepNum };
    try {
      await fetch(`${API_BASE}/profile`, {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(updatePayload),
      });
    } catch {
      // Continue even if save fails
    }
  };

  const nextStep = async (extraData?: Partial<OnboardingData>) => {
    if (extraData) {
      setData((prev) => ({ ...prev, ...extraData }));
    }
    const next = step + 1;
    setStep(next);
    await saveProgress(next, extraData);
  };

  const completeOnboarding = async () => {
    const token = getStoredToken();
    if (!token) return;
    setLoading(true);
    try {
      await fetch(`${API_BASE}/complete`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      toast("Onboarding complete! Welcome aboard.", "success");
      navigate("/dashboard");
    } catch {
      toast("Failed to complete onboarding", "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-900 p-4">
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 h-96 w-96 rounded-full bg-sky-500/10 blur-3xl" />
        <div className="absolute -bottom-40 -left-40 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl" />
      </div>

      <div className="relative w-full max-w-lg">
        {/* Progress bar */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-slate-400">Step {step + 1} of {STEPS.length}</span>
            <span className="text-xs text-slate-500">{STEPS[step]}</span>
          </div>
          <div className="h-1.5 rounded-full bg-slate-700 overflow-hidden">
            <div
              className="h-full rounded-full bg-sky-500 transition-all duration-500"
              style={{ width: `${((step + 1) / STEPS.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Step content */}
        <div className="rounded-2xl border border-slate-700 bg-slate-800 p-8 shadow-2xl">
          {step === 0 && (
            <WelcomeStep onNext={() => nextStep()} />
          )}
          {step === 1 && (
            <RiskStep
              value={data.risk_appetite}
              horizon={data.investment_horizon}
              onNext={(risk, horizon) => nextStep({ risk_appetite: risk, investment_horizon: horizon })}
            />
          )}
          {step === 2 && (
            <GoalsStep
              value={data.primary_goals}
              onNext={(goals) => nextStep({ primary_goals: goals })}
            />
          )}
          {step === 3 && (
            <ProfileStep
              data={data}
              onNext={(updates) => nextStep(updates)}
            />
          )}
          {step === 4 && (
            <UploadStep onNext={() => nextStep()} onSkip={() => nextStep()} />
          )}
          {step === 5 && (
            <DoctorResult onComplete={completeOnboarding} loading={loading} />
          )}
        </div>
      </div>
    </div>
  );
}

function WelcomeStep({ onNext }: { onNext: () => void }) {
  return (
    <div className="text-center">
      <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-sky-500/20">
        <svg className="h-8 w-8 text-sky-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
      </div>
      <h2 className="text-xl font-bold text-white mb-3">Welcome to Personal CFO AI</h2>
      <p className="text-slate-400 mb-6">
        Let's set up your profile in 2 minutes. This helps our AI give you
        personalized investment recommendations, risk-adjusted alerts, and
        portfolio optimization.
      </p>
      <ul className="text-left text-sm text-slate-400 space-y-2 mb-8">
        <li className="flex items-center gap-2">
          <span className="text-sky-400">✓</span> Personalized risk assessment
        </li>
        <li className="flex items-center gap-2">
          <span className="text-sky-400">✓</span> Goal-based recommendations
        </li>
        <li className="flex items-center gap-2">
          <span className="text-sky-400">✓</span> AI Portfolio Doctor analysis
        </li>
      </ul>
      <Button variant="primary" className="w-full" onClick={onNext}>
        Let's get started
      </Button>
    </div>
  );
}
