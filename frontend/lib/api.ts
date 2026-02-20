// lib/api.ts
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

async function readError(res: Response) {
  const text = await res.text().catch(() => "");
  return text ? `${res.status} ${res.statusText} - ${text}` : `${res.status} ${res.statusText}`;
}

export type IngestDoc = {
  path: string;
  text: string;
  title?: string;
  mtime?: number;
};

export async function searchNotes(sessionId: string, query: string, topK: number) {
  const url = new URL(`${API_BASE}/notes/search`);
  url.searchParams.set("session_id", sessionId);
  url.searchParams.set("q", query);
  url.searchParams.set("top_k", String(topK));

  const res = await fetch(url.toString(), { cache: "no-store" });
  if (!res.ok) throw new Error(`Search failed: ${await readError(res)}`);
  return res.json();
}

export async function askNotes(sessionId: string, query: string, topK: number) {
  const res = await fetch(`${API_BASE}/notes/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, query, top_k: topK }),
  });

  if (!res.ok) throw new Error(`Ask failed: ${await readError(res)}`);
  return res.json();
}

export async function ingestNotes(sessionId: string, docs: IngestDoc[]) {
  const res = await fetch(`${API_BASE}/notes/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, docs }),
  });

  if (!res.ok) throw new Error(`Ingest failed: ${await readError(res)}`);
  return res.json();
}

export async function clearNotes(sessionId: string) {
  const res = await fetch(`${API_BASE}/notes/clear`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId }),
  });

  if (!res.ok) throw new Error(`Clear failed: ${await readError(res)}`);
  return res.json();
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Health check failed: ${await readError(res)}`);
  return res.json();
}