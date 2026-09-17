from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any


# 1차 분야 → 2차 연구 주제 → 탐지어. 제목 일치는 본문/카테고리보다 높은 가중치를 받습니다.
TAXONOMY: dict[str, dict[str, tuple[str, ...]]] = {
    "Foundation Models": {
        "Language Models": ("language model", "large language model", " llm", "transformer language"),
        "Reasoning & Inference": ("reasoning", "chain-of-thought", "test-time compute", "inference-time", "verifier"),
        "Agents & Tool Use": ("agentic", "ai agent", "multi-agent", "tool use", "tool-using", "computer use"),
        "Retrieval & Memory": ("retrieval-augmented", "retrieval augmented", " rag ", "long context", "memory system"),
        "Multimodal Foundation Models": ("multimodal", "vision-language", "vision language", "audio-language", "vlm"),
    },
    "Vision & Generative Media": {
        "Vision-Language": ("vision-language", "vision language", "visual question", "image-text"),
        "Image Generation": ("image generation", "text-to-image", "diffusion model", "flow matching", "rectified flow"),
        "Video Generation": ("video generation", "text-to-video", "image-to-video", "video diffusion"),
        "3D & Spatial": ("3d generation", "3d reconstruction", "neural radiance", "gaussian splatting", "spatial intelligence"),
        "Perception & Recognition": ("object detection", "image segmentation", "visual recognition", "computer vision", "image classification"),
    },
    "Embodied & Decision AI": {
        "Robotics & Manipulation": ("robot", "robotic", "embodied", "manipulation", "grasping"),
        "Reinforcement Learning": ("reinforcement learning", "policy optimization", "reward model", "offline rl", "multi-armed bandit"),
        "World Models": ("world model", "world-model", "environment model", "latent dynamics"),
        "Planning & Control": ("motion planning", "task planning", "model predictive control", "control policy"),
    },
    "Trustworthy AI": {
        "Safety & Alignment": ("alignment", "ai safety", "red teaming", "jailbreak", "guardrail"),
        "Robustness & Security": ("adversarial", "robustness", "model security", "prompt injection", "backdoor attack"),
        "Interpretability": ("interpretability", "explainable ai", "mechanistic", "feature attribution"),
        "Fairness & Governance": ("fairness", "bias mitigation", "responsible ai", "ai governance", "algorithmic bias"),
        "Privacy": ("differential privacy", "privacy-preserving", "membership inference", "machine unlearning"),
    },
    "AI Systems & Evaluation": {
        "Efficient Training & Inference": ("efficient inference", "training efficiency", "mixture of experts", "sparse model", "speculative decoding"),
        "Evaluation & Benchmarks": ("benchmark", "evaluation", " evals", "leaderboard", "human evaluation"),
        "Data & Synthetic Data": ("synthetic data", "data curation", "data quality", "dataset distillation", "data mixture"),
        "Infrastructure & Hardware": ("accelerator", "gpu cluster", "distributed training", "inference serving", "ml system"),
        "Optimization & Compression": ("quantization", "distillation", "pruning", "low-rank", "model compression"),
    },
    "Science & Applications": {
        "AI for Science": ("ai for science", "scientific discovery", "foundation model for science", "surrogate model"),
        "Biology & Healthcare": ("protein", "drug discovery", "clinical", "medical imaging", "healthcare", "genomics"),
        "Climate & Earth": ("climate", "weather forecasting", "earth observation", "geospatial"),
        "Math & Formal Methods": ("theorem proving", "formal verification", "mathematical reasoning", "proof assistant"),
        "Recommenders & Search": ("recommender", "recommendation system", "web search", "information retrieval", "ranking model"),
    },
    "Learning & Theory": {
        "Representation & Self-Supervision": ("self-supervised", "representation learning", "contrastive learning", "masked modeling"),
        "Graph ML": ("graph neural", "graph learning", "knowledge graph", "gnn"),
        "Causal & Probabilistic": ("causal inference", "causal learning", "probabilistic model", "bayesian"),
        "Continual & Federated": ("continual learning", "lifelong learning", "federated learning", "catastrophic forgetting"),
        "General Machine Learning": ("machine learning", "deep learning", "neural network", "optimization", "generalization"),
    },
}

CATEGORY_HINTS: dict[str, tuple[str, str]] = {
    "cs.CL": ("Foundation Models", "Language Models"),
    "cs.CV": ("Vision & Generative Media", "Perception & Recognition"),
    "cs.RO": ("Embodied & Decision AI", "Robotics & Manipulation"),
    "cs.AI": ("Foundation Models", "Agents & Tool Use"),
    "cs.IR": ("Science & Applications", "Recommenders & Search"),
    "cs.CR": ("Trustworthy AI", "Robustness & Security"),
    "cs.LG": ("Learning & Theory", "General Machine Learning"),
    "stat.ML": ("Learning & Theory", "General Machine Learning"),
}


