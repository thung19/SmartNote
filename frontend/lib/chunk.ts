// app/lib/chunk.ts
// Pure chunking utilities (no React, no browser-only APIs).

export type Chunk = {
  /** 0-based chunk index in this document */
  index: number;
  /** chunk text */
  text: string;
  /** character offsets in the ORIGINAL normalized text (best-effort) */
  startChar: number;
  endChar: number;
  /** short preview for UI/debug */
  preview: string;
};

export type ChunkOptions = {
  /**
   * Soft cap on chunk size in characters.
   * (Embeddings often work well with ~1k–2k chars depending on model.)
   */
  maxChars?: number;

  /**
   * Desired overlap between consecutive chunks in characters.
   * Helps preserve context across chunk boundaries.
   */
  overlapChars?: number;

  /**
   * If true, we try to split on paragraphs first, then sentences, then hard-split.
   */
  preferNaturalBreaks?: boolean;

  /**
   * If you want to ensure no chunk is tiny (except maybe last one).
   * If a chunk would be smaller, we may merge with the next.
   */
  minChars?: number;
};

const DEFAULTS: Required<ChunkOptions> = {
  maxChars: 1400,
  overlapChars: 200,
  preferNaturalBreaks: true,
  minChars: 200,
};

/**
 * Normalize input text:
 * - unify line endings
 * - collapse excessive whitespace (but keep paragraph breaks)
 */
export function normalizeText(raw: string): string {
  const s = (raw ?? "").replace(/\r\n/g, "\n").replace(/\r/g, "\n");

  // Preserve paragraph boundaries: treat 2+ newlines as paragraph separators.
  // Inside paragraphs, collapse runs of whitespace to single spaces.
  const paragraphs = s
    .split(/\n{2,}/g)
    .map(p => p.replace(/[ \t]+/g, " ").replace(/\n+/g, " ").trim())
    .filter(Boolean);

  return paragraphs.join("\n\n").trim();
}

/**
 * Split normalized text into paragraphs.
 */
export function splitParagraphs(text: string): string[] {
  const t = (text ?? "").trim();
  if (!t) return [];
  return t.split(/\n{2,}/g).map(p => p.trim()).filter(Boolean);
}

/**
 * Very simple sentence splitter (heuristic).
 * We avoid heavy deps; this is "good enough" for notes.
 */
export function splitSentences(paragraph: string): string[] {
  const p = (paragraph ?? "").trim();
  if (!p) return [];

  // Split on sentence-ending punctuation followed by whitespace.
  // Keeps punctuation in the sentence.
  const parts = p.split(/(?<=[.!?])\s+/g).map(s => s.trim()).filter(Boolean);
  return parts.length ? parts : [p];
}

/**
 * Chunk text into overlapping chunks.
 * Strategy:
 * 1) Normalize
 * 2) Build "units" (paragraphs or sentences) to respect natural breaks
 * 3) Pack units into chunks up to maxChars
 * 4) Add overlap by carrying tail characters into next chunk
 */
export function chunkText(rawText: string, options: ChunkOptions = {}): Chunk[] {
  const opt = { ...DEFAULTS, ...options };

  if (opt.overlapChars >= opt.maxChars) {
    // Avoid infinite overlap
    opt.overlapChars = Math.floor(opt.maxChars / 4);
  }

  const normalized = normalizeText(rawText);
  if (!normalized) return [];

  // Build units
  const units: string[] = [];
  if (opt.preferNaturalBreaks) {
    for (const para of splitParagraphs(normalized)) {
      const sentences = splitSentences(para);
      // If the paragraph is already short-ish, keep as paragraph unit
      if (para.length <= opt.maxChars && sentences.length <= 2) {
        units.push(para);
      } else {
        units.push(...sentences);
      }
    }
  } else {
    units.push(normalized);
  }

  // Pack units
  const chunks: Chunk[] = [];
  let cursor = 0; // best-effort char offset in normalized text
  let current = "";
  let currentStart = 0;

  const flush = () => {
    const text = current.trim();
    if (!text) return;

    const startChar = currentStart;
    const endChar = currentStart + text.length;

    chunks.push({
      index: chunks.length,
      text,
      startChar,
      endChar,
      preview: text.slice(0, 140),
    });
  };

  for (const unit of units) {
    const u = unit.trim();
    if (!u) continue;

    // If adding this unit would overflow, flush current chunk.
    if (current && (current.length + 2 + u.length > opt.maxChars)) {
      flush();

      // Compute overlap tail
      const prevText = current.trim();
      const tail = prevText.slice(Math.max(0, prevText.length - opt.overlapChars));

      // Start new chunk with overlap tail
      current = tail ? tail + "\n\n" + u : u;

      // Best-effort: set startChar to cursor - tail.length (approx)
      currentStart = Math.max(0, cursor - tail.length);
    } else {
      // Append unit
      if (!current) {
        currentStart = cursor;
        current = u;
      } else {
        current += "\n\n" + u;
      }
    }

    // Advance cursor best-effort:
    // Find this unit in the remaining normalized text to keep offsets closer to reality.
    // If not found, just approximate by adding lengths.
    const remainder = normalized.slice(cursor);
    const idx = remainder.indexOf(u);
    if (idx >= 0) {
      cursor += idx + u.length;
    } else {
      cursor += u.length + 2;
    }
  }

  flush();

  // Merge tiny chunks (except if it's the only one)
  if (chunks.length > 1 && opt.minChars > 0) {
    const merged: Chunk[] = [];
    for (let i = 0; i < chunks.length; i++) {
      const c = chunks[i];
      const last = merged[merged.length - 1];

      if (last && c.text.length < opt.minChars) {
        // merge into previous
        const joined = (last.text + "\n\n" + c.text).trim();
        last.text = joined;
        last.endChar = last.startChar + joined.length;
        last.preview = joined.slice(0, 140);
      } else {
        merged.push({ ...c, index: merged.length });
      }
    }
    return merged.map((c, i) => ({ ...c, index: i }));
  }

  return chunks;
}