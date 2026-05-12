import sys
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import endpoints

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(
    title="W2B Scraper API",
    description="Professional search-and-scrape API with social media features.",
    version="1.0.0"
)

# CORS configuration to allow local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace with specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(endpoints.router, prefix="/api/v1")

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "message": "W2B Scraper API is running. Visit /docs for Swagger UI."
    }

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8010, reload=True)
