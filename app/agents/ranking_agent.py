import logging
from typing import List
from app.matching.schema import JobMatch, MatchCategory

logger = logging.getLogger(__name__)


class JobRankingAgent:
    """Ranks and stratifies matched jobs by relevance score and category."""

    def rank(self, matches: List[JobMatch]) -> List[JobMatch]:
        ranked = sorted(matches, key=lambda m: m.relevance_score, reverse=True)
        logger.info(f"Ranked {len(ranked)} jobs. Top score: {ranked[0].relevance_score if ranked else 0}")
        return ranked

    def get_top_recommendations(self, ranked_matches: List[JobMatch], top_n: int = 5) -> List[JobMatch]:
        # Exclude LOW_MATCH from top highlights unless no other jobs exist
        non_low = [m for m in ranked_matches if m.category != MatchCategory.LOW_MATCH]
        return non_low[:top_n] if non_low else ranked_matches[:top_n]
