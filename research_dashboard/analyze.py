from __future__ import annotations

import math
from collections import Counter, defaultdict
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

PRIMARY_LABELS_KO: dict[str, str] = {
    "Foundation Models": "파운데이션 모델",
    "Vision & Generative Media": "비전·생성 미디어",
    "Embodied & Decision AI": "로보틱스·의사결정 AI",
    "Trustworthy AI": "신뢰할 수 있는 AI",
    "AI Systems & Evaluation": "AI 시스템·평가",
    "Science & Applications": "과학·산업 응용",
    "Learning & Theory": "학습 방법·이론",
    "Unclassified": "미분류",
}

SECONDARY_LABELS_KO: dict[str, str] = {
    "Language Models": "언어 모델",
    "Reasoning & Inference": "추론·인퍼런스",
    "Agents & Tool Use": "에이전트·도구 사용",
    "Retrieval & Memory": "검색·메모리",
    "Multimodal Foundation Models": "멀티모달 파운데이션 모델",
    "Vision-Language": "비전-언어",
    "Image Generation": "이미지 생성",
    "Video Generation": "비디오 생성",
    "3D & Spatial": "3D·공간 지능",
    "Perception & Recognition": "인지·인식",
    "Robotics & Manipulation": "로보틱스·조작",
    "Reinforcement Learning": "강화학습",
    "World Models": "월드 모델",
    "Planning & Control": "계획·제어",
    "Safety & Alignment": "안전·정렬",
    "Robustness & Security": "강건성·보안",
    "Interpretability": "해석 가능성",
    "Fairness & Governance": "공정성·거버넌스",
    "Privacy": "프라이버시",
    "Efficient Training & Inference": "효율적 학습·추론",
    "Evaluation & Benchmarks": "평가·벤치마크",
    "Data & Synthetic Data": "데이터·합성 데이터",
    "Infrastructure & Hardware": "인프라·하드웨어",
    "Optimization & Compression": "최적화·압축",
    "AI for Science": "과학을 위한 AI",
    "Biology & Healthcare": "생명과학·헬스케어",
    "Climate & Earth": "기후·지구",
    "Math & Formal Methods": "수학·형식 방법",
    "Recommenders & Search": "추천·검색",
    "Representation & Self-Supervision": "표현학습·자기지도학습",
    "Graph ML": "그래프 머신러닝",
    "Causal & Probabilistic": "인과·확률 모델",
    "Continual & Federated": "지속·연합학습",
    "General Machine Learning": "일반 머신러닝",
    "Needs Review": "분류 검토 필요",
}


def topic_label_ko(value: str | None) -> str:
    label = str(value or "Unclassified")
    return PRIMARY_LABELS_KO.get(label, SECONDARY_LABELS_KO.get(label, label))


def korean_summary(item: dict[str, Any]) -> str:
    """Create a concise Korean digest without depending on a paid translation API."""
    classification = {
        "primary_topic": item.get("primary_topic"),
        "secondary_topic": item.get("secondary_topic"),
    }
    if not classification["primary_topic"] or not classification["secondary_topic"]:
        classification.update(classify_item(item))

    primary = topic_label_ko(classification["primary_topic"])
    secondary = topic_label_ko(classification["secondary_topic"])
    text = f" {item.get('title', '')} {item.get('summary', '')} ".lower()
    focus = _korean_focus(text)
    if item.get("type") == "news":
        source = str(item.get("source") or "공식 연구 채널")
        return f"{source}가 공개한 {primary} 분야의 {secondary} 관련 소식입니다. {focus}"
    return f"{primary} 분야에서 {secondary}를 다루는 연구입니다. {focus}"


