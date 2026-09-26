import logging
import re
from typing import Optional
from app.config import settings
from app.matching.schema import CandidateProfile, CanonicalJob

logger = logging.getLogger(__name__)

_model = None


def get_embedding_model():
    global _model
    if _model is None and settings.ENABLE_SEMANTIC_EMBEDDINGS:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded SentenceTransformer for semantic scoring.")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer ({e}). Falling back to lexical similarity.")
            _model = False
    return _model


def _tokenize(text: str) -> set:
    words = re.findall(r"\b[a-zA-Z0-9_\+\#\.\-]{2,}\b", text.lower())
    return set(words)


def compute_semantic_similarity(profile: CandidateProfile, job: CanonicalJob) -> float:
    """Compute semantic score between 0.0 and 100.0."""
    profile_text = (
        f"{profile.name} "
        f"{' '.join([e.degree + ' ' + e.field for e in profile.education])} "
        f"{' '.join([exp.title + ' ' + exp.description for exp in profile.experience])} "
        f"{' '.join(profile.technical_skills)} "
        f"{' '.join(profile.target_roles)}"
    )

    job_text = (
        f"{job.title} {job.company} {job.description} "
        f"{' '.join(job.required_skills)} {' '.join(job.preferred_skills)}"
    )

    model = get_embedding_model()
    if model:
        try:
            from sentence_transformers import util
            emb_p = model.encode(profile_text, convert_to_tensor=True)
            emb_j = model.encode(job_text, convert_to_tensor=True)
            cos_sim = util.cos_sim(emb_p, emb_j).item()
            # Normalize [-1, 1] to [0, 100]
            normalized_score = max(0.0, min(100.0, (cos_sim + 0.2) / 1.2 * 100.0))
            return normalized_score
        except Exception as e:
            logger.warning(f"Semantic embedding calculation failed ({e}), using lexical similarity.")

    # High-quality deterministic token overlap fallback
    tokens_p = _tokenize(profile_text)
    tokens_j = _tokenize(job_text)
    if not tokens_j:
        return 50.0

    intersection = tokens_p.intersection(tokens_j)
    jaccard = len(intersection) / len(tokens_j)
    # Scale to 0-100 range
    score = min(100.0, jaccard * 180.0)
    return round(score, 2)
