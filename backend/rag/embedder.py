import os
import requests
from typing import List


EMBED_MODEL       = "gemini-embedding-001"
OUTPUT_DIMENSIONS = 768    # compressed from 3072 native dims
BATCH_SIZE        = 100
API_BASE          = "https://generativelanguage.googleapis.com/v1beta/models"


def _api_key() -> str:
    return os.environ["GEMINI_API_KEY"]


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of document texts via Gemini embedContent (one call per text).
    Returns 512-dimensional vectors.
    """
    return [_embed_single(t, task_type="RETRIEVAL_DOCUMENT") for t in texts]


def embed_query(text: str) -> List[float]:
    """Embed a single user query for retrieval."""
    return _embed_single(text, task_type="RETRIEVAL_QUERY")


def _embed_single(text: str, task_type: str) -> List[float]:
    """Call Gemini embedContent for one text."""
    payload = {
        "content":             {"parts": [{"text": text}]},
        "taskType":            task_type,
        "outputDimensionality": OUTPUT_DIMENSIONS,
    }
    url = f"{API_BASE}/{EMBED_MODEL}:embedContent?key={_api_key()}"
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()["embedding"]["values"]
