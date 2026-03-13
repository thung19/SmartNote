"use client";

import { useState } from "react";
import { searchNotes } from "@/lib/api";
import { getOrCreateSessionId } from "@/lib/session";

type Result = {
  chunk_id?: string;
  file_path: string;
  text: string;
  score: number;
};

export default function SearchPage() {
  const [q, setQ] = useState("");
  const [topK, setTopK] = useState(5);
  const [results, setResults] = useState<Result[]>([]);
  const [status, setStatus] = useState("");

  return (
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/70 bg-white/80 p-6 shadow-xl shadow-cyan-100/70 backdrop-blur">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <div className="inline-flex items-center rounded-full border border-cyan-200 bg-cyan-50 px-3 py-1 text-xs font-medium text-cyan-700">
              Semantic retrieval
            </div>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">Search your ingested notes</h1>
            <p className="mt-2 text-sm text-slate-600">
              Enter a query to find the most relevant note chunks from the current session.
            </p>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-[1fr_110px_auto]">
          <input
            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search query..."
          />
          <input
            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-cyan-400 focus:ring-4 focus:ring-cyan-100"
            type="number"
            min={1}
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value || "5", 10))}
          />
          <button
            type="button"
            className="rounded-2xl bg-gradient-to-r from-cyan-500 to-sky-600 px-5 py-3 text-sm font-medium text-white shadow-lg shadow-cyan-200/60 transition hover:scale-[1.01]"
            onClick={async () => {
              const sid = getOrCreateSessionId();
              setStatus("Searching...");
              try {
                const data = await searchNotes(sid, q, topK);
                setResults(data ?? []);
                setStatus(`Found ${(data ?? []).length} result(s).`);
              } catch (e: unknown) {
                const message = e instanceof Error ? e.message : "Search failed";
                setStatus(message);
              }
            }}
          >
            Search
          </button>
        </div>

        {status && <div className="mt-4 rounded-2xl border border-cyan-100 bg-cyan-50 px-4 py-3 text-sm text-cyan-800">{status}</div>}
      </section>

      <section className="space-y-4">
        {results.length === 0 ? (
          <div className="rounded-[28px] border border-slate-200 bg-white/80 px-6 py-10 text-center text-sm text-slate-500 shadow-lg shadow-slate-200/50">
            No results yet.
          </div>
        ) : (
          results.map((r, i) => (
            <article
              key={r.chunk_id ?? String(i)}
              className="rounded-[24px] border border-white/70 bg-white/85 p-5 shadow-lg shadow-slate-200/60 backdrop-blur"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm font-semibold text-slate-900">{r.file_path}</div>
                <div className="rounded-full bg-cyan-50 px-3 py-1 text-xs font-medium text-cyan-700">score {r.score.toFixed(3)}</div>
              </div>
              <pre className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-700">{r.text}</pre>
            </article>
          ))
        )}
      </section>
    </main>
  );
}