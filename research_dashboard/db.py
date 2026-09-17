from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Iterator


SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('paper', 'news', 'conference')),
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL,
    published_at TEXT,
    updated_at TEXT,
    authors_json TEXT NOT NULL DEFAULT '[]',
    categories_json TEXT NOT NULL DEFAULT '[]',
    raw_json TEXT NOT NULL DEFAULT '{}',
    collected_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_items_published ON items(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_items_type ON items(type, published_at DESC);
CREATE INDEX IF NOT EXISTS idx_items_source ON items(source, published_at DESC);

CREATE TABLE IF NOT EXISTS item_classifications (
    external_id TEXT PRIMARY KEY,
    primary_topic TEXT NOT NULL,
    secondary_topic TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0,
    matched_terms_json TEXT NOT NULL DEFAULT '[]',
    classified_at TEXT NOT NULL,
    FOREIGN KEY(external_id) REFERENCES items(external_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_classifications_primary ON item_classifications(primary_topic);
CREATE INDEX IF NOT EXISTS idx_classifications_secondary ON item_classifications(secondary_topic);

CREATE TABLE IF NOT EXISTS source_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ok', 'error')),
    item_count INTEGER NOT NULL DEFAULT 0,
    message TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_source_runs_latest ON source_runs(source, finished_at DESC);

CREATE TABLE IF NOT EXISTS annual_metrics (
    field_key TEXT NOT NULL,
    field_label_ko TEXT NOT NULL,
    category TEXT NOT NULL,
    year INTEGER NOT NULL,
    count INTEGER NOT NULL,
    source_url TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    PRIMARY KEY(field_key, year)
);

CREATE INDEX IF NOT EXISTS idx_annual_metrics_year ON annual_metrics(year, field_key);

CREATE TABLE IF NOT EXISTS conferences (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    status TEXT NOT NULL,
    date_label TEXT NOT NULL,
    field TEXT NOT NULL DEFAULT 'General AI',
    edition INTEGER,
    timeline_json TEXT NOT NULL DEFAULT '[]',
    last_checked_at TEXT
);
"""


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 5000")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize(path: Path) -> None:
    with connect(path) as connection:
        connection.executescript(SCHEMA)
        _ensure_column(connection, "conferences", "field", "TEXT NOT NULL DEFAULT 'General AI'")
        _ensure_column(connection, "conferences", "edition", "INTEGER")
        _ensure_column(connection, "conferences", "timeline_json", "TEXT NOT NULL DEFAULT '[]'")
        try:
            connection.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(title, summary, authors, categories)"
            )
        except sqlite3.OperationalError:
            # Some minimal Python builds omit FTS5. The dashboard still works.
            pass
        connection.execute("PRAGMA optimize")


def upsert_items(path: Path, items: Iterable[dict[str, Any]]) -> int:
    rows = list(items)
    if not rows:
        return 0

    sql = """
        INSERT INTO items (
            external_id, type, source, title, summary, url, published_at,
            updated_at, authors_json, categories_json, raw_json, collected_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(external_id) DO UPDATE SET
            type=excluded.type,
            source=excluded.source,
            title=excluded.title,
            summary=excluded.summary,
            url=excluded.url,
            published_at=excluded.published_at,
            updated_at=excluded.updated_at,
            authors_json=excluded.authors_json,
            categories_json=excluded.categories_json,
            raw_json=excluded.raw_json,
            collected_at=excluded.collected_at
    """
    values = [
        (
            row["external_id"],
            row["type"],
            row["source"],
            row["title"],
            row.get("summary", ""),
            row["url"],
            row.get("published_at"),
            row.get("updated_at"),
            json.dumps(row.get("authors", []), ensure_ascii=False),
            json.dumps(row.get("categories", []), ensure_ascii=False),
            json.dumps(row.get("raw", {}), ensure_ascii=False),
            row["collected_at"],
        )
        for row in rows
    ]
    with connect(path) as connection:
        connection.executemany(sql, values)
        rebuild_search_index(connection)
    return len(rows)


def rebuild_search_index(connection: sqlite3.Connection) -> None:
    try:
        connection.execute("DELETE FROM items_fts")
        connection.execute(
            """
            INSERT INTO items_fts(rowid, title, summary, authors, categories)
            SELECT id, title, summary, authors_json, categories_json FROM items
            """
        )
    except sqlite3.OperationalError:
        pass


def upsert_classifications(path: Path, rows: Iterable[dict[str, Any]], classified_at: str) -> int:
    values = [
        (
            row["external_id"],
            row["primary_topic"],
            row["secondary_topic"],
            float(row.get("confidence", 0)),
            json.dumps(row.get("matched_terms", []), ensure_ascii=False),
            classified_at,
        )
        for row in rows
    ]
    if not values:
        return 0
    with connect(path) as connection:
        connection.executemany(
            """
            INSERT INTO item_classifications(
                external_id, primary_topic, secondary_topic, confidence,
                matched_terms_json, classified_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(external_id) DO UPDATE SET
                primary_topic=excluded.primary_topic,
                secondary_topic=excluded.secondary_topic,
                confidence=excluded.confidence,
                matched_terms_json=excluded.matched_terms_json,
                classified_at=excluded.classified_at
            """,
            values,
        )
        connection.execute("PRAGMA optimize")
    return len(values)


def record_source_run(
    path: Path,
    *,
    source: str,
    started_at: str,
    finished_at: str,
    status: str,
    item_count: int,
    message: str = "",
) -> None:
    with connect(path) as connection:
        connection.execute(
            """
            INSERT INTO source_runs(source, started_at, finished_at, status, item_count, message)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (source, started_at, finished_at, status, item_count, message[:1000]),
        )


def upsert_conferences(path: Path, conferences: Iterable[dict[str, Any]], checked_at: str) -> None:
    rows = [
        (
            item["code"],
            item["name"],
            item["url"],
            _conference_status(item),
            item.get("date_label", "공식 일정 확인"),
            item.get("field", "General AI"),
            item.get("edition"),
            json.dumps(item.get("timeline", []), ensure_ascii=False),
            checked_at,
        )
        for item in conferences
    ]
    with connect(path) as connection:
        connection.executemany(
            """
            INSERT INTO conferences(
                code, name, url, status, date_label, field, edition,
                timeline_json, last_checked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                name=excluded.name,
                url=excluded.url,
                status=excluded.status,
                date_label=excluded.date_label,
                field=excluded.field,
                edition=excluded.edition,
                timeline_json=excluded.timeline_json,
                last_checked_at=excluded.last_checked_at
            """,
            rows,
        )


def query_items(path: Path, *, limit: int = 300) -> list[dict[str, Any]]:
    with connect(path) as connection:
        rows = connection.execute(
            """
            SELECT items.*, c.primary_topic, c.secondary_topic,
                   c.confidence, c.matched_terms_json
            FROM items
            LEFT JOIN item_classifications c ON c.external_id = items.external_id
            ORDER BY COALESCE(published_at, collected_at) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_decode_item(row) for row in rows]


def upsert_annual_metric(path: Path, metric: dict[str, Any]) -> None:
    with connect(path) as connection:
        connection.execute(
            """
            INSERT INTO annual_metrics(
                field_key, field_label_ko, category, year, count, source_url, collected_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(field_key, year) DO UPDATE SET
                field_label_ko=excluded.field_label_ko,
                category=excluded.category,
                count=excluded.count,
                source_url=excluded.source_url,
                collected_at=excluded.collected_at
            """,
            (
                metric["field_key"], metric["field_label_ko"], metric["category"],
                int(metric["year"]), int(metric["count"]), metric["source_url"],
                metric["collected_at"],
            ),
        )


def has_annual_metric(path: Path, field_key: str, year: int) -> bool:
    with connect(path) as connection:
        row = connection.execute(
            "SELECT 1 FROM annual_metrics WHERE field_key = ? AND year = ?",
            (field_key, int(year)),
        ).fetchone()
    return row is not None


def query_annual_metrics(path: Path) -> list[dict[str, Any]]:
    with connect(path) as connection:
        rows = connection.execute(
            "SELECT * FROM annual_metrics ORDER BY year, field_key"
        ).fetchall()
    return [dict(row) for row in rows]


def search_items(path: Path, query: str, *, limit: int = 30) -> list[dict[str, Any]]:
    with connect(path) as connection:
        try:
            rows = connection.execute(
                """
                SELECT items.*, c.primary_topic, c.secondary_topic,
                       c.confidence, c.matched_terms_json
                FROM items_fts
                JOIN items ON items.id = items_fts.rowid
                LEFT JOIN item_classifications c ON c.external_id = items.external_id
                WHERE items_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            like = f"%{query}%"
            rows = connection.execute(
                """
                SELECT items.*, c.primary_topic, c.secondary_topic,
                       c.confidence, c.matched_terms_json
                FROM items
                LEFT JOIN item_classifications c ON c.external_id = items.external_id
                WHERE title LIKE ? OR summary LIKE ? OR authors_json LIKE ? OR categories_json LIKE ?
                ORDER BY COALESCE(published_at, collected_at) DESC
                LIMIT ?
                """,
                (like, like, like, like, limit),
            ).fetchall()
    return [_decode_item(row) for row in rows]


def query_conferences(path: Path) -> list[dict[str, Any]]:
    with connect(path) as connection:
        rows = connection.execute("SELECT * FROM conferences ORDER BY code").fetchall()
    decoded: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["timeline"] = json.loads(item.pop("timeline_json") or "[]")
        decoded.append(item)
    return decoded


def latest_source_runs(path: Path) -> list[dict[str, Any]]:
    with connect(path) as connection:
        rows = connection.execute(
            """
            SELECT sr.*
            FROM source_runs sr
            JOIN (
                SELECT source, MAX(id) AS max_id FROM source_runs GROUP BY source
            ) latest ON latest.max_id = sr.id
            ORDER BY sr.source
            """
        ).fetchall()
    return [dict(row) for row in rows]


def aggregate_counts(path: Path) -> dict[str, int]:
    with connect(path) as connection:
        total_rows = connection.execute(
            "SELECT type, COUNT(*) AS count FROM items GROUP BY type"
        ).fetchall()
        today = connection.execute(
            """
            SELECT COUNT(*) FROM items
            WHERE datetime(COALESCE(published_at, collected_at)) >= datetime('now', '-1 day')
            """
        ).fetchone()[0]
        conference_count = connection.execute("SELECT COUNT(*) FROM conferences").fetchone()[0]
    counts = {row["type"]: row["count"] for row in total_rows}
    return {
        "today": int(today),
        "papers": int(counts.get("paper", 0)),
        "news": int(counts.get("news", 0)),
        "conferences": int(conference_count),
    }


def _decode_item(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["authors"] = json.loads(item.pop("authors_json") or "[]")
    item["categories"] = json.loads(item.pop("categories_json") or "[]")
    item["matched_terms"] = json.loads(item.pop("matched_terms_json", None) or "[]")
    item.pop("raw_json", None)
    return item


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _conference_status(item: dict[str, Any]) -> str:
    start_value = item.get("start_date")
    end_value = item.get("end_date")
    if not start_value or not end_value:
        return item.get("status", "추적 중")
    try:
        start = date.fromisoformat(start_value)
        end = date.fromisoformat(end_value)
    except ValueError:
        return item.get("status", "추적 중")
    today = date.today()
    if today < start:
        return "예정"
    if today <= end:
        return "진행 중"
    return "아카이브"
