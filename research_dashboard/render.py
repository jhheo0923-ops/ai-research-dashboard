from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import analyze, db
from .sources import utc_now


def build_payload(database_path: Path, *, item_limit: int = 300) -> dict[str, Any]:
    items = db.query_items(database_path, limit=max(item_limit, 5000))
    trends = analyze.build_trends(items)
    trend_scores = {
        (trend["primary"], trend["secondary"]): int(trend["score"])
        for trend in trends
    }
    browser_items = [_browser_item(item, trend_scores) for item in items[:item_limit]]
    conferences = [_conference_item(item) for item in db.query_conferences(database_path)]
    source_runs = db.latest_source_runs(database_path)

    sources = [
        {
            "name": row["source"],
            "kind": _source_kind(row["source"]),
            "status": "정상" if row["status"] == "ok" else "오류",
            "count": row["item_count"],
            "message": row.get("message", ""),
        }
        for row in source_runs
    ]
    if not any(source["kind"] == "일정" for source in sources):
        sources.append(
            {
                "name": "Official Venues",
                "kind": "일정",
                "status": "정상",
                "count": len(conferences),
                "message": "공식 학회 페이지",
            }
        )

    generated_at = utc_now()
    return {
        "generated_at": generated_at,
        "metrics": db.aggregate_counts(database_path),
        "briefing": analyze.build_briefing(items, trends),
        "trends": trends,
        "statistics": _statistics(items, source_runs, db.query_annual_metrics(database_path)),
        "items": browser_items,
        "conferences": conferences,
        "sources": sources,
    }


def write_payload(database_path: Path, web_directory: Path, data_directory: Path, *, item_limit: int = 300) -> dict[str, Any]:
    payload = build_payload(database_path, item_limit=item_limit)
    web_directory.mkdir(parents=True, exist_ok=True)
    data_directory.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    (data_directory / "dashboard.json").write_text(serialized + "\n", encoding="utf-8")
    (web_directory / "data.js").write_text(
        "window.RESEARCH_DATA = " + serialized + ";\n",
        encoding="utf-8",
    )
    return payload


def _browser_item(item: dict[str, Any], trend_scores: dict[tuple[str, str], int]) -> dict[str, Any]:
    published = item.get("published_at")
    importance = _importance(item, trend_scores)
    return {
        "external_id": item["external_id"],
        "type": item["type"],
        "source": item["source"],
        "title": item["title"],
        "summary": item.get("summary", ""),
        "summary_ko": analyze.korean_summary(item),
        "url": item["url"],
        "published_at": published,
        "date_label": _date_label(published),
        "authors": item.get("authors", []),
        "keywords": analyze.item_keywords(item),
        "primary_topic": item.get("primary_topic"),
        "secondary_topic": item.get("secondary_topic"),
        "primary_topic_ko": analyze.topic_label_ko(item.get("primary_topic")),
        "secondary_topic_ko": analyze.topic_label_ko(item.get("secondary_topic")),
        "classification_confidence": item.get("confidence", 0),
        "matched_terms": item.get("matched_terms", []),
        "importance_score": importance["score"],
        "importance_label": importance["label"],
        "importance_reason": importance["reason"],
    }


def _importance(item: dict[str, Any], trend_scores: dict[tuple[str, str], int]) -> dict[str, Any]:
    score = 28
    reasons: list[str] = []
    topic_key = (
        str(item.get("primary_topic") or ""),
        str(item.get("secondary_topic") or ""),
    )
    momentum = trend_scores.get(topic_key, 0)
    if momentum:
        score += round(momentum * 0.34)
        reasons.append("급상승 주제" if momentum >= 70 else "주제 모멘텀")

    if item.get("type") == "paper":
        score += 8
        reasons.append("신규 논문")
    else:
        score += 4

    confidence = float(item.get("confidence") or 0)
    score += round(confidence * 10)

    published = item.get("published_at")
    if published:
        try:
            date = datetime.fromisoformat(str(published).replace("Z", "+00:00"))
            if date.tzinfo is None:
                date = date.replace(tzinfo=timezone.utc)
            age_days = max(0, (datetime.now(timezone.utc) - date.astimezone(timezone.utc)).days)
        except ValueError:
            age_days = 999
        if age_days <= 1:
            score += 15
            reasons.append("24시간 내")
        elif age_days <= 3:
            score += 11
            reasons.append("최신 자료")
        elif age_days <= 7:
            score += 8
        elif age_days <= 30:
            score += 4

    if item.get("source") in {
        "arXiv", "OpenAI News", "Google DeepMind", "Microsoft Research",
        "BAIR Blog", "NVIDIA Technical Blog",
    }:
        score += 4
        reasons.append("주요 연구 채널")

    score = min(100, score)
    if score >= 80:
        label = "핵심"
    elif score >= 65:
        label = "높음"
    elif score >= 50:
        label = "주목"
    else:
        label = "일반"
    return {
        "score": score,
        "label": label,
        "reason": " · ".join(reasons[:2]) or "일반 연구 신호",
    }


