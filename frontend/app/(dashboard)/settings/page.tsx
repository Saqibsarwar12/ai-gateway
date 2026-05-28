"""System settings page."""
"use client";
import { useState } from "react";
import { Save, Globe, Key, Bell, Shield, Database, ToggleLeft, ToggleRight } from "lucide-react";

const featureFlags = [
  { key: "enable_streaming", label: "Streaming Responses", description: "Allow SSE streaming for chat completions", enabled: true },
  { key: "enable_caching", label: "Response Caching", description: "Cache repeated requests for 60s", enabled: true },
  { key: "enable_rate_limit", label: "Rate Limiting", description: "Enforce per-user rate limits", enabled: true },
  { key: "enable_cost_tracking", label: "Cost Tracking", description: "Track per-user spending in real-time", enabled: true },
  { key: "enable_failover", label: "Automatic Failover", description: "Route to backup provider on failure", enabled: true },
  { key: "enable_auth", label: "API Key Auth", description: "Require API keys for /v1/ endpoints", enabled: true },
  { key: "allow_websocket", label: "WebSocket Support", description: "Enable WebSocket upgrade for streaming", enabled: false },
  { key: "enable_analytics", label: "Analytics Pipeline", description: "Stream request logs to analytics", enabled: true },
];

const sections = [
  { id: "general", icon: Globe, label: "General" },
  { id: "security", icon: Shield, label: "Security" },
  { id: "providers", icon: Key, label: "API Keys" },
  { id: "notifications", icon: Bell, label: "Notifications" },
  { id: "database", icon: Database, label: "Database" },
  { id: "features", icon: ToggleRight, label: "Feature Flags" },
];

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState("features");
  const [flags, setFlags] = useState(featureFlags);
  const [saved, setSaved] = useState(false);

  const toggle = (key: string) => {
    setFlags(flags.map(f => f.key === key ? { ...f, enabled: !f.enabled } : f));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-white">Settings</h1>
        <p className="text-sm text-slate-400 mt-1">Configure system behavior, security, and feature toggles</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-48 space-y-1">
          {sections.map(s => (
            <button
              key={s.id}
              onClick={() => setActiveSection(s.id)}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all ${
                activeSection === s.id
                  ? "bg-blue-500/15 text-blue-400 border border-blue-500/20"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <s.icon className="w-4 h-4" />{s.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1">
          {activeSection === "features" && (
            <div className="glass p-6 space-y-4">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-base font-semibold text-white">Feature Flags</h2>
                  <p className="text-xs text-slate-500 mt-1">Toggle system features on or off in real-time</p>
                </div>
                {saved && <span className="badge badge-green">Saved</span>}
              </div>
              {flags.map(f => (
                <div key={f.key} className="flex items-center justify-between p-4 bg-[#0d1424]/50 rounded-lg border border-[#1e2d4d]/50">
                  <div>
                    <div className="text-sm font-medium text-white">{f.label}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{f.description}</div>
                  </div>
                  <button
                    onClick={() => toggle(f.key)}
                    className={`text-2xl transition-colors ${f.enabled ? "text-blue-400" : "text-slate-600"}`}
                  >
                    {f.enabled ? <ToggleRight /> : <ToggleLeft />}
                  </button>
                </div>
              ))}
              <button className="btn btn-primary mt-4"><Save className="w-4 h-4" />Save Changes</button>
            </div>
          )}

          {activeSection === "security" && (
            <div className="glass p-6 space-y-4">
              <h2 className="text-base font-semibold text-white">Security Settings</h2>
              <div className="space-y-4">
                {[
                  { label: "Require API Key", desc: "All /v1/ endpoints require valid API key" },
                  { label: "Enable JWT Auth", desc: "Allow JWT Bearer tokens as auth method" },
                  { label: "IP Whitelist", desc: "Restrict access to specific IP ranges" },
                  { label: "Request Signing", desc: "Validate request signatures for webhook security" },
                ].map(s => (
                  <div key={s.label} className="flex items-center justify-between p-4 bg-[#0d1424]/50 rounded-lg">
                    <div>
                      <div className="text-sm font-medium text-white">{s.label}</div>
                      <div className="text-xs text-slate-500">{s.desc}</div>
                    </div>
                    <button className="text-2xl text-blue-400"><ToggleRight /></button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeSection === "general" && (
            <div className="glass p-6 space-y-4">
              <h2 className="text-base font-semibold text-white">General Settings</h2>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">App Name</label>
                  <input className="input" defaultValue="AI Gateway" />
                </div>
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Default Rate Limit</label>
                  <input className="input" type="number" defaultValue="100" />
                </div>
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Request Timeout (s)</label>
                  <input className="input" type="number" defaultValue="120" />
                </div>
                <div>
                  <label className="text-xs text-slate-400 mb-1 block">Max Retries</label>
                  <input className="input" type="number" defaultValue="3" />
                </div>
              </div>
              <button className="btn btn-primary mt-4"><Save className="w-4 h-4" />Save</button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}