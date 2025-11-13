from  sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None

def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        _model = SentenceTransformer(model_name)
    return _model

def embed_text(text: str) -> List[float]:
    if not text:
        return []

    model = get_embedding_model()

    vector = model.encode(text, show_progress_bar = False, normalize_embeddings = True)

def embed_batch(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []

    model = get_embedding_model()

    vectors = model.encode(texts, show_progress_bar = False, normalize_embeddings = True)

    return [vec.tolist() for vec in vectors]