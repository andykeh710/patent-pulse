// Prevent static prerendering — Today page uses dynamic per-user data
export const dynamic = "force-dynamic";

export default function TodayLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
