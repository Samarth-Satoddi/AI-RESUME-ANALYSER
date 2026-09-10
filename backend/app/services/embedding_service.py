import math
try:
    import numpy as np
except ImportError:
    np = None
from typing import Optional, Tuple
from app.core.logging import logger

_model_instance = None
_model_load_attempted = False


class EmbeddingService:
    """
    Singleton embedding service for computing dense vector representations
    and cosine similarities between resume text and job descriptions.
    Includes automated fallback to TF-IDF cosine if model is unavailable.
    """

    MODEL_NAME = "all-MiniLM-L6-v2"

    @classmethod
    def get_model(cls):
        global _model_instance, _model_load_attempted
        if _model_instance is not None:
            return _model_instance

        if not _model_load_attempted:
            _model_load_attempted = True
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading SentenceTransformer embedding model: {cls.MODEL_NAME}")
                _model_instance = SentenceTransformer(cls.MODEL_NAME)
                logger.info("SentenceTransformer model loaded successfully.")
            except Exception as e:
                logger.warning(f"SentenceTransformer unavailable, falling back to TF-IDF similarity: {e}")
                _model_instance = None

        return _model_instance

    @classmethod
    def compute_semantic_similarity(cls, text1: str, text2: str) -> Tuple[float, bool]:
        """
        Computes cosine similarity between two texts using dense embeddings.
        Returns:
            (similarity_score: float [0-100], used_embeddings: bool)
        """
        if not text1 or not text2:
            return 0.0, False

        model = cls.get_model()
        if model is not None and np is not None:
            try:
                # Truncate to avoid excessive token length
                t1 = text1[:2000]
                t2 = text2[:2000]
                embs = model.encode([t1, t2], normalize_embeddings=True)
                cosine = float(np.dot(embs[0], embs[1]))
                score = round(max(0.0, min(cosine * 100.0, 100.0)), 1)
                return score, True
            except Exception as e:
                logger.warning(f"Error computing dense embedding similarity: {e}")

        # Fallback: Term-frequency cosine
        words1 = [w.lower() for w in text1.split()]
        words2 = [w.lower() for w in text2.split()]
        from collections import Counter
        v1, v2 = Counter(words1), Counter(words2)
        common = set(v1.keys()) & set(v2.keys())
        dot = sum(v1[k] * v2[k] for k in common)
        norm1 = math.sqrt(sum(v**2 for v in v1.values()))
        norm2 = math.sqrt(sum(v**2 for v in v2.values()))
        if norm1 and norm2:
            sim = (dot / (norm1 * norm2)) * 100.0
            return round(min(sim, 100.0), 1), False

        return 50.0, False
