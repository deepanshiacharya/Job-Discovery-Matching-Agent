import logging
import sys
from app.config import settings
from app.graph.workflow import create_job_discovery_graph

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("JobDiscoveryApp")


def run_pipeline():
    logger.info("=" * 65)
    logger.info("       STARTING AI-POWERED JOB DISCOVERY & MATCHING PIPELINE       ")
    logger.info("=" * 65)

    app = create_job_discovery_graph()
    initial_state = {}

    try:
        final_state = app.invoke(initial_state)

        stats = final_state.get("stats")
        report_path = final_state.get("report_path")
        ranked = final_state.get("ranked_matches", [])

        logger.info("=" * 65)
        logger.info("                   PIPELINE EXECUTION COMPLETE                   ")
        logger.info("=" * 65)
        if stats:
            logger.info(f"Run ID:                {stats.run_id}")
            logger.info(f"Jobs Discovered:       {stats.jobs_discovered}")
            logger.info(f"Jobs Normalized:       {stats.jobs_normalized}")
            logger.info(f"Jobs After Dedup:      {stats.jobs_deduplicated}")
            logger.info(f"Jobs Evaluated:        {stats.jobs_matched}")
            logger.info(f"High Matches (>=85%):  {stats.high_matches}")
            logger.info(f"Good Matches (>=70%):  {stats.good_matches}")
            logger.info(f"Stretch Matches (>=55%): {stats.stretch_matches}")
            logger.info(f"Total Recommended:     {stats.jobs_recommended}")

        if report_path:
            logger.info(f"Excel Report Saved:    {report_path}")

        logger.info("Top Matches Summary:")
        for idx, match in enumerate(ranked[:5], start=1):
            logger.info(
                f"  [{idx}] {match.relevance_score:.1f}% ({match.category.value}) - "
                f"{match.job.title} @ {match.job.company} [{', '.join(match.job.sources)}]"
            )

        logger.info("=" * 65)
        return final_state

    except Exception as e:
        logger.error(f"Fatal error during pipeline execution: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_pipeline()
