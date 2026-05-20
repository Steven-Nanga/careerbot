"""MyJobMalawi static HTML scraper."""

from __future__ import annotations

import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, USER_AGENT

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://www.myjobmalawi.com"
SEARCH_URL = f"{BASE_URL}/jobs/"


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def scrape() -> list[dict]:
    try:
        response = requests.get(
            SEARCH_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.warning("MyJobMalawi is unavailable; skipping source: %s", exc)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.select("article, .job_listing, .job-listing, .job, .type-job_listing")

    jobs = []
    for card in cards:
        link = card.select_one("a[href]")
        title_node = card.select_one("h1, h2, h3, .job-title, .entry-title") or link
        url = urljoin(BASE_URL, link["href"]) if link else SEARCH_URL
        title = _text(title_node)
        if not title or not url:
            continue
        organisation = _text(card.select_one(".company, .company-name, .job-company"))
        location = _text(card.select_one(".location, .job-location"))
        description = _text(card)
        jobs.append(
            {
                "id": f"myjobmalawi:{url}",
                "title": title,
                "organisation": organisation or "MyJobMalawi",
                "location": location,
                "closing_date": "",
                "url": url,
                "description": description,
                "source": "MyJobMalawi",
            }
        )
    LOGGER.info("MyJobMalawi returned %s jobs", len(jobs))
    return jobs
