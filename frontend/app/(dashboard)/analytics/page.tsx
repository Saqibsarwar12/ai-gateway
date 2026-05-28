"""Analytics dashboard page."""
"use client";
import { useState } from "react";
import { BarChart, Bar, AreaChart, Area, LineChart, Line, PieChart, Pie, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Download, Calendar } from "lucide-react";

const dailyData = [
  { date: "Oct 1", requests: 42800, cost: 124, tokens: 8900000 },
  { date: "Oct 2", requests: 48200, cost: 138, tokens: 10200000 },
  { date: "Oct 3", requests: 39100, cost: 112, tokens: 7400000 },
  { date: "Oct 4", requests: 55300, cost: 161, tokens: 12800000 },
  { date: "Oct 5", requests: 61800, cost: 182, tokens: 14200000 },
  { date: "Oct 6", requests: 74200, cost: 221, tokens: 16800000 },
  { date: "Oct 7", requests: 68300, cost: 198, tokens: 15200000 },
  { date: "Oct 8", requests: 58400, cost: 167, tokens: 13400000 },
  { date: "Oct 9", requests: 72900, cost: 214, tokens: 16900000 },
  { date: "Oct 10", requests: 81200, cost: 241, tokens: 18900000 },
  { date: "Oct 11", requests: 76800, cost: 228, tokens: 17800000 },
  { date: "Oct 12", requests: 69400, cost: 205, tokens: 16100000 },
  { date: "Oct 13", requests: 59100, cost: 172, tokens: 13800000 },
];

const modelBreakdown = [
  { model: "gpt-4o", requests: 312000, cost: 892, tokens: 42800000, pct: 38 },
  { model: "claude-3-5-sonnet", requests: 248000, cost: 1240, tokens: 31200000, pct: 30 },
  { model: "deepseek-chat", requests: 124000, cost: 186, tokens: 18600000, pct: 15 },
  { model: "groq-llama", requests: 98000, cost: 98, tokens: 9800000, pct: 12 },
  { model: "gemini-pro", requests: 42000, cost: 84, tokens: 8400000, pct: 5 },
];

export default function AnalyticsPage() {
  const [period, setPeriod] = useState("7d");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">Analytics</h1>
          <p className="text-sm text-slate-400 mt-1">Usage metrics, costs, and performance insights</p>
        </div>
        <div className="flex items-center gap-3">
          <select className="input w-32" value={period} onChange={e => setPeriod(e.target.value)}>
            <option value="24h">Last 24h</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
          <button className="btn btn-secondary"><Download className="w-4 h-4" />Export CSV</button>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        {[
          { label: "Total Requests", value: "2.8M", change: "+23.4%", color: "#3b82f6" },
          { label: "Total Cost", value: "$4,821", change: "+18.2%", color: "#f59e0b" },
          { label: "Tokens Used", value: "94.4B", change: "+31.2%", color: "#8b5cf6" },
          { label: "Avg Latency", value: "847ms", change: "-12.3%", color: "#06b6d4" },
          { label: "Error Rate", value: "0.03%", change: "-0.01%", color: "#22c55e" },
        ].map(kpi => (
          <div key={kpi.label} className="glass p-4">
            <div className="text-xs text-slate-500 mb-2">{kpi.label}</div>
            <div className="text-xl font-bold" style={{ color: kpi.color }}>{kpi.value}</div>
            <div className="text-xs text-green-400 mt-1">{kpi.change} vs prev period</div>
          </div>
        ))}
      </div>

      {/* Daily requests + cost charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Daily Requests</h3>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={dailyData}>
              <defs>
                <linearGradient id="reqGrad2" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#475569" }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "#475569" }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#0d1424", border: "1px solid #1e2d4d", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="requests" stroke="#3b82f6" strokeWidth={2} fill="url(#reqGrad2)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="glass p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Daily Cost ($)</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={dailyData}>
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#475569" }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "#475569" }} tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#0d1424", border: "1px solid #1e2d4d", borderRadius: 8, fontSize: 12 }} />
              <Bar dataKey="cost" fill="#f59e0b" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Model breakdown table */}
      <div className="table-container p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Usage by Model</h3>
        <table className="table">
          <thead>
            <tr>
              <th>Model</th>
              <th>Requests</th>
              <th>Tokens</th>
              <th>Cost</th>
              <th>Share</th>
              <th>Trend</th>
            </tr>
          </thead>
          <tbody>
            {modelBreakdown.map(m => (
              <tr key={m.model}>
                <td className="font-mono text-white text-sm">{m.model}</td>
                <td className="font-mono text-white">{(m.requests / 1000).toFixed(0)}K</td>
                <td className="font-mono text-white">{(m.tokens / 1_000_000).toFixed(0)}M</td>
                <td className="font-mono text-yellow-400">${m.cost.toLocaleString()}</td>
                <td>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden max-w-[80px]">
                      <div className="h-full bg-blue-500 rounded-full" style={{ width: `${m.pct}%` }} />
                    </div>
                    <span className="text-xs text-slate-400">{m.pct}%</span>
                  </div>
                </td>
                <td>
                  <div className="flex items-center gap-1 text-xs text-green-400">
                    <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                      <path d="M6 9L6 3M6 3L3.5 5.5M6 3L8.5 5.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                    +{Math.floor(Math.random() * 20 + 5)}%
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