from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
import json
import uuid
import os
import re
import tempfile
import numpy as np
import fitz  # PyMuPDF
import faiss
from openai import OpenAI

# Initialize FastAPI app
app = FastAPI(title="InsightAgent API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ CONFIGURATION ============
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
LLM_MODEL = "gpt-4o-mini"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
TOP_K = 5
MAX_TEXT_LENGTH = 25000
BATCH_SIZE = 100

# ============ PYDANTIC MODELS ============
class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    chunk_index: int
    text: str

class Citation(BaseModel):
    document_name: str
    page_number: int
    text_excerpt: str
    relevance_score: float

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)

class QueryResponse(BaseModel):
    answer: str
    confidence: float
    citations: list[Citation]
    processing_time_ms: int

class UploadResponse(BaseModel):
    document_id: str
    filename: str
    page_count: int
    chunk_count: int
    message: str

class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    page_count: int
    chunk_count: int

# ============ IN-MEMORY STORAGE ============
# Note: Serverless functions are stateless, so this resets on each cold start
# For production, use a database like Vercel KV, Upstash, or Supabase
documents_store: dict[str, DocumentInfo] = {}
chunks_store: list[ChunkMetadata] = []
embeddings_store: list[np.ndarray] = []

# ============ HELPER FUNCTIONS ============
def get_openai_client():
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API key not configured")
    return OpenAI(api_key=OPENAI_API_KEY)

def sanitize_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace('\x00', '')
    text = ''.join(char for char in text if char >= ' ' or char in '\n\t')
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]
    return text

def clean_text(text: str) -> str:
    text = ''.join(char for char in text if char >= ' ' or char in '\n\t')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def split_into_sentences(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def create_chunks(text: str, document_id: str, document_name: str, page_number: int, start_index: int) -> list[ChunkMetadata]:
    chunks = []
    text = clean_text(text)
    
    if not text:
        return chunks
    
    if len(text) <= CHUNK_SIZE:
        return [ChunkMetadata(
            chunk_id=str(uuid.uuid4()),
            document_id=document_id,
            document_name=document_name,
            page_number=page_number,
            chunk_index=start_index,
            text=text
        )]
    
    sentences = split_into_sentences(text)
    current_chunk = ""
    chunk_index = start_index
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= CHUNK_SIZE:
            current_chunk += sentence + " "
        else:
            if current_chunk.strip():
                chunks.append(ChunkMetadata(
                    chunk_id=str(uuid.uuid4()),
                    document_id=document_id,
                    document_name=document_name,
                    page_number=page_number,
                    chunk_index=chunk_index,
                    text=current_chunk.strip()
                ))
                chunk_index += 1
            # Keep some overlap
            words = current_chunk.split()
            overlap = ' '.join(words[-10:]) if len(words) > 10 else ''
            current_chunk = overlap + " " + sentence + " "
    
    if current_chunk.strip():
        chunks.append(ChunkMetadata(
            chunk_id=str(uuid.uuid4()),
            document_id=document_id,
            document_name=document_name,
            page_number=page_number,
            chunk_index=chunk_index,
            text=current_chunk.strip()
        ))
    
    return chunks

def process_pdf(file_content: bytes, document_id: str, filename: str) -> tuple[list[ChunkMetadata], int]:
    chunks = []
    page_count = 0
    
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = tmp.name
    
    try:
        doc = fitz.open(tmp_path)
        page_count = len(doc)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            
            if not text.strip():
                continue
            
            page_chunks = create_chunks(
                text=text,
                document_id=document_id,
                document_name=filename,
                page_number=page_num + 1,
                start_index=len(chunks)
            )
            chunks.extend(page_chunks)
        
        doc.close()
    finally:
        os.unlink(tmp_path)
    
    return chunks, page_count

def embed_texts(client: OpenAI, texts: list[str]) -> list[np.ndarray]:
    if not texts:
        return []
    
    sanitized = [sanitize_text(t) for t in texts]
    valid_texts = [t for t in sanitized if t]
    
    if not valid_texts:
        return [np.zeros(EMBEDDING_DIMENSION, dtype=np.float32) for _ in texts]
    
    all_embeddings = []
    for i in range(0, len(valid_texts), BATCH_SIZE):
        batch = valid_texts[i:i + BATCH_SIZE]
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=batch)
        for item in response.data:
            emb = np.array(item.embedding, dtype=np.float32)
            emb = emb / np.linalg.norm(emb)
            all_embeddings.append(emb)
    
    return all_embeddings

