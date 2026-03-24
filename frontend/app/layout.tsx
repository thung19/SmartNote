import type { Metadata } from "next";
import Link from "next/link";
import { Bricolage_Grotesque, Geist_Mono } from "next/font/google";
import "./globals.css";

import { SessionProvider } from "./state/sessionStore";

const bricolage = Bricolage_Grotesque({
  variable: "--font-bricolage",
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
      <body className={`${bricolage.variable} ${geistMono.variable} antialiased`}>
        <SessionProvider>
          <div className="min-h-screen">
            <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-xl">
              <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3.5 sm:px-6">
                <Link href="/" className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-linear-to-br from-violet-600 via-fuchsia-500 to-cyan-400 text-base text-white shadow-md shadow-violet-500/20">
                    ✦
                  </div>
                  <div>
                    <div className="text-sm font-semibold tracking-tight text-slate-900">SmartNote</div>
                    <div className="text-xs text-slate-400">Upload · Search · Ask</div>
                  </div>
                </Link>

                <nav className="flex items-center gap-0.5 text-sm font-medium text-slate-500">
                  <Link href="/" className="px-3 py-1.5 transition hover:text-violet-700">
                    Home
                  </Link>
                  <span className="text-slate-300">·</span>
                  <Link href="/search" className="px-3 py-1.5 transition hover:text-cyan-700">
                    Search
                  </Link>
                  <span className="text-slate-300">·</span>
                  <Link href="/ask" className="px-3 py-1.5 transition hover:text-fuchsia-700">
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
