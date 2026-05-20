"""ReliefWeb scraper.

The official API is preferred, but ReliefWeb now rejects unapproved app names
with 403 responses. When that happens, fall back to the public jobs RSS feed.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

import feedparser
import requests
from bs4 import BeautifulSoup

from config import RELIEFWEB_ENDPOINT, RELIEFWEB_PROFILE, REQUEST_TIMEOUT, USER_AGENT
from sources.request_helpers import BROWSER_HEADERS

LOGGER = logging.getLogger(__name__)
RSS_URL = "https://reliefweb.int/jobs/rss.xml?search=Malawi"


def _clean_html(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(BeautifulSoup(value, "html.parser").get_text(" ", strip=True).split())


def _child_text(item: ET.Element, tag: str) -> str:
    node = item.find(tag)
    return (node.text or "").strip() if node is not None else ""


def _namespaced_text(item: ET.Element, namespace: str, tag: str) -> str:
    node = item.find(f"{{{namespace}}}{tag}")
    return (node.text or "").strip() if node is not None else ""


def _closing_date_from_text(text: str) -> str:
    match = re.search(r"(?:closing date|deadline|apply by)[:\s-]+([^.;\n]+)", text, re.I)
    return match.group(1).strip() if match else ""


def _api_jobs() -> list[dict]:
    params = {
        "appname": RELIEFWEB_PROFILE,
        "profile": "list",
        "limit": 50,
        "preset": "latest",
        "query[value]": "Malawi",
        "filter[operator]": "AND",
        "filter[conditions][0][field]": "country",
        "filter[conditions][0][value]": "Malawi",
        "fields[include][]": [
            "id",
            "title",
            "url",
            "source.name",
            "country.name",
            "city.name",
            "date.closing",
            "body",
        ],
    }
    response = requests.get(
        RELIEFWEB_ENDPOINT,
        params=params,
        headers={"User-Agent": USER_AGENT},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    jobs = []
    for item in response.json().get("data", []):
        fields = item.get("fields", {})
        source_names = [source.get("name", "") for source in fields.get("source", [])]
        countries = [country.get("name", "") for country in fields.get("country", [])]
        cities = [city.get("name", "") for city in fields.get("city", [])]
        jobs.append(
            {
                "id": f"reliefweb:{item.get('id')}",
                "title": fields.get("title", "Untitled role"),
                "organisation": ", ".join(filter(None, source_names)) or "ReliefWeb",
                "location": ", ".join(filter(None, cities + countries)),
                "closing_date": (fields.get("date") or {}).get("closing"),
                "url": fields.get("url") or f"https://reliefweb.int/job/{item.get('id')}",
                "description": fields.get("body", ""),
                "source": "ReliefWeb",
            }
        )
    LOGGER.info("ReliefWeb API returned %s jobs", len(jobs))
    return jobs


def _rss_jobs() -> list[dict]:
    response = requests.get(
        RSS_URL,
        headers=BROWSER_HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    root = ET.fromstring(response.content)
    content_ns = "http://purl.org/rss/1.0/modules/content/"
    dc_ns = "http://purl.org/dc/elements/1.1/"
    jobs = []
    for item in root.findall("./channel/item"):
        title = _child_text(item, "title") or "Untitled role"
        url = _child_text(item, "link")
        guid = _child_text(item, "guid") or url
        description_html = (
            _namespaced_text(item, content_ns, "encoded")
            or _child_text(item, "description")
        )
        description = _clean_html(description_html)
        organisation = _namespaced_text(item, dc_ns, "creator") or "ReliefWeb"
        categories = [
            (node.text or "").strip()
            for node in item.findall("category")
            if (node.text or "").strip()
        ]
        location = "Malawi" if "malawi" in " ".join([title, description, *categories]).lower() else ""
        jobs.append(
            {
                "id": f"reliefweb:{guid}",
                "title": title,
                "organisation": organisation,
                "location": location,
                "closing_date": _closing_date_from_text(description),
                "url": url,
                "description": description,
                "source": "ReliefWeb",
            }
        )
    LOGGER.info("ReliefWeb RSS fallback returned %s jobs", len(jobs))
    return jobs


def _rss_jobs_tolerant() -> list[dict]:
    response = requests.get(
        RSS_URL,
        headers=BROWSER_HEADERS,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    feed = feedparser.parse(response.content)
    jobs = []
    for entry in feed.entries:
        title = getattr(entry, "title", "") or "Untitled role"
        url = getattr(entry, "link", "")
        guid = getattr(entry, "id", "") or getattr(entry, "guid", "") or url
        description_html = getattr(entry, "summary", "") or getattr(entry, "description", "")
        if not description_html and getattr(entry, "content", None):
            description_html = entry.content[0].get("value", "")
        description = _clean_html(description_html)
        organisation = getattr(entry, "author", "") or "ReliefWeb"
        tags = [tag.get("term", "") for tag in getattr(entry, "tags", [])]
        location = "Malawi" if "malawi" in " ".join([title, description, *tags]).lower() else ""
        jobs.append(
            {
                "id": f"reliefweb:{guid}",
                "title": title,
                "organisation": organisation,
                "location": location,
                "closing_date": _closing_date_from_text(description),
                "url": url,
                "description": description,
                "source": "ReliefWeb",
            }
        )
    LOGGER.info("ReliefWeb tolerant RSS fallback returned %s jobs", len(jobs))
    return jobs


def scrape() -> list[dict]:
    try:
        return _api_jobs()
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        LOGGER.warning(
            "ReliefWeb API failed with HTTP %s; using RSS fallback instead",
            status_code,
        )
    except requests.RequestException as exc:
        LOGGER.warning("ReliefWeb API request failed; using RSS fallback instead: %s", exc)

    try:
        return _rss_jobs()
    except requests.RequestException as exc:
        LOGGER.warning("ReliefWeb RSS fallback is unavailable; skipping source: %s", exc)
    except ET.ParseError as exc:
        LOGGER.warning("ReliefWeb RSS fallback returned invalid XML; trying tolerant parser: %s", exc)
        try:
            return _rss_jobs_tolerant()
        except requests.RequestException as tolerant_exc:
            LOGGER.warning("ReliefWeb tolerant RSS fallback is unavailable; skipping source: %s", tolerant_exc)
    return []
