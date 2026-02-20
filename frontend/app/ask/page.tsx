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
    <main className="max-w-3xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-semibold">Ask</h1>

      <div className="flex gap-2">
        <input className="flex-1 border rounded p-2" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Ask a question..." />
        <input className="w-20 border rounded p-2" type="number" value={topK} onChange={(e) => setTopK(parseInt(e.target.value || "5", 10))} />
        <button
          className="px-4 py-2 rounded bg-black text-white"
          onClick={async () => {
            const sid = getOrCreateSessionId();
            setStatus("Thinking...");
            setAnswer("");
            setChunks([]);
            try {
              const data = await askNotes(sid, query, topK);
              setAnswer(data.answer ?? "");
              setChunks(data.chunks ?? []);
              setStatus("✅ Done.");
            } catch (e: any) {
              setStatus(`❌ ${e.message}`);
            }
          }}
        >
          Ask
        </button>
      </div>

      {status && <div className="text-sm">{status}</div>}

      {answer && (
        <div className="border rounded p-3">
          <div className="text-sm font-medium">Answer</div>
          <pre className="text-sm whitespace-pre-wrap">{answer}</pre>
        </div>
      )}

      {chunks.length > 0 && (
        <div className="space-y-3">
          <div className="text-sm font-medium">Citations</div>
          {chunks.map((c, i) => (
            <div key={c.chunk_id ?? i} className="border rounded p-3">
              <div className="text-sm font-medium">{c.file_path}</div>
              <div className="text-xs text-gray-600">score: {c.score.toFixed(3)}</div>
              <pre className="text-sm whitespace-pre-wrap">{c.text}</pre>
            </div>
          ))}
        </div>
      )}

      <div className="pt-4 underline">
        <a href="/">← Back</a>
      </div>
    </main>
  );
}