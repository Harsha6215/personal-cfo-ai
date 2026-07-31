import React from "react";

/**
 * Chart placeholder component.
 *
 * In a full implementation, wrap Recharts or Chart.js here.
 * For now, this provides the visual container and loading states
 * so other components can use <Chart /> without importing a library directly.
 *
 * When ready to add real charts (Epic 2+):
 *   npm install recharts
 *   Then implement line/bar/pie variants inside this file.
 */

type ChartType = "line" | "bar" | "pie" | "area";

interface ChartProps {
  type?: ChartType;
  title?: string;
  height?: number;
  data?: unknown[];
  loading?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function Chart({
  type = "line",
  title,
  height = 200,
  data,
  loading = false,
  className = "",
  children,
}: ChartProps) {
  const hasData = data && data.length > 0;

  return (
    <div className={`rounded-lg border border-slate-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800 ${className}`}>
      {title && (
        <h4 className="mb-3 text-sm font-medium text-slate-700 dark:text-slate-300">{title}</h4>
      )}

      <div
        className="flex items-center justify-center rounded-md bg-slate-50 dark:bg-slate-900/50"
        style={{ height }}
      >
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading chart…
          </div>
        ) : children ? (
          // If children provided, render them (for when Recharts is integrated)
          <div className="h-full w-full">{children}</div>
        ) : hasData ? (
          // Minimal visual placeholder showing data exists
          <div className="flex h-full w-full items-end gap-1 px-4 pb-2">
            {(data as number[]).slice(0, 20).map((val, i) => (
              <div
                key={i}
                className="flex-1 rounded-t bg-sky-500/60 transition-all dark:bg-sky-400/40"
                style={{ height: `${Math.min(100, Math.max(10, (val as number / Math.max(...(data as number[]))) * 100))}%` }}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-slate-400">
            {type.charAt(0).toUpperCase() + type.slice(1)} chart — add data in Epic 2+
          </p>
        )}
      </div>
    </div>
  );
}
