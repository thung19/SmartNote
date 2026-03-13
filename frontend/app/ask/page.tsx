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
    <main className="space-y-6">
      <section className="rounded-[28px] border border-white/70 bg-white/80 p-6 shadow-xl shadow-fuchsia-100/70 backdrop-blur">
        <div className="mb-5">
          <div className="inline-flex items-center rounded-full border border-fuchsia-200 bg-fuchsia-50 px-3 py-1 text-xs font-medium text-fuchsia-700">
            Grounded Q&A
          </div>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">Ask a question about your notes</h1>
          <p className="mt-2 text-sm text-slate-600">
            The answer is generated from the note chunks in the current session and returned with citations.
          </p>
        </div>

        <div className="grid gap-3 md:grid-cols-[1fr_110px_auto]">
          <input
            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-fuchsia-400 focus:ring-4 focus:ring-fuchsia-100"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask a question..."
          />
          <input
            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 outline-none transition focus:border-fuchsia-400 focus:ring-4 focus:ring-fuchsia-100"
            type="number"
            min={1}
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value || "5", 10))}
          />
          <button
            type="button"
            className="rounded-2xl bg-gradient-to-r from-fuchsia-600 to-violet-600 px-5 py-3 text-sm font-medium text-white shadow-lg shadow-fuchsia-200/60 transition hover:scale-[1.01]"
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

        {status && <div className="mt-4 rounded-2xl border border-fuchsia-100 bg-fuchsia-50 px-4 py-3 text-sm text-fuchsia-800">{status}</div>}
      </section>

      {answer && (
        <section className="rounded-[28px] border border-white/70 bg-white/85 p-6 shadow-xl shadow-violet-100/60 backdrop-blur">
          <div className="mb-3 text-sm font-semibold uppercase tracking-wide text-violet-700">Answer</div>
          <pre className="whitespace-pre-wrap text-sm leading-7 text-slate-700">{answer}</pre>
        </section>
      )}

      {chunks.length > 0 && (
        <section className="space-y-4">
          <div className="text-sm font-semibold uppercase tracking-wide text-slate-600">Citations</div>
          {chunks.map((c, i) => (
            <article
              key={c.chunk_id ?? i}
              className="rounded-[24px] border border-white/70 bg-white/85 p-5 shadow-lg shadow-slate-200/60 backdrop-blur"
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="text-sm font-semibold text-slate-900">{c.file_path}</div>
                <div className="rounded-full bg-fuchsia-50 px-3 py-1 text-xs font-medium text-fuchsia-700">score {c.score.toFixed(3)}</div>
              </div>
              <pre className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-700">{c.text}</pre>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}