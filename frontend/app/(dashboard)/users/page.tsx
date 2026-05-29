/* TSX file */
"use client";
import { useState } from "react";
import { Users, Plus, Search, Key, Trash2, Edit2, Copy, CheckCircle, XCircle, Shield } from "lucide-react";

const mockUsers = [
  { id: "u1", name: "Acme Corp", email: "api@acme.com", tier: "enterprise", api_keys: ["sk-live-xxxx"], is_active: true, used_tokens: 1_250_000, limit_tokens: 10_000_000, created: "2025-01-15" },
  { id: "u2", name: "StartupXYZ", email: "dev@startupxyz.io", tier: "pro", api_keys: ["sk-live-yyyy"], is_active: true, used_tokens: 450_000, limit_tokens: 2_000_000, created: "2025-03-01" },
  { id: "u3", name: "DevPerson", email: "dev@example.com", tier: "free", api_keys: ["sk-test-zzzz"], is_active: true, used_tokens: 12_000, limit_tokens: 100_000, created: "2025-04-10" },
  { id: "u4", name: "BigCorp Inc", email: "ml@bigcorp.com", tier: "enterprise", api_keys: ["sk-live-aaaa"], is_active: false, used_tokens: 8_900_000, limit_tokens: 100_000_000, created: "2024-11-20" },
];

export default function UsersPage() {
  const [users] = useState(mockUsers);
  const [search, setSearch] = useState("");

  const filtered = users.filter(
    (u) =>
      u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase())
  );

  const tierColors: Record<string, string> = {
    free: "bg-slate-600/20 text-slate-400",
    pro: "bg-blue-500/20 text-blue-400",
    enterprise: "bg-purple-500/20 text-purple-400",
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Users & API Keys</h1>
          <p className="text-slate-400 text-sm mt-1">Manage client accounts, API keys, and usage limits</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">
          <Plus size={16} /> Create User
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total Users", value: "1,247", icon: Users },
          { label: "Active Keys", value: "2,891" },
          { label: "Enterprise", value: "12" },
          { label: "This Month", value: "+89 new" },
        ].map((stat, i) => (
          <div key={i} className="stat-card">
            <p className="stat-label">{stat.label}</p>
            <p className="stat-value">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
        <input
          type="text"
          placeholder="Search users or emails..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
        />
      </div>

      {/* Users Table */}
      <div className="bg-slate-800/40 rounded-xl border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-800/60 border-b border-slate-700">
            <tr>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">User</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Tier</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">API Key</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Usage</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Status</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Created</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {filtered.map((user) => (
              <tr key={user.id} className="hover:bg-slate-700/20 transition-colors">
                <td className="px-4 py-3">
                  <div>
                    <p className="font-medium text-white">{user.name}</p>
                    <p className="text-slate-400 text-xs">{user.email}</p>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-md text-xs font-medium ${tierColors[user.tier]}`}>
                    {user.tier}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    <code className="text-xs font-mono text-slate-300 bg-slate-700/50 px-2 py-0.5 rounded">
                      {user.api_keys[0]?.slice(0, 20)}...
                    </code>
                    <button className="text-slate-400 hover:text-white p-1"><Copy size={12} /></button>
                  </div>
                </td>
                <td className="px-4 py-3 min-w-48">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full"
                        style={{ width: `${(user.used_tokens / user.limit_tokens) * 100}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-400 font-mono">
                      {(user.used_tokens / 1_000_000).toFixed(1)}M
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  {user.is_active ? (
                    <span className="flex items-center gap-1 text-emerald-400 text-xs"><CheckCircle size={12} /> Active</span>
                  ) : (
                    <span className="flex items-center gap-1 text-red-400 text-xs"><XCircle size={12} /> Disabled</span>
                  )}
                </td>
                <td className="px-4 py-3 text-slate-400 text-xs">{user.created}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    <button className="text-slate-400 hover:text-white p-1"><Edit2 size={14} /></button>
                    <button className="text-slate-400 hover:text-red-400 p-1"><Trash2 size={14} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}