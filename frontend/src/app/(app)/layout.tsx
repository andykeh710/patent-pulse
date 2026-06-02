import { TopNav } from "@/components/nav/TopNav";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--bg-base)]">
      <TopNav />
      <main className="pt-14 px-6 max-w-[1440px] mx-auto text-[var(--text-primary)]">
        {children}
      </main>
    </div>
  );
}
