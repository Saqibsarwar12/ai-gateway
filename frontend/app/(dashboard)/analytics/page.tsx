/* TSX file */
"use client";
import { useState } from "react";
import { BarChart3, TrendingUp, Clock, Zap, DollarSign, Activity } from "lucide-react";

export default function AnalyticsPage() {
  const [period, setPeriod] = useState<"24h" | "7d" | "30d" | "90d">("7d");

  const periods = [
    { id: "24h", label: "24 Hours" },
    { id: "7d", label: "7 Days" },
    { id: "30d", label: "30 Days" },
    { id: "90d", label: "90 Days" },
  ];

  // Mock chart data
  const chartData = Array.from({ length: 14 }, (_, i) => ({
    day: `Day ${i + 1}`,
    requests: Math.floor(Math.random() * 50000) + 10000,
    cost: Math.random() * 200,
    latency: Math.floor(Math.random() * 500) + 100,
  }));

  const totalRequests = chartData.reduce((s, d) => s + d.requests, 0);
  const totalCost = chartData.reduce((s, d) => s + d.cost, 0);
  const avgLatency = Math.floor(chartData.reduce((s, d) => s + d.latency, 0) / chartData.length);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Analytics</h1>
          <p className="text-slate-400 text-sm mt-1">Usage metrics, costs, and performance insights</p>
        </div>
        <div className="flex gap-1 bg-slate-800 p-1 rounded-lg">
          {periods.map((p) => (
            <button
              key={p.id}
              onClick={() => setPeriod(p.id as typeof period)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                period === p.id ? "bg-blue-600 text-white" : "text-slate-400 hover:text-white"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-5 gap-3">
        {[
          { label: "Total Requests", value: totalRequests.toLocaleString(), icon: Activity, color: "blue" },
          { label: "Total Cost", value: `$${totalCost.toFixed(2)}`, icon: DollarSign, color: "amber" },
          { label: "Avg Latency", value: `${avgLatency}ms`, icon: Clock, color: "purple" },
          { label: "Req/min Peak", value: "847", icon: Zap, color: "emerald" },
          { label: "Success Rate", value: "99.7%", icon: TrendingUp, color: "cyan" },
        ].map((stat, i) => (
          <div key={i} className="stat-card">
            <div className="flex items-center gap-2 mb-2">
              <stat.icon size={14} className={`text-${stat.color}-400`} />
              <span className="stat-label">{stat.label}</span>
            </div>
            <p className="stat-value">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Requests Chart */}
      <div className="bg-slate-800/40 rounded-xl border border-slate-700 p-5">
        <h3 className="text-white font-semibold mb-4">Request Volume</h3>
        <div className="h-48 flex items-end gap-1">
          {chartData.map((d, i) => (
            <div key={i} className="flex-1 flex flex-col items-center gap-1">
              <div
                className="w-full bg-gradient-to-t from-blue-600 to-blue-400 rounded-t-sm min-h-[4px]"
                style={{ height: `${(d.requests / 55000) * 160}px` }}
              />
              <span className="text-xs text-slate-500">{d.day.split(" ")[1]}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Provider Breakdown */}
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-slate-800/40 rounded-xl border border-slate-700 p-5">
          <h3 className="text-white font-semibold mb-4">Requests by Provider</h3>
          <div className="space-y-3">
            {[
              { name: "OpenAI", pct: 58, requests: 183_420, color: "bg-emerald-500" },
              { name: "Anthropic", pct: 27, requests: 85_410, color: "bg-amber-500" },
              { name: "DeepSeek", pct: 10, requests: 31_630, color: "bg-blue-500" },
              { name: "Cohere", pct: 5, requests: 15_815, color: "bg-purple-500" },
            ].map((p) => (
              <div key={p.name} className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-300">{p.name}</span>
                  <span className="text-slate-400">{p.requests.toLocaleString()} ({p.pct}%)</span>
                </div>
                <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                  <div className={`h-full ${p.color} rounded-full`} style={{ width: `${p.pct}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-800/40 rounded-xl border border-slate-700 p-5">
          <h3 className="text-white font-semibold mb-4">Cost by Provider</h3>
          <div className="space-y-3">
            {[
              { name: "OpenAI", cost: "$1,203.40", color: "bg-emerald-500" },
              { name: "Anthropic", cost: "$487.20", color: "bg-amber-500" },
              { name: "DeepSeek", cost: "$89.30", color: "bg-blue-500" },
              { name: "Cohere", cost: "$34.10", color: "bg-purple-500" },
            ].map((p) => (
              <div key={p.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-3 h-3 rounded-sm ${p.color}`} />
                  <span className="text-sm text-slate-300">{p.name}</span>
                </div>
                <span className="text-sm font-mono text-slate-200">{p.cost}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 pt-4 border-t border-slate-700 flex justify-between">
            <span className="text-slate-400 text-sm">Total</span>
            <span className="text-white font-semibold">$1,814.00</span>
          </div>
        </div>
      </div>

      {/* Model Usage Table */}
      <div className="bg-slate-800/40 rounded-xl border border-slate-700 overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-700">
          <h3 className="text-white font-semibold">Top Models</h3>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-slate-800/40 border-b border-slate-700">
            <tr>
              <th className="text-left px-4 py-2 text-slate-400 font-medium">Model</th>
              <th className="text-left px-4 py-2 text-slate-400 font-medium">Requests</th>
              <th className="text-left px-4 py-2 text-slate-400 font-medium">Tokens</th>
              <th className="text-left px-4 py-2 text-slate-400 font-medium">Cost</th>
              <th className="text-left px-4 py-2 text-slate-400 font-medium">Avg Latency</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {[
              { model: "gpt-4o", requests: 98_420, tokens: "412M", cost: "$687.40", latency: "342ms" },
              { model: "claude-3.5-sonnet", requests: 67_830, tokens: "289M", cost: "$432.80", latency: "389ms" },
              { model: "gpt-4o-mini", requests: 45_210, tokens: "98M", cost: "$68.40", latency: "198ms" },
              { model: "deepseek-chat", requests: 31_630, tokens: "156M", cost: "$89.30", latency: "267ms" },
              { model: "command-r-plus", requests: 15_815, tokens: "67M", cost: "$34.10", latency: "312ms" },
            ].map((row) => (
              <tr key={row.model} className="hover:bg-slate-700/20">
                <td className="px-4 py-2 font-mono text-slate-200">{row.model}</td>
                <td className="px-4 py-2 text-slate-300">{row.requests.toLocaleString()}</td>
                <td className="px-4 py-2 text-slate-300">{row.tokens}</td>
                <td className="px-4 py-2 text-slate-300 font-mono">{row.cost}</td>
                <td className="px-4 py-2 text-slate-300 font-mono">{row.latency}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}