"""
debug_search.py — DuckDuckGo Connectivity Debugger
====================================================
A minimal diagnostic script to verify that:

  1. The DuckDuckGo HTML endpoint is reachable.
  2. The POST request returns HTTP 200.
  3. Result ``<div class="result">`` elements are present.
  4. The title anchor (``a.result__a``) can be extracted.

Run this script when troubleshooting blocked requests, unexpected status
codes, or selector failures before running the full pipeline.

Usage::

    python debug_search.py
    python debug_search.py --query "python" --verbose
"""

from __future__ import annotations

import argparse
import sys

import requests
from bs4 import BeautifulSoup

from scraper.config import DDG_SEARCH_URL, DEFAULT_USER_AGENT
from scraper.logger import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Core diagnostic
# ---------------------------------------------------------------------------
def run_diagnostics(query: str = "python", *, verbose: bool = False) -> bool:
    """
    Execute a single DuckDuckGo POST search and print a structured report.

    Args:
        query:   Test search term.
        verbose: When ``True``, prints the full response HTML excerpt.

    Returns:
        ``True`` if the diagnostic passes (200 OK + results found),
        ``False`` otherwise.
    """
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    }
    payload = {"q": query}

    print("─" * 55)
    print(f"  DDG Debug  |  endpoint : {DDG_SEARCH_URL}")
    print(f"             |  query    : {query!r}")
    print("─" * 55)

    # ── Request ─────────────────────────────────────────────────────────────
    try:
        response = requests.post(DDG_SEARCH_URL, headers=headers, data=payload, timeout=15)
    except requests.exceptions.RequestException as exc:
        logger.error("Network error: %s", exc)
        print(f"\n❌ FAIL — Network error: {exc}")
        return False

    print(f"  Status Code : {response.status_code}")

    if response.status_code != 200:
        print(f"\n❌ FAIL — Expected 200, got {response.status_code}.")
        return False

    # ── Parsing ──────────────────────────────────────────────────────────────
    soup = BeautifulSoup(response.text, "lxml")
    result_divs = soup.select("div.result")
    print(f"  Results found : {len(result_divs)}")

    if not result_divs:
        print("\n❌ FAIL — No result <div> elements found. Selectors may have changed.")
        return False

    first_title_tag = result_divs[0].select_one("a.result__a")
    first_title = first_title_tag.get_text(strip=True) if first_title_tag else "(no title)"
    print(f"  First result  : {first_title}")

    if verbose:
        print("\n── Response HTML excerpt (first 1000 chars) ─────────────────")
        print(response.text[:1000])
        print("─" * 55)

    print("\n✅ PASS — DuckDuckGo endpoint is reachable and results are parseable.")
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="debug_search.py",
        description="Diagnostic check for the DuckDuckGo HTML search endpoint.",
    )
    parser.add_argument(
        "-q", "--query",
        type=str,
        default="python",
        help="Test search term (default: 'python').",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Print the first 1000 characters of the raw HTML response.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    passed = run_diagnostics(query=args.query, verbose=args.verbose)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
