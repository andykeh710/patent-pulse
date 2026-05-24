import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/AuthContext";
import { NavSidebar } from "./NavSidebar";

export const metadata: Metadata = {
  title: "Patent Pulse",
  description: "Patent intelligence and summarization system",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased bg-gray-50 min-h-screen">
        <div className="flex min-h-screen">
          <NavSidebar />
          <main className="flex-1 ml-64 p-8">
            <AuthProvider>{children}</AuthProvider>
          </main>
        </div>
      </body>
    </html>
  );
}
