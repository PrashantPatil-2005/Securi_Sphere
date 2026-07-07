import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { buildContentSecurityPolicy, createNonce } from "@/lib/csp";

const AUTH_COOKIE = "ss_auth";
const publicPaths = ["/login", "/register", "/forgot-password", "/reset-password", "/accept-invite"];

function requestWithNonce(request: NextRequest, nonce: string): Headers {
  const headers = new Headers(request.headers);
  headers.set("x-nonce", nonce);
  return headers;
}

function applySecurityHeaders(response: NextResponse, nonce: string) {
  response.headers.set("Content-Security-Policy", buildContentSecurityPolicy(nonce));
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublic = publicPaths.some((p) => pathname.startsWith(p));
  const hasAuth = request.cookies.has(AUTH_COOKIE);
  const nonce = createNonce();

  if (isPublic) {
    const response = NextResponse.next({ request: { headers: requestWithNonce(request, nonce) } });
    applySecurityHeaders(response, nonce);
    return response;
  }

  if (!hasAuth) {
    const loginUrl = new URL("/login", request.url);
    if (pathname !== "/") loginUrl.searchParams.set("next", pathname);
    const response = NextResponse.redirect(loginUrl);
    applySecurityHeaders(response, nonce);
    return response;
  }

  const response = NextResponse.next({ request: { headers: requestWithNonce(request, nonce) } });
  applySecurityHeaders(response, nonce);
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
