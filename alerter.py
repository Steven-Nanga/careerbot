"""Email digest formatting and sending."""

from __future__ import annotations

import logging
import smtplib
from datetime import datetime
from datetime import date
from email.headerregistry import Address
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from config import (
    ALERT_EMAIL,
    EMAIL_FROM_NAME,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_TIMEOUT,
    SMTP_USER,
)

LOGGER = logging.getLogger(__name__)


def build_digest(jobs: list[dict]) -> tuple[str, str, str]:
    today = date.today().isoformat()
    count = len(jobs)
    subject = f"[Job Alert] {count} New Roles Matching Your Profile - {today}"

    lines = [
        "Hi Steven,",
        "",
        f"{count} new role(s) were found matching your profile today.",
        "",
    ]
    for index, job in enumerate(jobs, start=1):
        lines.extend(
            [
                f"{index}. {job.get('title', 'Untitled role')} - {job.get('organisation', 'Unknown organisation')}",
                f"   Location: {job.get('location') or 'Not specified'}",
                f"   Closing Date: {job.get('closing_date') or 'Not specified'}",
                f"   Link: {job.get('url')}",
                f"   Match reason: {job.get('match_reason')}",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "This alert was generated automatically by your job scraper.",
        ]
    )
    rows = []
    for index, job in enumerate(jobs, start=1):
        rows.append(
            f"""
            <tr>
              <td>{index}</td>
              <td><strong>{escape(str(job.get('title', 'Untitled role')))}</strong><br>
                  <span>{escape(str(job.get('organisation') or 'Unknown organisation'))}</span></td>
              <td>{escape(str(job.get('location') or 'Not specified'))}</td>
              <td>{escape(str(job.get('closing_date') or 'Not specified'))}</td>
              <td><strong>{escape(str(job.get('match_score') or ''))}/100</strong></td>
              <td>{escape(str(job.get('match_reason') or ''))}</td>
              <td><a href="{escape(str(job.get('url') or ''))}">Open</a></td>
            </tr>
            """
        )

    html = f"""
    <!doctype html>
    <html>
      <body style="font-family: Arial, sans-serif; color: #1f2937;">
        <h2 style="margin-bottom: 4px;">CareerBot Job Alert</h2>
        <p>{count} new role(s) were found matching your profile today.</p>
        <table cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 14px;">
          <thead>
            <tr style="background: #f3f4f6;">
              <th align="left">#</th>
              <th align="left">Role</th>
              <th align="left">Location</th>
              <th align="left">Closing Date</th>
              <th align="left">Score</th>
              <th align="left">Match Reason</th>
              <th align="left">Link</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows)}
          </tbody>
        </table>
        <p style="margin-top: 24px; color: #6b7280;">This alert was generated automatically by CareerBot.</p>
      </body>
    </html>
    """
    return subject, "\n".join(lines), html


def build_test_job() -> dict:
    return {
        "title": "Test Data Analyst Role",
        "organisation": "CareerBot Test",
        "location": "Malawi / Remote",
        "closing_date": datetime.now().date().isoformat(),
        "url": "https://example.com/test-job",
        "match_score": 99,
        "match_reason": "Score: 99/100; Primary: Data Analyst; Supporting: Power BI, SQL; Resume: Data Analysis",
    }


def send_email(jobs: list[dict]) -> None:
    if not jobs:
        LOGGER.info("No matching jobs to email.")
        return
    if not SMTP_PASSWORD:
        raise RuntimeError("SMTP_PASSWORD is not set; cannot send email.")

    subject, body, html = build_digest(jobs)
    message = MIMEMultipart("alternative")
    message["From"] = str(Address(display_name=EMAIL_FROM_NAME, addr_spec=SMTP_USER))
    message["To"] = ALERT_EMAIL
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))
    message.attach(MIMEText(html, "html", "utf-8"))

    LOGGER.info("Sending email digest with %s jobs to %s", len(jobs), ALERT_EMAIL)
    LOGGER.info("Connecting to SMTP server %s:%s as %s", SMTP_HOST, SMTP_PORT, SMTP_USER)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as server:
        server.starttls()
        LOGGER.info("SMTP TLS started")
        server.login(SMTP_USER, SMTP_PASSWORD)
        LOGGER.info("SMTP login accepted")
        server.sendmail(SMTP_USER, [ALERT_EMAIL], message.as_string())
        LOGGER.info("Email sent successfully to %s", ALERT_EMAIL)


def send_test_email() -> None:
    send_email([build_test_job()])
