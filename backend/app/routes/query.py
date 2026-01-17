from fastapi import APIRouter, HTTPException, Request
import time

from app.core.config import get_settings
from app.models.schemas import QueryRequest, QueryResponse
from app.services.vector_store import VectorStore
from app.services.search_service import SearchService
from app.services.llm_service import LLMService

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_documents(request: Request, query: QueryRequest):
    """
    Ask a question about the uploaded documents.
    
    The system will:
    1. Search for relevant chunks using FAISS
    2. Rerank results using cross-encoder
    3. Generate an answer using OpenAI with citations
    """
    start_time = time.time()
    
    settings = get_settings()
    vector_store: VectorStore = request.app.state.vector_store
    
    # Check if we have any documents
    if vector_store.document_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents uploaded. Please upload a PDF first."
        )
    
    # Initialize services
    search_service = SearchService(settings, vector_store)
    llm_service = LLMService(settings)
    
    # Search and rerank
    relevant_chunks = search_service.search(query.question)
    
    if not relevant_chunks:
        raise HTTPException(
            status_code=404,
            detail="No relevant information found for your question."
        )
    
    # Generate answer with citations
    response = llm_service.generate_answer(query.question, relevant_chunks)
    
    # Calculate processing time
    processing_time_ms = int((time.time() - start_time) * 1000)
    response.processing_time_ms = processing_time_ms
    
    return response
