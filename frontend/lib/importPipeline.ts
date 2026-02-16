// app/lib/importPipeline.ts
// High-level ingestion pipeline utilities (framework-agnostic).

import { chunkText, type Chunk } from "./chunk";
import { nanoid } from "nanoid";

/**
 * Supported input types for ingestion.
 * You can expand this later (pdf, md, html, etc).
 */
export type ImportSource =
  | {
      kind: "text";
      text: string;
      name?: string;
    }
  | {
      kind: "file";
      file: File;
    };

/**
 * Metadata attached to every chunk.
 */
export type ChunkMetadata = {
  documentId: string;
  chunkId: string;
  sourceName: string;
  chunkIndex: number;
  startChar: number;
  endChar: number;
};

/**
 * Final object returned by the import pipeline.
 * This is what downstream embedding/indexing layers consume.
 */
export type ImportedChunk = {
  text: string;
  metadata: ChunkMetadata;
  preview: string;
};

/**
 * Extract raw text from a File.
 * (Right now: text-like files only. Expand later.)
 */
async function extractTextFromFile(file: File): Promise<string> {
  // Browser-safe extraction
  const text = await file.text();
  return text;
}

/**
 * Main entry point:
 * Ingest ONE source (file or raw text) and return structured chunks.
 */
export async function importOneFile(
  source: ImportSource,
  options?: {
    maxChars?: number;
    overlapChars?: number;
  }
): Promise<ImportedChunk[]> {
  const documentId = nanoid();

  let rawText = "";
  let sourceName = "untitled";

  // --- Step 1: Extract text ---
  if (source.kind === "text") {
    rawText = source.text;
    sourceName = source.name ?? "text-input";
  } else {
    rawText = await extractTextFromFile(source.file);
    sourceName = source.file.name;
  }

  if (!rawText || !rawText.trim()) {
    return [];
  }

  // --- Step 2: Chunk text ---
  const chunks: Chunk[] = chunkText(rawText, {
    maxChars: options?.maxChars ?? 1400,
    overlapChars: options?.overlapChars ?? 200,
  });

  // --- Step 3: Attach metadata ---
  const imported: ImportedChunk[] = chunks.map((chunk) => {
    const chunkId = nanoid();

    return {
      text: chunk.text,
      preview: chunk.preview,
      metadata: {
        documentId,
        chunkId,
        sourceName,
        chunkIndex: chunk.index,
        startChar: chunk.startChar,
        endChar: chunk.endChar,
      },
    };
  });

  return imported;
}