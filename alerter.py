"""Email digest formatting and sending."""

from __future__ import annotations

import logging
import smtplib
import socket
from datetime import datetime
from datetime import date
from email.headerregistry import Address
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

import requests

from config import (
    ALERT_EMAIL,
    BREVO_API_KEY,
    EMAIL_FROM_NAME,
    EMAIL_PROVIDER,
    NTFY_PRIORITY,
    NTFY_TOPIC,
    NTFY_URL,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_TIMEOUT,
    SMTP_USER,
)

LOGGER = logging.getLogger(__name__)
BREVO_EMAIL_URL = "https://api.brevo.com/v3/smtp/email"
MAX_NTFY_BODY_LENGTH = 3800


class IPv4SMTP(smtplib.SMTP):
    """SMTP client that resolves/connects using IPv4 only."""

    def _get_socket(self, host, port, timeout):
        LOGGER.debug("Opening IPv4 SMTP socket to %s:%s", host, port)
        addresses = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        last_error = None
        for family, socktype, proto, _, sockaddr in addresses:
            sock = socket.socket(family, socktype, proto)
            sock.settimeout(timeout)
            try:
                sock.connect(sockaddr)
                return sock
            except OSError as exc:
                last_error = exc
                sock.close()
        if last_error:
            raise last_error
        raise OSError(f"No IPv4 address found for SMTP host {host}")


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


def _send_via_brevo(subject: str, body: str, html: str) -> None:
    if not BREVO_API_KEY:
        raise RuntimeError("BREVO_API_KEY is not set; cannot send email through Brevo.")

    payload = {
        "sender": {"name": EMAIL_FROM_NAME, "email": SMTP_USER},
        "to": [{"email": ALERT_EMAIL}],
        "subject": subject,
        "textContent": body,
        "htmlContent": html,
    }
    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }
    LOGGER.info("Sending email through Brevo API to %s", ALERT_EMAIL)
    response = requests.post(BREVO_EMAIL_URL, json=payload, headers=headers, timeout=SMTP_TIMEOUT)
    if response.status_code >= 400:
        LOGGER.error("Brevo API rejected email with HTTP %s: %s", response.status_code, response.text)
        response.raise_for_status()
    LOGGER.info("Brevo accepted email for delivery: %s", response.text)


def _send_via_smtp(subject: str, body: str, html: str) -> None:
    if not SMTP_PASSWORD:
        raise RuntimeError("SMTP_PASSWORD is not set; cannot send email through SMTP.")

    message = MIMEMultipart("alternative")
    message["From"] = str(Address(display_name=EMAIL_FROM_NAME, addr_spec=SMTP_USER))
    message["To"] = ALERT_EMAIL
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))
    message.attach(MIMEText(html, "html", "utf-8"))

    LOGGER.info("Sending email digest to %s through SMTP", ALERT_EMAIL)
    LOGGER.info("Connecting to SMTP server %s:%s as %s", SMTP_HOST, SMTP_PORT, SMTP_USER)
    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)
    except OSError as exc:
        LOGGER.warning("SMTP connection failed over default network path: %s", exc)
        LOGGER.info("Retrying SMTP connection over IPv4")
        server = IPv4SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT)

    with server:
        server.starttls()
        LOGGER.info("SMTP TLS started")
        server.login(SMTP_USER, SMTP_PASSWORD)
        LOGGER.info("SMTP login accepted")
        server.sendmail(SMTP_USER, [ALERT_EMAIL], message.as_string())
        LOGGER.info("Email sent successfully to %s", ALERT_EMAIL)


def _build_ntfy_body(jobs: list[dict], body: str) -> str:
    lines = body.splitlines()
    if len(body) <= MAX_NTFY_BODY_LENGTH:
        return body

    compact = [
        lines[0] if lines else "Hi Steven,",
        "",
        f"{len(jobs)} new matching job(s) found.",
        "",
    ]
    for index, job in enumerate(jobs[:10], start=1):
        compact.extend(
            [
                f"{index}. {job.get('title', 'Untitled role')} - {job.get('organisation', 'Unknown organisation')}",
                f"   Score: {job.get('match_score') or 'N/A'}/100",
                f"   Link: {job.get('url')}",
                "",
            ]
        )
    remaining = len(jobs) - 10
    if remaining > 0:
        compact.append(f"...and {remaining} more role(s).")
    return "\n".join(compact)


def _send_via_ntfy(subject: str, body: str, jobs: list[dict]) -> None:
    if not NTFY_TOPIC:
        raise RuntimeError("NTFY_TOPIC is not set; cannot send notification through ntfy.")

    url = f"{NTFY_URL.rstrip('/')}/{NTFY_TOPIC}"
    headers = {
        "Title": subject,
        "Priority": NTFY_PRIORITY,
        "Tags": "briefcase",
    }
    first_url = jobs[0].get("url") if jobs else ""
    if first_url:
        headers["Click"] = str(first_url)

    LOGGER.info("Sending notification through ntfy topic %s", NTFY_TOPIC)
    response = requests.post(
        url,
        data=_build_ntfy_body(jobs, body).encode("utf-8"),
        headers=headers,
        timeout=SMTP_TIMEOUT,
    )
    if response.status_code >= 400:
        LOGGER.error("ntfy rejected notification with HTTP %s: %s", response.status_code, response.text)
        response.raise_for_status()
    LOGGER.info("ntfy accepted notification: %s", response.text)


def send_email(jobs: list[dict]) -> None:
    if not jobs:
        LOGGER.info("No matching jobs to email.")
        return

    subject, body, html = build_digest(jobs)
    if EMAIL_PROVIDER == "brevo":
        _send_via_brevo(subject, body, html)
        return
    if EMAIL_PROVIDER == "ntfy":
        _send_via_ntfy(subject, body, jobs)
        return
    _send_via_smtp(subject, body, html)


def send_test_email() -> None:
    send_email([build_test_job()])
