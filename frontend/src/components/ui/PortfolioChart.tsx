import { useEffect, useState } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Spinner } from "./Spinner";
import { getStoredToken } from "@/services/auth";

interface DataPoint {
  date: string;
  value: number;
}

interface Props {
  days?: number;
}

const formatValue = (val: number) => `₹${(val / 1000).toFixed(1)}k`;
const formatDate = (d: string) => {
  const date = new Date(d);
  return date.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
};

export function PortfolioChart({ days = 365 }: Props) {
  const [data, setData] = useState<DataPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetch_data() {
      try {
        const token = getStoredToken();
        const res = await fetch(`/api/v1/prices/portfolio-performance?days=${days}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const points: DataPoint[] = await res.json();
          setData(points);
        }
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    fetch_data();
  }, [days]);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="md" />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center text-sm text-slate-400">
        No performance data yet. Import holdings to see the chart.
      </div>
    );
  }

  const minValue = Math.min(...data.map(d => d.value)) * 0.98;
  const maxValue = Math.max(...data.map(d => d.value)) * 1.02;

  return (
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
            interval={Math.floor(data.length / 6)}
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
  );
}
