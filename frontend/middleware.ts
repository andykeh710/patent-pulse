import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Routes that do NOT require authentication
const PUBLIC_PATHS = [
  "/",
  "/login",
  "/login/verify",
  "/pricing",
  "/about",
  "/terms",
  "/privacy",
  "/contact",
  "/health",
  "/api",
  "/_next",
  "/favicon.ico",
  "/og-image.svg",
];

function isPublic(pathname: string): boolean {
  if (pathname === "/") return true;
  return PUBLIC_PATHS.some((p) => pathname.startsWith(p));
}

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;

  // Public routes — allow through
  if (isPublic(pathname)) {
    // If already logged in and on landing page, redirect to Today
    if (pathname === "/") {
      try {
        const sessionCookie = request.cookies.get("auth_session");
        if (sessionCookie?.value) {
          return NextResponse.redirect(new URL("/today", request.url));
        }
      } catch {
        // Cookie parse error — serve landing page
      }
    }
    return NextResponse.next();
  }

  // Protected route — require session
  try {
    const sessionCookie = request.cookies.get("auth_session");
    if (!sessionCookie?.value) {
      const loginUrl = new URL("/login", request.url);
      loginUrl.searchParams.set("redirect", pathname);
      return NextResponse.redirect(loginUrl);
    }
  } catch {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for static files:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - _next/data (getServerSideProps)
     * - favicon.ico, robots.txt, sitemap.xml
     */
    "/((?!_next/static|_next/image|_next/data|favicon.ico|robots.txt|sitemap.xml).*)",
  ],
};
