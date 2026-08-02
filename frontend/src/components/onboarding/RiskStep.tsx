import { useState } from "react";
import { Button } from "@/components/ui/Button";

interface Props {
  value: string | null;
  horizon: string | null;
  onNext: (risk: string, horizon: string) => void;
}

const RISK_OPTIONS = [
  { id: "CONSERVATIVE", label: "Conservative", desc: "Capital preservation, low volatility", icon: "🛡️" },
  { id: "MODERATE", label: "Moderate", desc: "Balanced growth with manageable risk", icon: "⚖️" },
  { id: "AGGRESSIVE", label: "Aggressive", desc: "High growth, comfortable with volatility", icon: "🚀" },
  { id: "VERY_AGGRESSIVE", label: "Very Aggressive", desc: "Maximum returns, high risk tolerance", icon: "⚡" },
];

const HORIZON_OPTIONS = [
  { id: "SHORT", label: "< 2 years" },
  { id: "MEDIUM", label: "2-5 years" },
  { id: "LONG", label: "5-10 years" },
  { id: "VERY_LONG", label: "10+ years" },
];

export function RiskStep({ value, horizon, onNext }: Props) {
  const [risk, setRisk] = useState(value || "");
  const [hz, setHz] = useState(horizon || "");

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-2">Risk Appetite</h2>
      <p className="text-sm text-slate-400 mb-5">How comfortable are you with investment volatility?</p>

      <div className="space-y-2 mb-6">
        {RISK_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            onClick={() => setRisk(opt.id)}
            className={`w-full flex items-center gap-3 rounded-xl border p-3.5 text-left transition-all ${
              risk === opt.id
                ? "border-sky-500 bg-sky-500/10"
                : "border-slate-700 bg-slate-700/30 hover:border-slate-600"
            }`}
          >
            <span className="text-xl">{opt.icon}</span>
            <div>
              <div className="text-sm font-medium text-white">{opt.label}</div>
              <div className="text-xs text-slate-400">{opt.desc}</div>
            </div>
          </button>
        ))}
      </div>

      <h3 className="text-sm font-medium text-slate-300 mb-2">Investment Horizon</h3>
      <div className="grid grid-cols-2 gap-2 mb-6">
        {HORIZON_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            onClick={() => setHz(opt.id)}
            className={`rounded-lg border px-3 py-2 text-sm transition-all ${
              hz === opt.id
                ? "border-sky-500 bg-sky-500/10 text-white"
                : "border-slate-700 text-slate-400 hover:border-slate-600"
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      <Button
        variant="primary"
        className="w-full"
        disabled={!risk || !hz}
        onClick={() => onNext(risk, hz)}
      >
        Continue
      </Button>
    </div>
  );
}
