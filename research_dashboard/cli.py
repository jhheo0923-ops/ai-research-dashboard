from __future__ import annotations

import argparse
import http.server
import socketserver
import sys
from pathlib import Path

from . import db, pipeline, render


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "ai_research.db"
DEFAULT_CONFIG = ROOT / "config" / "sources.json"
DEFAULT_WEB = ROOT / "web"
DEFAULT_DATA = ROOT / "data"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AI 리서치 대시보드 수집·검색·발행 도구")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="SQLite 데이터베이스와 학회 목록 초기화")

    collect_parser = subparsers.add_parser("collect", help="모든 활성 소스에서 새 자료 수집")
    collect_parser.add_argument("--max-items", type=int, default=None, help="소스별 최대 수집 수")

    render_parser = subparsers.add_parser("render", help="SQLite 데이터로 정적 대시보드 데이터 생성")
    render_parser.add_argument("--item-limit", type=int, default=300, help="브라우저 검색용 최대 자료 수")

    update_parser = subparsers.add_parser("update", help="초기화, 수집, 정적 데이터 생성을 한 번에 실행")
    update_parser.add_argument("--max-items", type=int, default=None, help="소스별 최대 수집 수")
    update_parser.add_argument("--item-limit", type=int, default=300, help="브라우저 검색용 최대 자료 수")

    search_parser = subparsers.add_parser("search", help="로컬 SQLite 아카이브 검색")
    search_parser.add_argument("query", help="FTS5 검색어")
    search_parser.add_argument("--limit", type=int, default=20)

    serve_parser = subparsers.add_parser("serve", help="로컬 대시보드 서버 실행")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    return parser


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)

    if args.command == "init":
        pipeline.initialize(DEFAULT_DB, DEFAULT_CONFIG)
        print(f"초기화 완료: {DEFAULT_DB}")
        return 0

    if args.command == "collect":
        pipeline.initialize(DEFAULT_DB, DEFAULT_CONFIG)
        _print_results(pipeline.collect_all(DEFAULT_DB, DEFAULT_CONFIG, max_items=args.max_items))
        return 0

    if args.command == "render":
        pipeline.initialize(DEFAULT_DB, DEFAULT_CONFIG)
        payload = render.write_payload(DEFAULT_DB, DEFAULT_WEB, DEFAULT_DATA, item_limit=args.item_limit)
        print(f"대시보드 생성 완료: {len(payload['items'])}개 자료")
        return 0

    if args.command == "update":
        pipeline.initialize(DEFAULT_DB, DEFAULT_CONFIG)
        results = pipeline.collect_all(DEFAULT_DB, DEFAULT_CONFIG, max_items=args.max_items)
        _print_results(results)
        payload = render.write_payload(DEFAULT_DB, DEFAULT_WEB, DEFAULT_DATA, item_limit=args.item_limit)
        ok_count = sum(1 for result in results if result.status == "ok")
        print(f"업데이트 완료: {ok_count}/{len(results)}개 소스 정상, 검색 자료 {len(payload['items'])}개")
        return 0 if ok_count else 1

    if args.command == "search":
        pipeline.initialize(DEFAULT_DB, DEFAULT_CONFIG)
        rows = db.search_items(DEFAULT_DB, args.query, limit=args.limit)
        for index, item in enumerate(rows, start=1):
            print(f"{index:>2}. [{item['source']}] {item['title']}\n    {item['url']}")
        print(f"{len(rows)}개 결과")
        return 0
    if args.command == "serve":
        return serve(args.host, args.port)
    return 2


def serve(host: str, port: int) -> int:
    handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *args,
        directory=str(DEFAULT_WEB),
        **kwargs,
    )
    with socketserver.ThreadingTCPServer((host, port), handler) as server:
        print(f"Signal 대시보드: http://{host}:{port}/")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


def _print_results(results: list[pipeline.CollectionResult]) -> None:
    for result in results:
        marker = "OK" if result.status == "ok" else "ERROR"
        detail = f" - {result.message}" if result.message else ""
        print(f"[{marker}] {result.source}: {result.count}개{detail}")
