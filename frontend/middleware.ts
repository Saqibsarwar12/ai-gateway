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

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const shouldProxy = PROXY_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/")
  );
  if (!shouldProxy) return NextResponse.next();

  try {
    const url = `${API}${pathname}${request.nextUrl.search}`;

    const headers: Record<string, string> = {};
    request.headers.forEach((value, key) => {
      if (key.toLowerCase() !== "host") {
        headers[key] = value;
      }
    });

    const body = request.method !== "GET" && request.method !== "HEAD"
      ? await request.text()
      : undefined;

    const res = await fetch(url, {
      method: request.method,
      headers,
      body,
      redirect: "manual",
    });

    const responseHeaders = new Headers();
    res.headers.forEach((value, key) => {
      if (key.toLowerCase() !== "content-encoding" &&
          key.toLowerCase() !== "transfer-encoding") {
        responseHeaders.set(key, value);
      }
    });
    responseHeaders.set("access-control-allow-origin", "*");
    responseHeaders.set("access-control-allow-credentials", "true");
    responseHeaders.set("access-control-allow-headers", "*");
    responseHeaders.set("access-control-allow-methods", "*");

    return new NextResponse(res.body, {
      status: res.status,
      statusText: res.statusText,
      headers: responseHeaders,
    });
  } catch (err) {
    console.error("Proxy error:", err);
    return NextResponse.json(
      { detail: "Gateway error — backend unavailable" },
      { status: 502 }
    );
  }
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
