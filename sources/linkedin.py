"""Public LinkedIn jobs search scraper.

LinkedIn heavily limits automated access. This scraper uses public guest search
pages only and does not log in, bypass access controls, or automate a browser.
It may return no results if LinkedIn blocks or changes the guest page markup.
"""

from __future__ import annotations

import logging
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

from config import LINKEDIN_SEARCH_TERMS, REQUEST_TIMEOUT, USER_AGENT
from sources.html_helpers import clean_text, first_text

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://www.linkedin.com"
SEARCH_URL = f"{BASE_URL}/jobs-guest/jobs/api/seeMoreJobPostings/search"


def _search(term: str) -> list[dict]:
    params = {
        "keywords": term,
        "location": "Malawi",
        "start": 0,
    }
    response = requests.get(
        f"{SEARCH_URL}?{urlencode(params)}",
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    cards = soup.select(".job-search-card, .base-card, li")

    jobs = []
    seen_urls = set()
    for card in cards:
        link = card.select_one("a[href]")
        if not link:
            continue
        url = urljoin(BASE_URL, link.get("href", "")).split("?")[0]
        if not url or url in seen_urls:
            continue
        title = first_text(card, (".base-search-card__title", "h3", "a")) or clean_text(link)
        organisation = first_text(card, (".base-search-card__subtitle", "h4"))
        location = first_text(card, (".job-search-card__location", ".job-result-card__location"))
        description = clean_text(card)
        if not title:
            continue

        seen_urls.add(url)
        jobs.append(
            {
                "id": f"linkedin:{url}",
                "title": title,
                "organisation": organisation or "LinkedIn",
                "location": location or "Malawi",
                "closing_date": "",
                "url": url,
                "description": description,
                "source": "LinkedIn",
            }
        )
    return jobs


def scrape() -> list[dict]:
    all_jobs = []
    seen_ids = set()
    for term in LINKEDIN_SEARCH_TERMS:
        try:
            for job in _search(term):
                if job["id"] in seen_ids:
                    continue
                seen_ids.add(job["id"])
                all_jobs.append(job)
        except Exception:
            LOGGER.exception("LinkedIn search failed for term %r", term)
    LOGGER.info("LinkedIn returned %s jobs", len(all_jobs))
    return all_jobs
