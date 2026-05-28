"""Users management page."""
"use client";
import { useState } from "react";
import { Users, Plus, Search, Ban, CheckCircle, Key, MoreHorizontal } from "lucide-react";

const mockUsers = [
  { id: "usr-001", email: "alice@company.io", name: "Alice Chen", role: "enterprise", is_active: true, rate_limit: 500, credits: 2847.50, total_requests: 92841, created_at: "2024-08-15" },
  { id: "usr-002", email: "bob@startup.co", name: "Bob Martinez", role: "user", is_active: true, rate_limit: 100, credits: 420.00, total_requests: 12847, created_at: "2024-09-02" },
  { id: "usr-003", email: "carol@research.edu", name: "Carol White", role: "staff", is_active: true, rate_limit: 200, credits: 0, total_requests: 23491, created_at: "2024-07-20" },
  { id: "usr-004", email: "david@dev.io", name: "David Kim", role: "user", is_active: false, rate_limit: 100, credits: 12.50, total_requests: 3201, created_at: "2024-10-01" },
  { id: "usr-005", email: "admin@yourco.com", name: "Admin User", role: "admin", is_active: true, rate_limit: 1000, credits: 99999, total_requests: 182947, created_at: "2024-06-01" },
  { id: "usr-006", email: "eve@freelancer.net", name: "Eve Patel", role: "user", is_active: true, rate_limit: 50, credits: 89.00, total_requests: 4820, created_at: "2024-10-15" },
];

const roleBadge = (role: string) => ({
  admin: <span className="badge badge-red">Admin</span>,
  staff: <span className="badge badge-purple">Staff</span>,
  enterprise: <span className="badge badge-blue">Enterprise</span>,
  user: <span className="badge badge-green">User</span>,
}[role] || <span className="badge badge-green">User</span>);

export default function UsersPage() {
  const [users] = useState(mockUsers);
  const [search, setSearch] = useState("");
  const [filterRole, setFilterRole] = useState("all");

  const filtered = users.filter(u => {
    const matchSearch = u.email.includes(search) || u.name.includes(search);
    const matchRole = filterRole === "all" || u.role === filterRole;
    return matchSearch && matchRole;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Users</h1>
          <p className="text-sm text-slate-400 mt-1">Manage user accounts, roles, and API access</p>
        </div>
        <button className="btn btn-primary"><Plus className="w-4 h-4" /> Add User</button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search by email or name..."
            className="input pl-10"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <select className="input w-40" value={filterRole} onChange={e => setFilterRole(e.target.value)}>
          <option value="all">All Roles</option>
          <option value="admin">Admin</option>
          <option value="staff">Staff</option>
          <option value="enterprise">Enterprise</option>
          <option value="user">User</option>
        </select>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total Users", value: users.length, color: "#3b82f6" },
          { label: "Active", value: users.filter(u => u.is_active).length, color: "#22c55e" },
          { label: "Enterprise", value: users.filter(u => u.role === "enterprise").length, color: "#8b5cf6" },
          { label: "Suspended", value: users.filter(u => !u.is_active).length, color: "#ef4444" },
        ].map(s => (
          <div key={s.label} className="glass p-4 text-center">
            <div className="text-xs text-slate-500 mb-2">{s.label}</div>
            <div className="text-2xl font-bold" style={{ color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* User table */}
      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>User</th>
              <th>Role</th>
              <th>Rate Limit</th>
              <th>Credits</th>
              <th>Requests</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(u => (
              <tr key={u.id}>
                <td>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center text-xs font-bold text-white">
                      {u.name[0]}
                    </div>
                    <div>
                      <div className="text-sm font-medium text-white">{u.name}</div>
                      <div className="text-[10px] text-slate-500">{u.email}</div>
                    </div>
                  </div>
                </td>
                <td>{roleBadge(u.role)}</td>
                <td className="font-mono text-white">{u.rate_limit}/min</td>
                <td className="font-mono text-white">${u.credits.toFixed(2)}</td>
                <td className="font-mono text-white">{(u.total_requests / 1000).toFixed(0)}K</td>
                <td>
                  {u.is_active
                    ? <span className="badge badge-green"><CheckCircle className="w-3 h-3" />Active</span>
                    : <span className="badge badge-red"><Ban className="w-3 h-3" />Suspended</span>}
                </td>
                <td>
                  <div className="flex gap-2">
                    <button className="btn btn-secondary text-xs py-1 px-2"><Key className="w-3 h-3" />API Key</button>
                    <button className="btn btn-secondary text-xs py-1 px-2">Edit</button>
                    <button className={`btn text-xs py-1 px-2 ${u.is_active ? "btn-danger" : "btn-secondary"}`}>
                      {u.is_active ? <><Ban className="w-3 h-3" />Suspend</> : <><CheckCircle className="w-3 h-3" />Activate</>}
                    </button>
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