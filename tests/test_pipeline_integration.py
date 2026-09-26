import unittest
from pathlib import Path
from app.graph.workflow import create_job_discovery_graph
from app.matching.schema import MatchCategory


class TestPipelineIntegration(unittest.TestCase):
    def test_full_pipeline_execution(self):
        graph = create_job_discovery_graph()
        initial_state = {}

        result = graph.invoke(initial_state)

        # Assert profile loaded
        profile = result.get("candidate_profile")
        self.assertIsNotNone(profile)
        self.assertIn("Python", profile.technical_skills)

        # Assert discovery
        raw_jobs = result.get("raw_jobs", [])
        self.assertGreater(len(raw_jobs), 0)

        # Assert normalization
        norm_jobs = result.get("normalized_jobs", [])
        self.assertEqual(len(norm_jobs), len(raw_jobs))

        # Assert deduplication (there are duplicate jobs in sample_jobs.json)
        dedup_jobs = result.get("deduplicated_jobs", [])
        self.assertLess(len(dedup_jobs), len(norm_jobs))

        # Assert scoring & ranking
        ranked = result.get("ranked_matches", [])
        self.assertGreater(len(ranked), 0)

        # Ensure scores are strictly sorted descending
        for i in range(len(ranked) - 1):
            self.assertGreaterEqual(ranked[i].relevance_score, ranked[i + 1].relevance_score)

        # Assert top matches are high quality
        top_match = ranked[0]
        self.assertIn(top_match.category, [MatchCategory.HIGH_MATCH, MatchCategory.GOOD_MATCH])
        self.assertGreater(len(top_match.why_matches), 0)

        # Assert report generation
        report_path = result.get("report_path")
        self.assertIsNotNone(report_path)
        self.assertTrue(Path(report_path).exists())

        # Assert stats
        stats = result.get("stats")
        self.assertIsNotNone(stats)
        self.assertEqual(stats.status, "SUCCESS")
        self.assertGreater(stats.jobs_discovered, 0)
        self.assertGreater(stats.jobs_recommended, 0)


if __name__ == "__main__":
    unittest.main()
