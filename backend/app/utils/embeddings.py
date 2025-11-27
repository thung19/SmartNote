from  sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None

# Loads model if not already loaded
def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        _model = SentenceTransformer(model_name)
    return _model

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