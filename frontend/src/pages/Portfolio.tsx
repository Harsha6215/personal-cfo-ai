import { useEffect, useState } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table, Column } from "@/components/ui/Table";
import { Spinner } from "@/components/ui/Spinner";
import { getStoredToken } from "@/services/auth";

interface Holding {
  asset_id: string;
  ticker: string;
  name: string;
  asset_type: string;
  quantity: number;
  average_cost: number;
  invested_value: number;
}

interface PortfolioData {
  portfolio_id: string;
  portfolio_name: string;
  total_invested: number;
  total_holdings: number;
  total_events: number;
  holdings: Holding[];
}

const columns: Column<Holding>[] = [
  {
    key: "ticker",
    header: "Ticker",
    render: (val, row) => (
      <div>
        <p className="font-medium text-slate-900 dark:text-slate-100">{row.ticker}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">{row.name}</p>
      </div>
    ),
  },
  { key: "asset_type", header: "Type", width: "80px" },
  {
    key: "quantity",
    header: "Qty",
    align: "right",
    render: (val) => <span className="font-mono">{Number(val).toLocaleString()}</span>,
  },
  {
    key: "average_cost",
    header: "Avg Cost",
    align: "right",
    render: (val) => <span className="font-mono">₹{Number(val).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>,
  },
  {
    key: "invested_value",
    header: "Invested",
    align: "right",
    render: (val) => <span className="font-mono font-medium">₹{Number(val).toLocaleString("en-IN", { minimumFractionDigits: 2 })}</span>,
  },
];

export default function Portfolio() {
  const [data, setData] = useState<PortfolioData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchPortfolio() {
      try {
        const token = getStoredToken();

        // Get user's portfolios
        const res = await fetch("/api/v1/portfolios", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!res.ok) throw new Error("Failed to fetch portfolios");

        const portfolios = await res.json();
        if (portfolios.length === 0) {
          setError("No portfolio found. Import your holdings first.");
          setLoading(false);
          return;
        }

        // Get holdings for first portfolio
        const holdingsRes = await fetch(`/api/v1/portfolios/${portfolios[0].id}/holdings`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!holdingsRes.ok) throw new Error("Failed to fetch holdings");

        const holdingsData: PortfolioData = await holdingsRes.json();
        setData(holdingsData);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }

    fetchPortfolio();
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="text-center">
          <p className="text-slate-500 dark:text-slate-400">{error}</p>
          <a href="/import" className="mt-2 inline-block text-sm text-sky-500 hover:text-sky-400">
            Go to Import →
          </a>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <div className="text-center">
            <p className="text-sm text-slate-500 dark:text-slate-400">Total Invested</p>
            <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">
              ₹{data.total_invested.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
            </p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-sm text-slate-500 dark:text-slate-400">Holdings</p>
            <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">
              {data.total_holdings}
            </p>
          </div>
        </Card>
        <Card>
          <div className="text-center">
            <p className="text-sm text-slate-500 dark:text-slate-400">Transactions</p>
            <p className="mt-1 text-2xl font-bold text-slate-900 dark:text-slate-100">
              {data.total_events}
            </p>
          </div>
        </Card>
      </div>

      {/* Holdings table */}
      <Card>
        <CardHeader
          title={`${data.portfolio_name} — Holdings`}
          subtitle={`${data.total_holdings} positions across ${data.total_events} transactions`}
        />
        <Table
          columns={columns}
          data={data.holdings}
          emptyMessage="No holdings yet. Import your broker CSV to get started."
        />
      </Card>
    </div>
  );
}
