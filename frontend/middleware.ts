import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const API = "https://ai-gateway-7dkh.onrender.com";
const PROXY_PATHS = [
  "/admin/auth",
  "/admin/users",
  "/admin/providers",
  "/admin/models",
  "/admin/routing",
  "/admin/analytics",
  "/admin/api-keys",
  "/admin/public",
  "/admin/logs",
  "/admin/stats",
  "/admin/playground",
  "/v1/",
  "/v2/",
  "/v3/",
  "/health",
  "/openapi.json",
];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const shouldProxy = PROXY_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );
  if (!shouldProxy) return NextResponse.next();

  const url = `${API}${pathname}${request.nextUrl.search}`;
  const headers = new Headers(request.headers);
  headers.set("host", new URL(API).host);

  return NextResponse.rewrite(url, { request: { headers } });
}

export const config = {
  matcher: [
    "/admin/:path*",
    "/v1/:path*",
    "/v2/:path*",
    "/v3/:path*",
    "/health",
    "/openapi.json",
  ],
};
