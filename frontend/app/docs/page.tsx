"use client";

import { useEffect, useRef, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.crossOrigin = "anonymous";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.body.appendChild(s);
  });
}

export default function DocsPage() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        await Promise.all([
          loadScript("https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"),
          loadScript("https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"),
        ]);
        if (cancelled) return;

        const SwaggerUIBundle = (window as any).SwaggerUIBundle;
        const StandalonePreset = (window as any).SwaggerUIStandalonePreset;

        SwaggerUIBundle({
          url: `${API_BASE}/openapi.json`,
          dom_id: "#swagger-ui",
          presets: [StandalonePreset],
          layout: "StandaloneLayout",
          deepLinking: true,
          defaultModelsExpandDepth: 1,
          defaultModelExpandDepth: 1,
          docExpansion: "list",
          filter: true,
          showExtensions: true,
          showCommonExtensions: true,
          tryItOutEnabled: true,
        });

        setReady(true);
      } catch (err) {
        console.error("Swagger UI load failed:", err);
      }
    }

    init();
    return () => { cancelled = true; };
  }, []);

  return (
    <>
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
      <div style={{ minHeight: "100vh", background: "#fafafa" }}>
        <div
          id="swagger-ui"
          style={{ maxWidth: 1460, margin: "0 auto", padding: "20px" }}
        />
        {!ready && (
          <div style={{ textAlign: "center", padding: "80px 20px", color: "#666" }}>
            Loading API documentation...
          </div>
        )}
      </div>
    </>
  );
}
