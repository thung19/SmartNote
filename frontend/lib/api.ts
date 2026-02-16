// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

/*
export async function indexNotes(rootDir: string) {
  const res = await fetch(`${API_BASE}/notes/index`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ root_dir: rootDir }),
  });
  if (!res.ok) throw new Error(`Index failed: ${res.status}`);
  return res.json();
}
*/

export async function searchNotes(query: string, topK: number) {
  const url = new URL(`${API_BASE}/notes/search`);
  url.searchParams.set("q", query);
  url.searchParams.set("top_k", String(topK));
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`Search failed: ${res.status}`);
  return res.json();
}

export async function askNotes(query: string, topK: number) {
  const res = await fetch(`${API_BASE}/notes/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, top_k: topK }),
  });
  if (!res.ok) throw new Error(`Ask failed: ${res.status}`);
  return res.json();
}

// ✅ NEW: ingest from browser uploads
export type IngestDoc = {
  path: string;
  text: string;
  title?: string;
  mtime?: number;
};

export async function ingestNotes(docs: IngestDoc[]) {
  const res = await fetch(`${API_BASE}/notes/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ docs }),
  });
  if (!res.ok) throw new Error(`Ingest failed: ${res.status}`);
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json(); // { ok: true }
}