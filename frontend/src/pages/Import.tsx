import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, Column } from "@/components/ui/Table";
import { useToast } from "@/components/ui/Toast";
import { getStoredToken } from "@/services/auth";

interface PreviewData {
  import_job_id: string | null;
  total_rows: number;
  valid_transactions: number;
  duplicates: number;
  errors: number;
  new_assets: string[];
  validation_errors: string[];
}

interface ImportResult {
  import_job_id: string;
  status: string;
  rows_imported: number;
  rows_failed: number;
  rows_duplicate: number;
  duration_ms: number | null;
}

export default function Import() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState<"upload" | "preview" | "done">("upload");
  const { toast } = useToast();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      setPreview(null);
      setResult(null);
      setStep("upload");
    }
  };

  const handlePreview = async () => {
    if (!file) return;
    setLoading(true);

    try {
      const token = getStoredToken();
      const formData = new FormData();
      formData.append("file", file);
      formData.append("portfolio_id", "default"); // We'll create one if needed

      const res = await fetch("/api/v1/import/upload", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail?.message || err.detail || "Preview failed");
      }

      const data: PreviewData = await res.json();
      setPreview(data);
      setStep("preview");
    } catch (err: any) {
      toast(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  const handleImport = async () => {
    if (!file) return;
    setLoading(true);

    try {
      const token = getStoredToken();
      const formData = new FormData();
      formData.append("file", file);
      formData.append("portfolio_id", "default");

      const res = await fetch("/api/v1/import/upload-and-import", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail?.message || err.detail || "Import failed");
      }

      const data: ImportResult = await res.json();
      setResult(data);
      setStep("done");
      toast(`Imported ${data.rows_imported} transactions successfully!`, "success");
    } catch (err: any) {
      toast(err.message, "error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">Import Portfolio</h2>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Upload your broker CSV to import holdings and transactions.
        </p>
      </div>

      {/* Step 1: Upload */}
      <Card>
        <CardHeader title="Upload File" subtitle="Supported: Zerodha Holdings CSV" />

        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <label
              htmlFor="csv-upload"
              className="flex cursor-pointer items-center gap-2 rounded-lg border-2 border-dashed border-slate-300 px-6 py-4 transition-colors hover:border-sky-400 dark:border-slate-600 dark:hover:border-sky-500"
            >
              <svg className="h-6 w-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span className="text-sm text-slate-600 dark:text-slate-300">
                {file ? file.name : "Choose CSV file…"}
              </span>
              <input
                id="csv-upload"
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleFileChange}
              />
            </label>

            {file && step === "upload" && (
              <Button onClick={handlePreview} loading={loading}>
                Preview
              </Button>
            )}
          </div>

          {file && (
            <p className="text-xs text-slate-500">
              {file.name} — {(file.size / 1024).toFixed(1)} KB
            </p>
          )}
        </div>
      </Card>

      {/* Step 2: Preview */}
      {preview && step === "preview" && (
        <Card>
          <CardHeader title="Import Preview" subtitle="Review before importing" />

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-lg bg-sky-50 p-3 dark:bg-sky-900/20">
              <p className="text-2xl font-bold text-sky-600 dark:text-sky-400">{preview.total_rows}</p>
              <p className="text-xs text-slate-500">Total Rows</p>
            </div>
            <div className="rounded-lg bg-emerald-50 p-3 dark:bg-emerald-900/20">
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{preview.valid_transactions}</p>
              <p className="text-xs text-slate-500">Valid</p>
            </div>
            <div className="rounded-lg bg-yellow-50 p-3 dark:bg-yellow-900/20">
              <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{preview.duplicates}</p>
              <p className="text-xs text-slate-500">Duplicates</p>
            </div>
            <div className="rounded-lg bg-red-50 p-3 dark:bg-red-900/20">
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">{preview.errors}</p>
              <p className="text-xs text-slate-500">Errors</p>
            </div>
          </div>

          {preview.new_assets.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
                New assets to be created:
              </p>
              <div className="mt-1 flex flex-wrap gap-2">
                {preview.new_assets.map((ticker) => (
                  <span key={ticker} className="badge-blue">{ticker}</span>
                ))}
              </div>
            </div>
          )}

          {preview.validation_errors.length > 0 && (
            <div className="mt-4 rounded-lg bg-red-50 p-3 dark:bg-red-900/20">
              <p className="text-sm font-medium text-red-700 dark:text-red-300">Errors:</p>
              <ul className="mt-1 list-disc pl-4 text-xs text-red-600 dark:text-red-400">
                {preview.validation_errors.map((err, i) => <li key={i}>{err}</li>)}
              </ul>
            </div>
          )}

          <div className="mt-6 flex gap-3">
            <Button onClick={handleImport} loading={loading}>
              Import {preview.valid_transactions} Transactions
            </Button>
            <Button variant="secondary" onClick={() => { setStep("upload"); setPreview(null); }}>
              Cancel
            </Button>
          </div>
        </Card>
      )}

      {/* Step 3: Result */}
      {result && step === "done" && (
        <Card>
          <CardHeader title="Import Complete ✓" />

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-lg bg-emerald-50 p-3 dark:bg-emerald-900/20">
              <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{result.rows_imported}</p>
              <p className="text-xs text-slate-500">Imported</p>
            </div>
            <div className="rounded-lg bg-yellow-50 p-3 dark:bg-yellow-900/20">
              <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{result.rows_duplicate}</p>
              <p className="text-xs text-slate-500">Duplicates Skipped</p>
            </div>
            <div className="rounded-lg bg-red-50 p-3 dark:bg-red-900/20">
              <p className="text-2xl font-bold text-red-600 dark:text-red-400">{result.rows_failed}</p>
              <p className="text-xs text-slate-500">Failed</p>
            </div>
            <div className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800">
              <p className="text-2xl font-bold text-slate-600 dark:text-slate-300">{result.duration_ms}ms</p>
              <p className="text-xs text-slate-500">Duration</p>
            </div>
          </div>

          <div className="mt-4">
            <span className={`badge ${result.status === "COMPLETED" ? "badge-green" : result.status === "PARTIAL" ? "badge-yellow" : "badge-red"}`}>
              {result.status}
            </span>
          </div>

          <div className="mt-6">
            <Button variant="secondary" onClick={() => { setFile(null); setPreview(null); setResult(null); setStep("upload"); }}>
              Import Another File
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
