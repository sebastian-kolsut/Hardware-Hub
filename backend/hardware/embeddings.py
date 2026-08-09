"""Thin wrapper around the Gemini embedding API.

Item embeddings are computed once and stored on Hardware.embedding (see
Hardware.save()) rather than recomputed per search — a search only ever
costs one API call, to embed the query text, then compares that vector
against whatever's already stored.
"""
import math

from django.conf import settings
from google import genai

EMBEDDING_MODEL = 'gemini-embedding-001'


class EmbeddingError(Exception):
    """Raised when the Gemini API call for an embedding fails for any
    reason (network, quota, missing/bad key, ...). Callers decide how to
    degrade — e.g. leave Hardware.embedding unset, or return a 503."""


def embed_text(text):
    """Returns the embedding vector (list[float]) for `text`."""
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.embed_content(model=EMBEDDING_MODEL, contents=text)
        return list(response.embeddings[0].values)
    except Exception as exc:
        raise EmbeddingError(str(exc)) from exc


def cosine_similarity(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
