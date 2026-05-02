import voyageai
from functools import lru_cache
from typing import List


EMBED_MODEL = "voyage-3-lite"   # 512-dim, fast and cheap
BATCH_SIZE  = 128


@lru_cache(maxsize=1)
def _client():
    return voyageai.Client()   # reads VOYAGE_API_KEY from env


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of texts in batches.
    Returns a list of 512-dimensional vectors.
    """
    vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch  = texts[i : i + BATCH_SIZE]
        result = _client().embed(batch, model=EMBED_MODEL, input_type="document")
        vectors.extend(result.embeddings)
    return vectors


def embed_query(text: str) -> List[float]:
    """Embed a single user query for retrieval."""
    result = _client().embed([text], model=EMBED_MODEL, input_type="query")
    return result.embeddings[0]
