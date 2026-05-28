"""Routing rules page."""
"use client";
import { useState } from "react";
import { GitBranch, Plus, Play, Pause, MoreHorizontal } from "lucide-react";

const mockRules = [
  { id: "rout-001", name: "Latency-based routing", strategy: "latency", priority: 100, is_active: true, models: ["*"], provider_id: null, total_requests: 1284917, failover_chain: ["openai", "deepseek", "groq"] },
  { id: "rout-002", name: "Cost optimization", strategy: "cost", priority: 80, is_active: true, models: ["gpt-4o-mini", "gpt-3.5-turbo"], provider_id: null, total_requests: 421847, failover_chain: ["deepseek", "groq"] },
  { id: "rout-003", name: "Premium tier routing", strategy: "priority", priority: 90, is_active: true, models: ["gpt-4o", "claude-3-5-sonnet"], provider_id: null, total_requests: 298421, failover_chain: ["openai", "anthropic"] },
  { id: "rout-004", name: "Enterprise failover", strategy: "failover", priority: 70, is_active: false, models: ["*"], provider_id: null, total_requests: 0, failover_chain: ["openai", "anthropic", "deepseek"] },
];

const strategyBadge = (s: string) => ({
  latency: <span className="badge badge-blue">Latency</span>,
  cost: <span className="badge badge-green">Cost</span>,
  weighted: <span className="badge badge-purple">Weighted</span>,
  failover: <span className="badge badge-yellow">Failover</span>,
  priority: <span className="badge badge-blue">Priority</span>,
}[s] || <span className="badge badge-green">{s}</span>);

export default function RoutingPage() {
  const [rules, setRules] = useState(mockRules);
  const toggle = (id: string) => setRules(rs => rs.map(r => r.id === id ? { ...r, is_active: !r.is_active } : r));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Routing Rules</h1>
          <p className="text-sm text-slate-400 mt-1">Configure intelligent request routing and failover chains</p>
        </div>
        <button className="btn btn-primary"><Plus className="w-4 h-4" /> Create Rule</button>
      </div>

      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Rule</th>
              <th>Strategy</th>
              <th>Models</th>
              <th>Priority</th>
              <th>Failover Chain</th>
              <th>Requests</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rules.map(r => (
              <tr key={r.id}>
                <td>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center">
                      <GitBranch className="w-4 h-4 text-blue-400" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-white">{r.name}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{r.id}</div>
                    </div>
                  </div>
                </td>
                <td>{strategyBadge(r.strategy)}</td>
                <td>
                  <div className="flex flex-wrap gap-1">
                    {r.models.slice(0, 3).map(m => (
                      <span key={m} className="badge badge-purple text-[10px]">{m}</span>
                    ))}
                    {r.models.length > 3 && (
                      <span className="text-xs text-slate-500">+{r.models.length - 3}</span>
                    )}
                  </div>
                </td>
                <td className="font-mono text-white">{r.priority}</td>
                <td>
                  <div className="flex items-center gap-1">
                    {r.failover_chain.map((p, i) => (
                      <div key={p} className="flex items-center gap-1">
                        <span className="text-xs text-slate-300 font-mono">{p}</span>
                        {i < r.failover_chain.length - 1 && <span className="text-slate-600">→</span>}
                      </div>
                    ))}
                  </div>
                </td>
                <td className="font-mono text-white">{(r.total_requests / 1000).toFixed(0)}K</td>
                <td>
                  <button
                    onClick={() => toggle(r.id)}
                    className={`btn text-xs py-1 px-2 ${r.is_active ? "btn-secondary" : "btn-danger"}`}
                  >
                    {r.is_active ? <><Play className="w-3 h-3" />Active</> : <><Pause className="w-3 h-3" />Paused</>}
                  </button>
                </td>
                <td>
                  <div className="flex gap-2">
                    <button className="btn btn-secondary text-xs py-1 px-2">Edit</button>
                    <button className="btn btn-secondary text-xs py-1 px-2"><MoreHorizontal className="w-3 h-3" /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Routing visualizer */}
      <div className="glass p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Failover Chain Visualizer</h3>
        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          {["User Request", "Routing Engine", "OpenAI (Primary)", "→ DeepSeek (Backup)", "→ Groq (Final)", "Response"].map((step, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className="flex flex-col items-center">
                <div className="w-24 h-12 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                  <span className="text-xs text-blue-300 text-center px-2">{step}</span>
                </div>
              </div>
              {i < 5 && <span className="text-slate-600 text-lg">→</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}