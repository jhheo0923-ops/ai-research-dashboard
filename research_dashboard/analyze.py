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

MOTIVATION_KO_BY_TOPIC: dict[str, str] = {
    "Language Models": "긴 문맥과 새로운 도메인에서 언어 모델의 정확성·일관성이 쉽게 흔들리고, 학습 및 추론 비용도 크다는 문제가 있습니다.",
    "Reasoning & Inference": "여러 단계의 추론에서는 작은 오류가 누적되며, 답이 맞더라도 추론 과정의 검증 가능성이 낮다는 한계가 있습니다.",
    "Agents & Tool Use": "에이전트가 계획을 세우고 외부 도구를 호출하는 과정에서 선택 오류가 연쇄적으로 커지고 장기 작업의 안정성이 떨어질 수 있습니다.",
    "Retrieval & Memory": "검색 결과의 관련성과 최신성이 부족하거나 장기 기억이 왜곡되면 생성 결과 전체의 신뢰성이 낮아집니다.",
    "Multimodal Foundation Models": "텍스트·이미지·음성 간 표현을 정확히 정렬하고 서로 다른 입력을 근거 있게 결합하는 일이 여전히 어렵습니다.",
    "Vision-Language": "시각 정보와 언어 지시를 함께 이해할 때 세부 객체·관계·공간 맥락을 놓치는 문제가 남아 있습니다.",
    "Image Generation": "생성 품질뿐 아니라 프롬프트 충실도, 세부 제어와 반복 생성의 일관성을 동시에 확보해야 합니다.",
    "Video Generation": "시간축의 움직임과 객체 일관성을 유지하면서도 고해상도 영상을 효율적으로 생성하기 어렵습니다.",
    "3D & Spatial": "제한된 관측만으로 3차원 구조와 공간 관계를 복원할 때 기하학적 오류와 일반화 문제가 발생합니다.",
    "Perception & Recognition": "실제 환경의 가림·노이즈·분포 변화에서도 객체와 장면을 안정적으로 인식해야 합니다.",
    "Robotics & Manipulation": "시뮬레이션과 실제 환경의 차이, 장기 행동 계획의 오차 때문에 로봇 정책을 현실에 안정적으로 적용하기 어렵습니다.",
    "Reinforcement Learning": "희소하거나 잘못 설계된 보상 아래에서 표본 효율과 정책 안정성을 동시에 얻기 어렵습니다.",
    "World Models": "환경의 동역학을 압축해 예측하면서도 장기 롤아웃에서 누적 오차를 억제해야 합니다.",
    "Planning & Control": "불확실한 환경에서 제약을 지키며 실시간으로 계획을 수정하고 제어해야 하는 부담이 큽니다.",
    "Safety & Alignment": "모델의 의도하지 않은 행동과 우회 공격을 줄이면서 유용성을 유지할 수 있는 검증 방법이 필요합니다.",
    "Robustness & Security": "적대적 입력과 분포 변화, 프롬프트 주입 상황에서 성능과 보안이 급격히 저하될 수 있습니다.",
    "Interpretability": "모델 내부 표현과 의사결정 근거를 사람이 검증하기 어려워 오류 원인과 위험을 추적하기 힘듭니다.",
    "Fairness & Governance": "데이터와 모델의 편향이 실제 의사결정에 확대 재생산될 수 있어 측정·완화·책임 체계가 필요합니다.",
    "Privacy": "학습 데이터의 민감 정보가 모델 출력이나 공격을 통해 노출될 수 있다는 위험이 있습니다.",
    "Efficient Training & Inference": "대규모 모델의 연산량·메모리·지연 시간이 연구 재현성과 실제 배포의 주요 제약이 됩니다.",
    "Evaluation & Benchmarks": "기존 지표가 실제 사용 능력과 실패 유형을 충분히 반영하지 못해 모델 간 공정한 비교가 어렵습니다.",
    "Data & Synthetic Data": "학습 데이터의 품질·대표성·라이선스 문제가 성능과 안전성에 직접 영향을 줍니다.",
    "Infrastructure & Hardware": "대규모 학습과 서빙에서 통신·메모리 병목이 비용과 처리량을 제한합니다.",
    "Optimization & Compression": "모델 크기와 비용을 줄이면 정확도와 강건성이 함께 저하될 수 있는 절충 문제가 있습니다.",
    "AI for Science": "복잡한 과학 현상을 학습한 모델이 물리적 제약과 불확실성을 함께 반영해야 합니다.",
    "Biology & Healthcare": "임상·생물 데이터의 희소성 및 기관 간 차이 때문에 높은 정확도와 안전한 일반화가 요구됩니다.",
    "Climate & Earth": "관측이 불완전한 시공간 데이터에서 극한 현상과 장기 변화를 안정적으로 예측해야 합니다.",
    "Math & Formal Methods": "정답뿐 아니라 검증 가능한 증명 과정과 엄밀한 제약 만족이 필요합니다.",
    "Recommenders & Search": "사용자 의도와 최신 정보를 반영하면서 편향·필터버블·관련성 저하를 줄여야 합니다.",
    "Representation & Self-Supervision": "라벨이 적은 환경에서도 전이 가능한 표현을 학습하고 불필요한 편향을 억제해야 합니다.",
    "Graph ML": "큰 그래프의 구조적 의존성을 보존하면서 확장성과 새로운 노드·그래프에 대한 일반화를 확보해야 합니다.",
    "Causal & Probabilistic": "상관관계만으로는 개입 효과와 불확실성을 설명하기 어려워 인과적 추론이 필요합니다.",
    "Continual & Federated": "새 지식을 학습하면서 기존 능력을 잊지 않고 분산 데이터의 개인정보도 보호해야 합니다.",
    "General Machine Learning": "새로운 데이터 분포에서도 성능이 유지되고 학습 결과를 재현할 수 있는 일반화가 핵심 과제입니다.",
    "Needs Review": "새 연구 결과나 시스템이 기존 접근법의 어떤 한계를 해결하며 실제 적용에 어떤 변화를 만드는지 확인할 필요가 있습니다.",
}


