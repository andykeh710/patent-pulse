import { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  variant?: "default" | "glass" | "elevated";
  interactive?: boolean;
  className?: string;
}

export function Card({
  children,
  variant = "default",
  interactive = false,
  className = "",
}: CardProps) {
  const base = "rounded-[var(--radius-lg)] border p-5";
  const variants = {
    default: "bg-[var(--bg-surface)] border-[var(--border-subtle)]",
    glass: "bg-[var(--bg-glass)] border-[var(--border-subtle)]",
    elevated: "bg-[var(--bg-elevated)] border-[var(--border-default)] shadow-[var(--shadow-sm)]",
  };
  const interactiveClasses = interactive
    ? "surface-interactive cursor-pointer"
    : "";

  return (
    <div className={`${base} ${variants[variant]} ${interactiveClasses} ${className}`}>
      {children}
    </div>
  );
}
