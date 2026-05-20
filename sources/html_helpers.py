"""Shared helpers for static HTML job-board scrapers."""

from __future__ import annotations

from urllib.parse import urljoin


JOB_CARD_SELECTORS = (
    "article",
    ".job",
    ".job-listing",
    ".job_listing",
    ".type-job_listing",
    ".vacancy",
    ".vacancies",
    ".post",
    ".entry",
    "li",
)

TITLE_SELECTORS = (
    "h1",
    "h2",
    "h3",
    ".entry-title",
    ".job-title",
    ".job_title",
    ".vacancy-title",
    ".title",
)

ORG_SELECTORS = (
    ".company",
    ".company-name",
    ".job-company",
    ".employer",
    ".organisation",
    ".organization",
)

LOCATION_SELECTORS = (
    ".location",
    ".job-location",
    ".job_location",
    ".vacancy-location",
)

DATE_SELECTORS = (
    ".closing-date",
    ".deadline",
    ".date",
    ".job-date",
    "time",
)

SKIP_TITLES = {
    "jobs",
    "job industries",
    "next",
    "next >",
    "previous",
    "< previous",
    "prev",
    "home",
}

SKIP_URL_PARTS = (
    "/job-tag/",
    "/tag/",
    "/category/",
    "/categories/",
    "/job-category/",
)


def clean_text(node) -> str:
    return " ".join(node.get_text(" ", strip=True).split()) if node else ""


def first_text(card, selectors: tuple[str, ...]) -> str:
    for selector in selectors:
        text = clean_text(card.select_one(selector))
        if text:
            return text
    return ""


def extract_jobs_from_cards(
    soup,
    *,
    base_url: str,
    source_name: str,
    default_organisation: str,
    card_selectors: tuple[str, ...] = JOB_CARD_SELECTORS,
    require_malawi: bool = False,
) -> list[dict]:
    jobs = []
    seen_urls = set()
    cards = soup.select(", ".join(card_selectors))

    for card in cards:
        link = card.select_one("a[href]")
        if not link:
            continue

        url = urljoin(base_url, link.get("href", ""))
        if not url or url in seen_urls:
            continue

        title = first_text(card, TITLE_SELECTORS) or clean_text(link)
        description = clean_text(card)
        if not title or len(title) < 4:
            continue
        lowered_title = title.lower().strip()
        lowered_url = url.lower()
        if lowered_title in SKIP_TITLES or any(part in lowered_url for part in SKIP_URL_PARTS):
            continue
        if lowered_title.endswith(" jobs") and "apply" not in description.lower():
            continue
        if require_malawi and "malawi" not in f"{title} {description} {url}".lower():
            continue

        seen_urls.add(url)
        jobs.append(
            {
                "id": f"{source_name.lower().replace(' ', '-')}:{url}",
                "title": title,
                "organisation": first_text(card, ORG_SELECTORS) or default_organisation,
                "location": first_text(card, LOCATION_SELECTORS),
                "closing_date": first_text(card, DATE_SELECTORS),
                "url": url,
                "description": description,
                "source": source_name,
            }
        )

    return jobs
