from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.routes import documents, query
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStore


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup and cleanup on shutdown."""
    settings = get_settings()
    
    # Initialize embedding service (loads model)
    embedding_service = EmbeddingService(settings)
    app.state.embedding_service = embedding_service
    
    # Initialize vector store (loads FAISS index if exists)
    vector_store = VectorStore(settings, embedding_service)
    app.state.vector_store = vector_store
    
    yield
    
    # Cleanup (save any pending changes)
    vector_store.save()


app = FastAPI(
    title="InsightAgent API",
    description="NLP search and retrieval tool for PDF question-answering",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(query.router, prefix="/api", tags=["query"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    settings = get_settings()
    vector_store: VectorStore = app.state.vector_store
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "embedding_model": settings.embedding_model,
        "documents_loaded": vector_store.document_count
    }
