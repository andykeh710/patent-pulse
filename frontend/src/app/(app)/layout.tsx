import { NavSidebar } from "./NavSidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <NavSidebar />
      <main className="flex-1 ml-64 p-8">{children}</main>
    </div>
  );
}
