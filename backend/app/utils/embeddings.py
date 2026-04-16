from  sentence_transformers import SentenceTransformer, CrossEncoder
from typing import List

_model: SentenceTransformer | None = None
_reranker: CrossEncoder | None = None

# Loads model if not already loaded
def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        _model = SentenceTransformer(model_name)
    return _model

def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _reranker

# Gets embedding for a single block of text
def embed_text(text: str) -> List[float]:
    if not text:
        return []

    # Get the model
    model = get_embedding_model()

    # Convert text to vector
    vector = model.encode(text, show_progress_bar = False, normalize_embeddings = True)
    return vector.tolist()

# Gets embeddings for a batch of texts
def embed_batch(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []

    # Get the model
    model = get_embedding_model()

    # Convert texts to vectors 
    vectors = model.encode(texts, show_progress_bar = False, normalize_embeddings = True)

    return [vec.tolist() for vec in vectors]


def rerank(query: str, texts: List[str]) -> List[float]:
    """
    Score query-text pairs using a cross-encoder.

    Unlike embeddings (which encode query and text independently),
    the cross-encoder sees both together and produces a more accurate
    relevance score. Use this to re-rank an initial candidate set.
    """
    if not texts:
        return []
    model = get_reranker()
    pairs = [[query, t] for t in texts]
    scores = model.predict(pairs, show_progress_bar=False)
    return scores.tolist()