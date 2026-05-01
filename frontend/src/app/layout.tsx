import type { Metadata } from "next";
import "./globals.css";

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
          <nav className="w-64 bg-white border-r border-gray-200 p-4 fixed h-full">
            <div className="mb-8">
              <h1 className="text-xl font-bold text-primary-700">
                Patent Pulse
              </h1>
              <p className="text-sm text-gray-500">Patent Intelligence</p>
            </div>

            <ul className="space-y-2">
              <li>
                <a
                  href="/dashboard"
                  className="flex items-center px-3 py-2 text-gray-700 rounded-lg hover:bg-gray-100"
                >
                  <svg
                    className="w-5 h-5 mr-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"
                    />
                  </svg>
                  Dashboard
                </a>
              </li>
              <li>
                <a
                  href="/patents"
                  className="flex items-center px-3 py-2 text-gray-700 rounded-lg hover:bg-gray-100"
                >
                  <svg
                    className="w-5 h-5 mr-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                  Patents
                </a>
              </li>
              <li>
                <a
                  href="/opportunity"
                  className="flex items-center px-3 py-2 text-gray-700 rounded-lg hover:bg-gray-100"
                >
                  <svg
                    className="w-5 h-5 mr-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"
                    />
                  </svg>
                  Opportunity
                </a>
              </li>
              <li>
                <a
                  href="/expiry"
                  className="flex items-center px-3 py-2 text-gray-700 rounded-lg hover:bg-gray-100"
                >
                  <svg
                    className="w-5 h-5 mr-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  Expiry Watch
                </a>
              </li>
              <li className="pt-4 mt-4 border-t border-gray-200">
                <span className="px-3 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                  Admin
                </span>
              </li>
              <li>
                <a
                  href="/admin/ai-runs"
                  className="flex items-center px-3 py-2 text-gray-700 rounded-lg hover:bg-gray-100"
                >
                  <svg
                    className="w-5 h-5 mr-3"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                    />
                  </svg>
                  AI Runs
                </a>
              </li>
            </ul>
          </nav>

          <main className="flex-1 ml-64 p-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
