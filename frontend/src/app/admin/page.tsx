"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import useSWR from "swr";
import { useAuth } from "@/lib/AuthContext";

const API_BASE = "";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
    ...options,
  });
  if (!res.ok) throw { status: res.status, detail: (await res.text()).slice(0, 200) };
  return res.json();
}

export default function AdminPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<"users" | "exports">("users");
  const [selectedUser, setSelectedUser] = useState<any>(null);
  const [tierValue, setTierValue] = useState("");
  const [reason, setReason] = useState("");

  const { data: usersData, mutate: mutateUsers } = useSWR(
    isAuthenticated && tab === "users" ? "/v1/admin/users" : null,
    (url) => apiFetch<any>(url)
  );
  const { data: exports } = useSWR(
    isAuthenticated && tab === "exports" ? "/v1/admin/exports" : null,
    (url) => apiFetch<any>(url)
  );

  if (isLoading) return <div className="p-8 text-gray-500">Loading...</div>;
  if (!isAuthenticated) { router.push("/login"); return null; }
  if (usersData && (usersData as any).code === 403) return <div className="p-8 text-red-600">Not authorized. Admin access required.</div>;

  const handleTierOverride = async () => {
    if (!selectedUser || !tierValue) return;
    const res = await fetch(`${API_BASE}/v1/admin/users/${selectedUser.id}/tier`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tier: tierValue, reason }),
    });
    if (res.ok) {
      mutateUsers();
      setSelectedUser(null);
      setTierValue("");
      setReason("");
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <h1 className="text-xl font-bold">Admin Dashboard</h1>

      <div className="flex gap-2 border-b">
        <button onClick={() => setTab("users")} className={`px-3 py-2 text-sm ${tab === "users" ? "border-b-2 border-blue-600 font-semibold" : "text-gray-500"}`}>Users</button>
        <button onClick={() => setTab("exports")} className={`px-3 py-2 text-sm ${tab === "exports" ? "border-b-2 border-blue-600 font-semibold" : "text-gray-500"}`}>Exports</button>
      </div>

      {tab === "users" && usersData && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-gray-500">
                <th className="pb-2">Email</th><th className="pb-2">Tier</th><th className="pb-2">Status</th><th className="pb-2">Period End</th>
              </tr>
            </thead>
            <tbody>
              {(usersData.users || []).map((u: any) => (
                <tr key={u.id} className="border-b hover:bg-gray-50 cursor-pointer" onClick={() => setSelectedUser(u)}>
                  <td className="py-2">{u.email || u.id}</td>
                  <td className="py-2"><span className="px-2 py-0.5 rounded text-xs font-semibold bg-gray-100">{u.tier}</span></td>
                  <td className="py-2">{u.billing_status || "-"}</td>
                  <td className="py-2">{u.current_period_end ? new Date(u.current_period_end).toLocaleDateString() : "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {selectedUser && (
            <div className="mt-4 border rounded p-4 space-y-2">
              <h3 className="font-semibold">Change Tier: {selectedUser.email || selectedUser.id}</h3>
              <select value={tierValue} onChange={(e) => setTierValue(e.target.value)} className="border rounded px-2 py-1 text-sm">
                <option value="">Select tier...</option>
                <option value="free">Free</option>
                <option value="basic">Basic</option>
                <option value="lifetime">Lifetime</option>
                <option value="enterprise">Enterprise</option>
              </select>
              <input type="text" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason (optional)" className="border rounded px-2 py-1 text-sm w-full" />
              <button onClick={handleTierOverride} disabled={!tierValue} className="px-3 py-1 bg-blue-600 text-white rounded text-sm disabled:opacity-50">Apply</button>
            </div>
          )}
        </div>
      )}

      {tab === "exports" && exports && (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-gray-500">
              <th className="pb-2">User</th><th className="pb-2">Type</th><th className="pb-2">Scope</th><th className="pb-2">Size</th><th className="pb-2">When</th>
            </tr>
          </thead>
          <tbody>
            {(exports || []).map((e: any) => (
              <tr key={e.id} className="border-b">
                <td className="py-2">{e.user_email}</td>
                <td className="py-2">{e.export_type}</td>
                <td className="py-2">{e.scope}</td>
                <td className="py-2">{e.payload_size_bytes == null ? "-" : `${(e.payload_size_bytes / 1024).toFixed(1)} KB`}</td>
                <td className="py-2">{e.created_at ? new Date(e.created_at).toLocaleString() : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
