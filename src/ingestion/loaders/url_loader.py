"""Blog and URL loader implementation."""

from __future__ import annotations

import hashlib
import re
from urllib.parse import urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from src.core.interfaces import DocumentLoader
from src.core.models import Document
from src.utils.logger import get_logger


logger = get_logger(__name__)


class URLLoader(DocumentLoader):
    supported_source_types = ("url", "blog")
    _excluded_section_titles = {
        "notes",
        "references",
        "bibliography",
        "further reading",
        "external links",
        "see also",
    }

    def __init__(self, *, timeout_seconds: int = 20, user_agent: str = "KDU-2026-AI/1.0") -> None:
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def load(self, source: str) -> Document:
        normalized_url = self._normalize_url(source)
        try:
            response = requests.get(
                normalized_url,
                timeout=self.timeout_seconds,
                headers={"User-Agent": self.user_agent},
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.exception("event=loader.url.fetch_failed source=%s", normalized_url)
            raise ValueError(
                f"Failed to fetch URL '{normalized_url}'. Check the address and network access, then try again."
            ) from exc

        soup = BeautifulSoup(response.text, "html.parser")
        for selector in (
            "script",
            "style",
            "noscript",
            "header",
            "footer",
            "nav",
            "aside",
            "form",
            ".toc",
            ".navbox",
            ".reflist",
            ".reference",
            ".mw-references-wrap",
            ".metadata",
            ".thumb",
            ".hatnote",
            ".sidebar",
            "sup.reference",
        ):
            for element in soup.select(selector):
                element.decompose()

        container = self._select_content_container(soup)
        if container is None:
            raise ValueError(f"Unable to extract article content from URL: {normalized_url}")

        title = self._extract_title(soup, container, normalized_url)
        content, sections = self._extract_content(container)
        if not content.strip():
            raise ValueError(f"URL did not yield readable article text: {normalized_url}")

        document_id = hashlib.sha256(f"url::{normalized_url}".encode("utf-8")).hexdigest()
        return Document(
            document_id=document_id,
            source_type="url",
            source=normalized_url,
            title=title,
            content=content,
            metadata={
                "document_title": title,
                "source": normalized_url,
                "source_type": "url",
                "sections": sections,
            },
        )

    def _normalize_url(self, source: str) -> str:
        parsed = urlsplit(source.strip())
        if not parsed.scheme:
            parsed = urlsplit(f"https://{source.strip()}")
        if parsed.scheme not in {"http", "https"}:
            raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", parsed.query, ""))

    def _extract_title(self, soup: BeautifulSoup, container: Tag, fallback: str) -> str:
        meta_title = soup.find("meta", attrs={"property": "og:title"}) or soup.find(
            "meta", attrs={"name": "twitter:title"}
        )
        if meta_title and meta_title.get("content"):
            return meta_title["content"].strip()
        if soup.title and soup.title.string:
            return soup.title.string.strip()
        heading = container.find(["h1", "h2"])
        if heading and heading.get_text(strip=True):
            return heading.get_text(strip=True)
        return fallback

    def _select_content_container(self, soup: BeautifulSoup) -> Tag | None:
        candidates = [candidate for candidate in soup.select(".mw-parser-output") if isinstance(candidate, Tag)]
        if candidates:
            return max(candidates, key=lambda candidate: len(candidate.get_text(" ", strip=True)))
        return soup.find("article") or soup.find("main") or soup.body

    def _extract_content(self, container: Tag) -> tuple[str, list[dict[str, object]]]:
        sections: list[dict[str, object]] = []
        current_offset = 0
        summary_text = self._extract_infobox_text(container)

        if summary_text:
            sections.append(
                {
                    "title": "Summary facts",
                    "text": summary_text,
                    "start_offset": current_offset,
                    "end_offset": current_offset + len(summary_text),
                    "metadata": {"section_type": "infobox"},
                }
            )
            current_offset += len(summary_text) + 2

        current_title = "Introduction"
        current_buffer: list[str] = []

        def flush_section() -> None:
            nonlocal current_title, current_buffer, current_offset
            text = "\n".join(part for part in current_buffer if part).strip()
            if not text:
                current_buffer = []
                return
            if current_title.strip().lower() in self._excluded_section_titles:
                current_buffer = []
                return
            sections.append(
                {
                    "title": current_title,
                    "text": text,
                    "start_offset": current_offset,
                    "end_offset": current_offset + len(text),
                    "metadata": {},
                }
            )
            current_offset += len(text) + 2
            current_buffer = []

        for table in container.select("table.infobox"):
            table.decompose()

        for node in container.find_all(["h1", "h2", "h3", "p", "blockquote", "pre", "ul", "ol"], recursive=True):
            if not isinstance(node, Tag) or self._should_skip_tag(node):
                continue
            if node.name in {"h1", "h2", "h3"}:
                flush_section()
                current_title = node.get_text(" ", strip=True) or current_title
            elif node.name in {"p", "blockquote", "pre"}:
                text = node.get_text(" ", strip=True)
                if text:
                    current_buffer.append(text)
            elif node.name in {"ul", "ol"}:
                for item in node.find_all("li", recursive=False):
                    text = item.get_text(" ", strip=True)
                    if text:
                        current_buffer.append(text)

        flush_section()
        content = "\n\n".join(section["text"] for section in sections)
        if not sections and content.strip():
            sections = [
                {
                    "title": current_title,
                    "text": content.strip(),
                    "start_offset": 0,
                    "end_offset": len(content.strip()),
                    "metadata": {},
                }
            ]
        return content.strip(), sections

    def _extract_infobox_text(self, container: Tag) -> str:
        tables = container.select("table.infobox")
        lines: list[str] = []
        for table in tables:
            for row in table.find_all("tr"):
                header = row.find("th")
                cells = row.find_all("td")
                if header is None or not cells:
                    continue
                label = header.get_text(" ", strip=True)
                value = " ".join(cell.get_text(" ", strip=True) for cell in cells).strip()
                if label and value:
                    lines.append(f"{label}: {value}")
        # De-duplicate while preserving order because some infoboxes repeat labels.
        deduped = list(dict.fromkeys(lines))
        return "\n".join(deduped).strip()

    def _should_skip_tag(self, node: Tag) -> bool:
        if node.find_parent(["table", "figure", "nav", "aside"]):
            return True
        classes = set(node.get("class", []))
        if classes.intersection(
            {
                "toc",
                "navbox",
                "reflist",
                "reference",
                "mw-references-wrap",
                "metadata",
                "thumb",
                "hatnote",
                "sidebar",
            }
        ):
            return True
        node_id = node.get("id", "")
        if node_id in {"toc", "References", "External_links", "See_also"}:
            return True
        if node.name in {"table", "figure"}:
            return True
        text = node.get_text(" ", strip=True)
        if not text:
            return True
        if re.fullmatch(r"\[\s*\d+\s*\]", text):
            return True
        return False
