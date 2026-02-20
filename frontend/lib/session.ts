"use client";

import { nanoid } from "nanoid";

const KEY = "smartnote_session_id";

export function getOrCreateSessionId(): string {
  if (typeof window === "undefined") return "server";

  const existing = window.localStorage.getItem(KEY);
  if (existing && existing.trim()) return existing;

  const sid = nanoid();
  window.localStorage.setItem(KEY, sid);
  return sid;
}

export function clearSessionId(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(KEY);
}