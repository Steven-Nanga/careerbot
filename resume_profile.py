"""Local resume parsing and profile keyword extraction."""

from __future__ import annotations

import logging
import re
import zipfile
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

from config import PRIMARY_KEYWORDS, RESUME_DIR, RESUME_PROFILE_TERMS, SECONDARY_KEYWORDS

LOGGER = logging.getLogger(__name__)


def _read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as docx:
        xml = docx.read("word/document.xml")
    root = ElementTree.fromstring(xml)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
        if text.strip():
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        LOGGER.warning("Skipping PDF resume %s because pypdf is not installed", path.name)
        return ""

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def read_resume_text() -> str:
    resume_dir = Path(RESUME_DIR)
    if not resume_dir.exists():
        LOGGER.info("Resume directory does not exist: %s", resume_dir)
        return ""

    chunks = []
    for path in sorted(resume_dir.glob("*")):
        if not path.is_file():
            continue
        try:
            if path.suffix.lower() == ".txt":
                chunks.append(_read_txt(path))
            elif path.suffix.lower() == ".docx":
                chunks.append(_read_docx(path))
            elif path.suffix.lower() == ".pdf":
                chunks.append(_read_pdf(path))
        except Exception:
            LOGGER.exception("Failed to read resume file %s", path)

    text = "\n".join(chunks)
    LOGGER.info("Loaded %s characters from resume files", len(text))
    return text


def _contains_term(text: str, term: str) -> bool:
    if len(term) == 1:
        return bool(re.search(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])", text, re.IGNORECASE))
    return term.lower() in text.lower()


@lru_cache(maxsize=1)
def get_resume_terms() -> list[str]:
    text = read_resume_text()
    if not text:
        return []

    candidates = list(dict.fromkeys(PRIMARY_KEYWORDS + SECONDARY_KEYWORDS + RESUME_PROFILE_TERMS))
    terms = [term for term in candidates if _contains_term(text, term)]
    LOGGER.info("Derived %s resume profile terms", len(terms))
    return terms
