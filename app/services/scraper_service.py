"""
app.services.scraper_service
============================
Service layer for the W2B scraper. Integrates search and deep scraping
as a unified interface for the API and frontend.
"""

from __future__ import annotations
import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from scraper import ScraperConfig, SearchEngine, DeepScraper, ScrapedPage, SearchResult
from scraper.logger import get_logger

logger = get_logger(__name__)

class ScraperService:
    """Handles high-level scraping operations asynchronously."""

    def __init__(self, output_dir: Optional[str] = None):
        self._custom_output_dir = output_dir
        self.deep_scraper = DeepScraper()

    @property
    def output_dir(self) -> Path:
        if self._custom_output_dir:
            path = Path(self._custom_output_dir)
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")
            path = Path(f"executions/{date_str}/results")
        path.mkdir(parents=True, exist_ok=True)
        return path

    async def search(self, query: str, max_pages: int = 5) -> List[SearchResult]:
        """Run DuckDuckGo discovery phase."""
        config = ScraperConfig(query=query, max_pages=max_pages, output_dir=self.output_dir)
        config.validate()
        
        # Offload the synchronous search to a thread to keep the API responsive
        engine = SearchEngine(config)
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, engine.execute_search)
        return results

    async def scrape_url(self, url: str) -> Optional[ScrapedPage]:
        """Deep scrape a single URL asynchronously."""
        loop = asyncio.get_event_loop()
        # Offload logic that creates its own asyncio loop to a thread
        results = await loop.run_in_executor(None, self.deep_scraper.run, [url])
        return results[0] if results else None

    async def run_pipeline(self, query: str, max_pages: int = 2) -> Dict[str, Any]:
        """Full search-and-deep-scrape pipeline."""
        config = ScraperConfig(query=query, max_pages=max_pages)
        config.validate()

        logger.info("Starting pipeline in: %s", config.output_dir)

        discovered = await self.search(query, max_pages=max_pages)
        if not discovered:
            return {"count": 0, "results": [], "storage_path": str(config.output_dir)}

        # Phase 2: Batch Scrape
        urls = [item["url"] for item in discovered]
        loop = asyncio.get_event_loop()
        scraped_results = await loop.run_in_executor(None, self.deep_scraper.run, urls)
        
        scraped_pages = []
        from scraper.exporters import save_json
        
        for page in scraped_results:
            url = page["metadata"]["url"]
            file_path = config.output_dir / self._sanitize_filename(url)
            save_json(page, file_path)
            scraped_pages.append(page)
        
        return {
            "count": len(scraped_pages),
            "results": scraped_pages,
            "storage_path": str(config.output_dir)
        }

    async def crawl_website(self, start_url: str, max_pages: int = 5) -> Dict[str, Any]:
        """Crawl a website starting from a URL and following internal links."""
        config = ScraperConfig(query=start_url, max_pages=max_pages, output_dir=self.output_dir)
        config.validate()

        logger.info("Starting crawl pipeline for %s in: %s", start_url, config.output_dir)

        scraped_pages = []
        visited = set()
        to_visit = [start_url]
        
        loop = asyncio.get_event_loop()
        from urllib.parse import urlparse
        start_domain = urlparse(start_url).netloc
        
        from scraper.exporters import save_json
        
        while to_visit and len(scraped_pages) < max_pages:
            current_batch = to_visit[:3]
            to_visit = to_visit[3:]
            
            for u in current_batch:
                visited.add(u)
                
            results = await loop.run_in_executor(None, self.deep_scraper.run, current_batch)
            
            for page in results:
                url = page["metadata"]["url"]
                file_path = config.output_dir / self._sanitize_filename(url)
                save_json(page, file_path)
                scraped_pages.append(page)
                
                for link in page.get("links", []):
                    if link.startswith("/"):
                        link = f"https://{start_domain}{link}"
                    if start_domain in link and link not in visited and link not in to_visit:
                        to_visit.append(link)
                        
                if len(scraped_pages) >= max_pages:
                    break

        return {
            "count": len(scraped_pages),
            "results": scraped_pages,
            "storage_path": str(config.output_dir)
        }

    def _sanitize_filename(self, url: str) -> str:
        """Safe filename from URL."""
        name = re.sub(r"https?://", "", url)
        name = re.sub(r"[^\w.\-]", "_", name)
        return f"{name[:100]}.json"
