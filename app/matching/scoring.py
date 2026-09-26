import logging
from datetime import datetime
from typing import List, Tuple
from rapidfuzz import fuzz

from app.matching.schema import (
    CandidateProfile,
    CanonicalJob,
    JobMatch,
    MatchCategory,
    ScoreBreakdown,
    ApplicationStatus
)

logger = logging.getLogger(__name__)


def _normalize_token(text: str) -> str:
    return text.lower().replace("-", " ").replace("/", " ").strip()


def calculate_role_score(job: CanonicalJob, profile: CandidateProfile) -> Tuple[float, List[str]]:
    """Score title relevance against candidate's target roles."""
    title_norm = _normalize_token(job.title)
    best_score = 0.0
    matched_target_role = ""

    for target_role in profile.target_roles:
        target_norm = _normalize_token(target_role)

        # Exact match
        if target_norm == title_norm:
            best_score = 100.0
            matched_target_role = target_role
            break

        # Substring containment
        if target_norm in title_norm or title_norm in target_norm:
            score = 90.0
            if score > best_score:
                best_score = score
                matched_target_role = target_role

        # Fuzzy token set ratio
        ratio = fuzz.token_set_ratio(target_norm, title_norm)
        if ratio > best_score:
            best_score = float(ratio)
            matched_target_role = target_role

    reasons = []
    if best_score >= 80 and matched_target_role:
        reasons.append(f"Strong role match with target role: '{matched_target_role}'")
    elif best_score >= 60 and matched_target_role:
        reasons.append(f"Moderate role alignment with target role: '{matched_target_role}'")

    return (min(100.0, best_score), reasons)


def calculate_skill_score(job: CanonicalJob, profile: CandidateProfile) -> Tuple[float, List[str], List[str], List[str]]:
    """Compare candidate skills with job required and preferred skills."""
    cand_skills_norm = {_normalize_token(s): s for s in profile.technical_skills}

    matched_skills = []
    missing_skills = []

    req_matches = 0
    total_req = len(job.required_skills)

    for skill in job.required_skills:
        s_norm = _normalize_token(skill)
        # Direct or fuzzy match
        found = False
        for c_norm, original in cand_skills_norm.items():
            if s_norm == c_norm or s_norm in c_norm or c_norm in s_norm or fuzz.ratio(s_norm, c_norm) > 85:
                matched_skills.append(original)
                req_matches += 1
                found = True
                break
        if not found:
            missing_skills.append(skill)

    pref_matches = 0
    total_pref = len(job.preferred_skills)

    for skill in job.preferred_skills:
        s_norm = _normalize_token(skill)
        for c_norm, original in cand_skills_norm.items():
            if s_norm == c_norm or s_norm in c_norm or c_norm in s_norm or fuzz.ratio(s_norm, c_norm) > 85:
                if original not in matched_skills:
                    matched_skills.append(original)
                pref_matches += 1
                break

    # Calculate weighted score
    if total_req > 0 and total_pref > 0:
        req_ratio = req_matches / total_req
        pref_ratio = pref_matches / total_pref
        skill_score = (req_ratio * 0.75 + pref_ratio * 0.25) * 100.0
    elif total_req > 0:
        skill_score = (req_matches / total_req) * 100.0
    elif total_pref > 0:
        skill_score = (pref_matches / total_pref) * 100.0
    else:
        # Fallback: scan description for profile skills
        desc_norm = job.description.lower()
        found_in_desc = [s for s, orig in cand_skills_norm.items() if s in desc_norm]
        skill_score = min(100.0, len(found_in_desc) * 15.0)

    reasons = []
    if matched_skills:
        top_matched = ", ".join(list(dict.fromkeys(matched_skills))[:5])
        reasons.append(f"Matched technical skills: {top_matched}")

    return (min(100.0, round(skill_score, 1)), matched_skills, missing_skills, reasons)


def calculate_experience_score(job: CanonicalJob, profile: CandidateProfile) -> Tuple[float, List[str], List[str]]:
    """Evaluate experience alignment with tolerance penalties."""
    cand_exp = profile.approx_experience_years
    min_req = job.min_experience_years
    max_req = job.max_experience_years

    reasons = []
    gaps = []

    if min_req is None:
        # Assume entry/junior friendly
        return (90.0, ["Experience requirement flexible or not specified."], [])

    # Exact sweet spot
    if min_req <= cand_exp <= (max_req or (min_req + 2.0)):
        score = 100.0
        reasons.append(f"Required experience ({job.experience_required}) perfectly aligns with candidate's {cand_exp} years.")
    elif cand_exp < min_req:
        gap_years = min_req - cand_exp
        if gap_years <= 1.0:
            score = 80.0
            reasons.append(f"Experience slightly above profile ({job.experience_required}), within reasonable stretch tolerance.")
        elif gap_years <= profile.experience_preference.tolerance_years:
            score = 65.0
            gaps.append(f"Requires {job.experience_required} (stretch for candidate's {cand_exp} years).")
        else:
            score = max(20.0, 60.0 - gap_years * 15.0)
            gaps.append(f"Requires {job.experience_required}, exceeding candidate's {cand_exp} years.")
    else:
        # Candidate has more experience than max (e.g. overqualified)
        score = 90.0
        reasons.append("Candidate meets and exceeds minimum experience requirement.")

    return (round(score, 1), reasons, gaps)


