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

    setIngestStatus("Ingest complete.");
  }

  async function clearSessionEverywhere() {
    const sid = getOrCreateSessionId();

    dispatch({ type: "CLEAR_ALL" });
    setNotice("");
    setIngestStatus("");

    try {
      await clearNotes(sid);
    } catch {
      // ignore if backend down
    }

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
    <main className="space-y-5">
      {/* Hero panel */}
      <section className="overflow-hidden rounded-xl border border-white/60 bg-white/80 shadow-lg shadow-slate-200/60 backdrop-blur">
        <div className="grid gap-6 px-6 py-8 sm:px-8 lg:grid-cols-[1.3fr_0.9fr] lg:items-center">
          <div className="space-y-5">
            <div className="inline-flex items-center gap-1.5 rounded border border-violet-200 bg-violet-50 px-2.5 py-1 text-xs font-semibold tracking-wide text-violet-700 uppercase">
              In-memory workspace
            </div>

            <div className="space-y-3">
              <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
                Ingest notes, search them fast, ask grounded questions.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-slate-500">
                Upload markdown and text files into the current session, then use Search and Ask from the top navigation.
              </p>
            </div>

            <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
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

            <div className="flex flex-wrap items-center gap-3">
              <div className="inline-flex items-center divide-x divide-slate-200 rounded-md border border-slate-200 bg-white shadow-sm">
                <button
                  type="button"
                  className="px-5 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                  onClick={() => fileInputRef.current?.click()}
                >
                  Choose files
                </button>
                <button
                  type="button"
                  className="px-5 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                  onClick={() => folderInputRef.current?.click()}
                >
                  Choose folder
                </button>
              </div>
              <p className="text-sm text-slate-400">
                Or drop files in the zone below.
              </p>
            </div>
          </div>

          {/* Stats */}
          <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
            <div className="rounded-lg border border-violet-100 bg-violet-50/60 p-5">
              <div className="text-xs font-semibold uppercase tracking-wide text-violet-600">Queued</div>
              <div className="mt-2 text-3xl font-bold text-violet-700">{queuedCount}</div>
            </div>
            <div className="rounded-lg border border-cyan-100 bg-cyan-50/60 p-5">
              <div className="text-xs font-semibold uppercase tracking-wide text-cyan-600">Ingested</div>
              <div className="mt-2 text-3xl font-bold text-cyan-700">{ingestedCount}</div>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-5">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Storage</div>
              <div className="mt-2 text-sm text-slate-500 leading-snug">RAM-backed, cleared on session reset.</div>
            </div>
          </div>
        </div>
      </section>

      {notice && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">{notice}</div>
      )}
      {ingestStatus && (
        <div className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-700">{ingestStatus}</div>
      )}

      {/* Drop zone */}
      <section
        className={[
          "rounded-xl border-2 border-dashed bg-white/70 p-10 text-center backdrop-blur transition-colors",
          isDragging
            ? "border-violet-400 bg-violet-50/80"
            : "border-slate-200 hover:border-violet-300 hover:bg-violet-50/40",
        ].join(" ")}
        onDragEnter={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }}
        onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(true); }}
        onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); setIsDragging(false); }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setIsDragging(false);
          const files = Array.from(e.dataTransfer.files ?? []);
          queueFiles(files);
        }}
      >
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-lg bg-linear-to-br from-violet-600 via-fuchsia-500 to-cyan-400 text-2xl text-white shadow-md shadow-violet-300/30">
          ⤴
        </div>
        <h2 className="mt-4 text-lg font-semibold text-slate-800">Drag and drop files here</h2>
        <p className="mt-1.5 text-sm text-slate-500">
          Drop <strong>.md</strong> or <strong>.txt</strong> files to queue them for ingestion.
        </p>
        <p className="mt-1 text-xs text-slate-400">Files are queued locally first — click "Ingest to backend" when ready.</p>
      </section>

      {/* File queue */}
      <section className="rounded-xl border border-white/60 bg-white/80 p-5 shadow-lg shadow-slate-200/50 backdrop-blur">
        <div className="mb-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Queued files</h2>
            <p className="text-sm text-slate-400">Remove individual files with the ✕ button.</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-700"
              onClick={ingestQueued}
            >
              Ingest to backend
            </button>
            <button
              type="button"
              className="rounded-md border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-50"
              onClick={clearSessionEverywhere}
            >
              Clear session
            </button>
          </div>
        </div>

        {state.items.length === 0 ? (
          <div className="rounded-lg border border-slate-100 bg-slate-50 px-4 py-8 text-center text-sm text-slate-400">
            No files queued yet.
          </div>
        ) : (
          <div className="space-y-2">
            {state.items.map((it: ImportItem) => (
              <div
                key={it.id}
                className="rounded-lg border border-slate-100 bg-white p-4"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium text-slate-900">{it.displayPath}</div>
                    <div className="mt-0.5 text-xs text-slate-400">
                      {it.stage} · {it.progress}%{it.ingested ? " · ingested" : ""}
                    </div>
                  </div>

                  <button
                    type="button"
                    aria-label={`Remove ${it.displayPath}`}
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded border border-rose-200 bg-white text-xs text-rose-500 transition hover:bg-rose-50"
                    onClick={() => void removeOneFile(it)}
                  >
                    ✕
                  </button>
                </div>

                <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={[
                      "h-full rounded-full transition-all",
                      it.stage === "error"
                        ? "bg-rose-500"
                        : it.ingested
                          ? "bg-linear-to-r from-emerald-500 to-cyan-500"
                          : "bg-linear-to-r from-violet-500 to-fuchsia-500",
                    ].join(" ")}
                    style={{ width: `${it.progress}%` }}
                  />
                </div>

                {it.error && <div className="mt-2 text-xs text-rose-500">{it.error}</div>}
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
