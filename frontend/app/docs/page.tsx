"use client";

import { useEffect } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function DocsPage() {
  useEffect(() => {
    const script = document.createElement("script");
    script.src = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js";
    script.crossOrigin = "anonymous";
    script.onload = () => {
      const SwaggerUIBundle = (window as any).SwaggerUIBundle;
      const presets = (window as any).SwaggerUIStandalonePreset;
      SwaggerUIBundle({
        url: `${API_BASE}/openapi.json`,
        dom_id: "#swagger-ui",
        presets: [presets],
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
    };
    document.body.appendChild(script);

    const css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css";
    document.head.appendChild(css);

    const presetScript = document.createElement("script");
    presetScript.src = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js";
    presetScript.crossOrigin = "anonymous";
    document.body.appendChild(presetScript);

    return () => {
      document.body.removeChild(script);
      document.head.removeChild(css);
      document.body.removeChild(presetScript);
    };
  }, []);

  return (
    <div style={{ minHeight: "100vh", background: "#fafafa" }}>
      <div
        id="swagger-ui"
        style={{ maxWidth: 1460, margin: "0 auto", padding: "0 20px" }}
      />
    </div>
  );
}
