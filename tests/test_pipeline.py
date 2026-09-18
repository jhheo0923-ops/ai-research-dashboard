from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from research_dashboard import analyze, db
from research_dashboard.sources import parse_arxiv, parse_feed, parse_openreview


ARXIV_XML = b"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns='http://www.w3.org/2005/Atom' xmlns:arxiv='http://arxiv.org/schemas/atom'>
  <entry>
    <id>http://arxiv.org/abs/2609.00001v1</id>
    <updated>2026-09-15T10:00:00Z</updated><published>2026-09-15T10:00:00Z</published>
    <title>Agentic Reasoning with Reliable Tool Use</title>
    <summary>A benchmark for multi-agent reasoning.</summary>
    <author><name>Ada Researcher</name></author>
    <category term='cs.AI'/><arxiv:primary_category term='cs.AI'/>
  </entry>
</feed>"""

RSS_XML = b"""<?xml version='1.0'?><rss version='2.0'><channel><title>Lab</title><item>
<title>New multimodal system</title><link>https://example.com/post</link>
<description><![CDATA[<p>A vision-language model.</p>]]></description>
<pubDate>Tue, 15 Sep 2026 10:00:00 GMT</pubDate></item></channel></rss>"""

OPENREVIEW_JSON = b'{"notes":[{"id":"abc123","cdate":1789466400000,"content":{"title":{"value":"World Models for Robotics"},"abstract":{"value":"Embodied learning."},"authors":{"value":["A. Author"]}}}]}'


class SourceParsingTests(unittest.TestCase):
    def test_arxiv_parser(self) -> None:
        items = parse_arxiv(ARXIV_XML)
        self.assertEqual(items[0]["external_id"], "arxiv:2609.00001")
        self.assertEqual(items[0]["authors"], ["Ada Researcher"])

    def test_rss_parser(self) -> None:
        items = parse_feed(RSS_XML, source_name="Lab")
        self.assertEqual(items[0]["summary"], "A vision-language model.")

    def test_openreview_parser(self) -> None:
        items = parse_openreview(OPENREVIEW_JSON, venue_id="ICLR.cc/2026/Conference")
        self.assertEqual(items[0]["source"], "OpenReview · ICLR")


class DatabaseTests(unittest.TestCase):
    def test_upsert_and_search(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.db"
            db.initialize(path)
            rows = parse_arxiv(ARXIV_XML)
            db.upsert_items(path, rows)
            results = db.search_items(path, "reasoning")
            self.assertEqual(len(results), 1)

    def test_trend_analysis(self) -> None:
        rows = parse_arxiv(ARXIV_XML)
        trends = analyze.build_trends(rows)
        labels = {row["label"] for row in trends}
        self.assertIn("Agents & Tool Use", labels)

    def test_hierarchical_classification(self) -> None:
        item = parse_arxiv(ARXIV_XML)[0]
        result = analyze.classify_item(item)
        self.assertEqual(result["primary_topic"], "Foundation Models")
        self.assertEqual(result["secondary_topic"], "Agents & Tool Use")
        self.assertGreater(result["confidence"], 0.5)

    def test_korean_card_summary(self) -> None:
        item = parse_arxiv(ARXIV_XML)[0]
        analysis = analyze.korean_card_analysis(item)
        self.assertIn("에이전트", analysis["overview"])
        self.assertIn("도구", analysis["motivation"])
        self.assertIn("벤치마크", analysis["contribution"])

    def test_detailed_topic_insights(self) -> None:
        rows = parse_arxiv(ARXIV_XML)
        details = analyze.build_detailed_topic_insights(rows)
        self.assertEqual(details["total_papers"], 1)
        self.assertEqual(details["rows"][0]["secondary"], "Agents & Tool Use")
        self.assertEqual(details["rows"][0]["status"], "핵심축")

    def test_annual_topic_share(self) -> None:
        rows = [
            {"type": "paper", "published_at": "2025-03-01T00:00:00+00:00", "primary_topic": "Foundation Models"},
            {"type": "paper", "published_at": "2025-04-01T00:00:00+00:00", "primary_topic": "Learning & Theory"},
            {"type": "paper", "published_at": "2025-05-01T00:00:00+00:00", "primary_topic": "Learning & Theory"},
            {"type": "paper", "published_at": "2026-03-01T00:00:00+00:00", "primary_topic": "Foundation Models"},
            {"type": "paper", "published_at": "2026-04-01T00:00:00+00:00", "primary_topic": "Foundation Models"},
        ]
        annual = analyze.build_annual_trends(rows, year_count=2, now=datetime(2026, 9, 1, tzinfo=timezone.utc))
        foundation = next(row for row in annual["series"] if row["primary"] == "Foundation Models")
        self.assertEqual(annual["years"], ["2025", "2026"])
        self.assertGreater(foundation["delta_pp"], 0)

    def test_official_annual_counts(self) -> None:
        metrics = [
            {"field_key": "Machine Learning", "field_label_ko": "머신러닝", "category": "cs.LG", "year": 2025, "count": 100, "source_url": "https://arxiv.org/list/cs.LG/2025"},
            {"field_key": "Machine Learning", "field_label_ko": "머신러닝", "category": "cs.LG", "year": 2026, "count": 125, "source_url": "https://arxiv.org/list/cs.LG/2026"},
            {"field_key": "Robotics", "field_label_ko": "로보틱스", "category": "cs.RO", "year": 2025, "count": 40, "source_url": "https://arxiv.org/list/cs.RO/2025"},
            {"field_key": "Robotics", "field_label_ko": "로보틱스", "category": "cs.RO", "year": 2026, "count": 42, "source_url": "https://arxiv.org/list/cs.RO/2026"},
        ]
        annual = analyze.build_annual_trends([], metrics=metrics, year_count=2, now=datetime(2026, 9, 1, tzinfo=timezone.utc))
        machine_learning = next(row for row in annual["series"] if row["primary"] == "Machine Learning")
        self.assertEqual(annual["value_mode"], "count")
        self.assertEqual(machine_learning["counts"], [100, 125])
        self.assertEqual(machine_learning["delta_pp"], 25.0)


if __name__ == "__main__":
    unittest.main()
