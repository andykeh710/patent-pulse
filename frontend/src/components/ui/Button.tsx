import { ReactNode, ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: "primary" | "secondary" | "ghost" | "danger" | "default" | "outline";
  size?: "sm" | "md";
  className?: string;
}

export function Button({
  children,
  variant = "primary",
  size = "md",
  className = "",
  ...props
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center rounded-lg text-sm font-medium transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--signal-glow)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-base)] disabled:opacity-50 disabled:cursor-not-allowed";

  const sizes = {
    sm: "px-3 py-1.5 text-xs",
    md: "px-4 py-2",
  };

  const variants: Record<NonNullable<ButtonProps["variant"]>, string> = {
    primary:
      "bg-gradient-to-r from-[var(--signal-blue)] to-[var(--signal-violet)] text-white hover:shadow-[0_0_20px_rgba(99,102,241,0.3)] hover:-translate-y-0.5 active:translate-y-0",
    secondary:
      "border border-[var(--border-strong)] text-[var(--text-secondary)] bg-transparent hover:bg-[var(--bg-glass)] hover:border-[var(--signal-blue)]/40",
    ghost:
      "text-[var(--text-muted)] bg-transparent hover:text-[var(--text-primary)] hover:bg-[var(--bg-glass)]",
    outline:
      "border border-[var(--border-strong)] text-[var(--text-secondary)] bg-transparent hover:bg-[var(--bg-glass)] hover:border-[var(--signal-blue)]/40",
    default:
      "bg-[var(--bg-glass)] border border-[var(--border-subtle)] text-[var(--text-primary)] hover:bg-[var(--bg-glass-strong)]",
    danger:
      "bg-red-500/10 border border-red-400/30 text-red-400 hover:bg-red-500/20",
  };

  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}