def search_similar(query_embedding: np.ndarray, top_k: int = TOP_K) -> list[tuple[ChunkMetadata, float]]:
    if not embeddings_store:
        return []
    
    # Build FAISS index
    embeddings_matrix = np.vstack(embeddings_store).astype(np.float32)
    index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
    index.add(embeddings_matrix)
    
    # Search
    query = query_embedding.reshape(1, -1).astype(np.float32)
    scores, indices = index.search(query, min(top_k, len(embeddings_store)))
    
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0 and idx < len(chunks_store):
            results.append((chunks_store[idx], float(score)))
    
    return results

def generate_answer(client: OpenAI, question: str, chunks: list[tuple[ChunkMetadata, float]]) -> QueryResponse:
    # Build context
    context_parts = []
    for i, (chunk, score) in enumerate(chunks, 1):
        context_parts.append(f"[Source {i}] (Document: {chunk.document_name}, Page: {chunk.page_number})\n{chunk.text}\n")
    context = "\n---\n".join(context_parts)
    
    system_prompt = """You are a helpful assistant that answers questions based on provided document excerpts.
Answer using ONLY the information from the provided sources. Cite sources using [Source N].
If sources don't contain enough information, say so clearly.

Respond with valid JSON:
{
    "answer": "Your answer with citations like [Source 1]",
    "confidence": 0.85,
    "citations": [{"source_number": 1, "relevance": "Why relevant"}]
}"""
    
    user_prompt = f"Question: {question}\n\nSources:\n{context}\n\nRespond with valid JSON."
    
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=1024,
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    
    # Build citations
    citations = []
    for ref in result.get("citations", []):
        idx = ref.get("source_number", 1) - 1
        if 0 <= idx < len(chunks):
            chunk, score = chunks[idx]
            excerpt = chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text
            citations.append(Citation(
                document_name=chunk.document_name,
                page_number=chunk.page_number,
                text_excerpt=excerpt,
                relevance_score=score
            ))
    
    # Fallback citations
    if not citations:
        for chunk, score in chunks[:3]:
            excerpt = chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text
            citations.append(Citation(
                document_name=chunk.document_name,
                page_number=chunk.page_number,
                text_excerpt=excerpt,
                relevance_score=score
            ))
    
    return QueryResponse(
        answer=result.get("answer", "Unable to generate answer."),
        confidence=min(max(result.get("confidence", 0.5), 0), 1),
        citations=citations,
        processing_time_ms=0
    )

# ============ API ROUTES ============
@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "documents_loaded": len(documents_store),
        "chunks_loaded": len(chunks_store)
    }

@app.get("/api/documents")
async def list_documents():
    return {
        "documents": list(documents_store.values()),
        "total_count": len(documents_store)
    }

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    
    document_id = str(uuid.uuid4())
    
    try:
        # Process PDF
        chunks, page_count = process_pdf(content, document_id, file.filename)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        # Generate embeddings
        client = get_openai_client()
        texts = [chunk.text for chunk in chunks]
        embeddings = embed_texts(client, texts)
        
        # Store in memory
        chunks_store.extend(chunks)
        embeddings_store.extend(embeddings)
        documents_store[document_id] = DocumentInfo(
            document_id=document_id,
            filename=file.filename,
            page_count=page_count,
            chunk_count=len(chunks)
        )
        
        return UploadResponse(
            document_id=document_id,
            filename=file.filename,
            page_count=page_count,
            chunk_count=len(chunks),
            message="Document uploaded and processed successfully"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@app.post("/api/query")
async def query_documents(query: QueryRequest):
    import time
    start_time = time.time()
    
    if not chunks_store:
        raise HTTPException(status_code=400, detail="No documents uploaded. Please upload a PDF first.")
    
    client = get_openai_client()
    
    # Embed query
    query_embeddings = embed_texts(client, [query.question])
    if not query_embeddings:
        raise HTTPException(status_code=500, detail="Failed to embed query")
    
    # Search
    results = search_similar(query_embeddings[0], TOP_K)
    
    if not results:
        raise HTTPException(status_code=404, detail="No relevant information found.")
    
    # Generate answer
    response = generate_answer(client, query.question, results)
    response.processing_time_ms = int((time.time() - start_time) * 1000)
    
    return response

@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    global chunks_store, embeddings_store
    
    if document_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Remove chunks and embeddings for this document
    indices_to_remove = [i for i, c in enumerate(chunks_store) if c.document_id == document_id]
    
    chunks_store = [c for i, c in enumerate(chunks_store) if i not in indices_to_remove]
    embeddings_store = [e for i, e in enumerate(embeddings_store) if i not in indices_to_remove]
    
    del documents_store[document_id]
    
    return {"document_id": document_id, "message": "Document deleted successfully"}
