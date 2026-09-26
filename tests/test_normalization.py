import unittest
from datetime import datetime
from app.agents.normalization_agent import JobNormalizationAgent
from app.matching.schema import RawJob
from app.matching.rules import parse_experience_range, parse_posted_date


class TestNormalization(unittest.TestCase):
    def setUp(self):
        self.agent = JobNormalizationAgent()

    def test_experience_range_parsing(self):
        cases = [
            ("1-2 years", (1.0, 2.0)),
            ("0–1 years / Fresher", (0.0, 1.0)),
            ("Fresher", (0.0, 1.0)),
            ("8+ years", (8.0, 12.0)),
            ("minimum 3 years", (3.0, 6.0)),
            ("2 yrs", (2.0, 3.0)),
            ("", (None, None)),
        ]
        for text, expected in cases:
            min_y, max_y = parse_experience_range(text)
            self.assertEqual(min_y, expected[0], f"Failed min on '{text}'")
            if expected[1] is not None:
                self.assertIsNotNone(max_y, f"Failed max on '{text}'")

    def test_date_parsing(self):
        dt = parse_posted_date("2026-09-25T10:00:00")
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 9)

        dt_rel = parse_posted_date("2 hours ago")
        self.assertIsInstance(dt_rel, datetime)

    def test_normalize_raw_job(self):
        raw = RawJob(
            source="LinkedIn",
            source_job_id="li-999",
            title="Junior Data Analyst ",
            company=" Acme Analytics ",
            location="Gurgaon, India",
            work_mode="Unknown",
            description="Remote position working with Python and SQL.",
            experience_required="1-2 years",
            education_required="Bachelor's in Math or CS",
            required_skills=["Python", "SQL"],
            preferred_skills=["Tableau"],
            salary="₹7,00,000",
            posted_at="2026-09-25T10:00:00",
            application_url="https://linkedin.com/jobs/999"
        )
        norm = self.agent.normalize_single(raw)

        self.assertEqual(norm.title, "Junior Data Analyst")
        self.assertEqual(norm.company, "Acme Analytics")
        self.assertEqual(norm.min_experience_years, 1.0)
        self.assertEqual(norm.max_experience_years, 2.0)
        self.assertEqual(norm.work_mode, "Remote")  # Detected from description
        self.assertEqual(len(norm.required_skills), 2)
        self.assertIn("Python", norm.required_skills)
        self.assertIsNotNone(norm.posted_at)


if __name__ == "__main__":
    unittest.main()