def topic_label_ko(value: str | None) -> str:
    label = str(value or "Unclassified")
    return PRIMARY_LABELS_KO.get(label, SECONDARY_LABELS_KO.get(label, label))


def korean_card_analysis(item: dict[str, Any]) -> dict[str, str]:
    """Create a structured Korean research digest without a paid translation API."""
    classification = {
        "primary_topic": item.get("primary_topic"),
        "secondary_topic": item.get("secondary_topic"),
    }
    if not classification["primary_topic"] or not classification["secondary_topic"]:
        classification.update(classify_item(item))

    primary_key = str(classification["primary_topic"])
    secondary_key = str(classification["secondary_topic"])
    primary = topic_label_ko(primary_key)
    secondary = topic_label_ko(secondary_key)
    text = f" {item.get('title', '')} {item.get('summary', '')} ".lower()
    focus = _korean_focus(text)
    motivation = _korean_motivation(text, secondary_key)
    contribution_focus = "제안된 접근법" if secondary_key == "Needs Review" else secondary
    contribution = _korean_contribution(text, contribution_focus)
    if item.get("type") == "news":
        source = str(item.get("source") or "공식 연구 채널")
        overview = f"{source}가 공개한 소식으로, {primary} 분야의 {secondary} 변화에 초점을 둡니다. {focus}"
    else:
        overview = f"{primary} 분야에 속하며 핵심 연구 주제는 {secondary}입니다. {focus}"
    return {"overview": overview, "motivation": motivation, "contribution": contribution}


def korean_summary(item: dict[str, Any]) -> str:
    return korean_card_analysis(item)["overview"]


def build_detailed_topic_insights(items: list[dict[str, Any]], *, limit: int = 18) -> dict[str, Any]:
    """Describe the current archive at second-level topic granularity."""
    papers = [item for item in items if item.get("type") == "paper"]
    counts: Counter[tuple[str, str]] = Counter()
    confidence_totals: Counter[tuple[str, str]] = Counter()
    term_counts: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)

    for item in papers:
        primary = str(item.get("primary_topic") or "")
        secondary = str(item.get("secondary_topic") or "")
        if not primary or not secondary:
            classification = classify_item(item)
            primary = classification["primary_topic"]
            secondary = classification["secondary_topic"]
        if secondary == "Needs Review":
            continue
        key = (primary, secondary)
        counts[key] += 1
        confidence_totals[key] += float(item.get("confidence") or 0)
        for term in item.get("matched_terms", []):
            clean = str(term).strip()
            if clean and not clean.startswith(("cs.", "stat.")):
                term_counts[key][clean] += 1

    total = sum(counts.values())
    active_topic_count = len(counts)
    possible_topic_count = sum(len(topics) for topics in TAXONOMY.values())
    parent_max: dict[str, int] = defaultdict(int)
    for (primary, _), count in counts.items():
        parent_max[primary] = max(parent_max[primary], count)

    rows: list[dict[str, Any]] = []
    for (primary, secondary), count in counts.items():
        share = round(count / total * 100, 1) if total else 0
        confidence = round(confidence_totals[(primary, secondary)] / count * 100) if count else 0
        status = "핵심축" if count == parent_max[primary] else "활성" if share >= 3 else "니치"
        rows.append(
            {
                "primary": primary,
                "primary_label_ko": topic_label_ko(primary),
                "secondary": secondary,
                "secondary_label_ko": topic_label_ko(secondary),
                "count": count,
                "share": share,
                "confidence": confidence,
                "status": status,
                "keywords": [term for term, _ in term_counts[(primary, secondary)].most_common(3)],
                "interpretation": MOTIVATION_KO_BY_TOPIC.get(secondary, "현재 표본에서 반복적으로 관찰되는 세부 연구 질문입니다."),
            }
        )

    rows.sort(key=lambda row: (row["count"], row["confidence"]), reverse=True)
    selected = rows[:limit]
    top_three_share = round(sum(row["count"] for row in rows[:3]) / total * 100, 1) if total else 0
    low_signal_topics = [
        topic_label_ko(secondary)
        for primary, topics in TAXONOMY.items()
        for secondary in topics
        if counts[(primary, secondary)] <= 1
    ]
    summaries = [
        {
            "label": "상위 주제 집중도",
            "value": f"{top_three_share:.1f}%",
            "detail": " · ".join(row["secondary_label_ko"] for row in rows[:3]) or "데이터 없음",
        },
        {
            "label": "활성 세부 주제",
            "value": f"{active_topic_count}/{possible_topic_count}",
            "detail": f"현재 논문 표본 {total:,}편에서 감지",
        },
        {
            "label": "탐색 여지가 큰 주제",
            "value": f"{len(low_signal_topics)}개",
            "detail": " · ".join(low_signal_topics[:4]) or "현재 없음",
        },
    ]
    return {
        "total_papers": total,
        "rows": selected,
        "summaries": summaries,
        "note": "최근 수집된 논문을 2차 연구 주제로 재분류한 표본 통계입니다. ‘탐색 여지’는 학계 전체의 부족이 아니라 현재 아카이브에서 신호가 적다는 뜻입니다.",
    }


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


