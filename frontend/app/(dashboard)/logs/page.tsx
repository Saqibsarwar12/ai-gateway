"""Request logs page with live tail + filtering."""
"use client";
import { useState } from "react";
import { Search, Download, RefreshCw, Play, Pause, Filter, ChevronDown } from "lucide-react";

const mockLogs = [
  { id: "req-001", model: "gpt-4o", provider: "OpenAI", user: "alice@company.io", latency_ms: 892, input_tokens: 1240, output_tokens: 482, status_code: 200, cache_hit: false, created_at: "2024-10-15 14:23:11" },
  { id: "req-002", model: "gpt-4o-mini", provider: "OpenAI", user: "bob@startup.co", latency_ms: 312, input_tokens: 380, output_tokens: 124, status_code: 200, cache_hit: true, created_at: "2024-10-15 14:23:09" },
  { id: "req-003", model: "claude-3-5-sonnet", provider: "Anthropic", user: "carol@research.edu", latency_ms: 1284, input_tokens: 2100, output_tokens: 892, status_code: 200, cache_hit: false, created_at: "2024-10-15 14:23:07" },
  { id: "req-004", model: "deepseek-chat", provider: "DeepSeek", user: "david@dev.io", latency_ms: 428, input_tokens: 620, output_tokens: 218, status_code: 429, cache_hit: false, created_at: "2024-10-15 14:23:05" },
  { id: "req-005", model: "gpt-4o", provider: "OpenAI", user: "alice@company.io", latency_ms: 0, input_tokens: 0, output_tokens: 0, status_code: 500, cache_hit: false, error: "Provider timeout", created_at: "2024-10-15 14:23:03" },
  { id: "req-006", model: "groq-llama-3.3", provider: "Groq", user: "eve@freelancer.net", latency_ms: 98, input_tokens: 182, output_tokens: 64, status_code: 200, cache_hit: false, created_at: "2024-10-15 14:23:01" },
];

const statusBadge = (code: number) => {
  if (code === 200) return <span className="badge badge-green">{code}</span>;
  if (code === 429) return <span className="badge badge-yellow">{code}</span>;
  if (code >= 500) return <span className="badge badge-red">{code}</span>;
  return <span className="badge badge-blue">{code}</span>;
};

export default function LogsPage() {
  const [logs, setLogs] = useState(mockLogs);
  const [filter, setFilter] = useState("");
  const [live, setLive] = useState(false);

  const filtered = logs.filter(l =>
    l.model.includes(filter) || l.user.includes(filter) || l.provider.includes(filter) || l.id.includes(filter)
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Request Logs</h1>
          <p className="text-sm text-slate-400 mt-1">Real-time request tracing and error analysis</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setLive(!live)} className={`btn ${live ? "btn-primary" : "btn-secondary"}`}>
            {live ? <><Pause className="w-4 h-4" />Pause Live</> : <><Play className="w-4 h-4" />Resume Live</>}
          </button>
          <button className="btn btn-secondary"><Download className="w-4 h-4" />Export</button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            className="input pl-10"
            placeholder="Filter by model, user, provider..."
            value={filter}
            onChange={e => setFilter(e.target.value)}
          />
        </div>
        <button className="btn btn-secondary"><Filter className="w-4 h-4" />Filters</button>
        <span className="text-xs text-slate-500">{filtered.length} requests</span>
      </div>

      {/* Terminal-style log viewer */}
      <div className="rounded-xl overflow-hidden" style={{ background: "#0a0f1e", border: "1px solid #1e2d4d" }}>
        <div className="flex items-center gap-2 px-4 py-2" style={{ background: "#0d1424", borderBottom: "1px solid #1e2d4d" }}>
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-red-500" />
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <div className="w-3 h-3 rounded-full bg-green-500" />
          </div>
          <span className="text-xs text-slate-500 ml-2">request_logs — tail -f</span>
          {live && <span className="pulse-dot ml-2" />}
        </div>
        <div className="p-4 font-mono text-xs space-y-1 max-h-[500px] overflow-y-auto">
          {filtered.map(log => (
            <div key={log.id} className="flex items-start gap-4 py-1 hover:bg-white/5 rounded px-2">
              <span className="text-slate-500 whitespace-nowrap">{log.created_at}</span>
              <span className="text-blue-400">{log.id}</span>
              <span className="text-white">{log.model}</span>
              <span className="text-slate-400">via {log.provider}</span>
              <span className="text-slate-500">user:{log.user}</span>
              <span className={log.cache_hit ? "text-cyan-400" : "text-slate-600"}>
                {log.cache_hit ? "HIT" : "MISS"}
              </span>
              <span className="text-yellow-400">{log.latency_ms}ms</span>
              <span className="text-slate-600">in:{log.input_tokens} out:{log.output_tokens}</span>
              {statusBadge(log.status_code)}
              {log.error && <span className="text-red-400">ERROR: {log.error}</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Request detail inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass p-4">
          <h3 className="text-sm font-semibold text-white mb-3">Response Time Distribution</h3>
          <div className="space-y-2">
            {["< 100ms", "100-300ms", "300-500ms", "500-1000ms", "> 1000ms"].map((bucket, i) => (
              <div key={bucket} className="flex items-center gap-3">
                <span className="text-xs text-slate-500 w-20">{bucket}</span>
                <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-full" style={{ width: `${[62, 84, 71, 48, 28][i]}%` }} />
                </div>
                <span className="text-xs text-slate-400 w-8">{[62, 84, 71, 48, 28][i]}%</span>
              </div>
            ))}
          </div>
        </div>
        <div className="glass p-4">
          <h3 className="text-sm font-semibold text-white mb-3">Status Code Distribution</h3>
          <div className="space-y-2">
            {[{ code: 200, label: "Success", color: "#22c55e" }, { code: 429, label: "Rate Limited", color: "#f59e0b" }, { code: 500, label: "Server Error", color: "#ef4444" }, { code: 401, label: "Auth Error", color: "#ef4444" }].map(s => (
              <div key={s.code} className="flex items-center gap-3">
                <span className="w-12 text-xs font-mono" style={{ color: s.color }}>{s.code}</span>
                <span className="text-xs text-slate-400 flex-1">{s.label}</span>
                <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${Math.random() * 60 + 10}%`, background: s.color }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}