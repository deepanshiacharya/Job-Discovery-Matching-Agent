from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Boolean,
    JSON
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class CandidateProfileModel(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    education = Column(JSON, nullable=False, default=list)
    experience = Column(JSON, nullable=False, default=list)
    skills = Column(JSON, nullable=False, default=list)
    target_roles = Column(JSON, nullable=False, default=list)
    locations = Column(JSON, nullable=False, default=list)
    preferences = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    matches = relationship("JobMatchModel", back_populates="candidate")
    applications = relationship("ApplicationModel", back_populates="candidate")


class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    canonical_job_id = Column(String(128), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    work_mode = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    experience_required = Column(String(128), nullable=True)
    min_experience_years = Column(Float, nullable=True)
    max_experience_years = Column(Float, nullable=True)
    education_required = Column(String(255), nullable=True)
    required_skills = Column(JSON, default=list)
    preferred_skills = Column(JSON, default=list)
    salary = Column(String(128), nullable=True)
    posted_at = Column(DateTime, nullable=True)
    application_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sources = relationship("JobSourceModel", back_populates="job", cascade="all, delete-orphan")
    matches = relationship("JobMatchModel", back_populates="job", cascade="all, delete-orphan")
    applications = relationship("ApplicationModel", back_populates="job", cascade="all, delete-orphan")


class JobSourceModel(Base):
    __tablename__ = "job_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(64), nullable=False)
    source_job_id = Column(String(128), nullable=True)
    source_url = Column(Text, nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("JobModel", back_populates="sources")


class JobMatchModel(Base):
    __tablename__ = "job_matches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=True)
    relevance_score = Column(Float, nullable=False)
    category = Column(String(64), nullable=False)
    role_score = Column(Float, default=0.0)
    skill_score = Column(Float, default=0.0)
    experience_score = Column(Float, default=0.0)
    education_score = Column(Float, default=0.0)
    location_score = Column(Float, default=0.0)
    seniority_score = Column(Float, default=0.0)
    freshness_score = Column(Float, default=0.0)
    matched_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    match_explanation = Column(JSON, default=list)
    gaps = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("JobModel", back_populates="matches")
    candidate = relationship("CandidateProfileModel", back_populates="matches")


class ApplicationModel(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(Integer, ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=True)
    status = Column(String(64), default="NOT_APPLIED", nullable=False)
    applied_at = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    resume_version = Column(String(128), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship("JobModel", back_populates="applications")
    candidate = relationship("CandidateProfileModel", back_populates="applications")


class PipelineRunModel(Base):
    __tablename__ = "pipeline_runs"

    id = Column(String(128), primary_key=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    jobs_discovered = Column(Integer, default=0)
    jobs_normalized = Column(Integer, default=0)
    jobs_deduplicated = Column(Integer, default=0)
    jobs_matched = Column(Integer, default=0)
    jobs_recommended = Column(Integer, default=0)
    high_matches = Column(Integer, default=0)
    good_matches = Column(Integer, default=0)
    stretch_matches = Column(Integer, default=0)
    status = Column(String(64), default="RUNNING")
    error_message = Column(Text, nullable=True)
    report_path = Column(Text, nullable=True)
