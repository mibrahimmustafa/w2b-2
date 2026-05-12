from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from app.services.scraper_service import ScraperService

router = APIRouter()
service = ScraperService()

class SearchRequest(BaseModel):
    query: str
    pages: int = 2

class CrawlRequest(BaseModel):
    url: str
    max_pages: int = 5

class PipelineResponse(BaseModel):
    total_found: int
    scraped_count: int
    results: List[dict]
    storage_path: str

@router.post("/search")
async def search(request: SearchRequest):
    """Discover URLs based on query."""
    try:
        results = await service.search(request.query, request.pages)
        return {"results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scrape")
async def scrape(url: str = Query(...)):
    """Deep scrape a specific URL."""
    try:
        result = await service.scrape_url(url)
        if not result:
            raise HTTPException(status_code=404, detail="Could not scrape URL")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/pipeline", response_model=PipelineResponse)
async def pipeline(request: SearchRequest):
    """Run the complete pipeline: search then deep-scrape."""
    try:
        # Run service pipeline with storage handling
        stats = await service.run_pipeline(request.query, request.pages)
        
        return PipelineResponse(
            total_found=stats.get("total_found", stats["count"]), # fallback
            scraped_count=stats["count"],
            results=stats["results"],
            storage_path=stats["storage_path"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/crawl", response_model=PipelineResponse)
async def crawl(request: CrawlRequest):
    """Crawl a website and its subpages."""
    try:
        stats = await service.crawl_website(request.url, request.max_pages)
        return PipelineResponse(
            total_found=stats["count"],
            scraped_count=stats["count"],
            results=stats["results"],
            storage_path=stats["storage_path"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
