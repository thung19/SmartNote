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
    <main className="space-y-5">
      <section className="rounded-xl border border-white/60 bg-white/80 p-6 shadow-lg shadow-slate-200/50 backdrop-blur">
        <div className="mb-5">
          <div className="inline-flex items-center gap-1.5 rounded border border-cyan-200 bg-cyan-50 px-2.5 py-1 text-xs font-semibold tracking-wide text-cyan-700 uppercase">
            Semantic retrieval
          </div>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">Search your notes</h1>
          <p className="mt-1.5 text-sm text-slate-500">
            Find the most relevant note chunks from the current session by meaning, not just keywords.
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-[1fr_110px_auto]">
          <input
            className="rounded-md border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") e.currentTarget.closest("section")?.querySelector("button")?.click();
            }}
            placeholder="Search query..."
          />
          <input
            className="rounded-md border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition focus:border-cyan-400 focus:ring-2 focus:ring-cyan-100"
            type="number"
            min={1}
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value || "5", 10))}
          />
          <button
            type="button"
            className="rounded-md bg-cyan-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-cyan-700"
            onClick={async () => {
              const sid = getOrCreateSessionId();
              setStatus("Searching...");
              try {
                const data = await searchNotes(sid, q, topK);
                setResults(data ?? []);
                setStatus(`${(data ?? []).length} result(s) found.`);
              } catch (e: unknown) {
                const message = e instanceof Error ? e.message : "Search failed";
                setStatus(message);
              }
            }}
          >
            Search
          </button>
        </div>

        {status && (
          <div className="mt-4 rounded-md border border-cyan-100 bg-cyan-50 px-4 py-2.5 text-sm text-cyan-800">
            {status}
          </div>
        )}
      </section>

      <section className="space-y-3">
        {results.length === 0 ? (
          <div className="rounded-xl border border-slate-100 bg-white/70 px-6 py-10 text-center text-sm text-slate-400 shadow-sm">
            No results yet. Run a search above.
          </div>
        ) : (
          results.map((r, i) => (
            <article
              key={r.chunk_id ?? String(i)}
              className="rounded-lg border border-slate-100 bg-white/90 p-5 shadow-sm backdrop-blur"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm font-semibold text-slate-800">{r.file_path}</div>
                <div className="rounded border border-cyan-200 bg-cyan-50 px-2 py-0.5 text-xs font-medium text-cyan-700">
                  {r.score.toFixed(3)}
                </div>
              </div>
              <pre className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-600">{r.text}</pre>
            </article>
          ))
        )}
      </section>
    </main>
  );
}
