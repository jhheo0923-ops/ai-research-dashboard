(function () {
  "use strict";

  const data = window.RESEARCH_DATA || {};
  const state = {
    route: "overview", filter: "all", topic: "all", query: "", conferenceField: "all",
    cardFilter: "all", cardSort: "importance", cardTopic: "all", cardSubtopic: "all", cardLimit: 24,
    readIds: new Set(), starredIds: new Set()
  };
  const routeMeta = {
    overview: ["DAILY INTELLIGENCE", "오늘의 AI 리서치 브리핑"],
    cards: ["RESEARCH DIGEST", "논문 · 뉴스 카드"],
    statistics: ["RESEARCH ANALYTICS", "통계 · 인사이트"],
    search: ["RESEARCH ARCHIVE", "검색 · 아카이브"],
    conferences: ["CONFERENCE RADAR", "학회 레이더"],
    sources: ["PIPELINE STATUS", "수집 소스"]
  };
  const typeLabels = { paper: "논문", news: "뉴스", conference: "학회" };
  const timelineKinds = { paper: "논문", decision: "결과", workshop: "워크샵", conference: "본학회" };

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
  const safeUrl = (value) => /^https?:\/\//i.test(value || "") ? value : "#";

  function formatDate(value) {
    if (!value) return "아직 없음";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
  }

  function shortDate(value) {
    if (!value) return "";
    const parts = value.split("-");
    return `${parts[0]}.${parts[1]}.${parts[2]}`;
  }

  function loadSavedSet(key) {
    try {
      const saved = JSON.parse(localStorage.getItem(key) || "[]");
      return new Set(Array.isArray(saved) ? saved : []);
    } catch (_error) {
      return new Set();
    }
  }

  function loadCardState() {
    state.readIds = loadSavedSet("signal.card.read.v1");
    state.starredIds = loadSavedSet("signal.card.starred.v1");
  }

  function saveCardState() {
    try {
      localStorage.setItem("signal.card.read.v1", JSON.stringify([...state.readIds]));
      localStorage.setItem("signal.card.starred.v1", JSON.stringify([...state.starredIds]));
    } catch (_error) {
      // File and privacy-restricted browsers may decline local storage.
    }
  }

  function renderMetrics() {
    const metrics = data.metrics || {};
    const rows = [
      ["오늘 수집", metrics.today || 0, "새로운 신호"],
      ["논문 아카이브", metrics.papers || 0, "검색 가능"],
      ["뉴스 · 블로그", metrics.news || 0, "공식 채널"],
      ["추적 학회", metrics.conferences || 0, "주요 AI 학회"]
    ];
    $("#metric-grid").innerHTML = rows.map(([label, value, note]) => `<article class="metric"><div class="metric-label">${escapeHtml(label)}</div><div class="metric-value">${Number(value).toLocaleString("ko-KR")}</div><div class="metric-note"><strong>●</strong> ${escapeHtml(note)}</div></article>`).join("");
  }

  function renderBriefing() {
    const briefing = data.briefing || [];
    $("#briefing-list").innerHTML = briefing.slice(0, 4).map((item, index) => `<article class="briefing-item"><span class="briefing-num">${String(index + 1).padStart(2, "0")}</span><div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.summary)}</p><div class="briefing-meta">${(item.tags || []).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div></div></article>`).join("");
  }

  function renderTrends() {
    $("#trend-list").innerHTML = (data.trends || []).slice(0, 7).map(item => `<div class="trend-row"><div class="trend-copy"><div><small>${escapeHtml(item.primary || "연구 분야")}</small><strong>${escapeHtml(item.secondary || item.label)}</strong></div><span>${escapeHtml(item.delta)}</span></div><div class="trend-track"><i style="width:${Math.max(2, Math.min(100, Number(item.score) || 0))}%"></i></div></div>`).join("");
  }

  function renderLatest() {
    const items = (data.items || []).slice(0, 6);
    $("#latest-list").innerHTML = items.length ? items.map(item => `<a class="latest-item" href="${safeUrl(item.url)}" target="_blank" rel="noreferrer"><span class="source-badge">${escapeHtml(item.source || typeLabels[item.type] || "자료")}</span><div><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml((item.summary_ko || item.summary || "").slice(0, 150))}</p><span class="topic-line">${escapeHtml(item.primary_topic_ko || item.primary_topic || "미분류")} › ${escapeHtml(item.secondary_topic_ko || item.secondary_topic || "미분류")}</span></div><time>${escapeHtml(item.date_label || formatDate(item.published_at))}</time></a>`).join("") : `<div class="empty-state">첫 수집을 실행하면 최신 자료가 여기에 표시됩니다.</div>`;
  }

  function researchCards() {
    return (data.items || []).filter(item => item.type === "paper" || item.type === "news");
  }

  function cardImportanceClass(score) {
    if (score >= 80) return "critical";
    if (score >= 65) return "high";
    if (score >= 50) return "medium";
    return "normal";
  }

  function renderCardStats() {
    const items = researchCards();
    const read = items.filter(item => state.readIds.has(item.external_id)).length;
    const starred = items.filter(item => state.starredIds.has(item.external_id)).length;
    const stats = [
      ["all", "전체 카드", items.length, "TOTAL"],
      ["unread", "안 읽은 카드", items.length - read, "UNREAD"],
      ["read", "읽은 카드", read, "READ"],
      ["starred", "별표 카드", starred, "STARRED"]
    ];
    $("#card-stats").innerHTML = stats.map(([filter, label, count, eyebrow]) => `<button class="card-stat ${state.cardFilter === filter ? "active" : ""}" data-card-stat-filter="${filter}" type="button"><span>${eyebrow}</span><strong>${Number(count).toLocaleString("ko-KR")}</strong><small>${escapeHtml(label)}</small></button>`).join("");
  }

  function renderCardFilters() {
    $$(".card-filter").forEach(button => button.classList.toggle("active", button.dataset.cardFilter === state.cardFilter));
  }

  function renderCardCategories() {
    const items = researchCards();
    const categories = new Map();
    items.forEach(item => {
      const key = item.primary_topic || "Unclassified";
      const current = categories.get(key) || { count: 0, label: item.primary_topic_ko || key };
      current.count += 1;
      categories.set(key, current);
    });
    const rows = [...categories.entries()].sort((a, b) => b[1].count - a[1].count);
    $("#card-category-filters").innerHTML = [["all", { label: "전체 분야", count: items.length }], ...rows].map(([key, value]) => `<button class="card-category-filter ${state.cardTopic === key ? "active" : ""}" data-card-topic="${escapeHtml(key)}" type="button"><span>${escapeHtml(value.label)}</span><b>${value.count}</b></button>`).join("");

    const secondaries = [...new Map(items
      .filter(item => state.cardTopic === "all" || item.primary_topic === state.cardTopic)
      .map(item => [item.secondary_topic || "Unclassified", item.secondary_topic_ko || item.secondary_topic || "미분류"])).entries()]
      .sort((a, b) => a[1].localeCompare(b[1], "ko"));
    if (state.cardSubtopic !== "all" && !secondaries.some(([key]) => key === state.cardSubtopic)) state.cardSubtopic = "all";
    $("#card-subtopic-filter").innerHTML = `<option value="all">모든 세부 주제</option>${secondaries.map(([key, label]) => `<option value="${escapeHtml(key)}" ${state.cardSubtopic === key ? "selected" : ""}>${escapeHtml(label)}</option>`).join("")}`;
  }

  function sortedCardItems() {
    const filtered = researchCards().filter(item => {
      const isRead = state.readIds.has(item.external_id);
      const isStarred = state.starredIds.has(item.external_id);
      if (state.cardTopic !== "all" && item.primary_topic !== state.cardTopic) return false;
      if (state.cardSubtopic !== "all" && item.secondary_topic !== state.cardSubtopic) return false;
      if (state.cardFilter === "unread") return !isRead;
      if (state.cardFilter === "read") return isRead;
      if (state.cardFilter === "starred") return isStarred;
      return true;
    });
    return filtered.sort((a, b) => {
      const readOrder = Number(state.readIds.has(a.external_id)) - Number(state.readIds.has(b.external_id));
      if (readOrder) return readOrder;
      if (state.cardSort === "latest") return (new Date(b.published_at || 0).getTime() || 0) - (new Date(a.published_at || 0).getTime() || 0);
      if (state.cardSort === "oldest") return (new Date(a.published_at || 0).getTime() || 0) - (new Date(b.published_at || 0).getTime() || 0);
      return Number(b.importance_score || 0) - Number(a.importance_score || 0)
        || (new Date(b.published_at || 0).getTime() || 0) - (new Date(a.published_at || 0).getTime() || 0);
    });
  }

  function renderCards() {
    const items = sortedCardItems();
    const visible = items.slice(0, state.cardLimit);
    renderCardStats();
    renderCardFilters();
    renderCardCategories();
    $("#card-grid").innerHTML = visible.length ? visible.map(item => {
      const id = escapeHtml(item.external_id);
      const isRead = state.readIds.has(item.external_id);
      const isStarred = state.starredIds.has(item.external_id);
      const importance = Number(item.importance_score || 0);
      const importanceClass = cardImportanceClass(importance);
      const keywords = (item.keywords || []).filter(Boolean).slice(0, 4);
      return `<article class="news-card ${isRead ? "is-read" : ""} ${isStarred ? "is-starred" : ""}"><div class="news-card-accent ${importanceClass}"></div><div class="news-card-top"><span class="source-badge">${escapeHtml(item.source || typeLabels[item.type])}</span><span class="importance-badge ${importanceClass}"><b>${importance}</b><small>${escapeHtml(item.importance_label || "일반")}</small></span></div><div class="card-label">${escapeHtml(typeLabels[item.type] || item.type)} HEADLINE</div><h3>${escapeHtml(item.title)}</h3><div class="card-topic">${escapeHtml(item.primary_topic_ko || item.primary_topic || "미분류")} <span>›</span> ${escapeHtml(item.secondary_topic_ko || item.secondary_topic || "미분류")}</div><p class="card-summary-ko"><b>한글 요약</b>${escapeHtml((item.summary_ko || "한글 요약 정보가 없습니다.").slice(0, 360))}</p><div class="card-research-analysis"><section><span>WHY · MOTIVATION</span><p>${escapeHtml((item.motivation_ko || "연구 동기를 분석 중입니다.").slice(0, 360))}</p></section><section><span>WHAT · CONTRIBUTION</span><p>${escapeHtml((item.contribution_ko || "핵심 기여를 분석 중입니다.").slice(0, 420))}</p></section></div><div class="card-keywords">${keywords.map(keyword => `<span>#${escapeHtml(keyword)}</span>`).join("")}</div><div class="importance-reason">${escapeHtml(item.importance_reason || "연구 신호")} · ${escapeHtml(item.date_label || formatDate(item.published_at))}</div><div class="news-card-actions"><a href="${safeUrl(item.url)}" data-card-open="${id}" target="_blank" rel="noreferrer">원문 읽기 ↗</a><div><button class="card-action star ${isStarred ? "active" : ""}" data-card-action="star" data-card-id="${id}" type="button" aria-label="${isStarred ? "별표 해제" : "별표 추가"}" aria-pressed="${isStarred}">${isStarred ? "★" : "☆"}</button><button class="card-action read ${isRead ? "active" : ""}" data-card-action="read" data-card-id="${id}" type="button" aria-label="${isRead ? "읽지 않음으로 표시" : "읽음으로 표시"}" aria-pressed="${isRead}">${isRead ? "읽음 ✓" : "읽음"}</button></div></div></article>`;
    }).join("") : `<div class="empty-state card-empty">선택한 조건에 해당하는 카드가 없습니다.</div>`;
    $("#card-more").hidden = items.length <= state.cardLimit;
  }

  function renderConferenceMini() {
    $("#conference-mini").innerHTML = (data.conferences || []).filter(item => item.status !== "아카이브").slice(0, 3).map(item => `<div class="conference-chip"><span class="conference-code">${escapeHtml(item.code)}</span><div><strong>${escapeHtml(item.name)}</strong><span>${escapeHtml(item.date_label)}</span></div></div>`).join("");
  }

  function conferenceGroup(item) {
    return String(item.field || "General AI").split(" · ")[0];
  }

  function renderConferenceFilters() {
    const fields = [...new Set((data.conferences || []).map(conferenceGroup))];
    $("#conference-filters").innerHTML = ["all", ...fields].map(field => `<button class="conference-filter ${state.conferenceField === field ? "active" : ""}" data-conference-field="${escapeHtml(field)}" type="button">${field === "all" ? "전체" : escapeHtml(field)}</button>`).join("");
  }

  function parseCycleDate(value) {
    const date = new Date(`${value}T00:00:00Z`);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function conferenceTimelineRange(items) {
    const starts = items.map(item => parseCycleDate(item.cycle?.submission_open)).filter(Boolean);
    const ends = items.map(item => parseCycleDate(item.cycle?.decision_date)).filter(Boolean);
    if (!starts.length || !ends.length) return { start: new Date("2026-01-01T00:00:00Z"), end: new Date("2026-12-31T00:00:00Z") };
    const start = new Date(Math.min(...starts.map(date => date.getTime())));
    const end = new Date(Math.max(...ends.map(date => date.getTime())));
    start.setUTCDate(1);
    end.setUTCMonth(end.getUTCMonth() + 1, 0);
    return { start, end };
  }

  function cyclePosition(value, range) {
    const date = parseCycleDate(value);
    if (!date) return 0;
    const duration = Math.max(1, range.end.getTime() - range.start.getTime());
    return Math.max(0, Math.min(100, (date.getTime() - range.start.getTime()) / duration * 100));
  }

  function cycleMidpoint(start, end) {
    const startDate = parseCycleDate(start);
    const endDate = parseCycleDate(end);
    if (!startDate || !endDate) return start;
    return new Date((startDate.getTime() + endDate.getTime()) / 2).toISOString().slice(0, 10);
  }

  function conferenceMonthMarkers(range) {
    const rows = [];
    const cursor = new Date(Date.UTC(range.start.getUTCFullYear(), range.start.getUTCMonth(), 1));
    while (cursor <= range.end) {
      const value = cursor.toISOString().slice(0, 10);
      rows.push({
        value,
        position: cyclePosition(value, range),
        label: cursor.getUTCMonth() === 0 || rows.length === 0 ? `${cursor.getUTCFullYear()} · ${cursor.getUTCMonth() + 1}월` : `${cursor.getUTCMonth() + 1}월`,
      });
      cursor.setUTCMonth(cursor.getUTCMonth() + 1);
    }
    return rows;
  }

  function cycleMarker(kind, date, range, label) {
    const position = cyclePosition(date, range);
    return `<span class="cycle-marker ${kind}" style="--point:${position}%" title="${escapeHtml(label)} · ${escapeHtml(shortDate(date))}"><i></i><b>${escapeHtml(label)}</b><em>${escapeHtml(shortDate(date))}</em></span>`;
  }

  function renderConferences() {
    const all = (data.conferences || []).filter(item => item.cycle);
    const filtered = all.filter(item => state.conferenceField === "all" || conferenceGroup(item) === state.conferenceField);
    const range = conferenceTimelineRange(all);
    const months = conferenceMonthMarkers(range);
    const monthLabels = months.map(month => `<span style="left:${month.position}%">${escapeHtml(month.label)}</span>`).join("");
    const gridLines = months.map(month => `<i style="left:${month.position}%"></i>`).join("");
    const rows = filtered.map(item => {
      const cycle = item.cycle;
      const submissionStart = cyclePosition(cycle.submission_open, range);
      const submissionEnd = cyclePosition(cycle.submission_deadline, range);
      const decision = cyclePosition(cycle.decision_date, range);
      const reviewDate = cycleMidpoint(cycle.review_start, cycle.review_end);
      return `<div class="conference-cycle-row"><a class="cycle-conference" href="${safeUrl(item.url)}" target="_blank" rel="noreferrer"><strong>${escapeHtml(item.code)}</strong><span>${escapeHtml(item.name)}</span><small>${escapeHtml(item.field)}</small></a><div class="cycle-track" aria-label="${escapeHtml(item.code)} 논문 제출부터 채택 발표까지"><div class="cycle-gridlines">${gridLines}</div><span class="cycle-segment submission" style="--segment-start:${submissionStart}%;--segment-end:${submissionEnd}%"></span><span class="cycle-segment review" style="--segment-start:${submissionEnd}%;--segment-end:${decision}%"></span>${cycleMarker("open", cycle.submission_open, range, "접수 시작")}${cycleMarker("deadline", cycle.submission_deadline, range, "제출 마감")}${cycleMarker("review", reviewDate, range, "리뷰")}${cycleMarker("decision", cycle.decision_date, range, "최종 발표")}</div><div class="cycle-result"><span>${escapeHtml(item.status)}</span><strong>${escapeHtml(shortDate(cycle.decision_date))}</strong></div></div>`;
    }).join("");
    $("#conference-grid").innerHTML = `<section class="conference-master-panel"><div class="conference-master-scroll"><div class="conference-master"><div class="conference-master-axis"><div><span>학회</span><small>제출 → 리뷰 → 발표</small></div><div class="cycle-month-axis">${monthLabels}</div><div class="axis-result">결과일</div></div><div class="conference-cycle-list">${rows || `<div class="empty-state">선택한 분야의 학회 일정이 없습니다.</div>`}</div></div></div><div class="conference-master-foot"><span>${filtered.length}개 학회 · ${escapeHtml(shortDate(range.start.toISOString().slice(0, 10)))}–${escapeHtml(shortDate(range.end.toISOString().slice(0, 10)))}</span><span>원 위에 마우스를 올리면 정확한 날짜를 볼 수 있습니다.</span></div></section>`;
    $$(".conference-filter").forEach(button => button.addEventListener("click", () => {
      state.conferenceField = button.dataset.conferenceField;
      renderConferenceFilters();
      renderConferences();
    }));
  }

  function renderSources() {
    $("#source-grid").innerHTML = (data.sources || []).map(item => `<article class="source-card"><div class="source-card-top"><span class="source-badge">${escapeHtml(item.kind)}</span><span class="status ${item.status === "정상" ? "ok" : "pending"}">${escapeHtml(item.status)}</span></div><h3>${escapeHtml(item.name)}</h3><p>${Number(item.count || 0).toLocaleString("ko-KR")}개 자료 수집</p>${item.message ? `<small class="source-message">${escapeHtml(item.message.slice(0, 120))}</small>` : ""}</article>`).join("");
  }

  function renderStatistics() {
    const stats = data.statistics || {};
    const kpis = stats.kpis || {};
    const rows = [
      ["분석 아카이브", kpis.archived_items || 0, "개"],
      ["정상 수집 소스", kpis.active_sources || 0, "개"],
      ["고유 연구자", kpis.unique_authors || 0, "명"],
      ["분류 신뢰 범위", kpis.classified_percent || 0, "%"]
    ];
    $("#stat-kpis").innerHTML = rows.map(([label, value, unit]) => `<article class="stat-kpi"><span>${escapeHtml(label)}</span><strong>${Number(value).toLocaleString("ko-KR")}<small>${unit}</small></strong></article>`).join("");

    const daily = stats.daily_volume || [];
    const maxDay = Math.max(1, ...daily.map(item => item.count || 0));
    $("#volume-chart").innerHTML = daily.map((item, index) => {
      const paperHeight = (item.papers || 0) / maxDay * 100;
      const newsHeight = (item.news || 0) / maxDay * 100;
      const label = index % 7 === 0 || index === daily.length - 1 ? item.day.slice(5).replace("-", ".") : "";
      return `<div class="volume-day" title="${escapeHtml(item.day)} · ${item.count || 0}개"><div class="volume-stack"><i class="news" style="height:${newsHeight}%"></i><i class="paper" style="height:${paperHeight}%"></i></div><span>${label}</span></div>`;
    }).join("");

    const types = stats.types || [];
    const typeTotal = Math.max(1, types.reduce((sum, item) => sum + item.count, 0));
    const paperCount = (types.find(item => item.type === "paper") || {}).count || 0;
    const paperPercent = Math.round(paperCount / typeTotal * 100);
    $("#type-mix").innerHTML = `<div class="donut" style="--paper:${paperPercent}%"><div><strong>${typeTotal.toLocaleString("ko-KR")}</strong><span>전체 자료</span></div></div><div class="mix-list">${types.map(item => `<div><span><i class="${escapeHtml(item.type)}"></i>${escapeHtml(typeLabels[item.type] || item.type)}</span><strong>${Number(item.count).toLocaleString("ko-KR")}</strong></div>`).join("")}</div>`;

    renderBars("#taxonomy-bars", stats.taxonomy || [], "primary");
    renderBars("#source-bars", stats.sources || [], "source");
    $("#taxonomy-map").innerHTML = (stats.taxonomy || []).map(group => `<article class="taxonomy-group"><div><strong>${escapeHtml(group.primary)}</strong><span>${Number(group.count).toLocaleString("ko-KR")}</span></div><ul>${(group.secondaries || []).slice(0, 6).map(item => `<li><span>${escapeHtml(item.secondary)}</span><em>${item.count}</em></li>`).join("")}</ul></article>`).join("");
    renderAnnualTrends(stats.annual_trends || {});
    renderDetailedTopics(stats.detailed_topics || {});
  }

  function renderDetailedTopics(details) {
    const summaries = details.summaries || [];
    const rows = details.rows || [];
    $("#detailed-topic-summary").innerHTML = summaries.map(item => `<article><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.value)}</strong><small>${escapeHtml(item.detail)}</small></article>`).join("");
    const maximum = Math.max(1, ...rows.map(item => Number(item.count || 0)));
    $("#detailed-topic-list").innerHTML = rows.length ? rows.map(item => {
      const width = Number(item.count || 0) / maximum * 100;
      const keywords = (item.keywords || []).map(keyword => `<em>#${escapeHtml(keyword)}</em>`).join("");
      return `<article class="detailed-topic-item"><div class="detailed-topic-head"><div><span>${escapeHtml(item.primary_label_ko || item.primary)}</span><h3>${escapeHtml(item.secondary_label_ko || item.secondary)}</h3></div><b class="topic-signal ${item.status === "핵심축" ? "core" : item.status === "활성" ? "active" : "niche"}">${escapeHtml(item.status)}</b></div><div class="detailed-topic-metrics"><strong>${Number(item.count || 0).toLocaleString("ko-KR")}편</strong><span>${Number(item.share || 0).toFixed(1)}%</span><i><b style="width:${width.toFixed(1)}%"></b></i></div><p>${escapeHtml(item.interpretation || "")}</p><div class="detailed-topic-foot"><span>분류 신뢰도 ${Number(item.confidence || 0)}%</span><div>${keywords || "<em>세부 키워드 분석 중</em>"}</div></div></article>`;
    }).join("") : `<div class="empty-state">세부 주제 통계를 만들 논문 표본이 아직 없습니다.</div>`;
    $("#detailed-topic-note").textContent = details.note || "";
  }

  function renderAnnualTrends(annual) {
    const years = annual.years || [];
    const series = annual.series || [];
    const insights = annual.insights || [];
    const countMode = annual.value_mode === "count";
    $("#annual-trend-insights").innerHTML = insights.map(item => `<article class="annual-insight ${escapeHtml(item.kind)}"><span>${escapeHtml(item.label)}</span><div><strong>${escapeHtml(item.topic)}</strong><b>${escapeHtml(item.value)}</b></div><small>${escapeHtml(item.detail)}</small></article>`).join("");
    if (!years.length || !series.length) {
      $("#annual-trend-matrix").innerHTML = `<div class="empty-state">연도별 논문 데이터가 아직 충분하지 않습니다.</div>`;
      $("#annual-trend-note").textContent = annual.note || "";
      return;
    }

    const palette = ["#76f7c5", "#7ea6ff", "#ffcb6b", "#f18f9f", "#9a8cff", "#50d5d0", "#f6a561", "#74b9e8", "#c8ef74", "#d68cff", "#e4d06f", "#77d99e", "#ff8c69"];
    const values = series.flatMap(item => (countMode ? (item.counts || []) : (item.shares || [])).map(Number));
    const maximum = Math.max(1, ...values);
    const formatter = value => countMode ? Number(value).toLocaleString("ko-KR") : `${Number(value).toFixed(1)}%`;
    const axisMaximum = countMode ? Math.ceil(maximum / 1000) * 1000 : Math.ceil(maximum / 5) * 5;
    const axisTicks = [axisMaximum, axisMaximum * .75, axisMaximum * .5, axisMaximum * .25, 0];
    const shortCode = category => String(category || "").replace(/^(cs|stat)\./, "");

    const legend = series.map((item, index) => `<div class="annual-category-key"><i style="--category-color:${palette[index % palette.length]}"></i><span>${escapeHtml(item.label_ko || item.primary)}</span><code>${escapeHtml(item.category || item.primary)}</code></div>`).join("");
    const groups = years.map((year, yearIndex) => {
      const isCurrent = yearIndex === years.length - 1;
      const bars = series.map((item, categoryIndex) => {
        const chartValues = countMode ? (item.counts || []) : (item.shares || []);
        const value = Number(chartValues[yearIndex] || 0);
        const height = value > 0 ? Math.max(1.5, value / axisMaximum * 100) : 0;
        const display = formatter(value);
        const unit = countMode ? "편" : "";
        return `<div class="annual-grouped-bar" title="${escapeHtml(year)} · ${escapeHtml(item.label_ko || item.primary)} · ${display}${unit}"><div class="annual-grouped-plot"><i style="height:${height.toFixed(2)}%;--category-color:${palette[categoryIndex % palette.length]}"></i></div><strong>${display}</strong><small>${escapeHtml(shortCode(item.category || item.primary))}</small></div>`;
      }).join("");
      return `<section class="annual-year-group ${isCurrent ? "current" : ""}" aria-label="${escapeHtml(year)}년 13개 분야"><div class="annual-year-bars">${bars}</div><div class="annual-year-heading"><strong>${escapeHtml(year)}</strong><span>${isCurrent ? "연중 누적" : `${series.length}개 분야`}</span></div></section>`;
    }).join("");
    const axis = axisTicks.map((value, index) => `<span style="top:${index * 25}%">${escapeHtml(formatter(value))}</span>`).join("");

    $("#annual-trend-matrix").innerHTML = `<div class="annual-grouped-shell"><div class="annual-chart-meta"><div><span>공통 Y축</span><strong>최대 ${formatter(axisMaximum)}${countMode ? "편" : ""}</strong></div><p>같은 색은 같은 분야입니다. 가로로 이동해 연도별 13개 분야를 연속 비교하세요.</p></div><div class="annual-category-legend">${legend}</div><div class="annual-grouped-scroll" tabindex="0"><div class="annual-grouped-layout" style="--category-count:${series.length}"><div class="annual-y-axis" aria-hidden="true">${axis}</div><div class="annual-year-groups" role="img" aria-label="연도별 13개 연구 분야 논문 수 통합 막대그래프">${groups}</div></div></div></div>`;
    $("#annual-trend-note").textContent = annual.note || "";
  }

  function renderBars(selector, rows, labelKey) {
    const maxValue = Math.max(1, ...rows.map(item => item.count || 0));
    $(selector).innerHTML = rows.slice(0, 10).map(item => `<div class="bar-row"><div><span>${escapeHtml(item[labelKey])}</span><strong>${Number(item.count).toLocaleString("ko-KR")}</strong></div><i><b style="width:${item.count / maxValue * 100}%"></b></i></div>`).join("");
  }

  function searchableItems() {
    const conferenceItems = (data.conferences || []).map(item => ({ ...item, type: "conference", title: `${item.code} — ${item.name}`, summary: item.date_label, source: "Official", published_at: "", keywords: [item.code, item.field], primary_topic: "Research Community", secondary_topic: item.field }));
    return [...(data.items || []), ...conferenceItems];
  }

  function renderTopicOptions() {
    const topics = [...new Set((data.items || []).map(item => item.primary_topic).filter(Boolean))].sort();
    $("#topic-filter").innerHTML = `<option value="all">모든 연구 분야</option>${topics.map(topic => `<option value="${escapeHtml(topic)}">${escapeHtml(topic)}</option>`).join("")}`;
  }

  function renderSearch() {
    const needle = state.query.trim().toLocaleLowerCase("ko");
    const filtered = searchableItems().filter(item => {
      if (state.filter !== "all" && item.type !== state.filter) return false;
      if (state.topic !== "all" && item.primary_topic !== state.topic) return false;
      if (!needle) return true;
      const haystack = [item.title, item.summary_ko, item.motivation_ko, item.contribution_ko, item.summary, item.source, item.primary_topic, item.secondary_topic, item.primary_topic_ko, item.secondary_topic_ko, ...(item.authors || []), ...(item.keywords || [])].join(" ").toLocaleLowerCase("ko");
      return haystack.includes(needle);
    });
    $("#result-count").textContent = `${filtered.length.toLocaleString("ko-KR")}개 결과`;
    $("#search-results").innerHTML = filtered.length ? filtered.map(item => `<a class="result-card" href="${safeUrl(item.url)}" target="_blank" rel="noreferrer"><span class="result-type">${escapeHtml(typeLabels[item.type] || item.type)}</span><div><div class="topic-path"><span>${escapeHtml(item.primary_topic_ko || item.primary_topic || "미분류")}</span><b>›</b><span>${escapeHtml(item.secondary_topic_ko || item.secondary_topic || "미분류")}</span></div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml((item.summary_ko || item.summary || "설명 없음").slice(0, 260))}</p><div class="result-meta">${escapeHtml(item.source || "공식 채널")} · ${escapeHtml(item.date_label || formatDate(item.published_at))}</div></div><span class="result-arrow">↗</span></a>`).join("") : `<div class="empty-state">검색 조건과 일치하는 자료가 없습니다.</div>`;
  }

  function setRoute(route) {
    if (!routeMeta[route]) return;
    state.route = route;
    $$(".view").forEach(view => view.classList.toggle("active", view.id === `view-${route}`));
    $$(".nav-item").forEach(button => button.classList.toggle("active", button.dataset.route === route));
    $("#page-eyebrow").textContent = routeMeta[route][0];
    $("#page-title").textContent = routeMeta[route][1];
    document.body.classList.remove("menu-open");
    history.replaceState(null, "", `#${route}`);
    if (route === "search") setTimeout(() => $("#search-input").focus(), 60);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function bindEvents() {
    $$('[data-route]').forEach(button => button.addEventListener("click", () => setRoute(button.dataset.route)));
    $$(".filter").forEach(button => button.addEventListener("click", () => {
      state.filter = button.dataset.filter;
      $$(".filter").forEach(item => item.classList.toggle("active", item === button));
      renderSearch();
    }));
    $("#topic-filter").addEventListener("change", event => { state.topic = event.target.value; renderSearch(); });
    $("#search-input").addEventListener("input", event => { state.query = event.target.value; renderSearch(); });
    $$(".card-filter").forEach(button => button.addEventListener("click", () => {
      state.cardFilter = button.dataset.cardFilter;
      state.cardLimit = 24;
      renderCards();
    }));
    $("#card-category-filters").addEventListener("click", event => {
      const button = event.target.closest("[data-card-topic]");
      if (!button) return;
      state.cardTopic = button.dataset.cardTopic;
      state.cardSubtopic = "all";
      state.cardLimit = 24;
      renderCards();
    });
    $("#card-subtopic-filter").addEventListener("change", event => {
      state.cardSubtopic = event.target.value;
      state.cardLimit = 24;
      renderCards();
    });
    $("#card-sort").addEventListener("change", event => {
      state.cardSort = event.target.value;
      state.cardLimit = 24;
      renderCards();
    });
    $("#card-more").addEventListener("click", () => {
      state.cardLimit += 24;
      renderCards();
    });
    $("#card-stats").addEventListener("click", event => {
      const button = event.target.closest("[data-card-stat-filter]");
      if (!button) return;
      state.cardFilter = button.dataset.cardStatFilter;
      state.cardLimit = 24;
      renderCards();
    });
    $("#card-grid").addEventListener("click", event => {
      const openLink = event.target.closest("[data-card-open]");
      if (openLink) {
        state.readIds.add(openLink.dataset.cardOpen);
        saveCardState();
        window.setTimeout(renderCards, 80);
        return;
      }
      const button = event.target.closest("[data-card-action]");
      if (!button) return;
      const id = button.dataset.cardId;
      const target = button.dataset.cardAction === "star" ? state.starredIds : state.readIds;
      target.has(id) ? target.delete(id) : target.add(id);
      saveCardState();
      renderCards();
    });
    $("#menu-button").addEventListener("click", () => document.body.classList.add("menu-open"));
    $("#scrim").addEventListener("click", () => document.body.classList.remove("menu-open"));
    window.addEventListener("hashchange", () => setRoute(location.hash.slice(1) || "overview"));
    document.addEventListener("keydown", event => {
      if (event.key === "/" && document.activeElement !== $("#search-input")) { event.preventDefault(); setRoute("search"); }
      if (event.key === "Escape") { $("#search-input").value = ""; state.query = ""; document.body.classList.remove("menu-open"); renderSearch(); }
    });
  }

  function init() {
    loadCardState();
    renderMetrics(); renderBriefing(); renderTrends(); renderLatest(); renderConferenceMini();
    renderCards(); renderConferenceFilters(); renderConferences(); renderSources(); renderStatistics(); renderTopicOptions(); renderSearch(); bindEvents();
    const updated = formatDate(data.generated_at);
    $("#last-updated").textContent = updated;
    $("#sidebar-sync").textContent = data.generated_at ? updated : "첫 수집 대기";
    setRoute(location.hash.slice(1) || "overview");
  }

  init();
})();
