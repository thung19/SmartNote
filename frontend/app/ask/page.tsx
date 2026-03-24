"use client";

import { useState } from "react";
import { askNotes } from "@/lib/api";
import { getOrCreateSessionId } from "@/lib/session";

type Chunk = {
  chunk_id?: string;
  file_path: string;
  text: string;
  score: number;
};

export default function AskPage() {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(5);
  const [answer, setAnswer] = useState("");
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [status, setStatus] = useState("");

  return (
    <main className="space-y-5">
      <section className="rounded-xl border border-white/60 bg-white/80 p-6 shadow-lg shadow-slate-200/50 backdrop-blur">
        <div className="mb-5">
          <div className="inline-flex items-center gap-1.5 rounded border border-fuchsia-200 bg-fuchsia-50 px-2.5 py-1 text-xs font-semibold tracking-wide text-fuchsia-700 uppercase">
            Grounded Q&amp;A
          </div>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-900">Ask your notes</h1>
          <p className="mt-1.5 text-sm text-slate-500">
            The answer is generated strictly from the note chunks in the current session, with citations.
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-[1fr_110px_auto]">
          <input
            className="rounded-md border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition focus:border-fuchsia-400 focus:ring-2 focus:ring-fuchsia-100"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question..."
          />
          <input
            className="rounded-md border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-900 outline-none transition focus:border-fuchsia-400 focus:ring-2 focus:ring-fuchsia-100"
            type="number"
            min={1}
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value || "5", 10))}
          />
          <button
            type="button"
            className="rounded-md bg-violet-700 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-800"
            onClick={async () => {
              const sid = getOrCreateSessionId();
              setStatus("Thinking...");
              setAnswer("");
              setChunks([]);
              try {
                const data = await askNotes(sid, query, topK);
                setAnswer(data.answer ?? "");
                setChunks(data.chunks ?? []);
                setStatus("Done.");
              } catch (e: unknown) {
                const message = e instanceof Error ? e.message : "Ask failed";
                setStatus(message);
              }
            }}
          >
            Ask
          </button>
        </div>

        {status && (
          <div className="mt-4 rounded-md border border-fuchsia-100 bg-fuchsia-50 px-4 py-2.5 text-sm text-fuchsia-800">
            {status}
          </div>
        )}
      </section>

      {answer && (
        <section className="rounded-xl border border-white/60 bg-white/85 p-6 shadow-lg shadow-slate-200/50 backdrop-blur">
          <div className="mb-3 text-xs font-semibold uppercase tracking-widest text-violet-600">Answer</div>
          <pre className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{answer}</pre>
        </section>
      )}

      {chunks.length > 0 && (
        <section className="space-y-3">
          <div className="text-xs font-semibold uppercase tracking-widest text-slate-400">Citations</div>
          {chunks.map((c, i) => (
            <article
              key={c.chunk_id ?? i}
              className="rounded-lg border border-slate-100 bg-white/90 p-5 shadow-sm backdrop-blur"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm font-semibold text-slate-800">{c.file_path}</div>
                <div className="rounded border border-fuchsia-200 bg-fuchsia-50 px-2 py-0.5 text-xs font-medium text-fuchsia-700">
                  {c.score.toFixed(3)}
                </div>
              </div>
              <pre className="mt-3 whitespace-pre-wrap text-sm leading-7 text-slate-600">{c.text}</pre>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
