
"use client";
import { useState } from "react";
import { Server, Plus, RefreshCw, CheckCircle, XCircle, AlertTriangle, MoreHorizontal, TestTube } from "lucide-react";

const mockProviders = [
  { id: "prov-001", name: "OpenAI", provider_type: "openai", base_url: "https://api.openai.com/v1", status: "active", avg_latency_ms: 420, total_requests: 842000, failed_requests: 412, is_default: true, weight: 100, region: "us-east" },
  { id: "prov-002", name: "Anthropic", provider_type: "anthropic", base_url: "https://api.anthropic.com", status: "active", avg_latency_ms: 580, total_requests: 412000, failed_requests: 89, is_default: false, weight: 80, region: "us-east" },
  { id: "prov-003", name: "Groq", provider_type: "openai", base_url: "https://api.groq.com/openai/v1", status: "active", avg_latency_ms: 127, total_requests: 298000, failed_requests: 12, is_default: false, weight: 90, region: "us-east" },
  { id: "prov-004", name: "DeepSeek", provider_type: "openai", base_url: "https://api.deepseek.com/v1", status: "active", avg_latency_ms: 218, total_requests: 187000, failed_requests: 234, is_default: false, weight: 60, region: "cn" },
  { id: "prov-005", name: "Ollama Local", provider_type: "ollama", base_url: "http://localhost:11434", status: "inactive", avg_latency_ms: 0, total_requests: 0, failed_requests: 0, is_default: false, weight: 50, region: "local" },
  { id: "prov-006", name: "NVIDIA NIM", provider_type: "openai", base_url: "https://integrate.api.nvidia.com/v1", status: "error", avg_latency_ms: 0, total_requests: 0, failed_requests: 0, is_default: false, weight: 40, region: "us-west" },
];

const statusBadge = (status: string) => ({
  active: <span className="badge badge-green"><span className="pulse-dot" />Online</span>,
  inactive: <span className="badge badge-yellow">Inactive</span>,
  error: <span className="badge badge-red"><AlertTriangle className="w-3 h-3" />Error</span>,
}[status] || <span className="badge badge-yellow">Unknown</span>);

export default function ProvidersPage() {
  const [providers, setProviders] = useState(mockProviders);
  const [testingId, setTestingId] = useState<string | null>(null);

  const testProvider = async (id: string) => {
    setTestingId(id);
    await new Promise(r => setTimeout(r, 2000));
    setTestingId(null);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Providers</h1>
          <p className="text-sm text-slate-400 mt-1">Manage AI providers and their configurations</p>
        </div>
        <button className="btn btn-primary">
          <Plus className="w-4 h-4" /> Add Provider
        </button>
      </div>

      {/* Provider cards grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {providers.map(p => (
          <div key={p.id} className="glass p-5 hover:border-blue-500/20 transition-all">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center">
                  <Server className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-white">{p.name}</h3>
                    {p.is_default && <span className="badge badge-blue text-[10px]">DEFAULT</span>}
                  </div>
                  <p className="text-[11px] text-slate-500 font-mono mt-0.5 truncate max-w-[200px]">{p.base_url}</p>
                </div>
              </div>
              {statusBadge(p.status)}
            </div>

            <div className="grid grid-cols-4 gap-3 mb-4">
              <div className="text-center">
                <div className="text-xs text-slate-500 mb-1">Latency</div>
                <div className="text-sm font-semibold text-white font-mono">
                  {p.avg_latency_ms > 0 ? `${p.avg_latency_ms}ms` : "—"}
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs text-slate-500 mb-1">Requests</div>
                <div className="text-sm font-semibold text-white font-mono">
                  {p.total_requests > 0 ? (p.total_requests / 1000).toFixed(0) + "K" : "—"}
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs text-slate-500 mb-1">Errors</div>
                <div className="text-sm font-semibold text-red-400 font-mono">
                  {p.failed_requests > 0 ? p.failed_requests : "0"}
                </div>
              </div>
              <div className="text-center">
                <div className="text-xs text-slate-500 mb-1">Weight</div>
                <div className="text-sm font-semibold text-white font-mono">{p.weight}</div>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex gap-2">
                <span className="badge badge-purple text-[10px]">{p.provider_type}</span>
                <span className="badge badge-blue text-[10px]">{p.region || "global"}</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => testProvider(p.id)}
                  className="btn btn-secondary text-xs py-1.5 px-3"
                  disabled={testingId === p.id}
                >
                  <TestTube className="w-3 h-3" />
                  {testingId === p.id ? "Testing..." : "Test"}
                </button>
                <button className="btn btn-secondary text-xs py-1.5 px-3">
                  <MoreHorizontal className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Provider table */}
      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Provider</th>
              <th>Type</th>
              <th>Region</th>
              <th>Status</th>
              <th>Latency</th>
              <th>Requests</th>
              <th>Error Rate</th>
              <th>Weight</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {providers.map(p => {
              const errorRate = p.total_requests > 0 ? (p.failed_requests / p.total_requests * 100).toFixed(1) : "0.0";
              return (
                <tr key={p.id}>
                  <td>
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-lg bg-blue-500/10 flex items-center justify-center">
                        <Server className="w-3.5 h-3.5 text-blue-400" />
                      </div>
                      <div>
                        <div className="text-sm font-medium text-white">{p.name}</div>
                        <div className="text-[10px] text-slate-500 font-mono">{p.base_url}</div>
                      </div>
                    </div>
                  </td>
                  <td><span className="badge badge-purple">{p.provider_type}</span></td>
                  <td><span className="badge badge-blue">{p.region || "global"}</span></td>
                  <td>{statusBadge(p.status)}</td>
                  <td className="font-mono text-white">{p.avg_latency_ms > 0 ? `${p.avg_latency_ms}ms` : "—"}</td>
                  <td className="font-mono text-white">{(p.total_requests / 1000).toFixed(0)}K</td>
                  <td className={`font-mono ${parseFloat(errorRate) > 1 ? "text-red-400" : "text-white"}`}>{errorRate}%</td>
                  <td className="font-mono text-white">{p.weight}</td>
                  <td>
                    <div className="flex gap-2">
                      <button className="btn btn-secondary text-xs py-1 px-2"><TestTube className="w-3 h-3" /></button>
                      <button className="btn btn-secondary text-xs py-1 px-2">Edit</button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
