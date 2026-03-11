from functools import lru_cache
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer("all-MiniLM-L6-v2")


def embed_texts(texts: List[str]) -> np.ndarray:
    model = get_model()
    return model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True
    )


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b))