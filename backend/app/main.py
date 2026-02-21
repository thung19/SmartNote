from __future__ import annotations

import os
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routes import notes
from backend.app.store.memory_store import evict_expired
from dotenv import load_dotenv
load_dotenv()

# Creates a FastAPI app object
app = FastAPI(title="SmartNote")

# -----------------------------
# CORS (dev defaults + prod env)
# -----------------------------
_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# Comma-separated list, e.g.:
# SMARTNOTE_CORS_ORIGINS="https://your-frontend.vercel.app,http://localhost:3000"
origins_env = os.getenv("SMARTNOTE_CORS_ORIGINS", "")
allowed_origins = [o.strip() for o in origins_env.split(",") if o.strip()] or _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Session eviction (TTL cleanup)
# -----------------------------
SESSION_TTL_SECONDS = int(os.getenv("SMARTNOTE_SESSION_TTL_SECONDS", "3600"))  # 1 hour
EVICT_EVERY_SECONDS = int(os.getenv("SMARTNOTE_EVICT_EVERY_SECONDS", "30"))   # run at most every 30s
_last_evict = 0.0


@app.middleware("http")
async def session_eviction_middleware(request: Request, call_next):
    global _last_evict
    now = time.time()
    if now - _last_evict > EVICT_EVERY_SECONDS:
        evict_expired(SESSION_TTL_SECONDS)
        _last_evict = now
    return await call_next(request)

# -----------------------------
# Health check endpoint
# -----------------------------
@app.get("/health")
def health():
    return {"ok": True}

# -----------------------------
# Routes
# -----------------------------
app.include_router(notes.router)