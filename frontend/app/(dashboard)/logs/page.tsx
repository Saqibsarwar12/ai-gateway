/* TSX file */
"use client";
import { useState } from "react";
import { FileText, Search, Filter, Download, ArrowUpDown } from "lucide-react";

const mockLogs = [
  { id: "req-001", timestamp: "2026-05-29T10:25:01Z", user: "Acme Corp", model: "gpt-4o", provider: "openai", status: 200, latency_ms: 342, tokens_in: 124, tokens_out: 89, cost: 0.0023, error: null },
  { id: "req-002", timestamp: "2026-05-29T10:24:58Z", user: "StartupXYZ", model: "deepseek-chat", provider: "deepseek", status: 200, latency_ms: 267, tokens_in: 56, tokens_out: 112, cost: 0.0008, error: null },
  { id: "req-003", timestamp: "2026-05-29T10:24:55Z", user: "DevPerson", model: "claude-3.5-sonnet", provider: "anthropic", status: 429, latency_ms: 14, tokens_in: 0, tokens_out: 0, cost: 0, error: "Rate limit exceeded" },
  { id: "req-004", timestamp: "2026-05-29T10:24:52Z", user: "Acme Corp", model: "gpt-4o-mini", provider: "openai", status: 200, latency_ms: 189, tokens_in: 234, tokens_out: 156, cost: 0.0011, error: null },
  { id: "req-005", timestamp: "2026-05-29T10:24:48Z", user: "BigCorp Inc", model: "command-r-plus", provider: "cohere", status: 200, latency_ms: 412, tokens_in: 445, tokens_out: 203, cost: 0.0038, error: null },
];

export default function LogsPage() {
  const [logs] = useState(mockLogs);
  const [search, setSearch] = useState("");

  const filtered = logs.filter(
    (l) =>
      l.user.toLowerCase().includes(search.toLowerCase()) ||
      l.model.toLowerCase().includes(search.toLowerCase()) ||
      l.provider.toLowerCase().includes(search.toLowerCase()) ||
      l.id.includes(search)
  );

  const statusColors: Record<number, string> = {
    200: "text-emerald-400",
    400: "text-amber-400",
    401: "text-red-400",
    429: "text-orange-400",
    500: "text-red-500",
    503: "text-red-500",
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Request Logs</h1>
          <p className="text-slate-400 text-sm mt-1">Live request stream, errors, and debug traces</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm font-medium transition-colors">
          <Download size={16} /> Export CSV
        </button>
      </div>

      <div className="flex gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
          <input
            type="text"
            placeholder="Search by user, model, provider, or request ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition-colors">
          <Filter size={16} /> Filters
        </button>
      </div>

      <div className="bg-slate-800/40 rounded-xl border border-slate-700 overflow-hidden overflow-x-auto">
        <table className="w-full text-sm min-w-[900px]">
          <thead className="bg-slate-800/60 border-b border-slate-700">
            <tr>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Request ID</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Time</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">User</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Model</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Provider</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Status</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Latency</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Tokens</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Cost</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Error</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {filtered.map((log) => (
              <tr key={log.id} className="hover:bg-slate-700/20 transition-colors">
                <td className="px-4 py-3 font-mono text-xs text-slate-400">{log.id}</td>
                <td className="px-4 py-3 text-slate-300 text-xs font-mono">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </td>
                <td className="px-4 py-3 text-slate-200 text-xs">{log.user}</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-300">{log.model}</td>
                <td className="px-4 py-3 text-xs">
                  <span className="text-blue-400 font-mono">{log.provider}</span>
                </td>
                <td className="px-4 py-3">
                  <span className={`font-mono font-medium ${statusColors[log.status] ?? "text-slate-400"}`}>
                    {log.status}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-slate-300">{log.latency_ms}ms</td>
                <td className="px-4 py-3 font-mono text-xs text-slate-300">
                  {log.tokens_in > 0 ? `${log.tokens_in}/${log.tokens_out}` : "—"}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-slate-300">
                  {log.cost > 0 ? `$${log.cost.toFixed(4)}` : "—"}
                </td>
                <td className="px-4 py-3 text-xs">
                  {log.error ? (
                    <span className="text-red-400">{log.error}</span>
                  ) : (
                    <span className="text-slate-600">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-xs text-slate-500">
        <span>Showing {filtered.length} of 12,847 requests</span>
        <span>Live streaming enabled</span>
      </div>
    </div>
  );
}