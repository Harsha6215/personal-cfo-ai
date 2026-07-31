import React from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface Column<T> {
  key: keyof T & string;
  header: string;
  width?: string;
  align?: "left" | "center" | "right";
  render?: (value: T[keyof T], row: T) => React.ReactNode;
}

interface TableProps<T> {
  columns: Column<T>[];
  data: T[];
  emptyMessage?: string;
  onRowClick?: (row: T) => void;
  loading?: boolean;
  className?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function Table<T extends Record<string, unknown>>({
  columns,
  data,
  emptyMessage = "No data available",
  onRowClick,
  loading = false,
  className = "",
}: TableProps<T>) {
  const alignClass = (align?: string) =>
    align === "right" ? "text-right" : align === "center" ? "text-center" : "text-left";

  return (
    <div className={`overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-700 ${className}`}>
      <table className="w-full text-sm" role="table">
        {/* Header */}
        <thead className="border-b border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/50">
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={`px-4 py-3 font-medium text-slate-500 dark:text-slate-400 ${alignClass(col.align)}`}
                style={col.width ? { width: col.width } : undefined}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>

        {/* Body */}
        <tbody className="divide-y divide-slate-100 dark:divide-slate-700">
          {loading ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-slate-400">
                <div className="flex items-center justify-center gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Loading…
                </div>
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center text-slate-400">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, idx) => (
              <tr
                key={idx}
                onClick={() => onRowClick?.(row)}
                className={`bg-white transition-colors dark:bg-slate-800 ${
                  onRowClick
                    ? "cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700"
                    : ""
                }`}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`px-4 py-3 text-slate-700 dark:text-slate-300 ${alignClass(col.align)}`}
                  >
                    {col.render
                      ? col.render(row[col.key], row)
                      : (row[col.key] as React.ReactNode) ?? "—"}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
