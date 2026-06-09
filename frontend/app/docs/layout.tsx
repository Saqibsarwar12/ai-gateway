import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "API Documentation — AI Gateway",
  description: "Swagger API documentation for AI Gateway — OpenAI-compatible endpoints, admin API, provider management, and more.",
  robots: { index: false, follow: false },
};

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
