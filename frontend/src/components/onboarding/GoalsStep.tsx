import { useState } from "react";
import { Button } from "@/components/ui/Button";

interface Props {
  value: string[];
  onNext: (goals: string[]) => void;
}

const GOAL_OPTIONS = [
  { id: "WEALTH_GROWTH", label: "Wealth Growth", icon: "📈", desc: "Grow my portfolio over time" },
  { id: "RETIREMENT", label: "Retirement", icon: "🏖️", desc: "Build a retirement corpus" },
  { id: "TAX_SAVING", label: "Tax Saving", icon: "💰", desc: "Minimize tax liability" },
  { id: "EMERGENCY_FUND", label: "Emergency Fund", icon: "🏦", desc: "Build 6-12 months buffer" },
  { id: "CHILDREN_EDUCATION", label: "Children's Education", icon: "🎓", desc: "Fund education expenses" },
  { id: "HOME_PURCHASE", label: "Home Purchase", icon: "🏠", desc: "Save for a house" },
  { id: "PASSIVE_INCOME", label: "Passive Income", icon: "💸", desc: "Generate regular dividends" },
  { id: "FINANCIAL_FREEDOM", label: "Financial Freedom", icon: "🎯", desc: "Achieve FIRE" },
];

export function GoalsStep({ value, onNext }: Props) {
  const [selected, setSelected] = useState<string[]>(value || []);

  const toggle = (id: string) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((g) => g !== id) : [...prev, id]
    );
  };

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-2">Financial Goals</h2>
      <p className="text-sm text-slate-400 mb-5">Select all that apply (at least 1)</p>

      <div className="grid grid-cols-2 gap-2 mb-6">
        {GOAL_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            onClick={() => toggle(opt.id)}
            className={`flex items-center gap-2 rounded-xl border p-3 text-left transition-all ${
              selected.includes(opt.id)
                ? "border-sky-500 bg-sky-500/10"
                : "border-slate-700 bg-slate-700/30 hover:border-slate-600"
            }`}
          >
            <span className="text-lg">{opt.icon}</span>
            <div>
              <div className="text-xs font-medium text-white">{opt.label}</div>
              <div className="text-[10px] text-slate-400">{opt.desc}</div>
            </div>
          </button>
        ))}
      </div>

      <Button
        variant="primary"
        className="w-full"
        disabled={selected.length === 0}
        onClick={() => onNext(selected)}
      >
        Continue
      </Button>
    </div>
  );
}
