
'use client';

import { useState } from 'react';
import { indexNotes } from '@/lib/api';
import Link from 'next/link';

export default function Home() {
  const [ rootDir, setRootDir ] = useState("");
  const [ status, setStatus] = useState<string>("");

  return (
    <main className="max-w-2xl mx-auto p-6 space-y-4">
      <h1 className="text-2xl font-semibold">SmartNote</h1>
      <p className="text-sm text-gray-600">Index a folder of .md/.txt notes, then search or ask questions.</p>

      <div className="space-y-2">
        <label className="text-sm font-medium">Notes folder path</label>
        <input
          className="w-full border rounded p-2"
          value={rootDir}
          onChange={(e) => setRootDir(e.target.value)}
          placeholder="C:\Users\thoma\Notes"
        />
      </div>

      <button
        className="px-4 py-2 rounded bg-black text-white"
        onClick={async () => {
          setStatus("Indexing...");
          try {
            await indexNotes(rootDir);
            setStatus("✅ Indexed successfully.");
          } catch (e: any) {
            setStatus(`❌ ${e.message}`);
          }
        }}
      >
        Index
      </button>

      {status && <pre className="text-sm whitespace-pre-wrap">{status}</pre>}

      <div className="pt-4 flex gap-4 underline">
        <Link href="/search">Search</Link>
        <Link href="/ask">Ask</Link>
      </div>
    </main>
  );
}