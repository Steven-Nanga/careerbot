"""Main entry point for the job scraper."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

import requests
import urllib3

from alerter import send_email, send_test_email
from config import SSL_VERIFY
from database import connect, has_seen, mark_seen
from matcher import match_job
from sources import (
    careersmw,
    careernova,
    fhi360,
    jhpiego,
    jobisland,
    jobsearchmalawi,
    jobsmw,
    linkedin,
    mlenje,
    mvungi,
    myjobmalawi,
    myjobo,
    ntchito,
    nyasajobs,
    palladium,
    reliefweb,
    unjobs,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
LOGGER = logging.getLogger("scraper")


def configure_http() -> None:
    if SSL_VERIFY:
        return

    original_request = requests.sessions.Session.request

    def request_with_ssl_override(self, method, url, **kwargs):
        kwargs.setdefault("verify", False)
        return original_request(self, method, url, **kwargs)

    requests.sessions.Session.request = request_with_ssl_override
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    LOGGER.warning("SSL certificate verification is disabled for this run.")


@dataclass
class SourceReport:
    name: str
    job_count: int = 0
    status: str = "ok"
    error: str = ""


SOURCES: list[tuple[str, Callable[[], list[dict]]]] = [
    ("ReliefWeb", reliefweb.scrape),
    ("MyJobMalawi", myjobmalawi.scrape),
    ("Job Search Malawi", jobsearchmalawi.scrape),
    ("CareersMW", careersmw.scrape),
    ("Nyasa Jobs", nyasajobs.scrape),
    ("Mlenje", mlenje.scrape),
    ("Ntchito", ntchito.scrape),
    ("CareerNova", careernova.scrape),
    ("MyJobo", myjobo.scrape),
    ("Jobs.mw", jobsmw.scrape),
    ("JobIsland Malawi", jobisland.scrape),
    ("Mvungi", mvungi.scrape),
    ("LinkedIn", linkedin.scrape),
    ("FHI 360", fhi360.scrape),
    ("Jhpiego", jhpiego.scrape),
    ("Palladium Group", palladium.scrape),
    ("UN Jobs", unjobs.scrape),
]


def collect_jobs() -> tuple[list[dict], list[SourceReport]]:
    all_jobs = []
    reports = []
    for source_name, scraper in SOURCES:
        try:
            LOGGER.info("Scraping %s", source_name)
            jobs = scraper()
            all_jobs.extend(jobs)
            reports.append(SourceReport(name=source_name, job_count=len(jobs)))
        except Exception as exc:
            LOGGER.warning("Failed to scrape %s; continuing with remaining sources: %s", source_name, exc)
            LOGGER.debug("Full scrape error for %s", source_name, exc_info=True)
            reports.append(SourceReport(name=source_name, status="failed", error="see log"))
    return all_jobs, reports


def find_new_matches(jobs: list[dict], *, dry_run: bool = False) -> list[dict]:
    new_matches = []
    with connect() as conn:
        for job in jobs:
            job_id = job.get("id") or job.get("url")
            if not job_id:
                LOGGER.warning("Skipping job without id/url: %s", job)
                continue
            job["id"] = job_id
            if has_seen(conn, job_id):
                continue

            match = match_job(job)
            if match.is_match:
                job["match_reason"] = match.reason
                job["match_score"] = match.score
                job["matched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                new_matches.append(job)
                LOGGER.info("Matched new job: %s (%s/100)", job.get("title"), match.score)
            elif not dry_run:
                job["match_score"] = match.score
                job["match_reason"] = match.reason
                mark_seen(conn, job)
    return new_matches


def mark_matches_seen(jobs: list[dict]) -> None:
    with connect() as conn:
        for job in jobs:
            mark_seen(conn, job)


def log_source_summary(reports: list[SourceReport], matched_count: int) -> None:
    LOGGER.info("Source health summary:")
    for report in reports:
        if report.status == "ok":
            LOGGER.info("  %s: %s jobs", report.name, report.job_count)
        else:
            LOGGER.info("  %s: failed (%s)", report.name, report.error)
    LOGGER.info("Matched jobs: %s", matched_count)


def print_dry_run_matches(jobs: list[dict]) -> None:
    if not jobs:
        print("Dry run: no new matching jobs found.")
        return
    print(f"Dry run: {len(jobs)} new matching job(s) found. No email sent and no database writes made for matches.")
    for index, job in enumerate(jobs, start=1):
        print()
        print(f"{index}. {job.get('title')} - {job.get('organisation')}")
        print(f"   Source: {job.get('source')}")
        print(f"   Location: {job.get('location') or 'Not specified'}")
        print(f"   Score: {job.get('match_score')}/100")
        print(f"   Link: {job.get('url')}")
        print(f"   Match reason: {job.get('match_reason')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape Malawi career sources and email matching jobs.")
    parser.add_argument("--dry-run", action="store_true", help="Scrape and score jobs without sending email or writing matches to the database.")
    parser.add_argument("--test-email", action="store_true", help="Send a sample CareerBot email and exit.")
    return parser.parse_args()


def main() -> None:
    configure_http()
    args = parse_args()
    if args.test_email:
        LOGGER.info("Sending CareerBot test email")
        send_test_email()
        LOGGER.info("Test email sent")
        return

    jobs, reports = collect_jobs()
    LOGGER.info("Collected %s jobs across all sources", len(jobs))
    new_matches = find_new_matches(jobs, dry_run=args.dry_run)
    LOGGER.info("Found %s new matching jobs", len(new_matches))
    log_source_summary(reports, len(new_matches))
    if args.dry_run:
        print_dry_run_matches(new_matches)
        return
    if new_matches:
        send_email(new_matches)
        mark_matches_seen(new_matches)


if __name__ == "__main__":
    main()
