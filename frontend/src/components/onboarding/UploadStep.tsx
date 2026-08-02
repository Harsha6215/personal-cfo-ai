import { useState, useRef } from "react";
import { Button } from "@/components/ui/Button";
import { getStoredToken } from "@/services/auth";

interface Props {
  onNext: () => void;
  onSkip: () => void;
}

export function UploadStep({ onNext, onSkip }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError("");

    const token = getStoredToken();
    const formData = new FormData();
    formData.append("file", file);
    formData.append("portfolio_id", "onboarding"); // Will use first portfolio or create

    try {
      // First, ensure user has a portfolio
      const portfolioRes = await fetch("/api/v1/portfolios", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const portfolios = await portfolioRes.json();

      let portfolioId: string;
      if (portfolios.length > 0) {
        portfolioId = portfolios[0].id;
      } else {
        // Create default portfolio
        const createRes = await fetch("/api/v1/portfolios", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ name: "My Portfolio", currency: "INR" }),
        });
        const newPortfolio = await createRes.json();
        portfolioId = newPortfolio.id;
      }

      // Upload and import
      const uploadFormData = new FormData();
      uploadFormData.append("file", file);
      uploadFormData.append("portfolio_id", portfolioId);

      const res = await fetch("/api/v1/import/upload-and-import", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: uploadFormData,
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail?.message || err.detail || "Upload failed");
      }

      const data = await res.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-2">Import Your Portfolio</h2>
      <p className="text-sm text-slate-400 mb-5">
        Upload a holdings CSV from Zerodha, Groww, or your broker. The AI Portfolio Doctor will analyze it.
      </p>

      {!result ? (
        <>
          <div
            onClick={() => fileRef.current?.click()}
            className="mb-4 flex cursor-pointer flex-col items-center rounded-xl border-2 border-dashed border-slate-600 p-8 transition-colors hover:border-sky-500/50"
          >
            <svg className="mb-3 h-10 w-10 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            {file ? (
              <span className="text-sm text-sky-400">{file.name}</span>
            ) : (
              <>
                <span className="text-sm text-slate-400">Drop CSV here or click to browse</span>
                <span className="mt-1 text-xs text-slate-500">Supports Zerodha, Groww, generic CSV</span>
              </>
            )}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />

          {error && (
            <p className="mb-4 text-sm text-red-400">{error}</p>
          )}

          <div className="flex gap-2">
            <Button
              variant="primary"
              className="flex-1"
              disabled={!file || uploading}
              loading={uploading}
              onClick={handleUpload}
            >
              {uploading ? "Importing…" : "Upload & Import"}
            </Button>
            <Button variant="ghost" className="text-slate-400" onClick={onSkip}>
              Skip
            </Button>
          </div>
        </>
      ) : (
        <div>
          <div className="mb-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
            <p className="text-sm font-medium text-emerald-400">✓ Import successful!</p>
            <p className="mt-1 text-xs text-slate-400">
              {result.rows_imported} transactions imported
            </p>
          </div>
          <Button variant="primary" className="w-full" onClick={onNext}>
            Continue to Portfolio Doctor
          </Button>
        </div>
      )}
    </div>
  );
}
