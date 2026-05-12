from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import os
import glob
from datetime import datetime
from vectorDB_API.vector_db import vector_db

app = FastAPI(title="Vector DB API for Scraped Results")

class QueryRequest(BaseModel):
    query: str
    n_results: int = 5

class IngestResponse(BaseModel):
    message: str
    target_folder: str
    files_processed: int
    chunks_ingested: int

@app.post("/ingest", response_model=IngestResponse)
def ingest_daily_scraped_data(date_str: Optional[str] = None):
    """
    Ingests scraped JSON results for a specific date.
    If no date is provided, it uses the current date.
    Finds the folder `scraped_results_<date>` and processes all JSON files inside.
    """
    # If no date string is provided, get today's date
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
        
    # Construct folder path
    # Try new structure first: executions/<date>/results
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_folder_path = os.path.join(root_dir, "executions", date_str, "results")
    
    # Fallback to old structure: scraped_results_<date>
    if not os.path.exists(target_folder_path):
        target_folder_path = os.path.join(root_dir, f"scraped_results_{date_str}")
    
    if not os.path.exists(target_folder_path):
        raise HTTPException(
            status_code=404, 
            detail=f"Folder not found. Tried: 'executions/{date_str}/results' and 'scraped_results_{date_str}'"
        )
    
    # Find all JSON files in the target folder and its subfolders
    search_pattern = os.path.join(target_folder_path, "**", "*.json")
    json_files = glob.glob(search_pattern, recursive=True)
    
    if not json_files:
        return IngestResponse(
            message="No JSON files found to ingest.",
            target_folder=target_folder_path,
            files_processed=0,
            chunks_ingested=0
        )
        
    total_chunks_ingested = 0
    files_processed = 0
    
    for file_path in json_files:
        chunks = vector_db.process_json_file(file_path)
        if chunks:
            ingested_count = vector_db.ingest_data(chunks)
            total_chunks_ingested += ingested_count
            files_processed += 1
            
    return IngestResponse(
        message=f"Successfully ingested data for {date_str}.",
        target_folder=target_folder_path,
        files_processed=files_processed,
        chunks_ingested=total_chunks_ingested
    )

@app.post("/query")
def query_vector_db(request: QueryRequest):
    """
    Query the Vector Database using RAG context.
    """
    try:
        results = vector_db.query_data(query_text=request.query, n_results=request.n_results)
        
        # Format results for easier consumption
        formatted_results = []
        if results and results.get("documents") and len(results["documents"][0]) > 0:
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            
            for doc, meta, dist in zip(documents, metadatas, distances):
                formatted_results.append({
                    "text": doc,
                    "metadata": meta,
                    "distance": dist
                })
                
        return {
            "query": request.query,
            "results": formatted_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query_descriptions")
def query_vector_db_descriptions(request: QueryRequest):
    """
    Query the Vector Database using RAG context, returning descriptions instead of links.
    """
    try:
        results = vector_db.query_data(query_text=request.query, n_results=request.n_results)
        
        # Format results for easier consumption
        formatted_results = []
        if results and results.get("documents") and len(results["documents"][0]) > 0:
            documents = results["documents"][0]
            metadatas = results["metadatas"][0]
            distances = results["distances"][0]
            
            for doc, meta, dist in zip(documents, metadatas, distances):
                new_meta = meta.copy()
                if "url" in new_meta:
                    del new_meta["url"]
                
                # The description is now directly stored in the metadata from the Vector DB
                if "description" not in new_meta:
                    new_meta["description"] = ""
                    
                formatted_results.append({
                    "text": doc,
                    "metadata": new_meta,
                    "distance": dist
                })
                
        return {
            "query": request.query,
            "results": formatted_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset")
def reset_database():
    """
    Clears all data from the Vector Database.
    """
    success = vector_db.reset_database()
    if success:
        return {"message": "Database reset successfully."}
    else:
        raise HTTPException(status_code=500, detail="Failed to reset database.")

if __name__ == "__main__":
    import uvicorn
    # Run the API locally for testing
    uvicorn.run("vectorDB_API.main:app", host="0.0.0.0", port=8011, reload=True)
