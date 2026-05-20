"""CareerNova jobs scraper."""

from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, USER_AGENT
from sources.html_helpers import extract_jobs_from_cards

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://careernova.net"
JOBS_URL = f"{BASE_URL}/"


def scrape() -> list[dict]:
    response = requests.get(
        JOBS_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    jobs = extract_jobs_from_cards(
        soup,
        base_url=BASE_URL,
        source_name="CareerNova",
        default_organisation="CareerNova",
    )
    LOGGER.info("CareerNova returned %s jobs", len(jobs))
    return jobs
