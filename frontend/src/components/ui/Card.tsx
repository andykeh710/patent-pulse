import { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  variant?: "default" | "glass" | "elevated";
  interactive?: boolean;
  className?: string;
}

export function Card({
  children,
  variant = "glass",
  interactive = false,
  className = "",
}: CardProps) {
  const base = "rounded-xl border p-4";
  const variants = {
    default: "bg-[var(--bg-base)] border-[var(--border-subtle)]",
    glass: "bg-[var(--bg-glass)] backdrop-blur-md border-[var(--border-subtle)]",
    elevated: "bg-[var(--bg-elevated)] border-[var(--border-strong)]",
  };
  const interactiveClasses = interactive
    ? "scan-hover gradient-border-hover cursor-pointer transition-transform hover:-translate-y-0.5 duration-200"
    : "";

  return (
    <div className={`${base} ${variants[variant]} ${interactiveClasses} ${className}`}>
      {children}
    </div>
  );
}
