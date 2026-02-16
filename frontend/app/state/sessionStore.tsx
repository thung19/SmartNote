"use client";

import React from "react";
import { nanoid } from "nanoid";

export type ImportStage = "queued" | "reading" | "parsing" | "chunking" | "ready" | "error";

export type ImportItem = {
  id: string;
  file: File;
  displayPath: string;
  stage: ImportStage;
  progress: number;
  ingested: boolean;   // ✅ add this
  error?: string;
};

export type SessionDocument = {
  id: string;
  displayPath: string;
  mime: string;
  text: string;
};

export type SessionChunk = {
  id: string;
  docId: string;
  index: number;
  text: string;
};

type State = {
  items: ImportItem[];
  docs: SessionDocument[];
  chunks: SessionChunk[];
};

type Action =
  | { type: "ADD_FILES"; files: File[] }
  | { type: "ADD_ITEMS"; items: ImportItem[] } // <-- you already dispatch this
  | { type: "SET_ITEM_STAGE"; id: string; stage: ImportStage; progress: number; error?: string; ingested?: boolean }
  | { type: "ADD_RESULT"; doc: SessionDocument; chunks: SessionChunk[] }
  | { type: "CLEAR_ALL" };

const SessionContext = React.createContext<{
  state: State;
  dispatch: React.Dispatch<Action>;
} | null>(null);

const initialState: State = { items: [], docs: [], chunks: [] };

function displayPath(file: File) {
  return (file as any).webkitRelativePath || file.name;
}

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "ADD_FILES": {
      const newItems: ImportItem[] = action.files.map((file) => ({
        id: nanoid(),
        file,
        displayPath: displayPath(file),
        stage: "queued",
        progress: 0,
        ingested: false,
      }));
      return { ...state, items: [...newItems, ...state.items] };
    }

    // ✅ IMPORTANT: your UI dispatches ADD_ITEMS, so reducer must handle it
    case "ADD_ITEMS": {
      return { ...state, items: [...action.items, ...state.items] };
    }

    case "SET_ITEM_STAGE": {
      return {
        ...state,
        items: state.items.map((it) =>
          it.id === action.id
            ? {
                ...it,
                stage: action.stage,
                progress: action.progress,
                error: action.error,
                ingested: action.ingested ?? it.ingested, // ✅ keep old value unless provided
              }
            : it
        ),
      };
    }

    case "ADD_RESULT": {
      return {
        ...state,
        docs: [action.doc, ...state.docs],
        chunks: [...action.chunks, ...state.chunks],
      };
    }

    case "CLEAR_ALL":
      return initialState;

    default:
      return state;
  }
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = React.useReducer(reducer, initialState);
  return <SessionContext.Provider value={{ state, dispatch }}>{children}</SessionContext.Provider>;
}

export function useSessionStore() {
  const ctx = React.useContext(SessionContext);
  if (!ctx) throw new Error("useSessionStore must be used inside SessionProvider");
  return ctx;
}