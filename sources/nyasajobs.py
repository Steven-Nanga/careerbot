"""Nyasa Jobs scraper."""

from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup

from config import REQUEST_TIMEOUT, USER_AGENT
from sources.html_helpers import extract_jobs_from_cards

LOGGER = logging.getLogger(__name__)
BASE_URL = "https://nyasajobs.com"
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
        source_name="Nyasa Jobs",
        default_organisation="Nyasa Jobs",
    )
    LOGGER.info("Nyasa Jobs returned %s jobs", len(jobs))
    return jobs
