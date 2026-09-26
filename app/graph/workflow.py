import logging
import uuid
from datetime import datetime
from langgraph.graph import StateGraph, START, END

from app.graph.state import JobAgentState
from app.agents.profile_agent import ProfileAgent
from app.agents.discovery_agent import JobDiscoveryAgent
from app.agents.normalization_agent import JobNormalizationAgent
from app.agents.matching_agent import JobMatchingAgent
from app.agents.ranking_agent import JobRankingAgent
from app.agents.report_agent import ReportAgent
from app.matching.schema import PipelineRunStats, MatchCategory
from app.database.connection import get_db_session, init_db
from app.database.repository import DatabaseRepository

logger = logging.getLogger(__name__)


# --- Graph Node Definitions ---

def load_profile_node(state: JobAgentState) -> JobAgentState:
    logger.info("--- [Node: Load Candidate Profile] ---")
    agent = ProfileAgent()
    profile = agent.load_profile()

    run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    stats = PipelineRunStats(run_id=run_id, started_at=datetime.utcnow())

    return {
        "candidate_profile": profile,
        "stats": stats,
        "errors": []
    }


def discover_jobs_node(state: JobAgentState) -> JobAgentState:
    logger.info("--- [Node: Discover Jobs] ---")
    agent = JobDiscoveryAgent()
    raw_jobs = agent.discover_all()

    stats = state.get("stats")
    if stats:
        stats.jobs_discovered = len(raw_jobs)

    return {
        "raw_jobs": raw_jobs,
        "stats": stats
    }


def normalize_jobs_node(state: JobAgentState) -> JobAgentState:
    logger.info("--- [Node: Normalize Jobs] ---")
    raw_jobs = state.get("raw_jobs", [])
    agent = JobNormalizationAgent()
    normalized_jobs = agent.normalize_all(raw_jobs)

    stats = state.get("stats")
    if stats:
        stats.jobs_normalized = len(normalized_jobs)

    return {
        "normalized_jobs": normalized_jobs,
        "stats": stats
    }


def deduplicate_jobs_node(state: JobAgentState) -> JobAgentState:
    logger.info("--- [Node: Deduplicate Jobs] ---")
    normalized_jobs = state.get("normalized_jobs", [])
    agent = JobMatchingAgent()
    deduped = agent.deduplicate(normalized_jobs)

    stats = state.get("stats")
    if stats:
        stats.jobs_deduplicated = len(deduped)

    return {
        "deduplicated_jobs": deduped,
        "stats": stats
    }


def match_and_score_node(state: JobAgentState) -> JobAgentState:
    logger.info("--- [Node: Match and Score Jobs] ---")
    deduped = state.get("deduplicated_jobs", [])
    profile = state.get("candidate_profile")

    agent = JobMatchingAgent()
    matches, filtered_out = agent.filter_and_match(deduped, profile)

    stats = state.get("stats")
    if stats:
        stats.jobs_matched = len(matches)

    return {
        "scored_matches": matches,
        "filtered_out_jobs": filtered_out,
        "stats": stats
    }


def rank_jobs_node(state: JobAgentState) -> JobAgentState:
    logger.info("--- [Node: Rank & Categorize Opportunities] ---")
    matches = state.get("scored_matches", [])
    agent = JobRankingAgent()
    ranked = agent.rank(matches)
    top_picks = agent.get_top_recommendations(ranked, top_n=5)

    stats = state.get("stats")
    if stats:
        stats.high_matches = sum(1 for m in ranked if m.category == MatchCategory.HIGH_MATCH)
        stats.good_matches = sum(1 for m in ranked if m.category == MatchCategory.GOOD_MATCH)
        stats.stretch_matches = sum(1 for m in ranked if m.category == MatchCategory.STRETCH)
        stats.jobs_recommended = stats.high_matches + stats.good_matches + stats.stretch_matches

    return {
        "ranked_matches": ranked,
        "top_recommendations": top_picks,
        "stats": stats
    }


def persist_database_node(state: JobAgentState) -> JobAgentState:
    logger.info("--- [Node: Persist to Database] ---")
    profile = state.get("candidate_profile")
    ranked = state.get("ranked_matches", [])
    stats = state.get("stats")

    try:
        init_db()
        with get_db_session() as session:
            repo = DatabaseRepository(session)
            db_profile = repo.sync_candidate_profile(profile)
            repo.save_job_matches(candidate_id=db_profile.id, matches=ranked)
            if stats:
                repo.complete_pipeline_run(stats)
            logger.info("Pipeline run data and matches successfully persisted to database.")
    except Exception as e:
        logger.error(f"Failed to persist state to database: {e}", exc_info=True)
        errors = state.get("errors", [])
        errors.append(f"DB persistence error: {e}")
        return {"errors": errors}

    return {"stats": stats}


def generate_report_node(state: JobAgentState) -> JobAgentState:
    logger.info("--- [Node: Generate Report & Deliver Email] ---")
    ranked = state.get("ranked_matches", [])
    top_picks = state.get("top_recommendations", [])
    stats = state.get("stats")

    agent = ReportAgent()
    report_path, email_sent = agent.generate_and_deliver(
        ranked_matches=ranked,
        top_matches=top_picks,
        stats=stats
    )

    if stats:
        stats.report_path = report_path
        stats.email_sent = email_sent
        stats.completed_at = datetime.utcnow()
        stats.status = "SUCCESS"

    return {
        "report_path": report_path,
        "email_sent": email_sent,
        "stats": stats
    }


# --- Workflow Graph Assembly ---

def create_job_discovery_graph():
    """Builds and compiles the LangGraph StateGraph workflow."""
    workflow = StateGraph(JobAgentState)

    workflow.add_node("load_profile", load_profile_node)
    workflow.add_node("discover_jobs", discover_jobs_node)
    workflow.add_node("normalize_jobs", normalize_jobs_node)
    workflow.add_node("deduplicate_jobs", deduplicate_jobs_node)
    workflow.add_node("match_jobs", match_and_score_node)
    workflow.add_node("rank_jobs", rank_jobs_node)
    workflow.add_node("persist_database", persist_database_node)
    workflow.add_node("generate_report", generate_report_node)

    # Workflow Edges
    workflow.add_edge(START, "load_profile")
    workflow.add_edge("load_profile", "discover_jobs")
    workflow.add_edge("discover_jobs", "normalize_jobs")
    workflow.add_edge("normalize_jobs", "deduplicate_jobs")
    workflow.add_edge("deduplicate_jobs", "match_jobs")
    workflow.add_edge("match_jobs", "rank_jobs")
    workflow.add_edge("rank_jobs", "persist_database")
    workflow.add_edge("persist_database", "generate_report")
    workflow.add_edge("generate_report", END)

    return workflow.compile()
