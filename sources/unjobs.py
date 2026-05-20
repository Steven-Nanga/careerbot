"""UN Jobs Malawi scraper."""

from __future__ import annotations

import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, USER_AGENT

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://unjobs.org"
MALAWI_URL = f"{BASE_URL}/duty_stations/malawi"


def _text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def scrape() -> list[dict]:
    response = requests.get(
        MALAWI_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.select(".job, .jtitle, li, tr")

    jobs = []
    seen_urls = set()
    for row in rows:
        link = row.select_one("a[href]")
        if not link:
            continue
        title = _text(link)
        url = urljoin(BASE_URL, link.get("href", ""))
        context = _text(row)
        if not title or url in seen_urls:
            continue
        if title.lower().strip() in {"next", "next >", "previous", "< previous"}:
            continue
        if "/duty_stations/" in url:
            continue
        if "/jobs/" not in url and "/vacancies/" not in url and "/organizations/" in url:
            continue
        seen_urls.add(url)
        jobs.append(
            {
                "id": f"unjobs:{url}",
                "title": title,
                "organisation": "UN Jobs",
                "location": "Malawi",
                "closing_date": "",
                "url": url,
                "description": context,
                "source": "UN Jobs",
            }
        )
    LOGGER.info("UN Jobs returned %s jobs", len(jobs))
    return jobs
