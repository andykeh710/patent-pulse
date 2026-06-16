"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import { TopNav } from "@/components/nav/TopNav";
import { UsageWarningBanner } from "@/components/UsageWarningBanner";

const PUBLIC_ROUTES = ["/login", "/login/verify"];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated && !PUBLIC_ROUTES.some((r) => pathname.startsWith(r))) {
      const login = new URL("/login", window.location.origin);
      login.searchParams.set("redirect", pathname);
      router.replace(login.toString());
    }
  }, [isAuthenticated, isLoading, pathname, router]);

  // Show nothing while checking auth — prevents flash of unauthenticated content
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[var(--bg-base)] flex items-center justify-center">
        <p className="text-[var(--text-muted)]">Loading…</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-[var(--bg-base)] flex items-center justify-center">
        <p className="text-[var(--text-muted)]">Redirecting to login…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      <TopNav />
      <UsageWarningBanner />
      <main className="pt-14 px-6 max-w-[1440px] mx-auto text-[var(--text-primary)]">
        {children}
      </main>
    </div>
  );
}
