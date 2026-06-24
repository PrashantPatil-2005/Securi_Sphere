import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

const AUTH_COOKIE = "ss_auth";
const publicPaths = ["/login", "/register", "/forgot-password", "/reset-password"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isPublic = publicPaths.some((p) => pathname.startsWith(p));
  const hasAuth = request.cookies.has(AUTH_COOKIE);

  if (isPublic) {
    return NextResponse.next();
  }

  if (!hasAuth) {
    const loginUrl = new URL("/login", request.url);
    if (pathname !== "/") loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|api).*)"],
};
