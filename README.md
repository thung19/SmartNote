# SmartNote

A session-based RAG (Retrieval-Augmented Generation) app for searching and querying your notes using semantic search and an LLM. Upload your `.md` and `.txt` files in the browser, search by meaning, and ask natural language questions — all answered strictly from your own notes.

**Live app:** [smartnote-two.vercel.app](https://smartnote-two.vercel.app/)

> Frontend hosted on Vercel. Backend hosted on Google Cloud Run.

---

## How it works

1. **Ingest** — drag and drop or select `.md`/`.txt` files in the browser. The frontend reads them and sends the text to the backend, which chunks and embeds them into an in-memory session store.
2. **Search** — find relevant notes by semantic similarity (vector search), not just keywords.
3. **Ask** — ask a natural language question. The backend retrieves the most relevant chunks and passes them to an LLM, which answers using only your notes as context.

Sessions are scoped per browser session and automatically expire after 1 hour of inactivity. Nothing is written to disk.

---

## Tech stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python) |
| Storage | In-memory per-session store (RAM) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| LLM | OpenAI API (`gpt-4o-mini` by default) |
| Frontend hosting | Vercel |
| Backend hosting | Google Cloud Run |

---

## Usage

1. Open [smartnote-two.vercel.app](https://smartnote-two.vercel.app/) (or your local instance).
2. Drag and drop `.md` or `.txt` files onto the home page, or use the file/folder picker.
3. Click **Ingest to backend** to embed and store them in your session.
4. Navigate to **Search** to find notes by semantic similarity.
5. Navigate to **Ask** to ask a question — the LLM answers using only your ingested notes, with source citations.
6. Click **Clear session** to wipe all notes from the current session.

> **Note:** Only `.md` and `.txt` files are supported. Other file types are ignored.

---

## Running locally (optional)

### Prerequisites

- Python 3.11+
- Node.js 18+
- An [OpenAI API key](https://platform.openai.com/api-keys)

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file:

```env
OPENAI_API_KEY=sk-...
```

Start the server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Point the frontend at your local backend:

```env
# frontend/.env.local
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

The app runs at `http://localhost:3000`.

---

## Deployment

### Frontend → Vercel

Deploy directly from GitHub. Set the following in your Vercel project settings:

```
NEXT_PUBLIC_API_BASE=https://your-backend-url.run.app
```

### Backend → Google Cloud Run

The `Dockerfile` in `backend/` is configured for Cloud Run (listens on port `8080`).

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT/smartnote-backend ./backend

gcloud run deploy smartnote-backend \
  --image gcr.io/YOUR_PROJECT/smartnote-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars OPENAI_API_KEY=sk-...,SMARTNOTE_CORS_ORIGINS=https://your-app.vercel.app
```

### CORS configuration

Set these on your Cloud Run service to allow your Vercel frontend:

| Variable | Example | Description |
|----------|---------|-------------|
| `SMARTNOTE_CORS_ORIGINS` | `https://your-app.vercel.app,http://localhost:3000` | Comma-separated allowed origins |
| `SMARTNOTE_CORS_ORIGIN_REGEX` | `https://smartnote-.*\.vercel\.app` | Regex to allow Vercel preview deployments |

---

## Environment variables

### Backend

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | **Required.** OpenAI API key |
| `SMARTNOTE_OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model to use |
| `SMARTNOTE_MAX_OUTPUT_TOKENS` | `300` | Max tokens per LLM response |
| `SMARTNOTE_MAX_ASKS_PER_SESSION_PER_DAY` | `30` | Daily ask quota per session |
| `SMARTNOTE_LLM_ENABLED` | `true` | Set to `false` to disable LLM responses |
| `SMARTNOTE_CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins |
| `SMARTNOTE_CORS_ORIGIN_REGEX` | — | Regex for dynamic CORS origins (e.g. Vercel previews) |
| `SMARTNOTE_SESSION_TTL_SECONDS` | `3600` | Idle session TTL before eviction |
| `SMARTNOTE_EVICT_EVERY_SECONDS` | `30` | How often to check for expired sessions |

### Frontend

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000` | URL of the backend API |

---

## API reference

All session-scoped endpoints require a `session_id` (generated client-side).

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/notes/ingest` | Ingest documents into a session |
| `GET` | `/notes/search` | Semantic search (`?session_id=&q=&top_k=5`) |
| `POST` | `/notes/ask` | Ask a question against ingested notes |
| `POST` | `/notes/clear` | Clear all notes for a session |

**Ingest**
```json
POST /notes/ingest
{
  "session_id": "abc123",
  "docs": [
    { "path": "notes/journal.md", "text": "...", "title": "journal.md", "mtime": 1711234567 }
  ]
}
```

**Search**
```
GET /notes/search?session_id=abc123&q=project+ideas&top_k=5
```

**Ask**
```json
POST /notes/ask
{
  "session_id": "abc123",
  "query": "What did I say about the API design?",
  "top_k": 5
}
```

---

## Project structure

```
SmartNote/
├── backend/
│   ├── Dockerfile                    # Cloud Run container
│   └── app/
│       ├── main.py                   # FastAPI entry point + CORS config
│       ├── routes/notes.py           # API endpoints
│       ├── services/
│       │   ├── ingester.py           # Chunking + embedding pipeline
│       │   ├── searcher.py           # Cosine similarity search
│       │   ├── summarizer.py         # LLM prompt construction + Q&A
│       │   └── llm_client.py         # OpenAI client + quota tracking
│       ├── store/
│       │   └── memory_store.py       # Per-session in-memory vector store
│       └── utils/
│           ├── chunker.py            # Text chunking logic
│           ├── embeddings.py         # Sentence transformer wrapper
│           └── file_loader.py        # File discovery utilities
├── frontend/
│   └── app/
│       ├── page.tsx                  # Home / ingest UI
│       ├── search/page.tsx           # Search UI
│       ├── ask/page.tsx              # Q&A UI
│       └── state/sessionStore.ts     # Client-side session state
└── tests/
    ├── unit/
    └── integration/
```

## Limitations

- **In-memory only** — all ingested notes live in RAM and are lost when the server restarts or the session expires (TTL: 1 hour by default).
- **Single instance quota** — the per-session ask quota is tracked in-process. Scaling to multiple Cloud Run replicas will not share quota across instances.
- **File support** — only `.md` and `.txt` files are accepted.
- **Ask quota** — each session is limited to 30 LLM asks per day (configurable via `SMARTNOTE_MAX_ASKS_PER_SESSION_PER_DAY`).
