"""
scraper.search
==============
DuckDuckGo search client with automatic backend selection.

**Primary backend** — ``duckduckgo-search`` (DDGS)
    Uses DDG's internal API with proper session tokens, automatic
    CAPTCHA avoidance, and retries.  This is the recommended path.

**Fallback backend** — HTML scraping
    Direct POST to ``html.duckduckgo.com``.  Used automatically if
    ``duckduckgo-search`` is not installed.  Subject to IP-level CAPTCHA
    blocks and HTML structure changes.

Usage::

    from scraper import ScraperConfig, SearchEngine

    config = ScraperConfig(query="python asyncio", max_pages=3)
    engine = SearchEngine(config)
    results = engine.execute_search()
    # results → list[SearchResult]
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import TypedDict

import requests
from bs4 import BeautifulSoup

from .config import DDG_SEARCH_URL, ScraperConfig
from .logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Backend availability check
# ---------------------------------------------------------------------------
try:
    from ddgs import DDGS

    _DDGS_AVAILABLE = True
    logger.debug("ddgs library found — using DDGS backend.")
except ImportError:
    _DDGS_AVAILABLE = False
    logger.debug("ddgs not installed — using HTML scraping fallback.")

# ---------------------------------------------------------------------------
# HTML-scraping constants (fallback only)
# ---------------------------------------------------------------------------
_DDG_LITE_URL: str = "https://lite.duckduckgo.com/lite/"

_CAPTCHA_MARKERS: tuple[str, ...] = (
    "anomaly-modal",
    "Unfortunately, bots use DuckDuckGo",
    "anomaly.js",
    "challenge-form",
)

_RESULT_CONTAINER_SELECTORS: list[str] = [
    "div.result",
    "div.results_links",
    "article",
]
_LINK_SELECTORS: list[str] = [
    "a.result__a",
    "a.result-link",
    "h2 > a",
]
_SNIPPET_SELECTORS: list[str] = [
    ".result__snippet",
    ".result__body",
    "p",
]

_DEBUG_DIR = Path("debug_html")


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------
class SearchResult(TypedDict):
    """Structured representation of a single DuckDuckGo search result."""

    title: str
    url: str
    snippet: str


# ---------------------------------------------------------------------------
# SearchEngine
# ---------------------------------------------------------------------------
class SearchEngine:
    """
    Discovers target URLs by querying DuckDuckGo.

    Automatically selects the best available backend:

    1. **DDGS** (``duckduckgo-search`` library) — preferred, handles
       rate-limiting and CAPTCHA avoidance internally.
    2. **HTML scraping** — fallback when the library is not installed;
       susceptible to IP-level CAPTCHA blocks.

    Args:
        config: Runtime configuration (query, pages, timeouts, etc.).
    """

    _RATE_LIMIT_STATUS = 205
    _RATE_LIMIT_SLEEP = 7  # seconds

    def __init__(self, config: ScraperConfig) -> None:
        self.config = config
        self._session = self._build_session()   # used only by HTML fallback

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def execute_search(self) -> list[SearchResult]:
        """
        Run the search and return deduplicated results.

        Delegates to :meth:`_search_via_ddgs` when the library is available,
        otherwise falls back to :meth:`_search_via_html`.

        Returns:
            Deduplicated list of :class:`SearchResult` dicts, up to
            ``config.max_pages × ~10`` results.
        """
        if _DDGS_AVAILABLE:
            logger.info("Using DDGS backend (ddgs library).")
            return self._search_via_ddgs()

        logger.warning(
            "duckduckgo-search not installed — using HTML scraping fallback. "
            "Run: pip install duckduckgo-search"
        )
        return self._search_via_html()

    # ------------------------------------------------------------------
    # Backend 1: DDGS (preferred)
    # ------------------------------------------------------------------
    def _search_via_ddgs(self) -> list[SearchResult]:
        """
        Fetch results via the ``duckduckgo-search`` DDGS client.

        DDGS internally handles session cookies, CAPTCHA challenges, and
        progressive back-off — so we just iterate and collect results.
        """
        # max_results = pages × ~10 results per DDG page
        max_results = self.config.max_pages * 10
        results: list[SearchResult] = []

        try:
            with DDGS() as ddgs:
                for item in ddgs.text(
                    self.config.query,
                    max_results=max_results,
                ):
                    results.append(
                        SearchResult(
                            title=item.get("title", ""),
                            url=item.get("href", ""),
                            snippet=item.get("body", ""),
                        )
                    )
                    logger.debug("  + %s", item.get("href", ""))

        except Exception as exc:  # noqa: BLE001
            logger.error("DDGS search failed: %s", exc)
            logger.info("Falling back to HTML scraping...")
            return self._search_via_html()

        logger.info("DDGS search complete. Total results: %d.", len(results))
        return results

    # ------------------------------------------------------------------
    # Backend 2: HTML scraping (fallback)
    # ------------------------------------------------------------------
    def _search_via_html(self) -> list[SearchResult]:
        """Paginated POST scrape of ``html.duckduckgo.com``."""
        results: list[SearchResult] = []
        seen_urls: set[str] = set()
        payload: dict[str, str] = {"q": self.config.query}
        parser = "lxml" if "lxml" in sys.modules else "html.parser"

        logger.debug("HTML fallback using parser: %s", parser)

        for page in range(1, self.config.max_pages + 1):
            logger.info(
                "Searching '%s'  —  page %d / %d",
                self.config.query,
                page,
                self.config.max_pages,
            )

            response = self._fetch_page_html(payload, page)
            if response is None:
                break

            logger.debug(
                "Response: HTTP %d | %d bytes", response.status_code, len(response.content)
            )

            if self._is_captcha_page(response.text):
                logger.error(
                    "CAPTCHA / IP-block detected on page %d. "
                    "Install duckduckgo-search for reliable results: "
                    "pip install duckduckgo-search",
                    page,
                )
                self._dump_debug_html(response.text, page)
                break  # Cannot proceed without CAPTCHA bypass

            soup = BeautifulSoup(response.text, parser)
            page_results = self._parse_html_results(soup, seen_urls, response.text, page)
            results.extend(page_results)
            logger.info("  └─ %d new result(s) found on page %d.", len(page_results), page)

            next_payload = self._build_next_payload(soup)
            if next_payload is None:
                logger.info("No further pages — stopping pagination.")
                break

            payload = next_payload
            time.sleep(self.config.request_delay)

        logger.info("HTML search complete. Total unique results: %d.", len(results))
        return results

    # ------------------------------------------------------------------
    # HTTP helpers (HTML backend)
    # ------------------------------------------------------------------
    def _build_session(self) -> requests.Session:
        """Build a persistent HTTP session for the HTML fallback backend."""
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": self.config.user_agent,
                "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Cache-Control": "no-cache",
            }
        )
        return session

    def _fetch_page_html(
        self, payload: dict[str, str], page: int
    ) -> requests.Response | None:
        """POST to the DDG HTML endpoint; returns ``None`` on any error."""
        try:
            response = self._session.post(
                DDG_SEARCH_URL,
                data=payload,
                timeout=self.config.timeout,
            )
            response.raise_for_status()
        except requests.exceptions.Timeout:
            logger.error("Request timed out on page %d (timeout=%ds).", page, self.config.timeout)
            return None
        except requests.exceptions.HTTPError as exc:
            logger.error("HTTP error on page %d: %s", page, exc)
            return None
        except requests.exceptions.RequestException as exc:
            logger.error("Network error on page %d: %s", page, exc)
            return None

        if response.status_code == self._RATE_LIMIT_STATUS:
            logger.warning(
                "Rate-limited (HTTP 205). Sleeping %ds.", self._RATE_LIMIT_SLEEP
            )
            time.sleep(self._RATE_LIMIT_SLEEP)
            return None

        return response

    # ------------------------------------------------------------------
    # HTML parsing helpers
    # ------------------------------------------------------------------
    def _parse_html_results(
        self,
        soup: BeautifulSoup,
        seen_urls: set[str],
        raw_html: str,
        page: int,
    ) -> list[SearchResult]:
        """Extract results from parsed HTML using multi-selector probing."""
        container_sel = self._detect_selector(soup, _RESULT_CONTAINER_SELECTORS, "container")
        if container_sel is None:
            logger.warning("Page %d: No result containers found.", page)
            self._dump_debug_html(raw_html, page)
            return []

        link_sel = self._detect_selector(
            soup, _LINK_SELECTORS, "link", within=container_sel
        )
        if link_sel is None:
            logger.warning("Page %d: No link anchors found inside '%s'.", page, container_sel)
            self._dump_debug_html(raw_html, page)
            return []

        snippet_sel = self._detect_selector(
            soup, _SNIPPET_SELECTORS, "snippet", within=container_sel
        )

        extracted: list[SearchResult] = []
        for item in soup.select(container_sel):
            link_tag = item.select_one(link_sel)
            if not link_tag:
                continue

            url = link_tag.get("href", "").strip()
            if not url or url.startswith(("/", "//")):
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

            snippet_tag = item.select_one(snippet_sel) if snippet_sel else None
            extracted.append(
                SearchResult(
                    title=link_tag.get_text(strip=True),
                    url=url,
                    snippet=snippet_tag.get_text(strip=True) if snippet_tag else "",
                )
            )

        return extracted

    def _detect_selector(
        self,
        soup: BeautifulSoup,
        candidates: list[str],
        label: str,
        within: str | None = None,
    ) -> str | None:
        """Return the first candidate selector that matches at least one element."""
        for sel in candidates:
            if within and within != sel:
                count = sum(1 for c in soup.select(within) if c.select_one(sel))
            else:
                count = len(soup.select(sel))

            logger.debug("  Selector probe [%s] '%s' → %d match(es)", label, sel, count)
            if count > 0:
                logger.debug("  ✓ Using [%s] selector: '%s'", label, sel)
                return sel
        return None

    def _is_captcha_page(self, html: str) -> bool:
        """Return ``True`` if the HTML contains a DDG anomaly/CAPTCHA challenge."""
        return any(marker in html for marker in _CAPTCHA_MARKERS)

    def _dump_debug_html(self, html: str, page: int) -> None:
        """Write raw HTML to ``debug_html/page_<N>.html`` for manual inspection."""
        try:
            _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            dump_path = _DEBUG_DIR / f"page_{page}.html"
            dump_path.write_text(html, encoding="utf-8")
            logger.info("Raw HTML dumped → %s", dump_path)
        except OSError as exc:
            logger.warning("Could not write debug HTML: %s", exc)

    def _build_next_payload(self, soup: BeautifulSoup) -> dict[str, str] | None:
        """Extract the hidden-input payload for the next DDG HTML page."""
        next_form = soup.select_one(".nav-link form")
        if not next_form:
            return None

        payload: dict[str, str] = {
            inp["name"]: inp.get("value", "")
            for inp in next_form.select("input[type='hidden']")
            if inp.get("name")
        }
        payload.setdefault("q", self.config.query)
        return payload
