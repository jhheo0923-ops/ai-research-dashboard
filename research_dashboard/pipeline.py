from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import analyze, db, sources


@dataclass
class CollectionResult:
    source: str
    status: str
    count: int
    message: str = ""


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def initialize(database_path: Path, config_path: Path) -> None:
    db.initialize(database_path)
    config = load_config(config_path)
    db.upsert_conferences(database_path, config.get("conferences", []), sources.utc_now())
    classify_archive(database_path)


def collect_all(database_path: Path, config_path: Path, *, max_items: int | None = None) -> list[CollectionResult]:
    config = load_config(config_path)
    results: list[CollectionResult] = []
    per_source = max_items or int(config.get("max_items_per_source", 80))

    arxiv_config = config.get("arxiv", {})
    if arxiv_config.get("enabled", True):
        results.append(
            _run_source(
                database_path,
                "arXiv",
                lambda: sources.collect_arxiv(arxiv_config.get("categories", []), max_results=per_source),
            )
        )

    for feed in config.get("rss_feeds", []):
        if not feed.get("enabled", True):
            continue
        results.append(
            _run_source(
                database_path,
                feed["name"],
                lambda feed=feed: sources.collect_rss(feed["name"], feed["url"], item_type="news")[:per_source],
            )
        )

    for venue in config.get("openreview_venues", []):
        if not venue.get("enabled", True):
            continue
        source_name = f"OpenReview · {venue['code']}"
        results.append(
            _run_source(
                database_path,
                source_name,
                lambda venue=venue: sources.collect_openreview(venue["venue_id"], limit=min(per_source, 1000)),
            )
        )
        time.sleep(float(config.get("request_delay_seconds", 1.0)))

    db.upsert_conferences(database_path, config.get("conferences", []), sources.utc_now())
    classify_archive(database_path)
    return results


def classify_archive(database_path: Path) -> int:
    classified_at = sources.utc_now()
    rows: list[dict[str, Any]] = []
    for item in db.query_items(database_path, limit=1_000_000):
        classification = analyze.classify_item(item)
        rows.append({"external_id": item["external_id"], **classification})
    return db.upsert_classifications(database_path, rows, classified_at)


def _run_source(database_path: Path, source_name: str, collector: Callable[[], list[dict[str, Any]]]) -> CollectionResult:
    started_at = sources.utc_now()
    try:
        items = collector()
        count = db.upsert_items(database_path, items)
        status = "ok"
        message = ""
    except Exception as exc:  # A single source must not abort the daily update.
        count = 0
        status = "error"
        message = f"{type(exc).__name__}: {exc}"
    finished_at = sources.utc_now()
    db.record_source_run(
        database_path,
        source=source_name,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        item_count=count,
        message=message,
    )
    return CollectionResult(source=source_name, status=status, count=count, message=message)
