"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { nanoid } from "nanoid";

import { useSessionStore } from "@/app/state/sessionStore";
import type { ImportItem } from "@/app/state/sessionStore";

import { ingestNotes, clearNotes } from "@/lib/api";
import { getOrCreateSessionId, clearSessionId } from "@/lib/session";

export default function Home() {
  const { state, dispatch } = useSessionStore();

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const folderInputRef = useRef<HTMLInputElement | null>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [notice, setNotice] = useState<string>("");
  const [ingestStatus, setIngestStatus] = useState<string>("");

  function filterSupported(files: File[]) {
    const supported = files.filter((f) => {
      const name = f.name.toLowerCase();
      return name.endsWith(".md") || name.endsWith(".txt");
    });

    const ignored = files.length - supported.length;
    if (ignored > 0) setNotice(`Ignored ${ignored} unsupported file(s). Only .md and .txt are accepted.`);
    else setNotice("");

    return supported;
  }

  function queueFiles(files: File[]) {
    const supported = filterSupported(files);
    if (supported.length === 0) return;

    const items: ImportItem[] = supported.map((file) => ({
      id: nanoid(),
      file,
      displayPath: (file as any).webkitRelativePath || file.name,
      stage: "queued",
      progress: 0,
      ingested: false,
    }));

    dispatch({ type: "ADD_ITEMS", items });
  }

  async function ingestQueued() {
    const sid = getOrCreateSessionId();

    const queued = state.items.filter((it) => !it.ingested && it.stage !== "error");
    if (queued.length === 0) {
      setIngestStatus("Nothing to ingest (everything is already ingested).");
      return;
    }

    setIngestStatus(`Ingesting ${queued.length} file(s) to backend memory...`);

    for (const it of queued) {
      try {
        dispatch({ type: "SET_ITEM_STAGE", id: it.id, stage: "reading", progress: 25 });

        const text = await it.file.text();

        dispatch({ type: "SET_ITEM_STAGE", id: it.id, stage: "parsing", progress: 50 });

        await ingestNotes(sid, [
          {
            path: it.displayPath,
            text,
            title: it.file.name,
            mtime: Date.now() / 1000,
          },
        ]);

        // ✅ mark ingested true
        dispatch({ type: "SET_ITEM_STAGE", id: it.id, stage: "ready", progress: 100, ingested: true });
      } catch (e: any) {
        dispatch({
          type: "SET_ITEM_STAGE",
          id: it.id,
          stage: "error",
          progress: 100,
          error: e?.message ?? "Unknown ingest error",
        });
      }
    }

    setIngestStatus("✅ Ingest complete.");
  }

  async function clearSessionEverywhere() {
    const sid = getOrCreateSessionId();

    // Clear frontend state
    dispatch({ type: "CLEAR_ALL" });
    setNotice("");
    setIngestStatus("");

    // Clear backend session (best-effort)
    try {
      await clearNotes(sid);
    } catch {
      // ignore if backend down
    }

    // Clear client session id so next run gets a new backend store
    clearSessionId();
  }

  const queuedCount = state.items.length;
  const ingestedCount = state.items.filter((it) => it.ingested).length;

  return (
    <main className="max-w-3xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">SmartNote</h1>
        <button className="px-3 py-2 rounded border text-sm hover:bg-gray-50" onClick={clearSessionEverywhere}>
          Clear session
        </button>
      </div>

      <p className="text-sm text-gray-600">
        Step 1: select notes (queued locally). Step 2: click “Ingest to backend” to chunk + embed + store in RAM (session-scoped).
      </p>

      {/* Hidden inputs */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          queueFiles(files);
          e.currentTarget.value = "";
        }}
      />

      <input
        ref={folderInputRef}
        type="file"
        multiple
        className="hidden"
        // @ts-expect-error - folder picker on Chromium browsers
        webkitdirectory="true"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          queueFiles(files);
          e.currentTarget.value = "";
        }}
      />

      <div className="flex flex-wrap gap-3 items-center">
        <button className="px-4 py-2 rounded border text-sm hover:bg-gray-50" onClick={() => fileInputRef.current?.click()}>
          Choose files
        </button>

        <button className="px-4 py-2 rounded border text-sm hover:bg-gray-50" onClick={() => folderInputRef.current?.click()}>
          Choose folder
        </button>

        <button className="px-4 py-2 rounded bg-black text-white text-sm hover:opacity-90" onClick={ingestQueued}>
          Ingest to backend
        </button>

        <div className="text-xs text-gray-600">
          Queued: {queuedCount} • Ingested: {ingestedCount}
        </div>
      </div>

      {notice && <div className="text-xs text-amber-700 border border-amber-200 bg-amber-50 rounded p-2">{notice}</div>}
      {ingestStatus && <div className="text-xs text-gray-700 border rounded p-2">{ingestStatus}</div>}

      {/* Drop zone */}
      <div
        className={["rounded border p-6 text-sm", isDragging ? "bg-gray-50 border-gray-400" : "border-gray-200"].join(" ")}
        onDragEnter={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsDragging(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsDragging(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsDragging(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsDragging(false);
          const files = Array.from(e.dataTransfer.files ?? []);
          queueFiles(files);
        }}
      >
        <div className="font-medium">Drag & drop files here</div>
        <div className="text-xs text-gray-600 mt-1">(.md and .txt only — queued locally until you ingest)</div>
      </div>

      {/* Items */}
      <div className="space-y-2">
        {state.items.map((it: ImportItem) => (
          <div key={it.id} className="border rounded p-3 text-sm">
            <div className="font-medium">{it.displayPath}</div>

            <div className="mt-1 flex items-center justify-between gap-3">
              <div className="text-xs text-gray-600">
                {it.stage} ({it.progress}%) {it.ingested ? "• ingested" : ""}
              </div>

              <div className="w-40 h-2 bg-gray-100 rounded overflow-hidden">
                <div className="h-full bg-gray-800" style={{ width: `${it.progress}%` }} />
              </div>
            </div>

            {it.error && <div className="mt-2 text-xs text-red-600">{it.error}</div>}
          </div>
        ))}
      </div>

      <div className="pt-2 flex gap-4 underline text-sm">
        <Link href="/search">Search</Link>
        <Link href="/ask">Ask</Link>
      </div>
    </main>
  );
}