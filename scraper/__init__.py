"""
scraper — W2B Web Scraping Package
====================================
Public API re-exports so callers can do:

    from scraper import ScraperConfig, SearchEngine, DeepScraper
"""

from .config import ScraperConfig
from .search import SearchEngine, SearchResult
from .deep_scraper import DeepScraper, ScrapedPage
from .exporters import save_json, save_xml
from .logger import get_logger

__all__ = [
    "ScraperConfig",
    "SearchEngine",
    "SearchResult",
    "DeepScraper",
    "ScrapedPage",
    "save_json",
    "save_xml",
    "get_logger",
]
