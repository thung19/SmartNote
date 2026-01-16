from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List

from backend.app.services.indexer import index_directory
from backend.app.services.searcher import search
from backend.app.services.summarizer import answer_query
# Create API router instance
router = APIRouter(prefix="/notes", tags=["notes"])

class IndexRequest(BaseModel):
    root_dir: str

class IndexResponse(BaseModel):
    ok: bool
    root_dir: str

@router.post("/index", response_model=IndexResponse)
def index_notes(payload: IndexRequest):
    index_directory(payload.root_dir)
    return {"ok": True, "root_dir": payload.root_dir}


@router.get("/search")
def search_notes(q: str, top_k: int = 5) -> List[Dict[str, Any]]:
    return search(q, top_k=top_k)


@router.post("/ask")
def ask_notes(payload: Dict[str, Any]) -> Dict[str, Any]:
    # expects { "query": "...", "top_k": 5 }
    query = str(payload.get("query", ""))
    top_k = int(payload.get("top_k", 5))
    return answer_query(query, top_k=top_k)


