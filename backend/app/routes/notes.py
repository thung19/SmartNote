from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

# from backend.app.services.indexer import index_directory
from backend.app.services.searcher import search
from backend.app.services.summarizer import answer_query
from backend.app.services.ingester import ingest_docs
from backend.app.store.memory_store import STORE

# Create API router instance
router = APIRouter(prefix="/notes", tags=["notes"])

#class IndexRequest(BaseModel):
#    root_dir: str

#class IndexResponse(BaseModel):
#    ok: bool
#    root_dir: str


#@router.post("/index", response_model=IndexResponse)
# def index_notes(payload: IndexRequest):
#    index_directory(payload.root_dir)
#    return {"ok": True, "root_dir": payload.root_dir}


@router.get("/search")
def search_notes(q: str, top_k: int = 5) -> List[Dict[str, Any]]:
    return search(q, top_k=top_k)


@router.post("/ask")
def ask_notes(payload: Dict[str, Any]) -> Dict[str, Any]:
    # expects { "query": "...", "top_k": 5 }
    query = str(payload.get("query", ""))
    top_k = int(payload.get("top_k", 5))
    return answer_query(query, top_k=top_k)

class DocIn(BaseModel):
    path: str
    text: str
    title: Optional[str] = None
    mtime: Optional[float] = None


class IngestRequest(BaseModel):
    docs: List[DocIn]


class IngestResponse(BaseModel):
    ok: bool
    ingested: int
    skipped_empty: int


@router.post("/ingest", response_model=IngestResponse)
def ingest_notes(payload: IngestRequest):
    stats = ingest_docs([d.model_dump() for d in payload.docs])
    return {"ok": True, **stats}

@router.post("/clear")
def clear_notes():
    STORE.clear()
    return {"ok": True, "stats": STORE.stats()}


