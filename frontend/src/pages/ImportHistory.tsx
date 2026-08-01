import { useEffect, useState } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, Column } from "@/components/ui/Table";
import { Spinner } from "@/components/ui/Spinner";
import { getStoredToken } from "@/services/auth";

interface ImportJob {
  id: string;
  source: string;
  filename: string | null;
  status: string;
  rows_total: number;
  rows_imported: number;
  rows_failed: number;
  rows_duplicate: number;
  duration_ms: number | null;
  created_at: string;
}

const statusBadge = (status: string) => {
  const map: Record<string, string> = {
    COMPLETED: "badge-green",
    PARTIAL: "badge-yellow",
    FAILED: "badge-red",
    PREVIEWING: "badge-blue",
    PENDING: "badge-blue",
    IMPORTING: "badge-blue",
  };
  return <span className={`badge ${map[status] || "badge-blue"}`}>{status}</span>;
};

const columns: Column<ImportJob>[] = [
  {
    key: "created_at",
    header: "Date",
    render: (val) => {
      const d = new Date(val as string);
      return <span className="text-xs">{d.toLocaleDateString("en-IN")} {d.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</span>;
    },
  },
  { key: "source", header: "Source" },
  {
    key: "filename",
    header: "File",
    render: (val) => <span className="text-xs truncate max-w-[150px] inline-block">{val || "—"}</span>,
  },
  {
    key: "rows_imported",
    header: "Imported",
    align: "right",
    render: (val, row) => (
      <span className="font-mono">
        {row.rows_imported}/{row.rows_total}
      </span>
    ),
  },
  {
    key: "rows_duplicate",
    header: "Dupes",
    align: "right",
    render: (val) => <span className="font-mono text-yellow-600 dark:text-yellow-400">{Number(val) || "—"}</span>,
  },
  {
    key: "rows_failed",
    header: "Failed",
    align: "right",
    render: (val) => <span className={`font-mono ${Number(val) > 0 ? "text-red-600 dark:text-red-400" : ""}`}>{Number(val) || "—"}</span>,
  },
  {
    key: "duration_ms",
    header: "Duration",
    align: "right",
    render: (val) => <span className="text-xs text-slate-500">{val ? `${val}ms` : "—"}</span>,
  },
  {
    key: "status",
    header: "Status",
    align: "center",
    render: (val) => statusBadge(val as string),
  },
];

export default function ImportHistory() {
  const [jobs, setJobs] = useState<ImportJob[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchJobs() {
      try {
        const token = getStoredToken();
        const res = await fetch("/api/v1/import/jobs", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          setJobs(await res.json());
        }
      } catch {
        // ignore
      } finally {
        setLoading(false);
      }
    }
    fetchJobs();
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Import History</h2>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Audit trail of all portfolio imports. Data is never overwritten.
          </p>
        </div>
        <a href="/import" className="btn-primary text-sm">
          New Import
        </a>
      </div>

      <Card>
        <Table
          columns={columns}
          data={jobs}
          emptyMessage="No imports yet. Upload your first CSV to get started."
        />
      </Card>

      {jobs.length > 0 && (
        <p className="text-xs text-slate-400 text-center">
          Showing {jobs.length} import{jobs.length !== 1 ? "s" : ""}. Each import creates an immutable audit record.
        </p>
      )}
    </div>
  );
}
