"""Job Search Malawi scraper."""

from __future__ import annotations

import logging
import shutil
import subprocess
from urllib.parse import urlencode, urljoin
from xml.etree import ElementTree

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT
from sources.html_helpers import extract_jobs_from_cards
from sources.request_helpers import AJAX_HEADERS, DEFAULT_HEADERS

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://jobsearchmalawi.com"
JOBS_URL = f"{BASE_URL}/"
AJAX_URL = f"{BASE_URL}/jm-ajax/get_listings/"
SEARCH_TERMS = (
    "data",
    "database",
    "monitoring evaluation",
    "MEL",
    "research",
    "statistics",
    "business intelligence",
)


def scrape() -> list[dict]:
    jobs = scrape_feed_jobs()
    if jobs:
        LOGGER.info("Job Search Malawi returned %s jobs via RSS search feeds", len(jobs))
        return jobs

    jobs = scrape_ajax_jobs()
    if jobs:
        LOGGER.info("Job Search Malawi returned %s jobs via AJAX", len(jobs))
        return jobs

    try:
        response = requests.get(
            JOBS_URL,
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except Exception as exc:
        LOGGER.warning("Job Search Malawi could not be reached: %s", exc)
        return []
    soup = BeautifulSoup(response.text, "html.parser")
    jobs = extract_jobs_from_cards(
        soup,
        base_url=BASE_URL,
        source_name="Job Search Malawi",
        default_organisation="Job Search Malawi",
    )
    LOGGER.info("Job Search Malawi returned %s jobs", len(jobs))
    return jobs


def scrape_ajax_jobs() -> list[dict]:
    jobs = []
    seen_urls = set()
    response_text = fetch_text(AJAX_URL)
    if not response_text:
        return jobs

    parsed_jobs = parse_ajax_response(response_text)
    for job in parsed_jobs:
        if job["id"] in seen_urls:
            continue
        seen_urls.add(job["id"])
        jobs.append(job)
    return jobs


def scrape_feed_jobs() -> list[dict]:
    jobs = []
    seen_urls = set()
    for term in SEARCH_TERMS:
        feed_url = f"{BASE_URL}/?{urlencode({'feed': 'job_feed', 'search_keywords': term})}"
        response_text = fetch_text(feed_url)
        if not response_text:
            continue
        parsed_jobs = parse_rss_response(response_text)
        for job in parsed_jobs:
            if job["id"] in seen_urls:
                continue
            seen_urls.add(job["id"])
            jobs.append(job)
    return jobs


def fetch_text(url: str) -> str:
    try:
        response = requests.get(
            url,
            headers=DEFAULT_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.text
    except Exception as exc:
        LOGGER.debug("Requests fetch failed for %s: %s", url, exc)

    return fetch_text_with_curl(url)


def fetch_text_with_curl(url: str) -> str:
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if not curl:
        LOGGER.debug("curl is not available for Job Search Malawi fallback")
        return ""

    command = [
        curl,
        "-L",
        "-k",
        "--tlsv1.2",
        "--max-time",
        str(REQUEST_TIMEOUT),
        url,
    ]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except Exception as exc:
        LOGGER.debug("curl fetch failed for %s: %s", url, exc)
        return ""

    if result.returncode != 0:
        LOGGER.debug("curl returned %s for %s: %s", result.returncode, url, result.stderr.strip())
        return ""
    return result.stdout


def parse_ajax_response(response_text: str) -> list[dict]:
    try:
        payload = requests.models.complexjson.loads(response_text)
        html = payload.get("html", "")
    except ValueError:
        html = response_text
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for listing in soup.select("li.job_listing, .job_listing, article, li"):
        link = listing.select_one("a[href*='/job/']")
        if not link:
            continue
        url = urljoin(BASE_URL, link.get("href", ""))
        title = _clean(listing.select_one("h3")) or _clean(link)
        company = _clean(listing.select_one(".company strong, .company"))
        location = _clean(listing.select_one(".location"))
        closing_date = _clean(listing.select_one("time"))
        jobs.append(
            {
                "id": f"job-search-malawi:{url}",
                "title": title,
                "organisation": company or "Job Search Malawi",
                "location": location,
                "closing_date": closing_date,
                "url": url,
                "description": _clean(listing),
                "source": "Job Search Malawi",
            }
        )
    return jobs


def parse_rss_response(response_text: str) -> list[dict]:
    try:
        root = ElementTree.fromstring(response_text.encode("utf-8"))
    except ElementTree.ParseError as exc:
        LOGGER.debug("Job Search Malawi RSS parse failed: %s", exc)
        return []

    namespace = {"content": "http://purl.org/rss/1.0/modules/content/"}
    jobs = []
    for item in root.findall(".//item"):
        title = _element_text(item, "title")
        url = _element_text(item, "link")
        description = _element_text(item, "description")
        content = _element_text(item, "content:encoded", namespace)
        text = _clean_html(f"{description}\n{content}")
        if not title or not url:
            continue
        jobs.append(
            {
                "id": f"job-search-malawi:{url}",
                "title": title,
                "organisation": "Job Search Malawi",
                "location": "Malawi",
                "closing_date": "",
                "url": url,
                "description": text,
                "source": "Job Search Malawi",
            }
        )
    return jobs


def _element_text(item: ElementTree.Element, tag: str, namespace: dict | None = None) -> str:
    node = item.find(tag, namespace or {})
    return (node.text or "").strip() if node is not None else ""


def _clean(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def _clean_html(html: str) -> str:
    return " ".join(BeautifulSoup(html, "html.parser").get_text(" ", strip=True).split())