def calculate_education_score(job: CanonicalJob, profile: CandidateProfile) -> Tuple[float, List[str]]:
    """Match education requirements with candidate's M.Sc. Data Science and B.Sc. Mathematics."""
    text = (job.education_required + " " + job.description).lower()
    score = 80.0  # Base score
    reasons = []

    has_master = any("m.sc" in text or "master" in text or "postgraduate" in text or "m.tech" in text for _ in [1])
    has_ds_math = any(kw in text for kw in ["data science", "mathematics", "statistics", "quantitative"])

    if has_master and has_ds_math:
        score = 100.0
        reasons.append("Target education explicitly calls for Master's in Data Science / Mathematics.")
    elif has_ds_math:
        score = 95.0
        reasons.append("Quantitative background (Data Science & Mathematics) aligns with requirements.")
    elif "ph.d" in text and "master" not in text:
        score = 45.0
    else:
        score = 85.0

    return (score, reasons)


def calculate_location_score(job: CanonicalJob, profile: CandidateProfile) -> Tuple[float, List[str]]:
    """Match location and work mode preferences."""
    work_mode = (job.work_mode or "").lower()
    job_loc = (job.location or "").lower()
    reasons = []

    if "remote" in work_mode or "remote" in job_loc:
        reasons.append("Remote work mode aligns with candidate preference.")
        return (100.0, reasons)

    # Check preferred locations
    matched_city = None
    for pref in profile.location_preferences:
        if pref.lower() in job_loc:
            matched_city = pref
            break

    if matched_city:
        reasons.append(f"Location in preferred region: {matched_city} ({job.work_mode}).")
        return (95.0 if "hybrid" in work_mode else 90.0, reasons)

    if "india" in job_loc:
        return (75.0, ["Located in India."])

    return (50.0, [])


def calculate_seniority_score(job: CanonicalJob) -> float:
    """Evaluate seniority fit."""
    title = job.title.lower()
    if any(k in title for k in ["junior", "intern", "associate", "entry", "fresher", "trainee"]):
        return 100.0
    if any(k in title for k in ["lead", "principal", "director", "vp", "head"]):
        return 35.0
    if "senior" in title:
        return 65.0
    return 85.0


def calculate_freshness_score(job: CanonicalJob) -> float:
    """Evaluate listing recency."""
    if not job.posted_at:
        return 65.0

    age = datetime.utcnow() - job.posted_at
    if age.total_seconds() <= 86400:  # <= 24 hours
        return 100.0
    elif age.total_seconds() <= 3 * 86400:  # <= 3 days
        return 85.0
    elif age.total_seconds() <= 7 * 86400:  # <= 7 days
        return 70.0
    else:
        return 50.0


def evaluate_job_relevance(
    job: CanonicalJob,
    profile: CandidateProfile,
    current_status: ApplicationStatus = ApplicationStatus.NOT_APPLIED
) -> JobMatch:
    """Compute complete multi-layer relevance score and generate structured match explanations."""
    w = profile.scoring_weights

    # Sub-scores
    role_score, role_reasons = calculate_role_score(job, profile)
    skill_score, matched_skills, missing_skills, skill_reasons = calculate_skill_score(job, profile)
    exp_score, exp_reasons, exp_gaps = calculate_experience_score(job, profile)
    edu_score, edu_reasons = calculate_education_score(job, profile)
    loc_score, loc_reasons = calculate_location_score(job, profile)
    sen_score = calculate_seniority_score(job)
    fresh_score = calculate_freshness_score(job)

    # Weighted calculation
    total_score = (
        w.role_relevance * role_score
        + w.skills_match * skill_score
        + w.experience_match * exp_score
        + w.education_match * edu_score
        + w.location_work_mode * loc_score
        + w.seniority * sen_score
        + w.freshness * fresh_score
    )
    total_score = max(0.0, min(100.0, round(total_score, 1)))

    breakdown = ScoreBreakdown(
        role_score=role_score,
        skill_score=skill_score,
        experience_score=exp_score,
        education_score=edu_score,
        location_score=loc_score,
        seniority_score=sen_score,
        freshness_score=fresh_score,
        total_relevance_score=total_score
    )

    # Categorization based on configurable thresholds
    th = profile.score_thresholds
    if total_score >= th.HIGH_MATCH:
        category = MatchCategory.HIGH_MATCH
    elif total_score >= th.GOOD_MATCH:
        category = MatchCategory.GOOD_MATCH
    elif total_score >= th.STRETCH:
        category = MatchCategory.STRETCH
    else:
        category = MatchCategory.LOW_MATCH

    # Synthesize evidence-based explanations
    why_matches = []
    why_matches.extend(role_reasons)
    why_matches.extend(skill_reasons)
    why_matches.extend(exp_reasons)
    why_matches.extend(edu_reasons)
    why_matches.extend(loc_reasons)

    # Domain background connection
    if any(k in job.title.lower() for k in ["business", "bi", "product"]):
        why_matches.append("Prior Amazon Business Analyst internship directly complements this role.")
    if any(k in job.title.lower() for k in ["ai", "agent", "llm", "nlp"]):
        why_matches.append("Avkalan.ai AI Engineer & LangGraph/LangChain experience strongly applies.")

    potential_gaps = []
    potential_gaps.extend(exp_gaps)
    if missing_skills:
        potential_gaps.append(f"Gaps in job requirements: {', '.join(missing_skills[:4])}")

    return JobMatch(
        job=job,
        relevance_score=total_score,
        category=category,
        score_breakdown=breakdown,
        matched_skills=list(dict.fromkeys(matched_skills)),
        missing_skills=missing_skills,
        why_matches=why_matches,
        potential_gaps=potential_gaps,
        application_status=current_status
    )