def _conference_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": item["code"],
        "name": item["name"],
        "url": item["url"],
        "status": item["status"],
        "date_label": item["date_label"],
        "field": item.get("field", "General AI"),
        "edition": item.get("edition"),
        "timeline": item.get("timeline", []),
        "cycle": _conference_cycle(item.get("timeline", [])),
    }


def _conference_cycle(timeline: list[dict[str, Any]]) -> dict[str, Any] | None:
    paper_events = [event for event in timeline if event.get("kind") == "paper" and event.get("start")]
    decision_events = [event for event in timeline if event.get("kind") == "decision" and event.get("start")]
    if not paper_events or not decision_events:
        return None
    submission_open = min(str(event["start"]) for event in paper_events)
    submission_deadline = max(str(event.get("end") or event["start"]) for event in paper_events)
    decision_date = max(str(event.get("end") or event["start"]) for event in decision_events)
    return {
        "submission_open": submission_open,
        "submission_deadline": submission_deadline,
        "review_start": submission_deadline,
        "review_end": decision_date,
        "decision_date": decision_date,
    }


def _statistics(
    items: list[dict[str, Any]],
    source_runs: list[dict[str, Any]],
    annual_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    first_day = (now - timedelta(days=27)).date()
    daily: dict[str, Counter[str]] = {
        (first_day + timedelta(days=offset)).isoformat(): Counter()
        for offset in range(28)
    }
    source_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    primary_counts: Counter[str] = Counter()
    secondary_counts: dict[str, Counter[str]] = defaultdict(Counter)
    authors: set[str] = set()
    confident = 0

    for item in items:
        source_counts[str(item.get("source", "Unknown"))] += 1
        type_counts[str(item.get("type", "item"))] += 1
        primary = str(item.get("primary_topic") or "Unclassified")
        secondary = str(item.get("secondary_topic") or "Unclassified")
        primary_counts[primary] += 1
        secondary_counts[primary][secondary] += 1
        if float(item.get("confidence") or 0) >= 0.38:
            confident += 1
        authors.update(str(author) for author in item.get("authors", []) if author)
        value = item.get("published_at") or item.get("collected_at")
        if value:
            try:
                day = datetime.fromisoformat(str(value).replace("Z", "+00:00")).date().isoformat()
            except ValueError:
                day = ""
            if day in daily:
                daily[day]["total"] += 1
                daily[day][str(item.get("type", "item"))] += 1

    taxonomy = [
        {
            "primary": primary,
            "count": count,
            "secondaries": [
                {"secondary": secondary, "count": secondary_count}
                for secondary, secondary_count in secondary_counts[primary].most_common()
            ],
        }
        for primary, count in primary_counts.most_common()
    ]
    healthy_sources = sum(1 for row in source_runs if row.get("status") == "ok")
    return {
        "kpis": {
            "archived_items": len(items),
            "active_sources": healthy_sources,
            "unique_authors": len(authors),
            "classified_percent": round(confident / len(items) * 100) if items else 0,
        },
        "daily_volume": [
            {
                "day": day,
                "count": counts["total"],
                "papers": counts["paper"],
                "news": counts["news"],
            }
            for day, counts in daily.items()
        ],
        "types": [{"type": kind, "count": count} for kind, count in type_counts.most_common()],
        "sources": [{"source": source, "count": count} for source, count in source_counts.most_common(10)],
        "taxonomy": taxonomy,
        "annual_trends": analyze.build_annual_trends(items, metrics=annual_metrics),
    }


def _source_kind(source: str) -> str:
    if source.startswith("arXiv"):
        return "논문"
    if source.startswith("OpenReview"):
        return "학회"
    return "뉴스"


def _date_label(value: str | None) -> str:
    if not value:
        return "날짜 미상"
    try:
        date = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value[:10]
    return date.strftime("%Y.%m.%d")
