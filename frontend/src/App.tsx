import { Routes, Route, Navigate } from "react-router-dom";

// Pages — implemented in Story 4
const Dashboard = () => (
  <div className="flex h-screen items-center justify-center bg-surface-dark text-white">
    <div className="text-center">
      <h1 className="text-3xl font-bold text-primary-500">Personal CFO AI</h1>
      <p className="mt-2 text-slate-400">Dashboard — coming in Story 4</p>
      <div className="mt-6 flex gap-4 justify-center">
        <StatusBadge label="Backend" url="/api/health" />
      </div>
    </div>
  </div>
);

const Login = () => (
  <div className="flex h-screen items-center justify-center bg-surface-dark text-white">
    <div className="text-center">
      <h1 className="text-3xl font-bold text-primary-500">Personal CFO AI</h1>
      <p className="mt-2 text-slate-400">Login — coming in Story 6</p>
    </div>
  </div>
);

// Temporary health badge to verify backend connectivity
const StatusBadge = ({ label, url }: { label: string; url: string }) => {
  const [status, setStatus] = React.useState<"checking" | "ok" | "error">("checking");

  React.useEffect(() => {
    fetch(url)
      .then((r) => (r.ok ? setStatus("ok") : setStatus("error")))
      .catch(() => setStatus("error"));
  }, [url]);

  const colours = {
    checking: "bg-yellow-500",
    ok: "bg-green-500",
    error: "bg-red-500",
  };

  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm ${colours[status]}`}>
      <span className="h-2 w-2 rounded-full bg-white" />
      {label}: {status}
    </span>
  );
};

import React from "react";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/login" element={<Login />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
