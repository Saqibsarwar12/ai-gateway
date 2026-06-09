"use client";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export default function DocsPage() {
  return (
    <iframe
      src={`${API_BASE}/docs`}
      style={{
        width: "100%",
        height: "100vh",
        border: "none",
        position: "fixed",
        top: 0,
        left: 0,
      }}
      title="API Documentation"
    />
  );
}
