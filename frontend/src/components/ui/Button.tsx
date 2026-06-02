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
    "inline-flex items-center justify-center rounded-[var(--radius-md)] text-sm font-medium transition-all duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-base)] disabled:opacity-50 disabled:cursor-not-allowed";

  const sizes = {
    sm: "px-3 py-1.5 text-xs",
    md: "px-4 py-2",
  };

  const variants: Record<NonNullable<ButtonProps["variant"]>, string> = {
    primary:
      "bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] active:scale-[0.98]",
    secondary:
      "border border-[var(--border-default)] text-[var(--text-secondary)] bg-transparent hover:bg-[var(--bg-glass)] hover:border-[var(--accent)]/40",
    ghost:
      "text-[var(--text-muted)] bg-transparent hover:text-[var(--text-primary)] hover:bg-[var(--bg-glass)]",
    outline:
      "border border-[var(--border-default)] text-[var(--text-secondary)] bg-transparent hover:bg-[var(--bg-glass)] hover:border-[var(--accent)]/40",
    default:
      "bg-[var(--bg-glass)] border border-[var(--border-subtle)] text-[var(--text-primary)] hover:bg-[var(--bg-glass-strong)]",
    danger:
      "bg-[var(--expiry-lapsed-confirmed)]/10 border border-[var(--expiry-lapsed-confirmed)]/30 text-[var(--expiry-lapsed-confirmed)] hover:bg-[var(--expiry-lapsed-confirmed)]/20",
  };

  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}
