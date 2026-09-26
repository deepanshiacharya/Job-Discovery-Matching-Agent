import unittest
from app.agents.profile_agent import ProfileAgent
from app.matching.schema import CandidateProfile


class TestProfileAgent(unittest.TestCase):
    def test_load_candidate_profile(self):
        agent = ProfileAgent()
        profile = agent.load_profile()

        self.assertIsInstance(profile, CandidateProfile)
        self.assertIn("Python", profile.technical_skills)
        self.assertIn("SQL", profile.technical_skills)
        self.assertIn("Data Analyst", profile.target_roles)
        self.assertIn("AI Engineer", profile.target_roles)
        self.assertGreater(len(profile.education), 0)
        self.assertGreater(len(profile.experience), 0)
        self.assertGreaterEqual(profile.approx_experience_years, 1.0)
        self.assertEqual(profile.experience_preference.max_years, 3.0)

    def test_weights_sum_to_one(self):
        agent = ProfileAgent()
        profile = agent.load_profile()
        w = profile.scoring_weights
        total_weight = (
            w.role_relevance
            + w.skills_match
            + w.experience_match
            + w.education_match
            + w.location_work_mode
            + w.seniority
            + w.freshness
        )
        self.assertAlmostEqual(total_weight, 1.0, places=4)


if __name__ == "__main__":
    unittest.main()