def build_annual_trends(
    items: list[dict[str, Any]],
    *,
    metrics: list[dict[str, Any]] | None = None,
    year_count: int = 5,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compare yearly field volume, preferring official arXiv category totals when available."""
    now = now or datetime.now(timezone.utc)
    years = list(range(now.year - year_count + 1, now.year + 1))
    metric_rows = [row for row in (metrics or []) if int(row.get("year", 0)) in years]
    if metric_rows:
        return _build_official_annual_trends(metric_rows, years)

    totals: Counter[int] = Counter()
    counts: dict[str, Counter[int]] = {primary: Counter() for primary in TAXONOMY}

    for item in items:
        if item.get("type") != "paper":
            continue
        published = _parse_date(item.get("published_at"))
        if published is None or published.year not in years:
            continue
        primary = str(item.get("primary_topic") or "")
        if primary not in TAXONOMY:
            primary = classify_item(item)["primary_topic"]
        if primary not in TAXONOMY:
            continue
        totals[published.year] += 1
        counts[primary][published.year] += 1

    series: list[dict[str, Any]] = []
    for primary in TAXONOMY:
        yearly_counts = [counts[primary][year] for year in years]
        shares = [round(count / totals[year] * 100, 1) if totals[year] else 0 for count, year in zip(yearly_counts, years)]
        delta = round(shares[-1] - shares[-2], 1) if len(shares) > 1 else 0
        direction = "증가" if delta >= 0.8 else "감소" if delta <= -0.8 else "유지"
        series.append(
            {
                "primary": primary,
                "label_ko": topic_label_ko(primary),
                "counts": yearly_counts,
                "shares": shares,
                "latest_count": yearly_counts[-1],
                "delta_pp": delta,
                "direction": direction,
            }
        )

    series.sort(key=lambda row: (row["shares"][-1], row["latest_count"]), reverse=True)
    populated = [row for row in series if row["latest_count"] > 0]
    rising = max(populated, key=lambda row: row["delta_pp"], default=None)
    falling = min(populated, key=lambda row: row["delta_pp"], default=None)
    sparse = min(populated, key=lambda row: (row["shares"][-1], row["latest_count"]), default=None)

    insights: list[dict[str, Any]] = []
    if rising:
        insights.append({"kind": "rise", "label": "가장 빠른 증가", "topic": rising["label_ko"], "value": f"{rising['delta_pp']:+.1f}%p", "detail": f"{years[-2]}년 대비 논문 비중"})
    if falling:
        insights.append({"kind": "fall", "label": "비중 감소", "topic": falling["label_ko"], "value": f"{falling['delta_pp']:+.1f}%p", "detail": f"{years[-2]}년 대비 논문 비중"})
    if sparse:
        insights.append({"kind": "sparse", "label": "현재 표본이 적은 분야", "topic": sparse["label_ko"], "value": f"{sparse['shares'][-1]:.1f}%", "detail": f"{years[-1]}년 {sparse['latest_count']}편"})

    return {
        "years": [str(year) for year in years],
        "year_totals": [totals[year] for year in years],
        "series": series,
        "insights": insights,
        "note": "연도별 수집 논문 표본 안에서 각 분야가 차지하는 비중입니다. 현재 연도는 연중 누적 수치입니다.",
    }


def _build_official_annual_trends(metrics: list[dict[str, Any]], years: list[int]) -> dict[str, Any]:
    by_field: dict[str, dict[int, int]] = defaultdict(dict)
    labels: dict[str, str] = {}
    categories: dict[str, str] = {}
    source_urls: dict[str, str] = {}
    for row in metrics:
        key = str(row["field_key"])
        year = int(row["year"])
        by_field[key][year] = int(row["count"])
        labels[key] = str(row.get("field_label_ko") or key)
        categories[key] = str(row.get("category") or "")
        source_urls[key] = str(row.get("source_url") or "")

    totals = {year: sum(counts.get(year, 0) for counts in by_field.values()) for year in years}
    comparison_index = len(years) - 2 if len(years) >= 3 else len(years) - 1
    baseline_index = max(0, comparison_index - 1)
    comparison_years = [years[baseline_index], years[comparison_index]]
    series: list[dict[str, Any]] = []
    for field_key, counts_by_year in by_field.items():
        counts = [counts_by_year.get(year, 0) for year in years]
        shares = [round(count / totals[year] * 100, 1) if totals[year] else 0 for count, year in zip(counts, years)]
        previous = counts[baseline_index]
        comparison = counts[comparison_index]
        latest = counts[-1]
        growth = round((comparison - previous) / previous * 100, 1) if previous else 0.0
        direction = "증가" if growth >= 3 else "감소" if growth <= -3 else "유지"
        series.append(
            {
                "primary": field_key,
                "label_ko": labels[field_key],
                "category": categories[field_key],
                "counts": counts,
                "shares": shares,
                "latest_count": latest,
                "delta_pp": growth,
                "direction": direction,
                "source_url": source_urls[field_key],
            }
        )

    series.sort(key=lambda row: row["latest_count"], reverse=True)
    comparable = [row for row in series if row["counts"][baseline_index] > 0 and row["counts"][comparison_index] > 0]
    rising = max(comparable, key=lambda row: row["delta_pp"], default=None)
    falling = min(comparable, key=lambda row: row["delta_pp"], default=None)
    sparse = min((row for row in series if row["latest_count"] > 0), key=lambda row: row["latest_count"], default=None)
    insights: list[dict[str, Any]] = []
    if rising:
        insights.append({"kind": "rise", "label": "가장 빠른 증가", "topic": rising["label_ko"], "value": f"{rising['delta_pp']:+.1f}%", "detail": f"{comparison_years[0]}→{comparison_years[1]}년 arXiv 등록 수"})
    if falling:
        insights.append({"kind": "fall", "label": "증가세가 가장 낮은 분야", "topic": falling["label_ko"], "value": f"{falling['delta_pp']:+.1f}%", "detail": f"{comparison_years[0]}→{comparison_years[1]}년 arXiv 등록 수"})
    if sparse:
        insights.append({"kind": "sparse", "label": "현재 논문 수가 적은 분야", "topic": sparse["label_ko"], "value": f"{sparse['latest_count']:,}편", "detail": f"{years[-1]}년 누적 · {sparse['category']}"})

    return {
        "years": [str(year) for year in years],
        "year_totals": [totals[year] for year in years],
        "series": series,
        "insights": insights,
        "value_mode": "count",
        "comparison_label": f"{comparison_years[0]}→{comparison_years[1]}",
        "note": "arXiv 공식 연도별 카테고리 등록 수입니다. 현재 연도는 연중 누적이며 교차 등록 논문은 카테고리 간 중복될 수 있습니다.",
    }


def _korean_focus(text: str) -> str:
    if any(term in text for term in ("benchmark", "evaluation", "leaderboard", "compare")):
        return "모델과 방법의 성능을 측정하고 기존 접근법과 비교하는 데 초점을 둡니다."
    if any(term in text for term in ("survey", "systematic review", "literature review")):
        return "기존 연구 흐름과 주요 방법, 앞으로의 과제를 체계적으로 정리합니다."
    if any(term in text for term in ("dataset", "synthetic data", "data curation")):
        return "학습·평가용 데이터의 구성과 품질, 활용 방법을 핵심적으로 살펴봅니다."
    if any(term in text for term in ("agent", "tool use", "tool-using", "multi-agent")):
        return "에이전트의 계획, 도구 선택과 실행 과정의 정확성·안정성을 살펴봅니다."
    if any(term in text for term in ("multimodal", "vision-language", "image-text", "vlm")):
        return "텍스트와 이미지 등 여러 입력을 함께 이해하고 연결하는 방법을 다룹니다."
    if any(term in text for term in ("diffusion", "image generation", "video generation", "text-to-")):
        return "생성 품질과 제어 가능성, 학습·추론 효율을 개선하는 방법을 다룹니다."
    if any(term in text for term in ("safety", "alignment", "jailbreak", "adversarial", "robust")):
        return "모델의 안전성, 신뢰성 및 예상하지 못한 입력에 대한 대응을 분석합니다."
    if any(term in text for term in ("robot", "embodied", "manipulation", "control")):
        return "환경을 인식하고 행동을 계획·제어하는 로봇 지능의 성능을 다룹니다."
    if any(term in text for term in ("efficient", "inference", "quantization", "compression", "pruning")):
        return "학습·추론 비용을 낮추면서 성능을 유지하거나 높이는 방법을 제안합니다."
    return "새로운 방법과 실험 결과, 실제 활용 가능성을 중심으로 핵심 내용을 살펴봅니다."


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
