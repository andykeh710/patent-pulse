import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  if (request.nextUrl.pathname !== "/") {
    return NextResponse.next();
  }

  try {
    const sessionCookie = request.cookies.get("auth_session");
    if (sessionCookie?.value) {
      return NextResponse.redirect(new URL("/today", request.url));
    }
  } catch {
    // Cookie parse/verify error — serve landing page, never block visitors.
  }

  return NextResponse.next();
}

export const config = {
  matcher: "/",
};
