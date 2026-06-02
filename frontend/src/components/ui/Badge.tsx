"use client";

import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "danger" | "speculative";
  size?: "sm" | "md";
  className?: string;
}

export function Badge({
  children,
  variant = "default",
  size = "sm",
  className,
}: BadgeProps) {
  const variantClasses = {
    default: "bg-[var(--text-muted)]/12 text-[var(--text-muted)]",
    success: "bg-[var(--score-high)]/12 text-[var(--score-high)]",
    warning: "bg-[var(--warning)]/12 text-[var(--warning)]",
    danger: "bg-[var(--expiry-lapsed-confirmed)]/12 text-[var(--expiry-lapsed-confirmed)]",
    speculative: "bg-[var(--warning)]/12 text-[var(--warning)] border border-[var(--warning)]/30",
  };

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-2.5 py-1 text-sm",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center font-medium rounded-full",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
    >
      {children}
    </span>
  );
}
