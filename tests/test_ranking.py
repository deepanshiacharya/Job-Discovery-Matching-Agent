import unittest
from app.agents.ranking_agent import JobRankingAgent
from app.matching.schema import (
    CanonicalJob,
    JobMatch,
    MatchCategory,
    ScoreBreakdown,
    ApplicationStatus
)


class TestRanking(unittest.TestCase):
    def setUp(self):
        self.agent = JobRankingAgent()

    def _create_mock_match(self, id_str: str, score: float, category: MatchCategory) -> JobMatch:
        job = CanonicalJob(
            canonical_id=id_str,
            title=f"Role {id_str}",
            company="Co",
            location="Remote",
            work_mode="Remote",
            description="",
            experience_required="",
            education_required="",
            application_url=""
        )
        return JobMatch(
            job=job,
            relevance_score=score,
            category=category,
            score_breakdown=ScoreBreakdown(total_relevance_score=score)
        )

    def test_ranking_sort_order(self):
        m1 = self._create_mock_match("1", 72.0, MatchCategory.GOOD_MATCH)
        m2 = self._create_mock_match("2", 91.5, MatchCategory.HIGH_MATCH)
        m3 = self._create_mock_match("3", 58.0, MatchCategory.STRETCH)
        m4 = self._create_mock_match("4", 42.0, MatchCategory.LOW_MATCH)

        ranked = self.agent.rank([m1, m2, m3, m4])

        self.assertEqual(len(ranked), 4)
        self.assertEqual(ranked[0].job.canonical_id, "2")
        self.assertEqual(ranked[1].job.canonical_id, "1")
        self.assertEqual(ranked[2].job.canonical_id, "3")
        self.assertEqual(ranked[3].job.canonical_id, "4")

    def test_top_recommendations_excludes_low(self):
        m1 = self._create_mock_match("1", 90.0, MatchCategory.HIGH_MATCH)
        m2 = self._create_mock_match("2", 40.0, MatchCategory.LOW_MATCH)
        top = self.agent.get_top_recommendations([m1, m2], top_n=5)

        self.assertEqual(len(top), 1)
        self.assertEqual(top[0].category, MatchCategory.HIGH_MATCH)


if __name__ == "__main__":
    unittest.main()
