import type { Metadata } from "next";
import Link from "next/link";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

import { SessionProvider } from "./state/sessionStore";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "SmartNote",
  description: "Session-scoped in-memory RAG",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <SessionProvider>
          <div className="min-h-screen">
            <header className="sticky top-0 z-40 border-b border-white/60 bg-white/75 backdrop-blur-xl">
              <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
                <Link href="/" className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 via-fuchsia-500 to-cyan-400 text-lg text-white shadow-lg shadow-violet-500/25">
                    ✦
                  </div>
                  <div>
                    <div className="text-base font-semibold text-slate-900">SmartNote</div>
                    <div className="text-xs text-slate-500">Upload, search, and ask your notes</div>
                  </div>
                </Link>

                <nav className="flex items-center gap-2 rounded-2xl border border-slate-200/80 bg-white/80 p-1 shadow-sm">
                  <Link
                    href="/"
                    className="rounded-xl px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-violet-50 hover:text-violet-700"
                  >
                    Home
                  </Link>
                  <Link
                    href="/search"
                    className="rounded-xl px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-cyan-50 hover:text-cyan-700"
                  >
                    Search
                  </Link>
                  <Link
                    href="/ask"
                    className="rounded-xl px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-fuchsia-50 hover:text-fuchsia-700"
                  >
                    Ask
                  </Link>
                </nav>
              </div>
            </header>

            <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">{children}</div>
          </div>
        </SessionProvider>
      </body>
    </html>
  );
}