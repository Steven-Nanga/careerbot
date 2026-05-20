"""Keyword matching logic for job records."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from config import PRIMARY_KEYWORDS, RESUME_SCORE_ALERT_THRESHOLD, SECONDARY_KEYWORDS
from resume_profile import get_resume_terms


@dataclass(frozen=True)
class MatchResult:
    is_match: bool
    primary_matches: list[str]
    secondary_matches: list[str]
    resume_matches: list[str]
    title_matches: list[str]
    score: int

    @property
    def reason(self) -> str:
        parts = []
        parts.append(f"Score: {self.score}/100")
        if self.title_matches:
            parts.append(f"Title: {', '.join(self.title_matches)}")
        if self.primary_matches:
            parts.append(f"Primary: {', '.join(self.primary_matches)}")
        if self.secondary_matches:
            parts.append(f"Supporting: {', '.join(self.secondary_matches)}")
        if self.resume_matches:
            parts.append(f"Resume: {', '.join(self.resume_matches[:8])}")
        return "; ".join(parts)


def _contains_keyword(text: str, keyword: str) -> bool:
    if len(keyword) <= 4 or not keyword.replace(" ", "").isalnum():
        return bool(re.search(rf"(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])", text, re.IGNORECASE))
    return keyword.lower() in text.lower()


def _matched_keywords(text: str, keywords: Iterable[str]) -> list[str]:
    return [keyword for keyword in keywords if _contains_keyword(text, keyword)]


def _unique(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def match_job(job: dict) -> MatchResult:
    """Return whether a job should alert.

    A job must match at least one primary keyword. Secondary keywords enrich the
    reason but do not trigger an alert alone.
    """

    title_text = str(job.get("title", "") or "")
    searchable_text = " ".join(str(job.get(field, "") or "") for field in ("title", "organisation", "location", "description"))
    primary_matches = _matched_keywords(searchable_text, PRIMARY_KEYWORDS)
    secondary_matches = _matched_keywords(searchable_text, SECONDARY_KEYWORDS)
    resume_matches = _matched_keywords(searchable_text, get_resume_terms())
    title_matches = _unique(
        _matched_keywords(title_text, PRIMARY_KEYWORDS)
        + _matched_keywords(title_text, SECONDARY_KEYWORDS)
        + _matched_keywords(title_text, get_resume_terms())
    )
    score = score_job(primary_matches, secondary_matches, resume_matches, title_matches)
    return MatchResult(
        is_match=bool(primary_matches) or score >= RESUME_SCORE_ALERT_THRESHOLD,
        primary_matches=primary_matches,
        secondary_matches=secondary_matches,
        resume_matches=resume_matches,
        title_matches=title_matches,
        score=score,
    )


def score_job(
    primary_matches: list[str],
    secondary_matches: list[str],
    resume_matches: list[str],
    title_matches: list[str],
) -> int:
    """Score a job from 0 to 100 using configured and resume-derived terms."""

    score = 0
    score += min(len(primary_matches) * 24, 54)
    score += min(len(secondary_matches) * 6, 24)
    score += min(len(resume_matches) * 4, 32)
    score += min(len(title_matches) * 12, 30)
    if primary_matches and resume_matches:
        score += 10
    if title_matches and primary_matches:
        score += 8
    return min(score, 100)