def classify_item(item: dict[str, Any]) -> dict[str, Any]:
    title = f" {str(item.get('title', '')).lower()} "
    body = f" {str(item.get('summary', '')).lower()} {' '.join(item.get('categories', [])).lower()} "
    candidates: list[tuple[float, str, str, list[str]]] = []

    for primary, secondary_topics in TAXONOMY.items():
        for secondary, phrases in secondary_topics.items():
            matched: list[str] = []
            score = 0.0
            for phrase in phrases:
                if phrase in title:
                    score += 3.0
                    matched.append(phrase.strip())
                elif phrase in body:
                    score += 1.0
                    matched.append(phrase.strip())
            if score:
                candidates.append((score, primary, secondary, matched))

    if candidates:
        candidates.sort(key=lambda row: (row[0], len(row[3])), reverse=True)
        score, primary, secondary, matched = candidates[0]
        confidence = min(0.98, 0.42 + math.log2(score + 1) * 0.16)
        return {
            "primary_topic": primary,
            "secondary_topic": secondary,
            "confidence": round(confidence, 3),
            "matched_terms": list(dict.fromkeys(matched))[:6],
        }

    for category in item.get("categories", []):
        if category in CATEGORY_HINTS:
            primary, secondary = CATEGORY_HINTS[category]
            return {
                "primary_topic": primary,
                "secondary_topic": secondary,
                "confidence": 0.38,
                "matched_terms": [category],
            }

    return {
        "primary_topic": "Unclassified",
        "secondary_topic": "Needs Review",
        "confidence": 0.18,
        "matched_terms": [],
    }


def topic_counts(items: list[dict[str, Any]], *, now: datetime | None = None) -> tuple[Counter[tuple[str, str]], Counter[tuple[str, str]]]:
    now = now or datetime.now(timezone.utc)
    recent_start = now - timedelta(days=7)
    baseline_start = now - timedelta(days=28)
    recent: Counter[tuple[str, str]] = Counter()
    baseline: Counter[tuple[str, str]] = Counter()

    for item in items:
        published = _parse_date(item.get("published_at"))
        if published is None or published < baseline_start:
            continue
        primary = item.get("primary_topic")
        secondary = item.get("secondary_topic")
        if not primary or not secondary:
            classification = classify_item(item)
            primary = classification["primary_topic"]
            secondary = classification["secondary_topic"]
        destination = recent if published >= recent_start else baseline
        destination[(str(primary), str(secondary))] += 1
    return recent, baseline


def build_trends(items: list[dict[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    recent, baseline = topic_counts(items)
    rows: list[dict[str, Any]] = []
    for primary, secondary_topics in TAXONOMY.items():
        for secondary in secondary_topics:
            key = (primary, secondary)
            recent_count = recent[key]
            weekly_baseline = baseline[key] / 3 if baseline[key] else 0
            momentum = (recent_count + 1) / (weekly_baseline + 1)
            strength = recent_count * math.log2(momentum + 1)
            rows.append(
                {
                    "primary": primary,
                    "secondary": secondary,
                    "recent": recent_count,
                    "baseline": round(weekly_baseline, 1),
                    "momentum": momentum,
                    "strength": strength,
                }
            )

    rows.sort(key=lambda row: (row["strength"], row["recent"]), reverse=True)
    selected = rows[:limit]
    maximum = max((row["strength"] for row in selected), default=0) or 1
    return [
        {
            "primary": row["primary"],
            "secondary": row["secondary"],
            "label": row["secondary"],
            "score": round(18 + (row["strength"] / maximum) * 82),
            "delta": _delta_label(row["momentum"], row["recent"]),
            "count": row["recent"],
        }
        for row in selected
    ]


def build_briefing(items: list[dict[str, Any]], trends: list[dict[str, Any]], *, limit: int = 4) -> list[dict[str, Any]]:
    briefing: list[dict[str, Any]] = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    for trend in trends:
        matching = [
            item
            for item in items
            if (_parse_date(item.get("published_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff
            and item.get("primary_topic") == trend["primary"]
            and item.get("secondary_topic") == trend["secondary"]
        ]
        if not matching:
            continue
        lead = matching[0]
        source_count = len({item.get("source") for item in matching if item.get("source")})
        briefing.append(
            {
                "title": f"{trend['secondary']}, 최근 신호 {len(matching)}건",
                "summary": f"{source_count}개 출처에서 관련 흐름이 포착됐습니다. 대표 자료: {lead['title']}",
                "tags": [trend["primary"].upper(), trend["secondary"].upper()],
            }
        )
        if len(briefing) >= limit:
            break

    if not briefing:
        newest = items[:limit]
        briefing = [
            {
                "title": item["title"],
                "summary": (item.get("summary") or "새로운 자료가 수집되었습니다.")[:220],
                "tags": [item.get("primary_topic", item.get("type", "item")).upper(), item.get("source", "source").upper()],
            }
            for item in newest
        ]
    return briefing


def item_keywords(item: dict[str, Any], *, limit: int = 4) -> list[str]:
    classification = classify_item(item)
    matches = [classification["primary_topic"], classification["secondary_topic"]]
    matches.extend(classification["matched_terms"])
    return list(dict.fromkeys(matches))[:limit]


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        date = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if date.tzinfo is None:
        return date.replace(tzinfo=timezone.utc)
    return date.astimezone(timezone.utc)


def _delta_label(momentum: float, count: int) -> str:
    if count == 0:
        return "신호 없음"
    if momentum >= 1.8:
        return f"↑ {momentum:.1f}×"
    if momentum >= 1.1:
        return f"↗ {momentum:.1f}×"
    if momentum <= 0.7:
        return f"↓ {momentum:.1f}×"
    return "→ 유지"
