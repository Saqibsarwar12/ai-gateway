/** Routing rules management page. */
"use client";
import { useState } from "react";
import { GitBranch, Plus, Globe, Zap, DollarSign, ToggleLeft, ToggleRight, ArrowUpDown } from "lucide-react";

const mockRules = [
  {
    id: "rule-001",
    name: "Default → Cheapest",
    strategy: "cost",
    is_active: true,
    conditions: [{ type: "always", value: null }],
    fallback_order: ["openai", "anthropic", "deepseek"],
    priority: 1,
  },
  {
    id: "rule-002",
    name: "Premium Users → GPT-4o",
    strategy: "model",
    is_active: true,
    conditions: [{ type: "user_tier", value: "premium" }],
    fallback_order: ["openai"],
    priority: 2,
  },
  {
    id: "rule-003",
    name: "Fast Response → Lowest Latency",
    strategy: "latency",
    is_active: false,
    conditions: [{ type: "always", value: null }],
    fallback_order: ["openai", "deepseek"],
    priority: 3,
  },
];

const strategies = [
  { id: "cost", label: "Cheapest First", icon: DollarSign },
  { id: "latency", label: "Lowest Latency", icon: Zap },
  { id: "round_robin", label: "Round Robin", icon: ArrowUpDown },
  { id: "weighted", label: "Weighted", icon: Globe },
  { id: "model", label: "Model Match", icon: GitBranch },
];

export default function RoutingPage() {
  const [rules, setRules] = useState(mockRules);
  const [showModal, setShowModal] = useState(false);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Routing Engine</h1>
          <p className="text-slate-400 text-sm mt-1">Configure intelligent request routing & failover chains</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          <Plus size={16} /> New Rule
        </button>
      </div>

      {/* Strategy Selector */}
      <div className="grid grid-cols-5 gap-3">
        {strategies.map((s) => (
          <button
            key={s.id}
            className="p-4 rounded-xl border border-slate-700 hover:border-blue-500 bg-slate-800/50 hover:bg-slate-800 transition-all text-center group"
          >
            <s.icon className="w-6 h-6 mx-auto text-blue-400 group-hover:scale-110 transition-transform" />
            <p className="text-xs font-medium text-slate-300 mt-2">{s.label}</p>
          </button>
        ))}
      </div>

      {/* Rules Table */}
      <div className="bg-slate-800/40 rounded-xl border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-800/60 border-b border-slate-700">
            <tr>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Rule</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Strategy</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Conditions</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Fallback Chain</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Priority</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {rules.map((rule) => (
              <tr key={rule.id} className="hover:bg-slate-700/20 transition-colors">
                <td className="px-4 py-3">
                  <span className="font-medium text-white">{rule.name}</span>
                </td>
                <td className="px-4 py-3">
                  <span className="px-2 py-1 rounded-md bg-blue-500/10 text-blue-400 text-xs font-mono">
                    {rule.strategy}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-400">
                  {rule.conditions.map((c, i) => (
                    <span key={i} className="font-mono text-xs">
                      {c.type}
                      {c.value && <span className="text-slate-500">={c.value}</span>}
                    </span>
                  ))}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1">
                    {rule.fallback_order.map((p, i) => (
                      <span key={i} className="px-1.5 py-0.5 bg-slate-700 rounded text-xs text-slate-300 font-mono">
                        {p}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-4 py-3 text-slate-300 font-mono text-xs">#{rule.priority}</td>
                <td className="px-4 py-3">
                  {rule.is_active ? (
                    <span className="flex items-center gap-1 text-emerald-400 text-xs">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" /> Active
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-slate-500 text-xs">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-500 inline-block" /> Disabled
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <button className="text-slate-400 hover:text-white text-xs">Edit</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Failover Visualization */}
      <div className="bg-slate-800/40 rounded-xl border border-slate-700 p-5">
        <h3 className="text-white font-semibold mb-4">Failover Chain Visualization</h3>
        <div className="flex items-center gap-2 flex-wrap">
          {["User Request", "OpenAI", "Anthropic", "DeepSeek", "Cohere", "Response"].map((step, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`px-3 py-1.5 rounded-lg text-xs font-medium ${
                i === 0 ? "bg-blue-600 text-white" : i === 5 ? "bg-emerald-600 text-white" : "bg-slate-700 text-slate-300"
              }`}>
                {step}
              </div>
              {i < 5 && <span className="text-slate-600 text-xs">→</span>}
            </div>
          ))}
          <span className="ml-3 px-2 py-1 bg-amber-500/10 text-amber-400 rounded text-xs">Fallback on failure</span>
        </div>
      </div>
    </div>
  );
}