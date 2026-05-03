import os
import requests
from typing import List


EMBED_MODEL       = "text-embedding-004"
OUTPUT_DIMENSIONS = 512    # matches Supabase vector(512)
BATCH_SIZE        = 100
API_BASE          = "https://generativelanguage.googleapis.com/v1beta/models"


def _api_key() -> str:
    return os.environ["GEMINI_API_KEY"]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of document texts via Gemini REST API (batchEmbedContents).
    Returns 512-dimensional vectors.
    """
    vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        payload = {
            "requests": [
                {
                    "model":   f"models/{EMBED_MODEL}",
                    "content": {"parts": [{"text": t}]},
                    "outputDimensionality": OUTPUT_DIMENSIONS,
                }
                for t in batch
            ]
        }
        url = f"{API_BASE}/{EMBED_MODEL}:batchEmbedContents?key={_api_key()}"
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        vectors.extend([e["values"] for e in resp.json()["embeddings"]])
    return vectors


def embed_query(text: str) -> List[float]:
    """Embed a single user query via Gemini REST API (embedContent)."""
    payload = {
        "content":             {"parts": [{"text": text}]},
        "outputDimensionality": OUTPUT_DIMENSIONS,
        "taskType":            "RETRIEVAL_QUERY",
    }
    url = f"{API_BASE}/{EMBED_MODEL}:embedContent?key={_api_key()}"
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["embedding"]["values"]
