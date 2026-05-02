from typing import List
from db.client import get_client
from rag.embedder import embed_query


TOP_K           = 5     # number of chunks to retrieve
SIMILARITY_THRESHOLD = 0.3


def retrieve(question: str) -> List[dict]:
    """
    Embed the question and return the top-K most similar document chunks.
    Each result has: content, filename, similarity.
    """
    query_vector = embed_query(question)

    response = get_client().rpc(
        "match_documents",
        {
            "query_embedding": query_vector,
            "match_threshold": SIMILARITY_THRESHOLD,
            "match_count":     TOP_K,
        },
    ).execute()

    return response.data or []


def build_context(chunks: List[dict]) -> str:
    """Format retrieved chunks into a context string for the prompt."""
    if not chunks:
        return ""

    parts = []
    for i, chunk in enumerate(chunks, 1):
        filename = chunk.get("metadata", {}).get("filename", "unknown")
        parts.append(f"[Source {i} – {filename}]\n{chunk['content']}")

    return "\n\n---\n\n".join(parts)
