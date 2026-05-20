"""JobIsland Malawi scraper."""

from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, USER_AGENT
from sources.html_helpers import extract_jobs_from_cards

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://mw.jobisland.com"
JOBS_URL = f"{BASE_URL}/"


def scrape() -> list[dict]:
    try:
        response = requests.get(
            JOBS_URL,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        LOGGER.warning("JobIsland Malawi is unavailable; skipping source: %s", exc)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    jobs = extract_jobs_from_cards(
        soup,
        base_url=BASE_URL,
        source_name="JobIsland Malawi",
        default_organisation="JobIsland Malawi",
        require_malawi=False,
    )
    LOGGER.info("JobIsland Malawi returned %s jobs", len(jobs))
    return jobs
