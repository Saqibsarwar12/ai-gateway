/** Platform settings page. */
"use client";
import { useState } from "react";
import { Settings, Key, Shield, Globe, Bell, Database, Save } from "lucide-react";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("general");

  const tabs = [
    { id: "general", label: "General", icon: Settings },
    { id: "api-keys", label: "API Keys", icon: Key },
    { id: "security", label: "Security", icon: Shield },
    { id: "domains", label: "Domains", icon: Globe },
    { id: "notifications", label: "Notifications", icon: Bell },
    { id: "billing", label: "Billing", icon: Database },
  ];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-slate-400 text-sm mt-1">Platform configuration, security, and billing</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar */}
        <div className="w-48 space-y-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                activeTab === tab.id
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:text-white hover:bg-slate-800"
              }`}
            >
              <tab.icon size={14} /> {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 space-y-6">
          {activeTab === "general" && (
            <div className="space-y-6">
              <div className="bg-slate-800/40 rounded-xl border border-slate-700 p-5">
                <h3 className="text-white font-semibold mb-4">Platform Info</h3>
                <div className="space-y-4">
                  {[
                    { label: "Platform Name", value: "AI Gateway" },
                    { label: "Admin Email", value: "admin@yourdomain.com" },
                    { label: "Base URL", value: "https://api.yourgateway.com" },
                    { label: "Environment", value: "Production" },
                  ].map((field) => (
                    <div key={field.label} className="flex items-center justify-between">
                      <label className="text-sm text-slate-400">{field.label}</label>
                      <input
                        type="text"
                        defaultValue={field.value}
                        className="w-64 px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500"
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-slate-800/40 rounded-xl border border-slate-700 p-5">
                <h3 className="text-white font-semibold mb-4">Default Limits</h3>
                <div className="space-y-4">
                  {[
                    { label: "Default RPM per user", value: "60" },
                    { label: "Default TPM per user", value: "100000" },
                    { label: "Max request timeout (ms)", value: "120000" },
                    { label: "Log retention (days)", value: "30" },
                  ].map((field) => (
                    <div key={field.label} className="flex items-center justify-between">
                      <label className="text-sm text-slate-400">{field.label}</label>
                      <input
                        type="text"
                        defaultValue={field.value}
                        className="w-32 px-3 py-1.5 bg-slate-700 border border-slate-600 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-blue-500 text-right font-mono"
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "api-keys" && (
            <div className="space-y-4">
              <div className="bg-slate-800/40 rounded-xl border border-slate-700 p-5">
                <h3 className="text-white font-semibold mb-4">Admin API Keys</h3>
                <div className="space-y-3">
                  {[
                    { name: "Production Admin", key: "sk-admin-prod-xxxx", created: "2025-01-01", last: "2 hours ago" },
                    { name: "Staging Key", key: "sk-admin-stag-yyyy", created: "2025-03-15", last: "3 days ago" },
                  ].map((k) => (
                    <div key={k.name} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                      <div>
                        <p className="text-sm font-medium text-white">{k.name}</p>
                        <p className="font-mono text-xs text-slate-500">{k.key.slice(0, 25)}...</p>
                        <p className="text-xs text-slate-600 mt-1">Created {k.created} · Last used {k.last}</p>
                      </div>
                      <button className="px-3 py-1.5 bg-red-500/10 text-red-400 border border-red-500/20 rounded-lg text-xs hover:bg-red-500/20">
                        Revoke
                      </button>
                    </div>
                  ))}
                </div>
                <button className="mt-4 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm">
                  + Create New Key
                </button>
              </div>
            </div>
          )}

          {activeTab === "security" && (
            <div className="space-y-4">
              <div className="bg-slate-800/40 rounded-xl border border-slate-700 p-5">
                <h3 className="text-white font-semibold mb-4">Security Settings</h3>
                <div className="space-y-4">
                  {[
                    { label: "Require API key for all requests", enabled: true },
                    { label: "Allow direct provider bypass", enabled: false },
                    { label: "Enable request logging", enabled: true },
                    { label: "Block suspicious request patterns", enabled: true },
                    { label: "Enforce rate limiting at gateway level", enabled: true },
                  ].map((opt) => (
                    <div key={opt.label} className="flex items-center justify-between">
                      <span className="text-sm text-slate-300">{opt.label}</span>
                      <button className={`w-10 h-5 rounded-full transition-colors ${opt.enabled ? "bg-blue-600" : "bg-slate-600"}`}>
                        <div className={`w-4 h-4 bg-white rounded-full transition-transform ${opt.enabled ? "translate-x-5" : "translate-x-0.5"}`} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === "domains" && (
            <div className="bg-slate-800/40 rounded-xl border border-slate-700 p-5">
              <h3 className="text-white font-semibold mb-4">Custom Domains</h3>
              <div className="space-y-3">
                {[
                  { domain: "api.yourgateway.com", status: "Active", cert: "Issued" },
                  { domain: "llm.yourgateway.com", status: "Pending", cert: "Pending" },
                ].map((d) => (
                  <div key={d.domain} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                    <div>
                      <p className="font-mono text-sm text-white">{d.domain}</p>
                      <p className="text-xs text-slate-500">Certificate: {d.cert}</p>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full ${d.status === "Active" ? "bg-emerald-500/10 text-emerald-400" : "bg-amber-500/10 text-amber-400"}`}>
                      {d.status}
                    </span>
                  </div>
                ))}
              </div>
              <button className="mt-4 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg text-sm">
                + Add Domain
              </button>
            </div>
          )}

          <button className="px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium flex items-center gap-2">
            <Save size={14} /> Save Changes
          </button>
        </div>
      </div>
    </div>
  );
}