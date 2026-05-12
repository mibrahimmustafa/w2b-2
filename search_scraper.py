"""
search_scraper.py — Standalone Search-Only CLI
===============================================
A lightweight script that runs only Phase 1 of the pipeline:
DuckDuckGo multi-page search → JSON output.

This is useful when you just need a list of URLs without the heavier
Playwright-based deep-scrape step.

Usage::

    python search_scraper.py --query "machine learning" --pages 3
    python search_scraper.py -q "تعلم الآلة" -p 2 -o ml_results.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scraper import ScraperConfig, SearchEngine
from scraper.exporters import save_json
from scraper.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="search_scraper.py",
        description="Search-only DuckDuckGo scraper — outputs a JSON list of results.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-q", "--query",
        metavar="QUERY",
        type=str,
        default=None,
        help="Search phrase (prompted interactively if omitted).",
    )
    parser.add_argument(
        "-p", "--pages",
        metavar="N",
        type=int,
        default=5,
        help="Maximum number of result pages to fetch.",
    )
    parser.add_argument(
        "-o", "--output",
        metavar="FILE",
        type=Path,
        default=Path("search_results.json"),
        help="Output JSON file path.",
    )
    return parser.parse_args(argv)


def _prompt_query() -> str:
    """Interactively prompt the user for a search query."""
    print("─" * 50)
    try:
        query = input("🔍 Enter search query: ").strip()
    except KeyboardInterrupt:
        print()
        logger.info("Cancelled by user.")
        sys.exit(0)
    print("─" * 50)
    return query


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    query = args.query or _prompt_query()
    if not query:
        logger.error("No search query provided. Exiting.")
        sys.exit(1)

    config = ScraperConfig(query=query, max_pages=args.pages)
    config.validate()

    engine = SearchEngine(config)
    results = engine.execute_search()

    if not results:
        logger.warning("No results found. No file written.")
        print("\n❌ No results extracted.")
        sys.exit(1)

    # Ensure parent directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)
    save_json(results, args.output)

    print(f"\n✅ {len(results)} result(s) saved to '{args.output}'.")


if __name__ == "__main__":
    main()
