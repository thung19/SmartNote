// lib/api.ts
const rawApiBase = process.env.NEXT_PUBLIC_API_BASE?.trim();
const API_BASE = (rawApiBase && rawApiBase.length > 0 ? rawApiBase : "/api").replace(/\/+$/, "");

async function readError(res: Response) {
  const text = await res.text().catch(() => "");
  return text ? `${res.status} ${res.statusText} - ${text}` : `${res.status} ${res.statusText}`;
}

async function safeFetch(url: string, init: RequestInit, label: string) {
  try {
    return await fetch(url, init);
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "network error";
    throw new Error(
      `${label} failed: could not reach API at ${API_BASE}. ` +
      `Check frontend env, rewrites, CORS, and backend health. ` +
      `Details: ${message}`
    );
  }
}

export type IngestDoc = {
  path: string;
  text: string;
  title?: string;
  mtime?: number;
};

export async function searchNotes(sessionId: string, query: string, topK: number) {
  const params = new URLSearchParams({
    session_id: sessionId,
    q: query,
    top_k: String(topK),
  });
  const url = `${API_BASE}/notes/search?${params.toString()}`;

  const res = await safeFetch(url, { cache: "no-store" }, "Search");
  if (!res.ok) throw new Error(`Search failed: ${await readError(res)}`);
  return res.json();
}

export async function askNotes(sessionId: string, query: string, topK: number) {
  const res = await safeFetch(
    `${API_BASE}/notes/ask`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, query, top_k: topK }),
    },
    "Ask"
  );

  if (!res.ok) throw new Error(`Ask failed: ${await readError(res)}`);
  return res.json();
}

export async function ingestNotes(sessionId: string, docs: IngestDoc[]) {
  const res = await safeFetch(
    `${API_BASE}/notes/ingest`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, docs }),
    },
    "Ingest"
  );

  if (!res.ok) throw new Error(`Ingest failed: ${await readError(res)}`);
  return res.json();
}

export async function clearNotes(sessionId: string) {
  const res = await safeFetch(
    `${API_BASE}/notes/clear`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId }),
    },
    "Clear"
  );

  if (!res.ok) throw new Error(`Clear failed: ${await readError(res)}`);
  return res.json();
}

export async function healthCheck() {
  const res = await safeFetch(`${API_BASE}/health`, { cache: "no-store" }, "Health check");
  if (!res.ok) throw new Error(`Health check failed: ${await readError(res)}`);
  return res.json();
}