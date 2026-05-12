"""
scraper.deep_scraper
====================
Deep content extraction using Scrapling's stealth browser engine.
Modified to support batch scraping with concurrency control.
"""

from __future__ import annotations
import asyncio
import re
import sys
import traceback
from typing import Optional, TypedDict, List

from scrapling.fetchers import AsyncStealthySession
from scrapling.spiders import Response
from .logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------
class PageMetadata(TypedDict):
    """Basic metadata extracted from a scraped page."""
    url: str
    title: str
    description: str

class SocialMediaData(TypedDict):
    """Specific data for social media posts."""
    platform: str  # 'facebook', 'instagram', 'x', 'tiktok'
    post_text: str
    media_urls: List[str]
    is_video: bool

class ScrapedPage(TypedDict):
    """Full result returned by DeepScraper."""
    metadata: PageMetadata
    headings: Dict[str, List[str]]
    paragraphs: List[str]
    links: List[str]
    social_data: Optional[SocialMediaData]

# ---------------------------------------------------------------------------
# DeepScraper
# ---------------------------------------------------------------------------
class DeepScraper:
    """
    Orchestrates stealth scraping with concurrency control.
    """
    _MAX_CONCURRENT_BROWSERS = 3  # Limit browsers to prevent crashes
    _MIN_PARAGRAPH_LEN = 40
    _MAX_PARAGRAPHS = 50

    def __init__(self) -> None:
        pass

    def run(self, urls: str | List[str]) -> List[ScrapedPage]:
        """
        Synchronous wrapper that correctly manages the asyncio event loop.
        """
        if isinstance(urls, str):
            urls = [urls]
        if not urls:
            return []

        # Windows-specific fix for NotImplementedError (ProactorEventLoop required for subprocesses)
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        # Run the async logic and handle the loop properly
        return asyncio.run(self._run_batch_async(urls))

    async def _run_batch_async(self, urls: List[str]) -> List[ScrapedPage]:
        """Runs multiple URLs in parallel with a concurrency limit."""
        semaphore = asyncio.Semaphore(self._MAX_CONCURRENT_BROWSERS)
        
        async def sem_scrape(url: str):
            async with semaphore:
                return await self._scrape_single_async(url)

        tasks = [sem_scrape(url) for url in urls]
        results = await asyncio.gather(*tasks)
        
        # Filter out None results (failed scrapes)
        return [r for r in results if r is not None]

    async def _scrape_single_async(self, url: str) -> Optional[ScrapedPage]:
        """Internal async method to scrape a single URL."""
        logger.debug("Starting deep scrape: %s", url)
        platform = self._identify_platform(url)

        # Exclude Facebook groups
        if platform == "facebook-group":
            logger.info("Excluding Facebook group URL: %s", url)
            return None

        try:
            async with AsyncStealthySession(headless=True, timeout=60000) as session:
                response = await session.fetch(url, network_idle=True)
                
                if not response:
                    logger.warning("No response for: %s", url)
                    return None

                # Extract basic data
                title = (response.css("title::text").get(default="") or "").strip()
                description = (response.css("meta[name='description']::attr(content)").get(default="") or "").strip()

                def _get_clean_text(sel) -> str:
                    return " ".join(t.strip() for t in sel.xpath(".//text()").getall() if t.strip())

                headings = {
                    "h1": [_get_clean_text(h) for h in response.css("h1") if _get_clean_text(h)],
                    "h2": [_get_clean_text(h) for h in response.css("h2") if _get_clean_text(h)],
                    "h3": [_get_clean_text(h) for h in response.css("h3") if _get_clean_text(h)],
                }

                all_paragraphs = []
                for p in response.css("p"):
                    p_text = _get_clean_text(p)
                    if len(p_text) >= self._MIN_PARAGRAPH_LEN:
                        all_paragraphs.append(p_text)
                
                unique_paragraphs = list(dict.fromkeys(all_paragraphs))[:self._MAX_PARAGRAPHS]

                all_links = []
                for a in response.css("a::attr(href)").getall():
                    link = a.strip()
                    if link and not link.startswith(("javascript:", "mailto:", "tel:", "#")):
                        if link not in all_links:
                            all_links.append(link)

                social_data = None
                if platform:
                    social_data = self._extract_social_data(response, platform)

                logger.debug("Scraped '%s' — %d paragraph(s).", title or url, len(unique_paragraphs))
                
                return {
                    "metadata": {"url": url, "title": title, "description": description},
                    "headings": headings,
                    "paragraphs": unique_paragraphs,
                    "links": all_links[:100],
                    "social_data": social_data,
                }

        except Exception:
            logger.error("Deep-scrape failed for '%s': %s", url, traceback.format_exc())
            return None

    def _identify_platform(self, url: str) -> Optional[str]:
        low_url = url.lower()
        if "facebook.com" in low_url:
            if "/groups/" in low_url: return "facebook-group"
            return "facebook"
        if "instagram.com" in low_url: return "instagram"
        if "twitter.com" in low_url or "x.com" in low_url: return "x"
        if "tiktok.com" in low_url: return "tiktok"
        return None

    def _extract_social_data(self, response: Response, platform: str) -> SocialMediaData:
        post_text = ""
        media_urls = []
        is_video = False

        if platform == "facebook":
            post_text = response.css('div[data-ad-comet-preview="message"]::text, div[data-testid="post_message"]::text').get(default="").strip()
            media_urls = response.css('div[role="article"] img::attr(src)').getall()
            videos = response.css('video::attr(src)').getall()
            if videos:
                media_urls.extend(videos)
                is_video = True
        elif platform == "instagram":
            post_text = response.css('h1::text, article span::text').get(default="").strip()
            media_urls = response.css('article img::attr(src)').getall()
            videos = response.css('video::attr(src)').getall()
            if videos:
                media_urls.extend(videos)
                is_video = True
        elif platform == "x":
            post_text = response.css('div[data-testid="tweetText"]::text').get(default="").strip()
            media_urls = response.css('div[data-testid="tweetPhoto"] img::attr(src)').getall()
            videos = response.css('video::attr(src)').getall()
            if videos:
                media_urls.extend(videos)
                is_video = True
        elif platform == "tiktok":
            post_text = response.css('h1[data-e2e="browse-video-desc"]::text, [data-e2e="video-desc"]::text').get(default="").strip()
            videos = response.css('video source::attr(src), video::attr(src)').getall()
            if videos:
                media_urls = videos
                is_video = True

        return {
            "platform": platform,
            "post_text": post_text,
            "media_urls": list(set(media_urls)),
            "is_video": is_video,
        }
