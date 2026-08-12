"use client";

import { useEffect, useMemo, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "";

type Param = {
  name: string;
  in: string;
  required?: boolean;
  schema?: { type?: string; default?: any; enum?: any[] };
  description?: string;
};

type Endpoint = {
  path: string;
  method: string;
  summary?: string;
  description?: string;
  tags?: string[];
  parameters?: Param[];
  requestBody?: any;
  responses?: Record<string, any>;
  security?: any[];
};

const METHOD_STYLE: Record<string, { bg: string; fg: string; border: string }> = {
  get:    { bg: "rgba(140, 180, 200, 0.14)", fg: "#9ec5d9", border: "rgba(140, 180, 200, 0.40)" },
  post:   { bg: "rgba(160, 200, 140, 0.14)", fg: "#a8d49a", border: "rgba(160, 200, 140, 0.40)" },
  put:    { bg: "rgba(220, 190, 120, 0.14)", fg: "#dcc47a", border: "rgba(220, 190, 120, 0.40)" },
  delete: { bg: "rgba(200, 130, 130, 0.14)", fg: "#d49a9a", border: "rgba(200, 130, 130, 0.40)" },
  patch:  { bg: "rgba(180, 150, 200, 0.14)", fg: "#bca8d4", border: "rgba(180, 150, 200, 0.40)" },
};
function methodStyle(m: string) {
  return METHOD_STYLE[m.toLowerCase()] || METHOD_STYLE.get;
}
function safeStr(x: any): string {
  if (x === undefined || x === null) return "";
  if (typeof x === "string") return x;
  try { return JSON.stringify(x, null, 2); } catch { return String(x); }
}
function resolveRef(spec: any, schema: any): any {
  if (!schema || typeof schema !== "object") return schema;
  if (schema.$ref) {
    const parts = schema.$ref.replace(/^#\//, "").split("/");
    let cur: any = spec;
    for (const p of parts) {
      if (cur && typeof cur === "object" && p in cur) cur = cur[p];
      else return schema;
    }
    return cur;
  }
  return schema;
}
function pickExample(spec: any, mediaObj: any): any {
  if (!mediaObj) return null;
  if (mediaObj.example !== undefined) return mediaObj.example;
  if (mediaObj.schema?.example !== undefined) return mediaObj.schema.example;
  const resolved = resolveRef(spec, mediaObj.schema);
  if (resolved?.example !== undefined) return resolved.example;
  return null;
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => {
        try { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch {}
      }}
      style={{
        background: "transparent", border: "1px solid var(--line)", color: "var(--fg-2)",
        fontSize: 10.5, padding: "4px 10px", borderRadius: 4, cursor: "pointer",
        fontFamily: "inherit", letterSpacing: "0.06em", textTransform: "uppercase",
      }}
    >{copied ? "Copied" : "Copy"}</button>
  );
}
function CodeBlock({ value }: { value: any }) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return (
    <div style={{ position: "relative" }}>
      <div style={{ position: "absolute", top: 8, right: 8 }}><CopyButton text={text} /></div>
      <pre style={{
        margin: 0, padding: "14px 16px", background: "var(--bg-0)",
        border: "1px solid var(--line)", borderRadius: 6, color: "var(--fg-0)",
        fontSize: 12.5, lineHeight: 1.6, overflowX: "auto", fontFamily: "var(--font-mono)",
      }}><code>{text}</code></pre>
    </div>
  );
}
function ParamRow({ p }: { p: Param }) {
  return (
    <div style={{
      padding: "12px 0", borderTop: "1px solid var(--line)",
      display: "grid", gridTemplateColumns: "200px 1fr", gap: 20,
    }}>
      <div>
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 13, color: "var(--fg-0)" }}>
          {p.name}{p.required && <span style={{ color: "#d49a9a", marginLeft: 6 }}>*</span>}
        </div>
        <div style={{ fontSize: 11, color: "var(--fg-3)", marginTop: 3 }}>
          {p.schema?.type || "string"}{p.schema?.enum ? ` · ${p.schema.enum.join(" | ")}` : ""}
        </div>
        <div style={{
          fontSize: 10, color: "var(--fg-3)", marginTop: 4,
          textTransform: "uppercase", letterSpacing: "0.06em",
        }}>in · {p.in}</div>
      </div>
      <div style={{ fontSize: 13.5, color: "var(--fg-1)", lineHeight: 1.55 }}>
        {p.description || <span style={{ color: "var(--fg-3)" }}>—</span>}
        {p.schema?.default !== undefined && (
          <div style={{ marginTop: 6, fontSize: 11.5, color: "var(--fg-3)" }}>
            default: <code style={{ color: "var(--fg-1)" }}>{safeStr(p.schema.default)}</code>
          </div>
        )}
      </div>
    </div>
  );
}
function ResponseBlock({ code, response, spec }: { code: string; response: any; spec: any }) {
  const media = response?.content?.["application/json"];
  const example = pickExample(spec, media);
  return (
    <div style={{ borderTop: "1px solid var(--line)", padding: "14px 0" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
        <span style={{
          fontFamily: "var(--font-mono)", fontSize: 12, padding: "3px 10px",
          borderRadius: 4, border: "1px solid var(--line-strong)",
          color: code.startsWith("2") ? "#a8d49a" : code.startsWith("4") ? "#dcc47a" : code.startsWith("5") ? "#d49a9a" : "var(--fg-1)",
          background: "var(--bg-1)",
        }}>{code}</span>
        <span style={{ fontSize: 13.5, color: "var(--fg-1)" }}>{response?.description || "Response"}</span>
      </div>
      {example !== null && example !== undefined && <CodeBlock value={example} />}
    </div>
  );
}

function EndpointCard({ e, spec }: { e: Endpoint; spec: any }) {
  const ms = methodStyle(e.method);
  const [open, setOpen] = useState(false);
  const reqExample = e.requestBody ? pickExample(spec, e.requestBody.content?.["application/json"]) : null;
  const responses = e.responses || {};
  const auth = e.security && e.security.length > 0;

  return (
    <div style={{
      background: "var(--bg-2)", border: "1px solid var(--line)", borderRadius: 8, overflow: "hidden",
    }}>
      <button onClick={() => setOpen((o) => !o)} style={{
        width: "100%", textAlign: "left", padding: "14px 18px",
        background: open ? "var(--bg-3)" : "transparent",
        border: "none", cursor: "pointer", color: "var(--fg-0)",
        display: "flex", alignItems: "center", gap: 14, fontFamily: "inherit",
      }}>
        <span style={{
          fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600,
          letterSpacing: "0.10em", textTransform: "uppercase",
          padding: "5px 10px", borderRadius: 4, background: ms.bg, color: ms.fg,
          border: `1px solid ${ms.border}`, minWidth: 70, textAlign: "center",
        }}>{e.method}</span>
        <span style={{
          fontFamily: "var(--font-mono)", fontSize: 14, color: "var(--fg-0)", wordBreak: "break-all",
        }}>{e.path}</span>
        <span style={{
          flex: 1, fontSize: 13, color: "var(--fg-2)", marginLeft: 12,
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>{e.summary || ""}</span>
        {auth && <span style={{
          fontSize: 10, color: "var(--fg-3)", border: "1px solid var(--line)",
          padding: "2px 7px", borderRadius: 3, textTransform: "uppercase", letterSpacing: "0.05em",
        }}>Auth</span>}
        <span style={{ color: "var(--fg-3)", fontSize: 14, marginLeft: 4, transition: "transform 0.15s", transform: open ? "rotate(180deg)" : "rotate(0)" }}>▾</span>
      </button>

      {open && (
        <div style={{
          padding: "16px 18px 20px", borderTop: "1px solid var(--line)",
          background: "var(--bg-1)",
        }}>
          {e.description && (
            <p style={{ margin: "0 0 16px", color: "var(--fg-1)", fontSize: 14, lineHeight: 1.6 }}>{e.description}</p>
          )}

          {e.parameters && e.parameters.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <div style={{
                fontSize: 11, color: "var(--fg-2)", textTransform: "uppercase",
                letterSpacing: "0.08em", marginBottom: 6, fontWeight: 600,
              }}>Parameters</div>
              {e.parameters.map((p) => <ParamRow key={p.name + p.in} p={p} />)}
            </div>
          )}

          {e.requestBody && (
            <div style={{ marginBottom: 20 }}>
              <div style={{
                fontSize: 11, color: "var(--fg-2)", textTransform: "uppercase",
                letterSpacing: "0.08em", marginBottom: 8, fontWeight: 600,
              }}>Request Body {e.requestBody.required && <span style={{ color: "#d49a9a" }}>*</span>}</div>
              {reqExample !== null && reqExample !== undefined ? (
                <CodeBlock value={reqExample} />
              ) : (
                <div style={{ fontSize: 13, color: "var(--fg-3)" }}>No example provided in spec.</div>
              )}
            </div>
          )}

          {Object.keys(responses).length > 0 && (
            <div>
              <div style={{
                fontSize: 11, color: "var(--fg-2)", textTransform: "uppercase",
                letterSpacing: "0.08em", marginBottom: 6, fontWeight: 600,
              }}>Responses</div>
              {Object.entries(responses).map(([code, r]) => (
                <ResponseBlock key={code} code={code} response={r} spec={spec} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function DocsPage() {
  const [spec, setSpec] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [activeTag, setActiveTag] = useState<string>("All");
  const [activeMethod, setActiveMethod] = useState<string>("ALL");
  const [baseUrl, setBaseUrl] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/openapi.json`, { cache: "no-store" });
        if (!res.ok) throw new Error(`Failed to load spec (${res.status})`);
        const data = await res.json();
        if (!cancelled) {
          setSpec(data);
          setBaseUrl(data.servers?.[0]?.url || API_BASE);
        }
      } catch (e: any) {
        if (!cancelled) setErr(e.message || "Failed to load spec");
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const endpoints: Endpoint[] = useMemo(() => {
    if (!spec?.paths) return [];
    const out: Endpoint[] = [];
    for (const [path, methods] of Object.entries(spec.paths as Record<string, any>)) {
      for (const m of ["get", "post", "put", "delete", "patch", "options", "head"]) {
        if (methods[m]) {
          out.push({
            path,
            method: m.toUpperCase(),
            summary: methods[m].summary,
            description: methods[m].description,
            tags: methods[m].tags,
            parameters: methods[m].parameters,
            requestBody: methods[m].requestBody,
            responses: methods[m].responses,
            security: methods[m].security,
          });
        }
      }
    }
    return out;
  }, [spec]);

  const tags = useMemo(() => {
    const s = new Set<string>();
    endpoints.forEach((e) => e.tags?.forEach((t) => s.add(t)));
    return ["All", ...Array.from(s).sort()];
  }, [endpoints]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return endpoints.filter((e) => {
      if (activeTag !== "All" && !(e.tags || []).includes(activeTag)) return false;
      if (activeMethod !== "ALL" && e.method !== activeMethod) return false;
      if (!q) return true;
      return (
        e.path.toLowerCase().includes(q) ||
        (e.summary || "").toLowerCase().includes(q) ||
        (e.description || "").toLowerCase().includes(q)
      );
    });
  }, [endpoints, query, activeTag, activeMethod]);

  if (err) {
    return (
      <main style={{ padding: 40, color: "var(--fg-0)", fontFamily: "var(--font-sans)" }}>
        <h1 style={{ fontSize: 22, marginBottom: 8 }}>API Documentation</h1>
        <p style={{ color: "#d49a9a" }}>Error: {err}</p>
        <p style={{ color: "var(--fg-3)", fontSize: 13 }}>Tried: <code>{API_BASE}/openapi.json</code></p>
      </main>
    );
  }

  if (!spec) {
    return (
      <main style={{ padding: 40, color: "var(--fg-1)", fontFamily: "var(--font-sans)" }}>
        <h1 style={{ fontSize: 22, marginBottom: 8 }}>API Documentation</h1>
        <p style={{ color: "var(--fg-3)" }}>Loading OpenAPI spec…</p>
      </main>
    );
  }

  const info = spec.info || {};
  const methodCounts = endpoints.reduce<Record<string, number>>((acc, e) => {
    acc[e.method] = (acc[e.method] || 0) + 1; return acc;
  }, {});

  return (
    <main style={{
      maxWidth: 1100, margin: "0 auto", padding: "40px 28px 80px",
      color: "var(--fg-0)", fontFamily: "var(--font-sans)",
    }}>
      <header style={{ marginBottom: 28 }}>
        <div style={{ fontSize: 11, color: "var(--fg-3)", letterSpacing: "0.10em", textTransform: "uppercase", marginBottom: 8 }}>
          API Reference
        </div>
        <h1 style={{ fontSize: 32, margin: "0 0 8px", letterSpacing: "-0.02em", fontWeight: 600 }}>
          {info.title || "AI Gateway"}
        </h1>
        {info.description && (
          <p style={{ color: "var(--fg-1)", fontSize: 14.5, lineHeight: 1.6, margin: "0 0 14px", maxWidth: 720 }}>
            {info.description}
          </p>
        )}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 16, fontSize: 12.5, color: "var(--fg-2)" }}>
          <span><span style={{ color: "var(--fg-3)" }}>Version</span> · {info.version || "—"}</span>
          <span><span style={{ color: "var(--fg-3)" }}>Base URL</span> · <code style={{ color: "var(--fg-0)", fontFamily: "var(--font-mono)" }}>{baseUrl}</code></span>
          <span><span style={{ color: "var(--fg-3)" }}>Endpoints</span> · {endpoints.length}</span>
        </div>
      </header>

      {/* Filters */}
      <div style={{
        position: "sticky", top: 0, zIndex: 10, background: "var(--bg-0)",
        padding: "14px 0 16px", marginBottom: 18, borderBottom: "1px solid var(--line)",
      }}>
        <div style={{ display: "flex", gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
          <input
            type="text"
            placeholder="Search endpoints, paths, descriptions…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{
              flex: 1, minWidth: 220, padding: "9px 14px",
              background: "var(--bg-2)", border: "1px solid var(--line)",
              borderRadius: 6, color: "var(--fg-0)", fontSize: 13.5,
              fontFamily: "inherit", outline: "none",
            }}
          />
          <select
            value={activeMethod}
            onChange={(e) => setActiveMethod(e.target.value)}
            style={{
              padding: "9px 14px", background: "var(--bg-2)",
              border: "1px solid var(--line)", borderRadius: 6,
              color: "var(--fg-0)", fontSize: 13.5, fontFamily: "inherit",
            }}
          >
            <option value="ALL">All methods</option>
            {Object.keys(methodCounts).sort().map((m) => (
              <option key={m} value={m}>{m} ({methodCounts[m]})</option>
            ))}
          </select>
        </div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {tags.map((t) => (
            <button
              key={t}
              onClick={() => setActiveTag(t)}
              style={{
                padding: "5px 12px", borderRadius: 999,
                border: "1px solid " + (activeTag === t ? "var(--line-strong)" : "var(--line)"),
                background: activeTag === t ? "var(--bg-3)" : "transparent",
                color: activeTag === t ? "var(--fg-0)" : "var(--fg-2)",
                fontSize: 12, cursor: "pointer", fontFamily: "inherit",
              }}
            >{t}</button>
          ))}
        </div>
      </div>

      {/* Endpoint list */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {filtered.length === 0 && (
          <div style={{ padding: 40, textAlign: "center", color: "var(--fg-3)" }}>
            No endpoints match your filters.
          </div>
        )}
        {filtered.map((e) => (
          <EndpointCard key={e.method + e.path} e={e} spec={spec} />
        ))}
      </div>

      <footer style={{
        marginTop: 60, paddingTop: 20, borderTop: "1px solid var(--line)",
        color: "var(--fg-3)", fontSize: 12, display: "flex", justifyContent: "space-between",
      }}>
        <span>Spec loaded from <code style={{ color: "var(--fg-2)" }}>{API_BASE}/openapi.json</code></span>
        <button
          onClick={() => { setSpec(null); setErr(null); fetch(`${API_BASE}/openapi.json`, { cache: "no-store" }).then(r => r.json()).then(setSpec).catch(e => setErr(e.message)); }}
          style={{
            background: "transparent", border: "1px solid var(--line)",
            color: "var(--fg-2)", padding: "4px 10px", borderRadius: 4,
            cursor: "pointer", fontFamily: "inherit", fontSize: 11,
            letterSpacing: "0.05em", textTransform: "uppercase",
          }}
        >Refresh</button>
      </footer>
    </main>
  );
}