def _korean_motivation(text: str, secondary: str) -> str:
    base = MOTIVATION_KO_BY_TOPIC.get(
        secondary,
        "기존 접근법의 정확성·효율·일반화 한계를 구체적으로 확인하고 개선할 필요가 있습니다.",
    )
    if any(term in text for term in ("limited data", "data scarcity", "few-shot", "low-resource")):
        return f"{base} 특히 제한된 데이터에서도 성능을 유지하는 것이 중요한 동기입니다."
    if any(term in text for term in ("real-world", "real world", "deployment", "in the wild")):
        return f"{base} 실제 환경으로 옮겼을 때 발생하는 성능 저하를 줄이는 것이 핵심 동기입니다."
    return base


def _korean_contribution(text: str, secondary_label: str) -> str:
    if any(term in text for term in ("survey", "systematic review", "literature review", "taxonomy")):
        base = "기존 연구를 방법·평가 기준·미해결 과제로 체계화해 후속 연구가 비교 가능한 공통 지도를 제공합니다."
    elif any(term in text for term in ("dataset", "data set", "corpus")):
        base = "새 데이터셋 또는 데이터 구성 절차를 제시해 학습과 평가에 사용할 수 있는 재현 가능한 기반을 넓힙니다."
    elif any(term in text for term in ("benchmark", "leaderboard", "evaluation suite")):
        base = "새 벤치마크와 평가 기준을 제안해 기존 방법의 강점·실패 유형을 동일한 조건에서 비교하도록 합니다."
    elif any(term in text for term in ("theorem", "proof", "theoretical", "bound")):
        base = "이론적 분석과 검증 가능한 조건을 제시해 방법이 작동하는 범위와 한계를 설명합니다."
    elif any(term in text for term in ("system", "platform", "toolkit", "pipeline")):
        base = "여러 구성 요소를 연결한 시스템 또는 파이프라인을 구현해 실제 사용과 반복 실험이 가능한 형태로 제시합니다."
    elif any(term in text for term in ("we propose", "we introduce", "we present", "novel method", "framework", "architecture")):
        base = "새 모델·학습법 또는 프레임워크를 제안하고 기존 접근법과의 실험 비교를 통해 효과를 검증합니다."
    else:
        base = "실험과 분석을 통해 기존 접근법의 동작 특성을 설명하고 개선 가능성을 뒷받침하는 근거를 제공합니다."

    if any(term in text for term in ("efficient", "latency", "memory", "compute", "quantization", "compression")):
        focus = "특히 계산량·메모리·지연 시간을 줄이면서 성능을 유지하는지가 기여의 핵심입니다."
    elif any(term in text for term in ("safety", "robust", "adversarial", "alignment", "privacy")):
        focus = "특히 안전성·강건성·신뢰성 측면의 실패를 줄이는 데 기여합니다."
    elif any(term in text for term in ("generalization", "domain shift", "out-of-distribution", "transfer")):
        focus = "특히 새로운 데이터와 환경으로의 일반화 성능을 검증하는 데 초점을 둡니다."
    else:
        focus = f"핵심 검증 대상은 {secondary_label}의 성능과 실제 적용 가능성입니다."
    return f"{base} {focus}"


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
