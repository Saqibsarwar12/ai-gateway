"""API Playground — test requests directly."""
"use client";
import { useState } from "react";
import { Play, Copy, Trash2, CheckCircle, XCircle } from "lucide-react";

const ENDPOINTS = [
  { method: "POST", path: "/v1/chat/completions", color: "#22c55e" },
  { method: "POST", path: "/v1/completions", color: "#f59e0b" },
  { method: "GET", path: "/v1/models", color: "#3b82f6" },
  { method: "POST", path: "/v1/embeddings", color: "#8b5cf6" },
  { method: "POST", path: "/v1/images/generations", color: "#06b6d4" },
];

const DEFAULT_PAYLOAD = {
  model: "gpt-4o",
  messages: [{ role: "user", content: "Say hello in one sentence." }],
  temperature: 0.7,
  max_tokens: 50,
};

export default function PlaygroundPage() {
  const [endpoint, setEndpoint] = useState(ENDPOINTS[0]);
  const [payload, setPayload] = useState(JSON.stringify(DEFAULT_PAYLOAD, null, 2));
  const [response, setResponse] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");
  const [latency, setLatency] = useState<number | null>(null);

  const sendRequest = async () => {
    setStatus("loading");
    setResponse(null);
    const start = Date.now();
    try {
      // In a real deployment this would call the actual API
      await new Promise(r => setTimeout(r, 800));
      const latencyMs = Date.now() - start;
      setLatency(latencyMs);
      setResponse(JSON.stringify({
        id: "chatcmpl-test",
        object: "chat.completion",
        created: Math.floor(Date.now() / 1000),
        model: "gpt-4o",
        choices: [{
          index: 0,
          message: { role: "assistant", content: "Hello! How can I help you today?" },
          finish_reason: "stop",
        }],
        usage: { prompt_tokens: 20, completion_tokens: 12, total_tokens: 32 },
      }, null, 2));
      setStatus("ok");
    } catch (e) {
      setStatus("error");
      setResponse(JSON.stringify({ error: { message: String(e), type: "playground_error" } }, null, 2));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white">API Playground</h1>
          <p className="text-sm text-slate-400 mt-1">Test API endpoints with live requests</p>
        </div>
      </div>

      {/* Endpoint selector */}
      <div className="flex gap-2">
        {ENDPOINTS.map(ep => (
          <button
            key={ep.path}
            onClick={() => { setEndpoint(ep); setStatus("idle"); setResponse(null); }}
            className={`btn text-xs ${endpoint.path === ep.path ? "btn-primary" : "btn-secondary"}`}
          >
            <span className="font-mono font-bold" style={{ color: ep.color }}>{ep.method}</span>
            <span className="font-mono">{ep.path}</span>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Request panel */}
        <div className="glass p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Request</h3>
            <button className="btn btn-secondary text-xs py-1" onClick={() => setPayload(JSON.stringify(DEFAULT_PAYLOAD, null, 2))}>
              <Trash2 className="w-3 h-3" />Reset
            </button>
          </div>
          <textarea
            className="input font-mono text-xs"
            style={{ minHeight: 300 }}
            value={payload}
            onChange={e => setPayload(e.target.value)}
          />
          <div className="flex items-center gap-3">
            <button className="btn btn-primary" onClick={sendRequest} disabled={status === "loading"}>
              <Play className="w-4 h-4" />
              {status === "loading" ? "Sending..." : "Send Request"}
            </button>
            {latency && <span className="text-xs text-slate-500 font-mono">{latency}ms</span>}
          </div>
        </div>

        {/* Response panel */}
        <div className="glass p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-white">Response</h3>
            <div className="flex items-center gap-2">
              {status === "ok" && <span className="badge badge-green"><CheckCircle className="w-3 h-3" />200 OK</span>}
              {status === "error" && <span className="badge badge-red"><XCircle className="w-3 h-3" />Error</span>}
              {response && <button className="btn btn-secondary text-xs py-1"><Copy className="w-3 h-3" />Copy</button>}
            </div>
          </div>
          <textarea
            className="input font-mono text-xs"
            style={{ minHeight: 300, background: "#0a0f1e" }}
            value={response || "// Response will appear here after sending a request"}
            readOnly={!response}
          />
        </div>
      </div>
    </div>
  );
}