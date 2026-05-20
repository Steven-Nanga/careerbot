"""CareersMW scraper."""

from __future__ import annotations

import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT
from sources.html_helpers import clean_text, extract_jobs_from_cards
from sources.request_helpers import BROWSER_HEADERS

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://careersmw.com"
JOBS_URL = f"{BASE_URL}/"


def scrape() -> list[dict]:
    response = requests.get(
        JOBS_URL,
        headers=BROWSER_HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    jobs = scrape_featured_jobs(soup)
    if not jobs:
        jobs = extract_jobs_from_cards(
            soup,
            base_url=BASE_URL,
            source_name="CareersMW",
            default_organisation="CareersMW",
        )
    LOGGER.info("CareersMW returned %s jobs", len(jobs))
    return jobs


def scrape_featured_jobs(soup: BeautifulSoup) -> list[dict]:
    jobs = []
    seen_urls = set()
    for link in soup.select("a[href*='/job/']"):
        url = urljoin(BASE_URL, link.get("href", ""))
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        job = scrape_job_detail(url, clean_text(link))
        if job:
            jobs.append(job)
    return jobs


def scrape_job_detail(url: str, fallback_title: str = "") -> dict | None:
    response = requests.get(
        url,
        headers=BROWSER_HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    title = clean_text(soup.select_one("h1.entry-title, h1")) or fallback_title
    if not title:
        return None

    content = soup.select_one("article, .entry-content, main") or soup
    lines = [clean_text(node) for node in content.select("li")]
    location = next((line for line in lines if "malawi" in line.lower()), "")
    logo = content.select_one(".entry-content img[alt], article img[alt]")
    organisation = logo.get("alt", "").strip() if logo else ""
    if not organisation:
        organisation = clean_text(content.select_one(".company, .job-company"))
    if not organisation:
        paragraphs = [clean_text(node) for node in content.select("p") if clean_text(node)]
        organisation = paragraphs[0] if paragraphs else "CareersMW"

    return {
        "id": f"careersmw:{url}",
        "title": title,
        "organisation": organisation,
        "location": location,
        "closing_date": "",
        "url": url,
        "description": clean_text(content),
        "source": "CareersMW",
    }
