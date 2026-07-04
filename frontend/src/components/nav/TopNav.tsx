"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandMark } from "./BrandMark";
import { AccountDropdown } from "./AccountDropdown";
import { ThemeToggle } from "@/lib/ThemeProvider";

const NAV_ITEMS = [
  { href: "/today", label: "Today" },
  { href: "/chat", label: "Chat" },
  { href: "/patents", label: "Patents" },
  { href: "/expiry", label: "Expiry" },
  { href: "/opportunity", label: "Opportunities" },
  { href: "/trends", label: "Trends" },
  { href: "/themes", label: "Topics" },
  { href: "/companies", label: "Companies" },
];

export function TopNav() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/today") return pathname === "/" || pathname === "/today";
    return pathname.startsWith(href);
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-[var(--z-sticky)] h-14 bg-[var(--bg-base)]/85 backdrop-blur-xl border-b border-[var(--border-subtle)]">
      <div className="max-w-[1440px] mx-auto px-6 h-full flex items-center justify-between">
        {/* Left: brand + nav */}
        <div className="flex items-center gap-8">
          <Link href="/today" className="flex-shrink-0">
            <BrandMark />
          </Link>

          <div className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`px-3 py-1.5 rounded-[var(--radius-sm)] text-sm transition-colors ${
                  isActive(item.href)
                    ? "bg-[var(--accent-muted)] text-[var(--accent)] font-medium"
                    : "text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-glass)]"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>
        </div>

        {/* Right: search + account */}
        <div className="flex items-center gap-4">
          <Link
            href="/search"
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
            aria-label="Search"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </Link>
          <ThemeToggle />
          <AccountDropdown />
        </div>
      </div>
    </nav>
  );
}
