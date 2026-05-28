"""Models management page."""
"use client";
import { useState } from "react";
import { Box, Plus, Eye, EyeOff, MoreHorizontal, Trash2 } from "lucide-react";

const mockModels = [
  { id: "gpt-4o", name: "GPT-4o", provider_id: "prov-001", model_type: "chat", enabled: true, hidden: false, cost_per_1k_input: 5.0, cost_per_1k_output: 15.0, context_window: 128000, total_requests: 482000 },
  { id: "gpt-4o-mini", name: "GPT-4o Mini", provider_id: "prov-001", model_type: "chat", enabled: true, hidden: false, cost_per_1k_input: 0.15, cost_per_1k_output: 0.60, context_window: 128000, total_requests: 891000 },
  { id: "claude-3-5-sonnet-20241022", name: "Claude 3.5 Sonnet", provider_id: "prov-002", model_type: "chat", enabled: true, hidden: false, cost_per_1k_input: 3.0, cost_per_1k_output: 15.0, context_window: 200000, total_requests: 248000 },
  { id: "deepseek-chat", name: "DeepSeek Chat", provider_id: "prov-004", model_type: "chat", enabled: true, hidden: false, cost_per_1k_input: 0.14, cost_per_1k_output: 0.28, context_window: 64000, total_requests: 187000 },
  { id: "groq-llama3-3-70b", name: "Llama 3.3 70B (Groq)", provider_id: "prov-003", model_type: "chat", enabled: true, hidden: false, cost_per_1k_input: 0.59, cost_per_1k_output: 0.79, context_window: 128000, total_requests: 98200 },
  { id: "gemini-pro", name: "Gemini Pro", provider_id: null, model_type: "chat", enabled: false, hidden: false, cost_per_1k_input: 0.25, cost_per_1k_output: 0.75, context_window: 32768, total_requests: 0 },
  { id: "custom-llm-v1", name: "Local LLaMA 3.2", provider_id: "prov-005", model_type: "chat", enabled: true, hidden: true, cost_per_1k_input: 0.0, cost_per_1k_output: 0.0, context_window: 8192, total_requests: 12400 },
];

export default function ModelsPage() {
  const [models, setModels] = useState(mockModels);

  const toggleEnabled = (id: string) => setModels(ms => ms.map(m => m.id === id ? { ...m, enabled: !m.enabled } : m));
  const toggleHidden = (id: string) => setModels(ms => ms.map(m => m.id === id ? { ...m, hidden: !m.hidden } : m));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Models</h1>
          <p className="text-sm text-slate-400 mt-1">Manage available models, pricing, and visibility</p>
        </div>
        <button className="btn btn-primary"><Plus className="w-4 h-4" /> Add Model</button>
      </div>

      <div className="table-container">
        <table className="table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Type</th>
              <th>Provider</th>
              <th>Context</th>
              <th>Input Cost</th>
              <th>Output Cost</th>
              <th>Requests</th>
              <th>Visibility</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {models.map(m => (
              <tr key={m.id}>
                <td>
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center">
                      <Box className="w-4 h-4 text-purple-400" />
                    </div>
                    <div>
                      <div className="text-sm font-medium text-white">{m.name}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{m.id}</div>
                    </div>
                  </div>
                </td>
                <td><span className="badge badge-blue">{m.model_type}</span></td>
                <td className="text-xs text-slate-400 font-mono">{m.provider_id || "—"}</td>
                <td className="font-mono text-white">{m.context_window?.toLocaleString() || "—"}</td>
                <td className="font-mono text-yellow-400">${m.cost_per_1k_input.toFixed(3)}</td>
                <td className="font-mono text-yellow-400">${m.cost_per_1k_output.toFixed(3)}</td>
                <td className="font-mono text-white">{(m.total_requests / 1000).toFixed(0)}K</td>
                <td>
                  <button onClick={() => toggleHidden(m.id)} className="btn btn-secondary text-xs py-1 px-2">
                    {m.hidden ? <><EyeOff className="w-3 h-3" />Hidden</> : <><Eye className="w-3 h-3" />Visible</>}
                  </button>
                </td>
                <td>
                  <button onClick={() => toggleEnabled(m.id)} className="btn text-xs py-1 px-2">
                    {m.enabled ? <span className="badge badge-green">Enabled</span> : <span className="badge badge-red">Disabled</span>}
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
    </div>
  );
}