/* TSX file */
"use client";
import { useState } from "react";
import { Boxes, Plus, Search, ToggleLeft, ToggleRight, Edit2, Trash2 } from "lucide-react";

const mockModels = [
  { id: "m1", model_id: "gpt-4o", provider: "openai", name: "GPT-4o", context_length: 128000, input_cost: 2.5, output_cost: 10, rpm: 500, tpm: 120000, is_active: true },
  { id: "m2", model_id: "gpt-4o-mini", provider: "openai", name: "GPT-4o Mini", context_length: 128000, input_cost: 0.15, output_cost: 0.6, rpm: 1500, tpm: 2000000, is_active: true },
  { id: "m3", model_id: "claude-3.5-sonnet", provider: "anthropic", name: "Claude 3.5 Sonnet", context_length: 200000, input_cost: 3.0, output_cost: 15.0, rpm: 400, tpm: 100000, is_active: true },
  { id: "m4", model_id: "claude-3.5-haiku", provider: "anthropic", name: "Claude 3.5 Haiku", context_length: 200000, input_cost: 0.8, output_cost: 4.0, rpm: 1000, tpm: 200000, is_active: false },
  { id: "m5", model_id: "deepseek-chat", provider: "deepseek", name: "DeepSeek Chat", context_length: 64000, input_cost: 0.14, output_cost: 0.28, rpm: 2000, tpm: 200000, is_active: true },
  { id: "m6", model_id: "command-r-plus", provider: "cohere", name: "Command R+", context_length: 128000, input_cost: 3.0, output_cost: 15.0, rpm: 100, tpm: 50000, is_active: true },
];

export default function ModelsPage() {
  const [models, setModels] = useState(mockModels);
  const [search, setSearch] = useState("");

  const filtered = models.filter(
    (m) =>
      m.name.toLowerCase().includes(search.toLowerCase()) ||
      m.model_id.toLowerCase().includes(search.toLowerCase()) ||
      m.provider.toLowerCase().includes(search.toLowerCase())
  );

  const providerColors: Record<string, string> = {
    openai: "text-emerald-400",
    anthropic: "text-amber-400",
    deepseek: "text-blue-400",
    cohere: "text-purple-400",
    google: "text-cyan-400",
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Models</h1>
          <p className="text-slate-400 text-sm mt-1">Configure pricing, rate limits, and availability per model</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">
          <Plus size={16} /> Add Model
        </button>
      </div>

      <div className="grid grid-cols-4 gap-4">
        {[
          { label: "Total Models", value: "24" },
          { label: "Active", value: "19" },
          { label: "Avg Cost/1M in", value: "$1.82" },
          { label: "Avg Cost/1M out", value: "$7.64" },
        ].map((stat, i) => (
          <div key={i} className="stat-card">
            <p className="stat-label">{stat.label}</p>
            <p className="stat-value">{stat.value}</p>
          </div>
        ))}
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
        <input
          type="text"
          placeholder="Search models, providers..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
        />
      </div>

      <div className="bg-slate-800/40 rounded-xl border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-800/60 border-b border-slate-700">
            <tr>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Model</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Provider</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Context</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Input ($/1M)</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Output ($/1M)</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">RPM / TPM</th>
              <th className="text-left px-4 py-3 text-slate-400 font-medium">Status</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {filtered.map((model) => (
              <tr key={model.id} className="hover:bg-slate-700/20 transition-colors">
                <td className="px-4 py-3">
                  <div>
                    <p className="font-medium text-white">{model.name}</p>
                    <p className="text-slate-500 text-xs font-mono">{model.model_id}</p>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <span className={`font-mono text-xs font-medium ${providerColors[model.provider]}`}>
                    {model.provider}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-300 text-xs font-mono">
                  {(model.context_length / 1000).toFixed(0)}K
                </td>
                <td className="px-4 py-3 text-slate-300 font-mono text-xs">${model.input_cost.toFixed(2)}</td>
                <td className="px-4 py-3 text-slate-300 font-mono text-xs">${model.output_cost.toFixed(2)}</td>
                <td className="px-4 py-3 text-slate-300 font-mono text-xs">
                  {model.rpm.toLocaleString()} / {(model.tpm / 1000).toFixed(0)}K
                </td>
                <td className="px-4 py-3">
                  <button
                    onClick={() => setModels(models.map(m => m.id === model.id ? { ...m, is_active: !m.is_active } : m))}
                    className="text-slate-400 hover:text-white"
                  >
                    {model.is_active ? (
                      <span className="flex items-center gap-1 text-emerald-400 text-xs">
                        <ToggleRight size={18} className="text-emerald-400" /> Active
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-slate-500 text-xs">
                        <ToggleLeft size={18} /> Disabled
                      </span>
                    )}
                  </button>
                </td>
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