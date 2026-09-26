import logging
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models import (
    CandidateProfileModel,
    JobModel,
    JobSourceModel,
    JobMatchModel,
    ApplicationModel,
    PipelineRunModel
)
from app.matching.schema import (
    CandidateProfile,
    CanonicalJob,
    JobMatch,
    PipelineRunStats,
    ApplicationStatus
)

logger = logging.getLogger(__name__)


class DatabaseRepository:
    def __init__(self, session: Session):
        self.session = session

    def sync_candidate_profile(self, profile: CandidateProfile) -> CandidateProfileModel:
        """Upsert the candidate profile into the database."""
        db_profile = self.session.query(CandidateProfileModel).filter_by(name=profile.name).first()
        education_dict = [e.model_dump() for e in profile.education]
        experience_dict = [exp.model_dump() for exp in profile.experience]
        preferences_dict = {
            "work_modes": profile.work_modes,
            "approx_experience_years": profile.approx_experience_years,
            "experience_preference": profile.experience_preference.model_dump(),
            "scoring_weights": profile.scoring_weights.model_dump(),
            "score_thresholds": profile.score_thresholds.model_dump(),
        }

        if db_profile:
            db_profile.education = education_dict
            db_profile.experience = experience_dict
            db_profile.skills = profile.technical_skills
            db_profile.target_roles = profile.target_roles
            db_profile.locations = profile.location_preferences
            db_profile.preferences = preferences_dict
            db_profile.updated_at = datetime.utcnow()
        else:
            db_profile = CandidateProfileModel(
                name=profile.name,
                education=education_dict,
                experience=experience_dict,
                skills=profile.technical_skills,
                target_roles=profile.target_roles,
                locations=profile.location_preferences,
                preferences=preferences_dict,
            )
            self.session.add(db_profile)
        self.session.flush()
        return db_profile

    def upsert_job(self, job: CanonicalJob) -> JobModel:
        """Upsert a canonical job record and record its sources."""
        db_job = self.session.query(JobModel).filter_by(canonical_job_id=job.canonical_id).first()
        if db_job:
            db_job.title = job.title
            db_job.company = job.company
            db_job.location = job.location
            db_job.work_mode = job.work_mode
            db_job.description = job.description
            db_job.experience_required = job.experience_required
            db_job.min_experience_years = job.min_experience_years
            db_job.max_experience_years = job.max_experience_years
            db_job.education_required = job.education_required
            db_job.required_skills = job.required_skills
            db_job.preferred_skills = job.preferred_skills
            db_job.salary = job.salary
            db_job.posted_at = job.posted_at
            db_job.application_url = job.application_url
            db_job.updated_at = datetime.utcnow()
        else:
            db_job = JobModel(
                canonical_job_id=job.canonical_id,
                title=job.title,
                company=job.company,
                location=job.location,
                work_mode=job.work_mode,
                description=job.description,
                experience_required=job.experience_required,
                min_experience_years=job.min_experience_years,
                max_experience_years=job.max_experience_years,
                education_required=job.education_required,
                required_skills=job.required_skills,
                preferred_skills=job.preferred_skills,
                salary=job.salary,
                posted_at=job.posted_at,
                application_url=job.application_url,
            )
            self.session.add(db_job)
            self.session.flush()

        # Update sources
        existing_sources = {
            s.source for s in self.session.query(JobSourceModel).filter_by(job_id=db_job.id).all()
        }
        for src in job.sources:
            if src not in existing_sources:
                src_job_id = job.source_job_ids.get(src, "")
                source_record = JobSourceModel(
                    job_id=db_job.id,
                    source=src,
                    source_job_id=src_job_id,
                    source_url=job.application_url,
                )
                self.session.add(source_record)

        self.session.flush()
        return db_job

    def save_job_matches(self, candidate_id: int, matches: List[JobMatch]):
        """Save computed matches and ensure application records exist."""
        for match in matches:
            db_job = self.upsert_job(match.job)

            # Check if match already recorded for this run/candidate
            existing_match = self.session.query(JobMatchModel).filter_by(
                job_id=db_job.id, candidate_id=candidate_id
            ).first()

            if existing_match:
                existing_match.relevance_score = match.relevance_score
                existing_match.category = match.category.value
                existing_match.role_score = match.score_breakdown.role_score
                existing_match.skill_score = match.score_breakdown.skill_score
                existing_match.experience_score = match.score_breakdown.experience_score
                existing_match.education_score = match.score_breakdown.education_score
                existing_match.location_score = match.score_breakdown.location_score
                existing_match.seniority_score = match.score_breakdown.seniority_score
                existing_match.freshness_score = match.score_breakdown.freshness_score
                existing_match.matched_skills = match.matched_skills
                existing_match.missing_skills = match.missing_skills
                existing_match.match_explanation = match.why_matches
                existing_match.gaps = match.potential_gaps
            else:
                db_match = JobMatchModel(
                    job_id=db_job.id,
                    candidate_id=candidate_id,
                    relevance_score=match.relevance_score,
                    category=match.category.value,
                    role_score=match.score_breakdown.role_score,
                    skill_score=match.score_breakdown.skill_score,
                    experience_score=match.score_breakdown.experience_score,
                    education_score=match.score_breakdown.education_score,
                    location_score=match.score_breakdown.location_score,
                    seniority_score=match.score_breakdown.seniority_score,
                    freshness_score=match.score_breakdown.freshness_score,
                    matched_skills=match.matched_skills,
                    missing_skills=match.missing_skills,
                    match_explanation=match.why_matches,
                    gaps=match.potential_gaps,
                )
                self.session.add(db_match)

            # Ensure application tracking record exists
            existing_app = self.session.query(ApplicationModel).filter_by(
                job_id=db_job.id, candidate_id=candidate_id
            ).first()
            if not existing_app:
                app_record = ApplicationModel(
                    job_id=db_job.id,
                    candidate_id=candidate_id,
                    status=match.application_status.value,
                )
                self.session.add(app_record)

        self.session.flush()

    def get_job_application_status(self, canonical_id: str, candidate_id: int) -> ApplicationStatus:
        """Fetch current application status for a job."""
        db_job = self.session.query(JobModel).filter_by(canonical_job_id=canonical_id).first()
        if not db_job:
            return ApplicationStatus.NOT_APPLIED
        app = self.session.query(ApplicationModel).filter_by(
            job_id=db_job.id, candidate_id=candidate_id
        ).first()
        if app:
            try:
                return ApplicationStatus(app.status)
            except ValueError:
                return ApplicationStatus.NOT_APPLIED
        return ApplicationStatus.NOT_APPLIED

    def start_pipeline_run(self, run_id: str) -> PipelineRunModel:
        run_record = PipelineRunModel(
            id=run_id,
            started_at=datetime.utcnow(),
            status="RUNNING"
        )
        self.session.add(run_record)
        self.session.flush()
        return run_record

    def complete_pipeline_run(self, stats: PipelineRunStats):
        run_record = self.session.query(PipelineRunModel).filter_by(id=stats.run_id).first()
        if run_record:
            run_record.completed_at = stats.completed_at or datetime.utcnow()
            run_record.jobs_discovered = stats.jobs_discovered
            run_record.jobs_normalized = stats.jobs_normalized
            run_record.jobs_deduplicated = stats.jobs_deduplicated
            run_record.jobs_matched = stats.jobs_matched
            run_record.jobs_recommended = stats.jobs_recommended
            run_record.high_matches = stats.high_matches
            run_record.good_matches = stats.good_matches
            run_record.stretch_matches = stats.stretch_matches
            run_record.status = stats.status
            run_record.error_message = stats.error_message
            run_record.report_path = stats.report_path
            self.session.flush()
