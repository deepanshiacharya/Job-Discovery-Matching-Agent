import unittest
from datetime import datetime
from app.matching.schema import CanonicalJob, CandidateProfile
from app.agents.profile_agent import ProfileAgent
from app.matching.scoring import (
    calculate_role_score,
    calculate_skill_score,
    calculate_experience_score,
    calculate_education_score,
    calculate_location_score,
    evaluate_job_relevance
)


class TestScoringEngine(unittest.TestCase):
    def setUp(self):
        self.profile = ProfileAgent().load_profile()

    def test_role_scoring(self):
        # High match role
        j1 = CanonicalJob(
            canonical_id="1",
            title="Junior AI/ML Engineer",
            company="TestCo",
            location="Delhi",
            work_mode="Remote",
            description="",
            experience_required="",
            education_required="",
            application_url=""
        )
        score1, _ = calculate_role_score(j1, self.profile)
        self.assertGreaterEqual(score1, 85.0)

        # Completely unrelated role
        j2 = CanonicalJob(
            canonical_id="2",
            title="Chef De Cuisine",
            company="Hotel Paris",
            location="Paris",
            work_mode="On-site",
            description="",
            experience_required="",
            education_required="",
            application_url=""
        )
        score2, _ = calculate_role_score(j2, self.profile)
        self.assertLess(score2, 50.0)

    def test_skill_scoring(self):
        j = CanonicalJob(
            canonical_id="1",
            title="Data Scientist",
            company="TestCo",
            location="Delhi",
            work_mode="Remote",
            description="",
            experience_required="",
            education_required="",
            required_skills=["Python", "SQL", "Machine Learning"],
            preferred_skills=["PyTorch", "Docker"],
            application_url=""
        )
        score, matched, missing, reasons = calculate_skill_score(j, self.profile)
        self.assertEqual(len(missing), 0)
        self.assertGreaterEqual(score, 90.0)
        self.assertIn("Python", matched)

    def test_experience_scoring(self):
        # In range
        j1 = CanonicalJob(
            canonical_id="1",
            title="Data Analyst",
            company="TestCo",
            location="Delhi",
            work_mode="Remote",
            description="",
            experience_required="1-2 years",
            min_experience_years=1.0,
            max_experience_years=2.0,
            education_required="",
            application_url=""
        )
        score1, _, _ = calculate_experience_score(j1, self.profile)
        self.assertEqual(score1, 100.0)

        # Extreme mismatch
        j2 = CanonicalJob(
            canonical_id="2",
            title="VP Analytics",
            company="TestCo",
            location="Delhi",
            work_mode="Remote",
            description="",
            experience_required="10+ years",
            min_experience_years=10.0,
            max_experience_years=15.0,
            education_required="",
            application_url=""
        )
        score2, _, gaps = calculate_experience_score(j2, self.profile)
        self.assertLess(score2, 50.0)
        self.assertGreater(len(gaps), 0)

    def test_end_to_end_job_relevance_evaluation(self):
        job = CanonicalJob(
            canonical_id="eval-1",
            title="Junior AI/ML Engineer",
            company="Synthetica Labs",
            location="Gurgaon, India",
            work_mode="Hybrid",
            description="Building LangGraph and LLM pipelines using Python and PyTorch.",
            experience_required="1-2 years",
            min_experience_years=1.0,
            max_experience_years=2.0,
            education_required="M.Sc. Data Science or Mathematics",
            required_skills=["Python", "Machine Learning", "PyTorch", "LangChain"],
            preferred_skills=["LangGraph", "Docker"],
            salary="₹9,00,000",
            posted_at=datetime.utcnow(),
            application_url="https://example.com/apply/eval-1"
        )
        match = evaluate_job_relevance(job, self.profile)

        self.assertGreaterEqual(match.relevance_score, 85.0)
        self.assertEqual(match.category.value, "HIGH_MATCH")
        self.assertGreater(len(match.why_matches), 0)
        self.assertIn("Python", match.matched_skills)


if __name__ == "__main__":
    unittest.main()
