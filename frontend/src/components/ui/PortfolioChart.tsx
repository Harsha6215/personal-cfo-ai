import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Spinner } from "./Spinner";
import { getStoredToken } from "@/services/auth";

interface DataPoint {
  date: string;
  value: number;
}

type Range = "1M" | "3M" | "6M" | "1Y" | "custom";

const RANGE_DAYS: Record<Exclude<Range, "custom">, number> = {
  "1M": 30,
  "3M": 90,
  "6M": 180,
  "1Y": 365,
};

const formatValue = (val: number) => `₹${(val / 1000).toFixed(1)}k`;
const formatDate = (d: string) => {
  const date = new Date(d);
  return date.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
};

interface Props {
  days?: number;
}

export function PortfolioChart({ days: initialDays = 365 }: Props) {
  const [data, setData] = useState<DataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [range, setRange] = useState<Range>("1Y");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");
  const [activeDays, setActiveDays] = useState(initialDays);

  const fetchData = async (numDays: number) => {
    setLoading(true);
    try {
      const token = getStoredToken();
      const res = await fetch(`/api/v1/prices/portfolio-performance?days=${numDays}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        let points: DataPoint[] = await res.json();

        // If custom range, filter by dates
        if (range === "custom" && customFrom && customTo) {
          points = points.filter(p => p.date >= customFrom && p.date <= customTo);
        }

        setData(points);
      }
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(activeDays);
  }, [activeDays]);

  const handleRangeClick = (r: Exclude<Range, "custom">) => {
    setRange(r);
    setActiveDays(RANGE_DAYS[r]);
  };

  const handleCustomApply = () => {
    if (!customFrom || !customTo) return;
    setRange("custom");
    // Calculate days between from and today
    const fromDate = new Date(customFrom);
    const today = new Date();
    const diffDays = Math.ceil((today.getTime() - fromDate.getTime()) / (1000 * 60 * 60 * 24));
    setActiveDays(Math.max(diffDays, 30));
  };

  if (loading && data.length === 0) {
    return (
      <div className="flex h-72 items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex h-72 items-center justify-center text-sm text-slate-400">
        No performance data yet.
      </div>
    );
  }

  const minValue = Math.min(...data.map(d => d.value)) * 0.98;
  const maxValue = Math.max(...data.map(d => d.value)) * 1.02;

  return (
    <div>
      {/* Range selector */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {(["1M", "3M", "6M", "1Y"] as const).map(r => (
          <button
            key={r}
            onClick={() => handleRangeClick(r)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
              range === r
                ? "bg-sky-500 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-700 dark:text-slate-300 dark:hover:bg-slate-600"
            }`}
          >
            {r}
          </button>
        ))}

        <span className="mx-2 text-xs text-slate-400">|</span>

        {/* Custom date range */}
        <input
          type="date"
          value={customFrom}
          onChange={e => setCustomFrom(e.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300"
        />
        <span className="text-xs text-slate-400">to</span>
        <input
          type="date"
          value={customTo}
          onChange={e => setCustomTo(e.target.value)}
          className="rounded-lg border border-slate-200 bg-white px-2 py-1 text-xs dark:border-slate-600 dark:bg-slate-800 dark:text-slate-300"
        />
        <button
          onClick={handleCustomApply}
          disabled={!customFrom || !customTo}
          className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-200 disabled:opacity-40 dark:bg-slate-700 dark:text-slate-300"
        >
          Apply
        </button>

        {loading && <Spinner size="sm" className="ml-2" />}
      </div>

      {/* Chart */}
      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.3} />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#475569" }}
              interval={Math.max(1, Math.floor(data.length / 6))}
            />
            <YAxis
              tickFormatter={formatValue}
              tick={{ fill: "#94a3b8", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              domain={[minValue, maxValue]}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #475569",
                borderRadius: "8px",
                fontSize: "12px",
              }}
              labelStyle={{ color: "#94a3b8" }}
              formatter={(value: number) => [`₹${value.toLocaleString("en-IN")}`, "Portfolio"]}
              labelFormatter={formatDate}
            />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#0ea5e9"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, fill: "#0ea5e9" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
