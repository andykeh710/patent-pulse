"use client";

import Link from "next/link";
import { useState } from "react";
import { ThemeToggle } from "@/lib/ThemeProvider";

export function MarketingNav() {
  const [open, setOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-[var(--z-sticky)] bg-[var(--bg-base)]/90 backdrop-blur-xl border-b border-[var(--border-subtle)]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link
            href="/"
            className="flex items-center gap-2 text-lg font-semibold text-[var(--text-primary)] hover:text-[var(--accent)] transition-colors"
          >
            <span>Invention Index 8</span>
          </Link>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-8">
            <a
              href="#pricing"
              className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            >
              Pricing
            </a>
            <a
              href="#about"
              className="text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
            >
              About
            </a>
            <Link
              href="/login"
              className="text-sm text-[var(--accent)] hover:text-[var(--accent-hover)] font-medium transition-colors"
            >
              Sign in
            </Link>
            <ThemeToggle />
          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden p-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
            onClick={() => setOpen(!open)}
            aria-label="Toggle menu"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              {open ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              )}
            </svg>
          </button>
        </div>

        {/* Mobile menu */}
        {open && (
          <div className="md:hidden pb-4 border-t border-[var(--border-subtle)]">
            <Link
              href="/pricing"
              className="block py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              onClick={() => setOpen(false)}
            >
              Pricing
            </Link>
            <Link
              href="/about"
              className="block py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              onClick={() => setOpen(false)}
            >
              About
            </Link>
            <Link
              href="/login"
              className="block py-2 text-sm text-[var(--accent)] font-medium hover:text-[var(--accent)]"
              onClick={() => setOpen(false)}
            >
              Sign in
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}
