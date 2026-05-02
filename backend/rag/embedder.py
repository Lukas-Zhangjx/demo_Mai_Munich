import os
from functools import lru_cache
from typing import List

import google.generativeai as genai


EMBED_MODEL       = "text-embedding-004"
OUTPUT_DIMENSIONS = 512    # match Supabase vector(512)
BATCH_SIZE        = 100


@lru_cache(maxsize=1)
def _configure():
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    return True


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of document texts in batches.
    Returns 512-dimensional vectors using Gemini text-embedding-004.
    """
    _configure()
    vectors = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        result = genai.embed_content(
            model=f"models/{EMBED_MODEL}",
            content=batch,
            task_type="retrieval_document",
            output_dimensionality=OUTPUT_DIMENSIONS,
        )
        vectors.extend(result["embedding"])

    return vectors


def embed_query(text: str) -> List[float]:
    """Embed a single user query for retrieval."""
    _configure()
    result = genai.embed_content(
        model=f"models/{EMBED_MODEL}",
        content=text,
        task_type="retrieval_query",
        output_dimensionality=OUTPUT_DIMENSIONS,
    )
    return result["embedding"]
