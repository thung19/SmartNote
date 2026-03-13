"use client";

import { useRef, useState } from "react";
import { nanoid } from "nanoid";

import { useSessionStore } from "@/app/state/sessionStore";
import type { ImportItem } from "@/app/state/sessionStore";

import { ingestNotes, clearNotes } from "@/lib/api";
import { getOrCreateSessionId, clearSessionId } from "@/lib/session";

type FileWithRelativePath = File & {
  webkitRelativePath?: string;
};

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
      displayPath: (file as FileWithRelativePath).webkitRelativePath || file.name,
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
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : "Unknown ingest error";
        dispatch({
          type: "SET_ITEM_STAGE",
          id: it.id,
          stage: "error",
          progress: 100,
          error: message,
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

  async function removeOneFile(item: ImportItem) {
    try {
      if (item.ingested) {
        const sid = getOrCreateSessionId();
        await ingestNotes(sid, [
          {
            path: item.displayPath,
            text: "",
            title: item.file.name,
            mtime: Date.now() / 1000,
          },
        ]);
      }

      dispatch({ type: "REMOVE_ITEM", id: item.id });
      setNotice(`Removed ${item.displayPath}${item.ingested ? " from backend session" : ""}.`);
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "unknown error";
      setNotice(`Could not remove ${item.displayPath}: ${message}`);
    }
  }

  const queuedCount = state.items.length;
  const ingestedCount = state.items.filter((it) => it.ingested).length;

  return (
    <main className="space-y-6">
      <section className="overflow-hidden rounded-[28px] border border-white/70 bg-white/75 shadow-xl shadow-slate-200/70 backdrop-blur">
        <div className="grid gap-6 px-6 py-8 sm:px-8 lg:grid-cols-[1.3fr_0.9fr] lg:items-center">
          <div className="space-y-5">
            <div className="inline-flex items-center gap-2 rounded-full border border-violet-200 bg-violet-50 px-3 py-1 text-xs font-medium text-violet-700">
              In-memory note workspace
            </div>

            <div className="space-y-3">
              <h1 className="text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
                Ingest notes, search them fast, and ask grounded questions.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-600">
                Upload markdown and text files into the current session, then use Search and Ask from the top navigation.
              </p>
            </div>

            <div className="rounded-2xl border border-amber-200 bg-gradient-to-r from-amber-50 to-orange-50 p-4 text-sm text-amber-900">
              <strong>Supported files only:</strong> SmartNote ingests <code>.txt</code> and <code>.md</code> files.
            </div>

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

            <div className="flex flex-wrap items-center gap-4">
              <div className="inline-flex items-center rounded-2xl border border-slate-200 bg-slate-50 p-1 shadow-sm">
                <button
                  type="button"
                  className="rounded-xl px-5 py-3 text-sm font-medium text-slate-700 transition hover:bg-white"
                  onClick={() => fileInputRef.current?.click()}
                >
                  Choose files
                </button>
                <div className="mx-1 h-6 w-px bg-slate-200" />
                <button
                  type="button"
                  className="rounded-xl px-5 py-3 text-sm font-medium text-slate-700 transition hover:bg-white"
                  onClick={() => folderInputRef.current?.click()}
                >
                  Choose folder
                </button>
              </div>

              <p className="text-sm text-slate-500">
                Select <code>.txt</code> or <code>.md</code> files, then ingest them from the queue below.
              </p>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
            <div className="rounded-2xl border border-violet-200 bg-gradient-to-br from-violet-50 to-fuchsia-50 p-5">
              <div className="text-sm font-medium text-violet-900">Queued files</div>
              <div className="mt-2 text-3xl font-semibold text-violet-700">{queuedCount}</div>
            </div>
            <div className="rounded-2xl border border-cyan-200 bg-gradient-to-br from-cyan-50 to-sky-50 p-5">
              <div className="text-sm font-medium text-cyan-900">Ingested</div>
              <div className="mt-2 text-3xl font-semibold text-cyan-700">{ingestedCount}</div>
            </div>
            <div className="rounded-2xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-teal-50 p-5">
              <div className="text-sm font-medium text-emerald-900">Session storage</div>
              <div className="mt-2 text-sm text-emerald-700">RAM-backed and cleared when the session resets.</div>
            </div>
          </div>
        </div>
      </section>

      {notice && <div className="rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{notice}</div>}
      {ingestStatus && <div className="rounded-2xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">{ingestStatus}</div>}

      {/* Drop zone */}
      <section
        className={[
          "rounded-[28px] border-2 border-dashed bg-white/80 p-8 text-center shadow-lg backdrop-blur transition",
          isDragging
            ? "border-violet-500 bg-violet-50 shadow-violet-200/60"
            : "border-violet-200 hover:border-violet-400 hover:bg-violet-50/60",
        ].join(" ")}
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
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-600 via-fuchsia-500 to-cyan-400 text-3xl text-white shadow-lg shadow-violet-300/40">
          ⤴
        </div>
        <h2 className="mt-4 text-xl font-semibold text-slate-900">Drag and drop files here</h2>
        <p className="mt-2 text-sm text-slate-600">
          Drop <strong>.md</strong> or <strong>.txt</strong> files anywhere in this area to queue them for ingestion.
        </p>
        <p className="mt-1 text-xs text-slate-500">Files are queued locally first. Click “Ingest to backend” when ready.</p>
      </section>

      {/* Items */}
      <section className="rounded-[28px] border border-white/70 bg-white/80 p-5 shadow-xl shadow-slate-200/60 backdrop-blur">
        <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Queued files</h2>
            <p className="text-sm text-slate-500">Remove individual files with the <strong>✕</strong> button.</p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              className="rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800"
              onClick={ingestQueued}
            >
              Ingest to backend
            </button>
            <button
              type="button"
              className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              onClick={clearSessionEverywhere}
            >
              Clear session
            </button>
          </div>
        </div>

        {state.items.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-8 text-center text-sm text-slate-500">
            No files queued yet.
          </div>
        ) : (
          <div className="space-y-3">
            {state.items.map((it: ImportItem) => (
              <div
                key={it.id}
                className="rounded-2xl border border-slate-200 bg-gradient-to-r from-white to-slate-50 p-4 shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-slate-900">{it.displayPath}</div>
                    <div className="mt-1 text-xs text-slate-500">
                      {it.stage} ({it.progress}%) {it.ingested ? "• ingested" : ""}
                    </div>
                  </div>

                  <button
                    type="button"
                    aria-label={`Remove ${it.displayPath}`}
                    title="Remove file"
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-rose-200 bg-white text-sm text-rose-600 transition hover:bg-rose-50 hover:border-rose-300"
                    onClick={() => void removeOneFile(it)}
                  >
                    ✕
                  </button>
                </div>

                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={[
                      "h-full rounded-full transition-all",
                      it.stage === "error"
                        ? "bg-rose-500"
                        : it.ingested
                          ? "bg-gradient-to-r from-emerald-500 to-cyan-500"
                          : "bg-gradient-to-r from-violet-500 to-fuchsia-500",
                    ].join(" ")}
                    style={{ width: `${it.progress}%` }}
                  />
                </div>

                {it.error && <div className="mt-2 text-xs text-rose-600">{it.error}</div>}
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}