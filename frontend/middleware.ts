import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const API = process.env.API_PROXY_TARGET || "https://ai-gateway-7dkh.onrender.com";

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;

  if (!pathname.startsWith("/api-proxy/")) {
    return NextResponse.next();
  }

  const targetPath = pathname.replace(/^\/api-proxy/, "");
  const url = `${API}${targetPath}${search}`;
  return NextResponse.rewrite(url);
}

export const config = {
  matcher: ["/api-proxy/:path*"],
};
