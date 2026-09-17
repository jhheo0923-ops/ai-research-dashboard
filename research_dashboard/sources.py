from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Iterable


ATOM = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
USER_AGENT = "SignalAIResearchDashboard/0.2 (https://github.com/jhheo0923-ops/ai-research-dashboard)"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_bytes(url: str, *, timeout: int = 30) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/atom+xml, application/rss+xml, application/json, text/html, text/xml;q=0.9, */*;q=0.5",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def collect_arxiv(
    categories: Iterable[str],
    *,
    max_results: int = 100,
) -> list[dict[str, Any]]:
    category_list = list(categories)
    query = " OR ".join(f"cat:{category}" for category in category_list)
    params = urllib.parse.urlencode(
        {
            "search_query": query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        },
        quote_via=urllib.parse.quote,
    )
    payload = fetch_bytes(f"https://export.arxiv.org/api/query?{params}", timeout=45)
    return parse_arxiv(payload)


def collect_arxiv_year_count(category: str, year: int) -> dict[str, Any]:
    """Read the official arXiv yearly listing total for one subject category."""
    url = f"https://arxiv.org/list/{urllib.parse.quote(category, safe='.')}/{int(year)}"
    payload = fetch_bytes(url, timeout=45).decode("utf-8", errors="replace")
    match = re.search(r"Total\s+of\s+([\d,]+)\s+entries", payload, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"arXiv yearly total not found for {category} {year}")
    return {
        "category": category,
        "year": int(year),
        "count": int(match.group(1).replace(",", "")),
        "source_url": url,
        "collected_at": utc_now(),
    }


def parse_arxiv(payload: bytes) -> list[dict[str, Any]]:
    root = ET.fromstring(payload)
    collected_at = utc_now()
    items: list[dict[str, Any]] = []
    for entry in root.findall("atom:entry", ATOM):
        url = _text(entry, "atom:id", ATOM)
        if not url:
            continue
        external_id = re.sub(r"v\d+$", "", url.rsplit("/", 1)[-1])
        authors = [
            _clean_text(_text(author, "atom:name", ATOM))
            for author in entry.findall("atom:author", ATOM)
        ]
        categories = [node.attrib.get("term", "") for node in entry.findall("atom:category", ATOM)]
        items.append(
            {
                "external_id": f"arxiv:{external_id}",
                "type": "paper",
                "source": "arXiv",
                "title": _clean_text(_text(entry, "atom:title", ATOM)),
                "summary": _clean_text(_text(entry, "atom:summary", ATOM)),
                "url": url.replace("http://", "https://"),
                "published_at": _normalize_date(_text(entry, "atom:published", ATOM)),
                "updated_at": _normalize_date(_text(entry, "atom:updated", ATOM)),
                "authors": [name for name in authors if name],
                "categories": [category for category in categories if category],
                "raw": {"primary_category": _primary_category(entry)},
                "collected_at": collected_at,
            }
        )
    return items


def collect_rss(source_name: str, url: str, *, item_type: str = "news") -> list[dict[str, Any]]:
    return parse_feed(fetch_bytes(url), source_name=source_name, item_type=item_type)


def parse_feed(payload: bytes, *, source_name: str, item_type: str = "news") -> list[dict[str, Any]]:
    root = ET.fromstring(payload)
    collected_at = utc_now()
    items: list[dict[str, Any]] = []
    is_atom = _local_name(root.tag) == "feed"
    entries = list(root) if is_atom else root.findall(".//item")

    for entry in entries:
        if _local_name(entry.tag) not in {"entry", "item"}:
            continue
        title = _child_text(entry, {"title"})
        url = _entry_link(entry)
        if not title or not url:
            continue
        summary = _child_text(entry, {"summary", "description", "content", "encoded"})
        published = _child_text(entry, {"published", "pubDate", "updated", "date"})
        authors = _entry_authors(entry)
        categories = _entry_categories(entry)
        guid = _child_text(entry, {"id", "guid"}) or url
        digest = hashlib.sha256(guid.encode("utf-8", errors="ignore")).hexdigest()[:24]
        items.append(
            {
                "external_id": f"rss:{_slug(source_name)}:{digest}",
                "type": item_type,
                "source": source_name,
                "title": _clean_text(title),
                "summary": _clean_text(summary),
                "url": url,
                "published_at": _normalize_date(published),
                "updated_at": _normalize_date(published),
                "authors": authors,
                "categories": categories,
                "raw": {},
                "collected_at": collected_at,
            }
        )
    return items


def collect_openreview(venue_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "content.venueid": venue_id,
            "limit": limit,
            "sort": "tcdate:desc",
        }
    )
    payload = fetch_bytes(f"https://api2.openreview.net/notes?{params}", timeout=45)
    return parse_openreview(payload, venue_id=venue_id)


def parse_openreview(payload: bytes, *, venue_id: str) -> list[dict[str, Any]]:
    response = json.loads(payload.decode("utf-8"))
    notes = response.get("notes", response if isinstance(response, list) else [])
    collected_at = utc_now()
    venue_code = venue_id.split(".", 1)[0]
    items: list[dict[str, Any]] = []
    for note in notes:
        content = note.get("content", {})
        title = _openreview_value(content.get("title"))
        if not title:
            continue
        note_id = note.get("id") or note.get("forum")
        url = f"https://openreview.net/forum?id={urllib.parse.quote(str(note_id))}"
        cdate = note.get("cdate") or note.get("tcdate")
        items.append(
            {
                "external_id": f"openreview:{note_id}",
                "type": "paper",
                "source": f"OpenReview · {venue_code}",
                "title": _clean_text(str(title)),
                "summary": _clean_text(str(_openreview_value(content.get("abstract")) or "")),
                "url": url,
                "published_at": _milliseconds_to_iso(cdate),
                "updated_at": _milliseconds_to_iso(note.get("mdate") or cdate),
                "authors": _as_list(_openreview_value(content.get("authors"))),
                "categories": [venue_code, venue_id],
                "raw": {"venue_id": venue_id, "note_number": note.get("number")},
                "collected_at": collected_at,
            }
        )
    return items


def _text(node: ET.Element, path: str, namespaces: dict[str, str]) -> str:
    child = node.find(path, namespaces)
    return child.text.strip() if child is not None and child.text else ""


def _primary_category(entry: ET.Element) -> str:
    node = entry.find("arxiv:primary_category", ATOM)
    return node.attrib.get("term", "") if node is not None else ""


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(node: ET.Element, names: set[str]) -> str:
    for child in node.iter():
        if child is node:
            continue
        if _local_name(child.tag) in names and child.text:
            return "".join(child.itertext()).strip()
    return ""


def _entry_link(entry: ET.Element) -> str:
    for child in entry:
        if _local_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        rel = child.attrib.get("rel", "alternate")
        if href and rel in {"alternate", ""}:
            return href.strip()
        if child.text and child.text.strip().startswith("http"):
            return child.text.strip()
    return _child_text(entry, {"link"})


def _entry_authors(entry: ET.Element) -> list[str]:
    names: list[str] = []
    for child in entry.iter():
        if _local_name(child.tag) in {"author", "creator"}:
            value = _child_text(child, {"name"}) or (child.text or "")
            value = _clean_text(value)
            if value and value not in names:
                names.append(value)
    return names


def _entry_categories(entry: ET.Element) -> list[str]:
    categories: list[str] = []
    for child in entry.iter():
        if _local_name(child.tag) != "category":
            continue
        value = child.attrib.get("term") or child.text or ""
        value = _clean_text(value)
        if value and value not in categories:
            categories.append(value)
    return categories


def _clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def _normalize_date(value: str) -> str | None:
    if not value:
        return None
    value = value.strip()
    try:
        date = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        try:
            date = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return value
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return date.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def _milliseconds_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value) / 1000, tz=timezone.utc).replace(microsecond=0).isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def _openreview_value(value: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return value["value"]
    return value


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_clean_text(str(item)) for item in value if str(item).strip()]
    return [_clean_text(str(value))]


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
