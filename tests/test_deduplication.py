import unittest
from datetime import datetime
from app.agents.matching_agent import JobMatchingAgent
from app.matching.schema import NormalizedJob


class TestDeduplication(unittest.TestCase):
    def setUp(self):
        self.agent = JobMatchingAgent()

    def test_exact_url_deduplication(self):
        j1 = NormalizedJob(
            job_id="id1",
            source="LinkedIn",
            source_job_id="111",
            title="Data Analyst",
            company="FinTech Corp",
            location="Bangalore",
            work_mode="Hybrid",
            description="SQL and Python analytics",
            experience_required="1-2 years",
            education_required="Degree in Math/CS",
            application_url="https://example.com/jobs/101"
        )
        j2 = NormalizedJob(
            job_id="id2",
            source="Indeed",
            source_job_id="222",
            title="Data Analyst Intern",
            company="FinTech Corp",
            location="Bangalore",
            work_mode="Hybrid",
            description="SQL and Python analytics with financial data",
            experience_required="1-2 years",
            education_required="Degree in Math/CS",
            application_url="https://example.com/jobs/101"  # Same URL
        )
        canonical = self.agent.deduplicate([j1, j2])
        self.assertEqual(len(canonical), 1)
        self.assertIn("LinkedIn", canonical[0].sources)
        self.assertIn("Indeed", canonical[0].sources)

    def test_company_title_location_deduplication(self):
        j1 = NormalizedJob(
            job_id="id1",
            source="LinkedIn",
            source_job_id="li-1",
            title="Junior AI Engineer",
            company="NeuralLabs AI",
            location="Gurgaon, India",
            work_mode="Hybrid",
            description="Working on PyTorch and LangChain LLM systems.",
            experience_required="1-2 years",
            education_required="M.Sc. or B.Sc. Data Science",
            application_url="https://linkedin.com/jobs/1"
        )
        j2 = NormalizedJob(
            job_id="id2",
            source="Naukri",
            source_job_id="nk-2",
            title="Junior AI Engineer",
            company="NeuralLabs AI",
            location="Gurgaon",
            work_mode="Hybrid",
            description="NeuralLabs is hiring a Junior AI Engineer for LangChain and PyTorch applications.",
            experience_required="1-2 years",
            education_required="M.Sc. or B.Sc. Data Science",
            application_url="https://naukri.com/jobs/2"
        )
        canonical = self.agent.deduplicate([j1, j2])
        self.assertEqual(len(canonical), 1)
        self.assertEqual(len(canonical[0].sources), 2)
        self.assertIn("LinkedIn", canonical[0].sources)
        self.assertIn("Naukri", canonical[0].sources)

    def test_distinct_jobs_not_merged(self):
        j1 = NormalizedJob(
            job_id="id1",
            source="LinkedIn",
            source_job_id="li-1",
            title="Junior AI Engineer",
            company="NeuralLabs AI",
            location="Gurgaon",
            work_mode="Hybrid",
            description="PyTorch and LLMs",
            experience_required="1-2 years",
            education_required="Data Science degree",
            application_url="https://linkedin.com/jobs/1"
        )
        j2 = NormalizedJob(
            job_id="id2",
            source="Indeed",
            source_job_id="ind-2",
            title="Senior Sales Executive",
            company="Aura Hardware",
            location="Jaipur",
            work_mode="On-site",
            description="B2B sales and cold calls",
            experience_required="3-5 years",
            education_required="Any",
            application_url="https://indeed.com/jobs/2"
        )
        canonical = self.agent.deduplicate([j1, j2])
        self.assertEqual(len(canonical), 2)


if __name__ == "__main__":
    unittest.main()
