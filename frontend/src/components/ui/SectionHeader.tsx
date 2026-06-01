import { ReactNode } from "react";

interface SectionHeaderProps {
  title: string;
  label?: string;
  meta?: string;
  action?: ReactNode;
}

export function SectionHeader({ title, label, meta, action }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div>
        {label && (
          <div className="text-[10px] uppercase tracking-[0.12em] text-[var(--text-muted)] mb-1">
            {label}
          </div>
        )}
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">
          {title}
        </h2>
        {meta && (
          <p className="text-xs text-[var(--text-muted)] mt-0.5">{meta}</p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
