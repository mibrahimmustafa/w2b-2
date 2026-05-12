import os
import json
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

# Use the sentence-transformers model (ChromaDB default)
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "chroma_db")

class VectorDBClient:
    def __init__(self, collection_name: str = "scraped_data"):
        self.collection_name = collection_name
        # Initialize persistent client with reset enabled
        self.client = chromadb.PersistentClient(
            path=CHROMA_DATA_PATH,
            settings=Settings(allow_reset=True)
        )
        
        # Setup the embedding function
        self.embedding_func = embedding_functions.DefaultEmbeddingFunction()
        
        # Get or create the collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_func
        )

    def process_json_file(self, file_path: str):
        """Reads a scraped JSON file and returns a list of text chunks with metadata."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata_info = data.get("metadata", {})
            url = metadata_info.get("url", "")
            title = metadata_info.get("title", "")
            description = metadata_info.get("description", "")
            
            # Extract main content (paragraphs and headings)
            paragraphs = data.get("paragraphs", [])
            headings = data.get("headings", {})
            
            # --- Enriched Description Fallback ---
            # Compile the actual content to serve as the "full details" description 
            # so the user always sees the comprehensive details when querying.
            details_parts = []
            if description:
                details_parts.append(description)
            for p in paragraphs:
                if len(p.strip()) > 20:
                    details_parts.append(p.strip())
                    
            enriched_description = "\n".join(details_parts)
            # Limit description size slightly if it's too huge, to prevent ChromaDB metadata limits
            if len(enriched_description) > 5000:
                enriched_description = enriched_description[:5000] + "..."
                
            all_text_chunks = []
            
            # Create a context header using title and description for better semantic search
            context_header = ""
            if title or enriched_description:
                context_header = f"Title: {title}\nDescription: {enriched_description[:500]}\n---\n"
                # Add the standalone meta chunk as well
                all_text_chunks.append({
                    "text": f"Title: {title}\nDescription: {enriched_description[:1000]}",
                    "meta": {"url": url, "source": file_path, "type": "meta", "description": enriched_description}
                })
            
            # Combine headings and paragraphs with context header
            for h1 in headings.get("h1", []):
                all_text_chunks.append({
                    "text": f"{context_header}Heading: {h1}",
                    "meta": {"url": url, "source": file_path, "type": "h1", "description": enriched_description}
                })
            
            for p in paragraphs:
                if len(p.strip()) > 20: # ignore very short/empty paragraphs
                    all_text_chunks.append({
                        "text": f"{context_header}Content: {p}",
                        "meta": {"url": url, "source": file_path, "type": "paragraph", "description": enriched_description}
                    })
                    
            return all_text_chunks

        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return []

    def ingest_data(self, chunks: list):
        """Ingests a list of chunks into ChromaDB."""
        if not chunks:
            return 0
        
        documents = [c["text"] for c in chunks]
        metadatas = [c["meta"] for c in chunks]
        
        # Generating deterministic IDs based on source and index
        # For a robust system we could hash the text
        ids = [f"{c['meta']['source']}_{i}" for i, c in enumerate(chunks)]
        
        # Upsert allows adding or updating existing ones
        self.collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        return len(documents)

    def query_data(self, query_text: str, n_results: int = 5):
        """Queries the vector database."""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )
        return results

    def reset_database(self):
        """Wipes the entire database and recreates the collection structure."""
        try:
            # Use client.reset() to wipe everything (requires allow_reset=True)
            self.client.reset()
            # Re-initialize the collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                embedding_function=self.embedding_func
            )
            return True
        except Exception as e:
            print(f"Error resetting database: {e}")
            # Fallback to just deleting the collection if reset fails
            try:
                self.client.delete_collection(name=self.collection_name)
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    embedding_function=self.embedding_func
                )
                return True
            except Exception as e2:
                print(f"Fallback reset also failed: {e2}")
                return False

# Singleton instance
vector_db = VectorDBClient()
