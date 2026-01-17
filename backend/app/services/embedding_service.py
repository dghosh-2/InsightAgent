import numpy as np
import re
from openai import OpenAI

from app.core.config import Settings


class EmbeddingService:
    """Service for generating text embeddings using OpenAI API."""
    
    # OpenAI text-embedding-3-small has 8191 token limit per text
    MAX_TEXT_LENGTH = 25000
    # OpenAI allows max 2048 inputs per batch request
    BATCH_SIZE = 100  # Use smaller batches for reliability
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_name = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self.client = OpenAI(api_key=settings.openai_api_key)
        print(f"Using OpenAI embedding model: {self.model_name}")
    
    def _sanitize_text(self, text: str) -> str:
        """
        Sanitize text for OpenAI API.
        
        Removes control characters, null bytes, and ensures valid encoding.
        """
        if not text:
            return ""
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        text = ''.join(char for char in text if char >= ' ' or char in '\n\t')
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        # Truncate if too long
        if len(text) > self.MAX_TEXT_LENGTH:
            text = text[:self.MAX_TEXT_LENGTH]
        
        return text
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Numpy array of shape (dimension,)
        """
        text = self._sanitize_text(text)
        
        if not text:
            return np.zeros(self.dimension, dtype=np.float32)
        
        response = self.client.embeddings.create(
            model=self.model_name,
            input=text
        )
        embedding = np.array(response.data[0].embedding, dtype=np.float32)
        
        # Normalize for cosine similarity
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding
    
    def embed_texts(self, texts: list[str]) -> np.ndarray:
        """
        Generate embeddings for multiple texts.
        
        Handles batching for large numbers of texts.
        
        Args:
            texts: List of input texts
            
        Returns:
            Numpy array of shape (n_texts, dimension)
        """
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        
        # Sanitize all texts
        sanitized = [self._sanitize_text(t) for t in texts]
        
        # Find valid (non-empty) texts and their original indices
        valid_pairs = [(i, t) for i, t in enumerate(sanitized) if t]
        
        if not valid_pairs:
            return np.zeros((len(texts), self.dimension), dtype=np.float32)
        
        valid_indices = [p[0] for p in valid_pairs]
        valid_texts = [p[1] for p in valid_pairs]
        
        # Process in batches
        all_embeddings = []
        for i in range(0, len(valid_texts), self.BATCH_SIZE):
            batch = valid_texts[i:i + self.BATCH_SIZE]
            print(f"  Embedding batch {i // self.BATCH_SIZE + 1}/{(len(valid_texts) + self.BATCH_SIZE - 1) // self.BATCH_SIZE} ({len(batch)} texts)")
            
            response = self.client.embeddings.create(
                model=self.model_name,
                input=batch
            )
            
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
        
        # Build result array
        result = np.zeros((len(texts), self.dimension), dtype=np.float32)
        
        for i, embedding in enumerate(all_embeddings):
            original_idx = valid_indices[i]
            emb_array = np.array(embedding, dtype=np.float32)
            
            # Normalize
            norm = np.linalg.norm(emb_array)
            if norm > 0:
                emb_array = emb_array / norm
            
            result[original_idx] = emb_array
        
        return result
    
    def embed_query(self, query: str) -> np.ndarray:
        """
        Generate embedding for a search query.
        
        Args:
            query: Search query text
            
        Returns:
            Numpy array of shape (dimension,)
        """
        return self.embed_text(query)
