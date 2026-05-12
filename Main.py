"""
W2B — Professional Multi-Page Search & Web Scraper
====================================================
Entry point for the full two-phase pipeline:

    Phase 1 — Search   : DuckDuckGo discovery → SearchResult list
    Phase 2 — Scrape   : Deep content extraction per URL → JSON files

Usage (CLI)::

    python Main.py --query "python asyncio" --pages 3
    python Main.py -q "تعلم البرمجة" -p 5 --output-dir my_results

Usage (programmatic)::

    from scraper import ScraperConfig
    from Main import run_pipeline

    config = ScraperConfig(query="web scraping", max_pages=2)
    run_pipeline(config)
"""

import sys
import asyncio
import argparse
import re
import time
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


from scraper import DeepScraper, ScraperConfig, SearchEngine
from scraper.exporters import save_json, save_xml
from scraper.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _sanitize_filename(url: str, max_length: int = 120) -> str:
    """
    Convert a URL into a safe filesystem filename (no special characters).

    Args:
        url:        Source URL string.
        max_length: Maximum character count before truncation.

    Returns:
        A ``*.json``-suffixed filename safe for all major operating systems.
    """
    name = re.sub(r"https?://", "", url)
    name = re.sub(r"[^\w.\-]", "_", name)
    return name[:max_length] + ".json"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Build and parse the CLI argument spec."""
    parser = argparse.ArgumentParser(
        prog="Main.py",
        description="Professional two-phase search-and-scrape pipeline.",
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
        help="Maximum number of DuckDuckGo result pages to fetch.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        metavar="DIR",
        type=Path,
        default=Path("executions") / datetime.now().strftime("%Y-%m-%d") / "results",
        help="Directory where all output files will be written.",
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Only run the search phase — skip deep content extraction.",
    )
    return parser.parse_args(argv)


def _prompt_query() -> str:
    """Interactively prompt the user for a search query."""
    print("─" * 55)
    try:
        query = input("🔍 Enter search query: ").strip()
    except KeyboardInterrupt:
        print()
        logger.info("Cancelled by user.")
        sys.exit(0)
    print("─" * 55)
    return query


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def run_pipeline(config: ScraperConfig, *, skip_scrape: bool = False) -> None:
    """
    Execute the full search-and-scrape pipeline.

    Args:
        config:      Validated :class:`~scraper.ScraperConfig` instance.
        skip_scrape: When ``True``, only Phase 1 (search) runs.
    """
    # ── Phase 1: Search ─────────────────────────────────────────────────────
    logger.info("=" * 55)
    logger.info("Phase 1 — Search  |  query='%s'  pages=%d", config.query, config.max_pages)
    logger.info("=" * 55)

    engine = SearchEngine(config)
    discovered = engine.execute_search()

    if not discovered:
        logger.warning("No results found. Exiting.")
        return

    # Export search results
    xml_path = config.output_dir / "search_results.xml"
    json_path = config.output_dir / "search_results.json"
    save_xml(discovered, xml_path, query=config.query)
    save_json(discovered, json_path)
    logger.info("Search results saved → %s  (XML + JSON)", config.output_dir)

    if skip_scrape:
        logger.info("--skip-scrape flag set. Stopping after Phase 1.")
        return

    # ── Phase 2: Deep Scrape ─────────────────────────────────────────────────
    logger.info("=" * 55)
    logger.info("Phase 2 — Scrape  |  %d URL(s) queued", len(discovered))
    logger.info("=" * 55)

    scraper = DeepScraper()
    urls = [item["url"] for item in discovered]
    
    # Process batch
    scraped_results = scraper.run(urls)
    
    success_count = 0
    for page in scraped_results:
        url = page["metadata"]["url"]
        file_path = config.output_dir / _sanitize_filename(url)
        save_json(page, file_path)
        success_count += 1

    logger.info("=" * 55)
    logger.info(
        "Done. %d / %d page(s) scraped successfully. Output → %s",
        success_count,
        len(discovered),
        config.output_dir,
    )
    logger.info("=" * 55)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    """Parse CLI arguments, build config, and run the pipeline."""
    args = _parse_args()

    query = args.query or _prompt_query()
    if not query:
        logger.error("Empty query. Exiting.")
        sys.exit(1)

    config = ScraperConfig(
        query=query,
        max_pages=args.pages,
    )
    # If the user provided an explicit output-dir via CLI, override the dynamic one
    default_dir = Path("executions") / datetime.now().strftime("%Y-%m-%d") / "results"
    if args.output_dir != default_dir:
        config.output_dir = args.output_dir
    
    config.validate()

    run_pipeline(config, skip_scrape=args.skip_scrape)


if __name__ == "__main__":
    main()
