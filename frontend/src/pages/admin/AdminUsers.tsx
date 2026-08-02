/**
 * Admin Users Page — Sprint 6.5
 *
 * User management table with: email, role, status, created date, actions.
 */

import { useEffect, useState } from "react";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { getStoredToken } from "@/services/auth";

interface UserItem {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
}

export default function AdminUsers() {
  const [users, setUsers] = useState<UserItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  useEffect(() => {
    fetchUsers();
  }, []);

  async function fetchUsers() {
    const token = getStoredToken();
    try {
      const res = await fetch("/api/v1/admin/users?limit=200", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error("Failed to fetch users");
      setUsers(await res.json());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function toggleUserStatus(userId: string, activate: boolean) {
    const token = getStoredToken();
    const action = activate ? "activate" : "deactivate";
    setActionLoading(userId);

    try {
      const res = await fetch(`/api/v1/admin/users/${userId}/${action}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `Failed to ${action} user`);
      }
      // Refresh the list
      await fetchUsers();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-slate-500">Loading users...</div>
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
        User Management
      </h1>

      <Card>
        <CardHeader title="All Users" subtitle={`${users.length} users total`} />
        <CardBody>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-400">Email</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-400">Name</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-400">Role</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-400">Status</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-400">Created</th>
                  <th className="px-3 py-2 font-medium text-slate-600 dark:text-slate-400">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr
                    key={user.id}
                    className="border-b border-slate-100 dark:border-slate-800"
                  >
                    <td className="px-3 py-2 text-slate-900 dark:text-slate-100">
                      {user.email}
                    </td>
                    <td className="px-3 py-2 text-slate-700 dark:text-slate-300">
                      {user.full_name || "—"}
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                          user.role === "ADMIN"
                            ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300"
                            : "bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400"
                        }`}
                      >
                        {user.role}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${
                          user.is_active
                            ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                            : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                        }`}
                      >
                        {user.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-slate-600 dark:text-slate-400">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-3 py-2">
                      <button
                        onClick={() => toggleUserStatus(user.id, !user.is_active)}
                        disabled={actionLoading === user.id}
                        className={`rounded px-3 py-1 text-xs font-medium transition ${
                          user.is_active
                            ? "bg-red-50 text-red-600 hover:bg-red-100 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/40"
                            : "bg-green-50 text-green-600 hover:bg-green-100 dark:bg-green-900/20 dark:text-green-400 dark:hover:bg-green-900/40"
                        } disabled:opacity-50`}
                      >
                        {actionLoading === user.id
                          ? "..."
                          : user.is_active
                          ? "Deactivate"
                          : "Activate"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
