import os
from functools import lru_cache
from typing import List

from google import genai
from google.genai import types


EMBED_MODEL       = "text-embedding-004"
OUTPUT_DIMENSIONS = 512    # matches Supabase vector(512)
BATCH_SIZE        = 100


@lru_cache(maxsize=1)
def _client():
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of document texts in batches.
    Returns 512-dimensional vectors using Gemini text-embedding-004.
    """
    vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        response = _client().models.embed_content(
            model=EMBED_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=OUTPUT_DIMENSIONS,
            ),
        )
        vectors.extend([e.values for e in response.embeddings])
    return vectors


def embed_query(text: str) -> List[float]:
    """Embed a single user query for retrieval."""
    response = _client().models.embed_content(
        model=EMBED_MODEL,
        contents=text,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=OUTPUT_DIMENSIONS,
        ),
    )
    return response.embeddings[0].values
