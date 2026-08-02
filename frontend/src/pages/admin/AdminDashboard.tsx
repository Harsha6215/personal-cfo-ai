/**
 * Admin Dashboard — Sprint 6.5
 *
 * Metrics overview cards: total users, requests today, errors,
 * active users, response time (p50/p95).
 */

import { useEffect, useState } from "react";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { getStoredToken } from "@/services/auth";

interface Metrics {
  requests_today: number;
  errors_today: number;
  latency_p50: number;
  latency_p95: number;
  active_users_today: number;
}

interface AIUsage {
  llm_calls_today: number;
}

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [aiUsage, setAIUsage] = useState<AIUsage | null>(null);
  const [totalUsers, setTotalUsers] = useState<number>(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData();
  }, []);

  async function fetchData() {
    const token = getStoredToken();
    const headers = { Authorization: `Bearer ${token}` };

    try {
      const [metricsRes, aiRes, usersRes] = await Promise.all([
        fetch("/api/v1/admin/metrics", { headers }),
        fetch("/api/v1/admin/ai-usage", { headers }),
        fetch("/api/v1/admin/users?limit=1", { headers }),
      ]);

      if (!metricsRes.ok || !aiRes.ok || !usersRes.ok) {
        throw new Error("Failed to fetch admin data");
      }

      setMetrics(await metricsRes.json());
      setAIUsage(await aiRes.json());

      const users = await usersRes.json();
      // The users endpoint returns a list; we need total count
      // For now use array length as an approximation, or fetch all
      const allUsersRes = await fetch("/api/v1/admin/users?limit=200", { headers });
      if (allUsersRes.ok) {
        const allUsers = await allUsersRes.json();
        setTotalUsers(allUsers.length);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load metrics");
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-slate-500">Loading admin dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700 dark:border-red-800 dark:bg-red-900/20 dark:text-red-400">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
        Admin Dashboard
      </h1>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <MetricCard title="Total Users" value={totalUsers} />
        <MetricCard title="Requests Today" value={metrics?.requests_today ?? 0} />
        <MetricCard
          title="Errors Today"
          value={metrics?.errors_today ?? 0}
          highlight={metrics?.errors_today ? metrics.errors_today > 0 : false}
        />
        <MetricCard title="Active Users Today" value={metrics?.active_users_today ?? 0} />
        <MetricCard
          title="Latency P50"
          value={`${metrics?.latency_p50 ?? 0} ms`}
        />
        <MetricCard
          title="Latency P95"
          value={`${metrics?.latency_p95 ?? 0} ms`}
        />
        <MetricCard title="LLM Calls Today" value={aiUsage?.llm_calls_today ?? 0} />
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  highlight = false,
}: {
  title: string;
  value: string | number;
  highlight?: boolean;
}) {
  return (
    <Card>
      <CardHeader title={title} />
      <CardBody>
        <p
          className={`text-3xl font-bold ${
            highlight
              ? "text-red-600 dark:text-red-400"
              : "text-slate-900 dark:text-slate-100"
          }`}
        >
          {value}
        </p>
      </CardBody>
    </Card>
  );
}
