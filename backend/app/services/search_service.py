from typing import Optional

from app.core.config import Settings
from app.models.schemas import ChunkMetadata
from app.services.vector_store import VectorStore


class SearchService:
    """
    Search service with FAISS retrieval.
    
    Uses FAISS vector similarity search to find relevant chunks.
    """
    
    def __init__(self, settings: Settings, vector_store: VectorStore):
        self.settings = settings
        self.vector_store = vector_store
        self.top_k = settings.top_k_rerank  # Number of results to return
    
    def search(self, query: str) -> list[tuple[ChunkMetadata, float]]:
        """
        Search for relevant chunks.
        
        Args:
            query: User's question
            
        Returns:
            List of (chunk, relevance_score) tuples, sorted by relevance
        """
        # FAISS retrieval
        results = self.vector_store.search(query, top_k=self.top_k)
        return results
