"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";

export function AccountDropdown() {
  const { user, isAuthenticated } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const router = useRouter();

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  if (!isAuthenticated) {
    return (
      <Link
        href="/login"
        className="text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
      >
        Sign in
      </Link>
    );
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
      >
        <span className="w-6 h-6 rounded-full bg-[var(--signal-blue)]/20 flex items-center justify-center text-xs">
          {user?.email?.[0]?.toUpperCase() || "?"}
        </span>
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-48 bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg shadow-lg py-1 z-50">
          <div className="px-3 py-2 border-b border-[var(--border-subtle)]">
            <p className="text-xs text-[var(--text-primary)] truncate">{user?.email}</p>
          </div>
          {[
            { label: "Watchlist", href: "/watchlist" },
            { label: "Account", href: "/account" },
            { label: "Billing", href: "/account/billing" },
            { label: "Logout", href: "/login", action: () => { document.cookie = "auth_session=; path=/; max-age=0"; router.push("/login"); } },
          ].map((item) => (
            <button
              key={item.label}
              onClick={() => { setOpen(false); item.action ? item.action() : router.push(item.href); }}
              className="w-full text-left px-3 py-2 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-glass)] transition-colors"
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
