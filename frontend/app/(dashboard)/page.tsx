"""Overview dashboard page."""
"use client";
import { useState, useEffect } from "react";
import { Activity, Users, Server, Zap, TrendingUp, TrendingDown, Clock, AlertTriangle, CheckCircle2 } from "lucide-react";
import { AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const mockStats = {
  totalRequests: 2847291,
  activeUsers: 1847,
  providers: 12,
  uptime: 99.97,
  tokensUsed: 94_382_918_204,
  totalCost: 4821.42,
  avgLatency: 847,
  errorRate: 0.03,
  cacheHitRate: 34.2,
};

const requestChartData = [
  { time: "00:00", requests: 4200 }, { time: "02:00", requests: 3800 },
  { time: "04:00", requests: 2100 }, { time: "06:00", requests: 5400 },
  { time: "08:00", requests: 12800 }, { time: "10:00", requests: 18200 },
  { time: "12:00", requests: 22100 }, { time: "14:00", requests: 19800 },
  { time: "16:00", requests: 17600 }, { time: "18:00", requests: 21400 },
  { time: "20:00", requests: 15300 }, { time: "22:00", requests: 8900 },
];

const providerChartData = [
  { name: "OpenAI", requests: 842_000, color: "#10a37f" },
  { name: "Anthropic", requests: 412_000, color: "#d97706" },
  { name: "Groq", requests: 298_000, color: "#7c3aed" },
  { name: "DeepSeek", requests: 187_000, color: "#0891b2" },
  { name: "Other", requests: 124_000, color: "#475569" },
];

const latencyChartData = [
  { time: "00:00", openai: 420, anthropic: 380, groq: 120, deepseek: 210 },
  { time: "04:00", openai: 380, anthropic: 360, groq: 110, deepseek: 190 },
  { time: "08:00", openai: 680, anthropic: 520, groq: 130, deepseek: 240 },
  { time: "12:00", openai: 890, anthropic: 640, groq: 140, deepseek: 280 },
  { time: "16:00", openai: 740, anthropic: 580, groq: 125, deepseek: 260 },
  { time: "20:00", openai: 620, anthropic: 490, groq: 118, deepseek: 230 },
];

function formatNumber(n: number): string {
  if (n >= 1_000_000_000) return `${(n / 1_000_000_000).toFixed(1)}B`;
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function StatCard({ icon: Icon, label, value, change, unit, color }: {
  icon: any; label: string; value: string | number; change?: number; unit?: string; color: string;
}) {
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between">
        <div>
          <div className="stat-label">{label}</div>
          <div className="flex items-baseline gap-1">
            <span className="stat-value" style={{ color }}>{value}</span>
            {unit && <span className="text-sm text-slate-500 ml-1">{unit}</span>}
          </div>
          {change !== undefined && (
            <div className={`stat-change ${change >= 0 ? "positive" : "negative"}`}>
              {change >= 0 ? <TrendingUp className="w-3 h-3 inline mr-1" /> : <TrendingDown className="w-3 h-3 inline mr-1" />}
              {Math.abs(change)}% vs yesterday
            </div>
          )}
        </div>
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${color}20` }}>
          <Icon className="w-5 h-5" style={{ color }} />
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Top stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={Zap} label="Total Requests" value={formatNumber(mockStats.totalRequests)} change={23.4} color="#3b82f6" />
        <StatCard icon={Users} label="Active Users" value={formatNumber(mockStats.activeUsers)} change={8.1} color="#06b6d4" />
        <StatCard icon={Server} label="Providers" value={mockStats.providers} change={0.0} color="#10a37f" />
        <StatCard icon={Activity} label="Avg Latency" value={mockStats.avgLatency} unit="ms" change={-12.3} color="#f59e0b" />
      </div>

      {/* Second row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon-{CheckCircle2} label="Uptime" value={mockStats.uptime.toFixed(2)} unit="%" change={0.01} color="#22c55e" />
        <StatCard icon={TrendingUp} label="Tokens Used" value={formatNumber(mockStats.tokensUsed)} change={31.2} color="#8b5cf6" />
        <StatCard icon={Clock} label="Cache Hit Rate" value={mockStats.cacheHitRate.toFixed(1)} unit="%" change={2.4} color="#06b6d4" />
        <StatCard icon={AlertTriangle} label="Error Rate" value={mockStats.errorRate.toFixed(2)} unit="%" change={-0.01} color="#ef4444" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Requests over time */}
        <div className="lg:col-span-2 glass p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Request Volume</h3>
              <p className="text-xs text-slate-500 mt-0.5">Last 24 hours</p>
            </div>
            <div className="badge badge-green">{formatNumber(mockStats.totalRequests)} total</div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={requestChartData}>
              <defs>
                <linearGradient id="reqGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#475569" }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "#475569" }} tickLine={false} axisLine={false} tickFormatter={v => formatNumber(v)} />
              <Tooltip
                contentStyle={{ background: "#0d1424", border: "1px solid #1e2d4d", borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: "#94a3b8" }}
                itemStyle={{ color: "#f1f5f9" }}
              />
              <Area type="monotone" dataKey="requests" stroke="#3b82f6" strokeWidth={2} fill="url(#reqGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Provider distribution */}
        <div className="glass p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Traffic by Provider</h3>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={providerChartData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={2} dataKey="requests">
                {providerChartData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
              </Pie>
              <Tooltip
                contentStyle={{ background: "#0d1424", border: "1px solid #1e2d4d", borderRadius: 8, fontSize: 12 }}
              />
            </PieChart>
          </ResponsiveContainer>
          <ul className="space-y-2 mt-2">
            {providerChartData.map(p => (
              <li key={p.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
                  <span className="text-slate-400">{p.name}</span>
                </div>
                <span className="text-slate-300 font-mono">{formatNumber(p.requests)}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Latency + System status */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Latency chart */}
        <div className="glass p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Provider Latency (ms)</h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={latencyChartData}>
              <XAxis dataKey="time" tick={{ fontSize: 10, fill: "#475569" }} tickLine={false} axisLine={false} />
              <YAxis tick={{ fontSize: 10, fill: "#475569" }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ background: "#0d1424", border: "1px solid #1e2d4d", borderRadius: 8, fontSize: 12 }}
              />
              <Bar dataKey="openai" fill="#10a37f" radius={[3,3,0,0]} />
              <Bar dataKey="anthropic" fill="#d97706" radius={[3,3,0,0]} />
              <Bar dataKey="groq" fill="#7c3aed" radius={[3,3,0,0]} />
              <Bar dataKey="deepseek" fill="#0891b2" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* System health */}
        <div className="glass p-5">
          <h3 className="text-sm font-semibold text-white mb-4">System Health</h3>
          <div className="space-y-3">
            {[
              { service: "API Gateway", status: "operational", latency: "1.2ms" },
              { service: "PostgreSQL", status: "operational", latency: "2.8ms" },
              { service: "Redis Cache", status: "operational", latency: "0.4ms" },
              { service: "Routing Engine", status: "operational", latency: "0.1ms" },
              { service: "Auth Service", status: "operational", latency: "3.1ms" },
              { service: "Analytics Pipeline", status: "degraded", latency: "892ms" },
            ].map(s => (
              <div key={s.service} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={`w-2 h-2 rounded-full ${s.status === "operational" ? "bg-green-500" : "bg-yellow-500 animate-pulse"}`} />
                  <span className="text-sm text-slate-300">{s.service}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500 font-mono">{s.latency}</span>
                  <span className={`badge text-[10px] ${s.status === "operational" ? "badge-green" : "badge-yellow"}`}>
                    {s.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
