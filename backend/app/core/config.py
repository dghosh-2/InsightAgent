import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# Project root is parent of backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # API Keys
    openai_api_key: str = ""
    
    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent.parent
    data_dir: Path = base_dir / "data"
    uploads_dir: Path = data_dir / "uploads"
    faiss_dir: Path = data_dir / "faiss_index"
    metadata_dir: Path = data_dir / "metadata"
    
    # Embedding model (OpenAI)
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    
    # Chunking settings
    chunk_size: int = 512
    chunk_overlap: int = 50
    
    # Search settings
    top_k_retrieval: int = 20  # Initial FAISS retrieval
    top_k_rerank: int = 5      # After reranking
    
    # OpenAI settings
    openai_model: str = "gpt-4o-mini"
    max_tokens: int = 1024
    
    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.faiss_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
