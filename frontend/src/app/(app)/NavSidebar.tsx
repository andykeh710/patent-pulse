"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/AuthContext";
import { BRAND } from "@/lib/brand";

const NAV_ITEMS = [
  {
    href: "/today",
    label: "Today",
    icon: "M13 10V3L4 14h7v7l9-11h-7z",
  },
  {
    href: "/opportunity",
    label: "Opportunities",
    icon: "M13 7h8m0 0v8m0-8l-8 8-4-4-6 6",
  },
  {
    href: "/trends",
    label: "Trends",
    icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
  },
  {
    href: "/expiry",
    label: "Expiring Patents",
    icon: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z",
  },
  {
    href: "/companies",
    label: "Companies",
    icon: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4",
  },
  {
    href: "/search",
    label: "Search",
    icon: "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z",
  },
  {
    href: "/themes",
    label: "Topics",
    icon: "M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A2 2 0 013 12V7a4 4 0 014-4z",
  },
  {
    href: "/patents",
    label: "Patents",
    icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
  },
  {
    href: "/watchlist",
    label: "Watchlist",
    icon: "M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z",
  },
  {
    href: "/about",
    label: "About / Limitations",
    icon: "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  },
];

const ADMIN_ITEMS = [
  {
    href: "/admin/ai-runs",
    label: "AI Runs",
    icon: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z",
  },
];

export function NavSidebar() {
  const pathname = usePathname();
  const { isAuthenticated, user } = useAuth();

  const isActive = (href: string) => {
    if (href === "/today") return pathname === "/" || pathname === "/today";
    return pathname.startsWith(href);
  };

  return (
    <nav className="w-64 bg-[var(--bg-surface)] border-r border-[var(--border-subtle)] p-4 fixed h-full">
      <div className="mb-8">
        <Link href="/" className="inline-flex items-center gap-2 group">
          <span className="text-xl font-bold text-[var(--accent)] group-hover:text-[var(--accent)] transition-colors">
            {BRAND.compactName}
          </span>
        </Link>
        <p className="text-sm text-[var(--text-muted)] mt-1">Invention Intelligence</p>
      </div>

      <ul className="space-y-1">
        {NAV_ITEMS.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              className={`flex items-center px-3 py-2 rounded-lg transition-colors ${
                isActive(item.href)
                  ? "bg-bg-[var(--bg-elevated)] text-[var(--accent)] font-medium"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)]"
              }`}
            >
              <svg
                className="w-5 h-5 mr-3 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d={item.icon}
                />
              </svg>
              {item.label}
            </Link>
          </li>
        ))}

        <li className="pt-4 mt-4 border-t border-[var(--border-subtle)]">
          <span className="px-3 text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wider">
            Admin
          </span>
        </li>

        {ADMIN_ITEMS.map((item) => (
          <li key={item.href}>
            <Link
              href={item.href}
              className={`flex items-center px-3 py-2 rounded-lg transition-colors ${
                isActive(item.href)
                  ? "bg-bg-[var(--bg-elevated)] text-[var(--accent)] font-medium"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)]"
              }`}
            >
              <svg
                className="w-5 h-5 mr-3 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d={item.icon}
                />
              </svg>
              {item.label}
            </Link>
          </li>
        ))}
      </ul>

      <div className="mt-6 pt-4 border-t border-[var(--border-subtle)]">
        {isAuthenticated ? (
          <div className="space-y-1">
            <p className="text-xs text-[var(--text-muted)] truncate px-3">{user?.email}</p>
            <Link
              href="/account"
              className="flex items-center px-3 py-2 rounded-lg text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)]"
            >
              Account
            </Link>
            <Link
              href="/account/billing"
              className="flex items-center px-3 py-2 rounded-lg text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)]"
            >
              Billing
            </Link>
          </div>
        ) : (
          <Link
            href="/login"
            className="flex items-center px-3 py-2 rounded-lg text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)]"
          >
            Sign In
          </Link>
        )}
      </div>
    </nav>
  );
}
