"""FHI 360 careers scraper."""

from __future__ import annotations

import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, USER_AGENT

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://www.fhi360.org"
CAREERS_URL = f"{BASE_URL}/careers"


def scrape() -> list[dict]:
    response = requests.get(
        CAREERS_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    candidates = soup.select("a[href*='job'], a[href*='career'], a[href*='greenhouse'], a[href*='workday']")

    jobs = []
    seen_urls = set()
    for link in candidates:
        title = " ".join(link.get_text(" ", strip=True).split())
        url = urljoin(BASE_URL, link.get("href", ""))
        context = " ".join((link.parent.get_text(" ", strip=True) if link.parent else title).split())
        if not title or url in seen_urls:
            continue
        if "malawi" not in context.lower() and "malawi" not in title.lower():
            continue
        seen_urls.add(url)
        jobs.append(
            {
                "id": f"fhi360:{url}",
                "title": title,
                "organisation": "FHI 360",
                "location": "Malawi",
                "closing_date": "",
                "url": url,
                "description": context,
                "source": "FHI 360",
            }
        )
    LOGGER.info("FHI 360 returned %s Malawi jobs", len(jobs))
    return jobs
