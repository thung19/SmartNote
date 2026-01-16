'use client';

import { useState } from "react";
import { searchNotes } from "@/lib/api";

type Result = { 
    file_path: string; 
    text: string; 
    score: number; 
    chunk_id?: number 
};

export default function SearchPage() {
    const [q, setQ] = useState("");
    const [topK, setTopK] = useState(5);
    const [results, setResults] = useState<Result[]>([]);
    const [status, setStatus] = useState("");

    return (
        <main className="max-w-3xl mx-auto p-6 space-y-4">
            <h1 className="text-2xl font-semibold">Search</h1>
            <div className="flex gap-2">
                <input className="flex-1 border rounded p-2" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search query..." />
                <input className="w-20 border rounded p-2" type="number" value={topK} onChange={(e) => setTopK(parseInt(e.target.value || "5", 10))} />
                <button
                    className="px-4 py-2 rounded bg-black text-white"
                    onClick={async () => {
                        setStatus("Searching...");
                        try {
                        const data = await searchNotes(q, topK);
                        setResults(data);
                        setStatus(`✅ Found ${data.length} result(s).`);
                        } catch (e: any) {
                        setStatus(`❌ ${e.message}`);
                        }
                    }}
                >
                Search
                </button>
            </div>

            {status && <div className="text-sm">{status}</div>}
            <div className="space-y-3">
                {results.map((r, i) => (
                <div key={i} className="border rounded p-3 space-y-1">
                    <div className="text-sm font-medium">{r.file_path}</div>
                    <div className="text-xs text-gray-600">score: {r.score.toFixed(3)}</div>
                    <pre className="text-sm whitespace-pre-wrap">{r.text}</pre>
                </div>
                ))}
            </div>

            <div className="pt-4 underline">
                <a href="/">← Back</a>
            </div>


        </main>
    );
}