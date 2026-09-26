import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
from app.matching.schema import CandidateProfile, NormalizedJob


def parse_experience_range(text: str) -> Tuple[Optional[float], Optional[float]]:
    """Extract minimum and maximum years of experience from text descriptions.

    Examples:
        '1-2 years' -> (1.0, 2.0)
        '0–1 years / Fresher' -> (0.0, 1.0)
        'Fresher' -> (0.0, 0.5)
        '8+ years' -> (8.0, 15.0)
        'minimum 3 years' -> (3.0, 5.0)
    """
    if not text:
        return (None, None)

    clean = text.lower().replace("–", "-").replace("—", "-")

    if "fresher" in clean and "-" not in clean:
        return (0.0, 1.0)

    # Match patterns like '1-3 years', '1 to 3 yrs', '1.5 - 3 yrs'
    range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:yrs|years|yr)?", clean)
    if range_match:
        try:
            min_y = float(range_match.group(1))
            max_y = float(range_match.group(2))
            return (min_y, max_y)
        except ValueError:
            pass

    # Match patterns like '3+ years', '3 + yrs'
    plus_match = re.search(r"(\d+(?:\.\d+)?)\s*\+\s*(?:yrs|years|yr)?", clean)
    if plus_match:
        try:
            min_y = float(plus_match.group(1))
            return (min_y, min_y + 4.0)
        except ValueError:
            pass

    # Match patterns like 'minimum 2 years'
    min_match = re.search(r"(?:min|minimum|at least)\s*(\d+(?:\.\d+)?)", clean)
    if min_match:
        try:
            min_y = float(min_match.group(1))
            return (min_y, min_y + 3.0)
        except ValueError:
            pass

    # Single digit like '2 years'
    single_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:yrs|years|yr)", clean)
    if single_match:
        try:
            val = float(single_match.group(1))
            return (val, val + 1.0)
        except ValueError:
            pass

    return (None, None)


def parse_posted_date(val: Optional[str]) -> Optional[datetime]:
    """Parse various date strings into UTC datetime."""
    if not val:
        return None

    clean = val.strip().lower()
    now = datetime.utcnow()

    # Relative time parsing
    if "just now" in clean or "today" in clean:
        return now
    if "yesterday" in clean:
        return now - timedelta(days=1)

    rel_hours = re.search(r"(\d+)\s*(?:hours?|hrs?)\s*ago", clean)
    if rel_hours:
        return now - timedelta(hours=int(rel_hours.group(1)))

    rel_days = re.search(r"(\d+)\s*(?:days?)\s*ago", clean)
    if rel_days:
        return now - timedelta(days=int(rel_days.group(1)))

    # ISO formats
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(val[:19], fmt)
        except (ValueError, IndexError):
            continue

    return None


def passes_hard_filters(job: NormalizedJob, profile: CandidateProfile) -> Tuple[bool, Optional[str]]:
    """Layer 1: Hard filter out completely incompatible jobs.

    Returns:
        (passes: bool, reason_if_failed: Optional[str])
    """
    # 1. Extreme experience check
    max_tolerable_experience = (
        profile.experience_preference.max_years + profile.experience_preference.tolerance_years
    )
    if job.min_experience_years is not None and job.min_experience_years > max_tolerable_experience:
        return (
            False,
            f"Requires {job.min_experience_years:.1f}+ years experience (exceeds max tolerance of {max_tolerable_experience:.1f} years)"
        )

    # 2. Location filter for strictly non-remote on-site jobs
    job_loc = (job.location or "").lower()
    job_mode = (job.work_mode or "").lower()

    if job_mode == "on-site" and job_loc:
        # Check if any preferred location matches
        loc_match = any(pref.lower() in job_loc for pref in profile.location_preferences)
        # Also allow general India matches
        if not loc_match and "india" not in job_loc:
            return (
                False,
                f"On-site role located at '{job.location}' outside preferred locations"
            )

    return (True, None)
