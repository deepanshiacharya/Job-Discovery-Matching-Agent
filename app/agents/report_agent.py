import logging
from typing import List, Tuple
from app.config import settings
from app.matching.schema import JobMatch, PipelineRunStats
from app.reports.excel import ExcelReportGenerator
from app.reports.email import get_email_service, build_email_content

logger = logging.getLogger(__name__)


class ReportAgent:
    """Orchestrates Excel generation and automated email distribution."""

    def __init__(self):
        self.excel_gen = ExcelReportGenerator()
        self.email_service = get_email_service()

    def generate_and_deliver(
        self,
        ranked_matches: List[JobMatch],
        top_matches: List[JobMatch],
        stats: PipelineRunStats
    ) -> Tuple[str, bool]:
        """Generate Excel file and send email notification.

        Returns:
            (report_path: str, email_sent: bool)
        """
        # 1. Generate Excel
        report_path = self.excel_gen.generate_report(ranked_matches, stats)

        # 2. Build and dispatch Email
        subject, body = build_email_content(stats, top_matches)
        recipient = settings.RECIPIENT_EMAIL

        email_sent = False
        try:
            email_sent = self.email_service.send_email(
                recipient=recipient,
                subject=subject,
                body=body,
                attachment_path=report_path
            )
        except Exception as e:
            logger.error(f"Email delivery encountered an error: {e}", exc_info=True)

        return report_path, email_sent
