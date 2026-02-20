from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from backend.app.services.searcher import search
from backend.app.services.summarizer import answer_query
from backend.app.services.ingester import ingest_docs
from backend.app.store.memory_store import clear_session, touch_session

router = APIRouter(prefix="/notes", tags=["notes"])


class DocIn(BaseModel):
    path: str
    text: str
    title: Optional[str] = None
    mtime: Optional[float] = None


class IngestRequest(BaseModel):
    session_id: str
    docs: List[DocIn]


class IngestResponse(BaseModel):
    ok: bool
    ingested: int
    skipped_empty: int
    rejected: int


class AskRequest(BaseModel):
    session_id: str
    query: str
    top_k: int = 5


class ClearRequest(BaseModel):
    session_id: str


@router.get("/search")
def search_notes(session_id: str, q: str, top_k: int = 5) -> List[Dict[str, Any]]:
    touch_session(session_id)
    return search(session_id, q, top_k=top_k)


@router.post("/ask")
def ask_notes(payload: AskRequest) -> Dict[str, Any]:
    touch_session(payload.session_id)
    return answer_query(payload.session_id, payload.query, top_k=payload.top_k)


@router.post("/ingest", response_model=IngestResponse)
def ingest_notes(payload: IngestRequest):
    touch_session(payload.session_id)
    stats = ingest_docs(payload.session_id, [d.model_dump() for d in payload.docs])
    return {"ok": True, **stats}


@router.post("/clear")
def clear_notes(payload: ClearRequest):
    clear_session(payload.session_id)
    return {"ok": True}