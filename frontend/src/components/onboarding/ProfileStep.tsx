import { useState } from "react";
import { Button } from "@/components/ui/Button";
import type { OnboardingData } from "@/pages/Onboarding";

interface Props {
  data: OnboardingData;
  onNext: (updates: Partial<OnboardingData>) => void;
}

const EXPERIENCE_OPTIONS = [
  { id: "BEGINNER", label: "Beginner", desc: "New to investing" },
  { id: "INTERMEDIATE", label: "Intermediate", desc: "1-3 years experience" },
  { id: "ADVANCED", label: "Advanced", desc: "3-7 years, active trader" },
  { id: "EXPERT", label: "Expert", desc: "7+ years, deep knowledge" },
];

export function ProfileStep({ data, onNext }: Props) {
  const [age, setAge] = useState(data.age?.toString() || "");
  const [income, setIncome] = useState(data.monthly_income?.toString() || "");
  const [experience, setExperience] = useState(data.experience_level || "");

  const handleSubmit = () => {
    onNext({
      age: age ? parseInt(age) : null,
      monthly_income: income ? parseFloat(income) : null,
      experience_level: experience || null,
    });
  };

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-2">About You</h2>
      <p className="text-sm text-slate-400 mb-5">Helps calibrate AI recommendations</p>

      <div className="space-y-4 mb-6">
        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-300">Age</label>
          <input
            type="number"
            min="18"
            max="100"
            value={age}
            onChange={(e) => setAge(e.target.value)}
            className="input"
            placeholder="30"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-sm font-medium text-slate-300">
            Monthly Income (₹)
          </label>
          <input
            type="number"
            min="0"
            value={income}
            onChange={(e) => setIncome(e.target.value)}
            className="input"
            placeholder="100000"
          />
          <p className="mt-1 text-xs text-slate-500">Used for savings rate analysis. Never shared.</p>
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-slate-300">
            Investment Experience
          </label>
          <div className="grid grid-cols-2 gap-2">
            {EXPERIENCE_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                onClick={() => setExperience(opt.id)}
                className={`rounded-lg border px-3 py-2 text-left transition-all ${
                  experience === opt.id
                    ? "border-sky-500 bg-sky-500/10"
                    : "border-slate-700 hover:border-slate-600"
                }`}
              >
                <div className="text-xs font-medium text-white">{opt.label}</div>
                <div className="text-[10px] text-slate-400">{opt.desc}</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      <Button variant="primary" className="w-full" onClick={handleSubmit}>
        Continue
      </Button>
    </div>
  );
}
