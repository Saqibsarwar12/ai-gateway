import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI Gateway — Admin",
  description: "Full-control AI gateway platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#030711] text-slate-100 min-h-screen">{children}</body>
    </html>
  );
}
