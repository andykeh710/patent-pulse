// Prevent static prerendering of auth pages — verify needs ?token= from URL
export const dynamic = "force-dynamic";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg-base)]">
      <div className="w-full max-w-md px-4">{children}</div>
    </div>
  );
}
