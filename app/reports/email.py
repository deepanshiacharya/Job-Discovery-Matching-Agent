import email
import logging
import smtplib
from abc import ABC, abstractmethod
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import List, Optional, Tuple

from app.config import settings
from app.matching.schema import JobMatch, PipelineRunStats

logger = logging.getLogger(__name__)


class EmailService(ABC):
    """Abstract email service interface."""

    @abstractmethod
    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None
    ) -> bool:
        pass


class SMTPEmailService(EmailService):
    """Production SMTP Email sender supporting TLS and file attachments."""

    def __init__(
        self,
        host: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        from_addr: str = None
    ):
        self.host = host or settings.EMAIL_HOST
        self.port = port or settings.EMAIL_PORT
        self.username = username or settings.EMAIL_USERNAME
        self.password = password or settings.EMAIL_PASSWORD
        self.from_addr = from_addr or settings.EMAIL_FROM

    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None
    ) -> bool:
        if not self.username or not self.password:
            logger.warning("SMTP credentials not configured. Please set EMAIL_USERNAME and EMAIL_PASSWORD.")
            return False

        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_addr
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain", "utf-8"))

            if attachment_path and Path(attachment_path).exists():
                path = Path(attachment_path)
                with open(path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f'attachment; filename="{path.name}"'
                )
                msg.attach(part)

            logger.info(f"Connecting to SMTP server {self.host}:{self.port}...")
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"Email successfully delivered to {recipient}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email via SMTP to {recipient}: {e}", exc_info=True)
            return False


class MockEmailService(EmailService):
    """Mock email service that logs delivery and persists notification summaries locally."""

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or settings.get_absolute_report_dir()

    def send_email(
        self,
        recipient: str,
        subject: str,
        body: str,
        attachment_path: Optional[str] = None
    ) -> bool:
        logger.info(f"[MOCK EMAIL] Simulating dispatch to: {recipient}")
        logger.info(f"[MOCK EMAIL] Subject: {subject}")
        logger.info(f"[MOCK EMAIL] Attachment: {attachment_path}")

        # Save email log artifact
        date_str = datetime.utcnow().strftime("%Y-%m-%d_%H%M%S")
        email_preview_file = self.log_dir / f"email_preview_{date_str}.txt"
        with open(email_preview_file, "w", encoding="utf-8") as f:
            f.write(f"TO: {recipient}\n")
            f.write(f"SUBJECT: {subject}\n")
            f.write(f"ATTACHMENT: {attachment_path}\n")
            f.write("=" * 60 + "\n\n")
            f.write(body)

        logger.info(f"[MOCK EMAIL] Preview saved to {email_preview_file}")
        return True


def get_email_service() -> EmailService:
    """Factory creating configured email delivery backend."""
    if settings.EMAIL_PROVIDER.lower() == "smtp" and settings.EMAIL_USERNAME:
        return SMTPEmailService()
    return MockEmailService()


def build_email_content(stats: PipelineRunStats, top_matches: List[JobMatch]) -> Tuple[str, str]:
    """Assemble structured daily email subject and text body."""
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    subject = f"Daily Job Matches — {date_str}"

    lines = [
        f"Jobs discovered: {stats.jobs_discovered}",
        f"Relevant jobs: {stats.jobs_recommended}",
        f"High matches: {stats.high_matches}",
        "",
        "Top opportunities:",
    ]

    for idx, match in enumerate(top_matches, start=1):
        lines.append(
            f"{idx}. {match.job.title} — {match.job.company} — {match.relevance_score:.0f}%"
        )

    lines.extend([
        "",
        "Full results are attached in Excel."
    ])

    body = "\n".join(lines)
    return subject, body
