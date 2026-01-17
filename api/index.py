from http.server import BaseHTTPRequestHandler
import json
import os
import re
import tempfile
import uuid
from urllib.parse import parse_qs, urlparse
import numpy as np

# Note: These imports may fail during build but work at runtime
try:
    import fitz  # PyMuPDF
    import faiss
    from openai import OpenAI
except ImportError:
    pass

# ============ CONFIGURATION ============
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
LLM_MODEL = "gpt-4o-mini"
CHUNK_SIZE = 512
TOP_K = 5
MAX_TEXT_LENGTH = 25000
BATCH_SIZE = 100

# ============ IN-MEMORY STORAGE ============
documents_store = {}
chunks_store = []
embeddings_store = []

def get_openai_client():
    if not OPENAI_API_KEY:
        raise Exception("OpenAI API key not configured. Set OPENAI_API_KEY environment variable.")
    return OpenAI(api_key=OPENAI_API_KEY)

def sanitize_text(text):
    if not text:
        return ""
    text = text.replace('\x00', '')
    text = ''.join(char for char in text if char >= ' ' or char in '\n\t')
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    if len(text) > MAX_TEXT_LENGTH:
        text = text[:MAX_TEXT_LENGTH]
    return text

def split_into_sentences(text):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]

def create_chunks(text, document_id, document_name, page_number, start_index):
    chunks = []
    text = sanitize_text(text)
    
    if not text:
        return chunks
    
    if len(text) <= CHUNK_SIZE:
        return [{
            "chunk_id": str(uuid.uuid4()),
            "document_id": document_id,
            "document_name": document_name,
            "page_number": page_number,
            "chunk_index": start_index,
            "text": text
        }]
    
    sentences = split_into_sentences(text)
    current_chunk = ""
    chunk_index = start_index
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 <= CHUNK_SIZE:
            current_chunk += sentence + " "
        else:
            if current_chunk.strip():
                chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "document_id": document_id,
                    "document_name": document_name,
                    "page_number": page_number,
                    "chunk_index": chunk_index,
                    "text": current_chunk.strip()
                })
                chunk_index += 1
            words = current_chunk.split()
            overlap = ' '.join(words[-10:]) if len(words) > 10 else ''
            current_chunk = overlap + " " + sentence + " "
    
    if current_chunk.strip():
        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "document_id": document_id,
            "document_name": document_name,
            "page_number": page_number,
            "chunk_index": chunk_index,
            "text": current_chunk.strip()
        })
    
    return chunks

def process_pdf(file_content, document_id, filename):
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

def embed_texts(client, texts):
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

def search_similar(query_embedding, top_k=TOP_K):
    if not embeddings_store:
        return []
    
    embeddings_matrix = np.vstack(embeddings_store).astype(np.float32)
    index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
    index.add(embeddings_matrix)
    
    query = query_embedding.reshape(1, -1).astype(np.float32)
    scores, indices = index.search(query, min(top_k, len(embeddings_store)))
    
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx >= 0 and idx < len(chunks_store):
            results.append((chunks_store[idx], float(score)))
    
    return results

def generate_answer(client, question, chunks):
    context_parts = []
    for i, (chunk, score) in enumerate(chunks, 1):
        context_parts.append(f"[Source {i}] (Document: {chunk['document_name']}, Page: {chunk['page_number']})\n{chunk['text']}\n")
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
    
    citations = []
    for ref in result.get("citations", []):
        idx = ref.get("source_number", 1) - 1
        if 0 <= idx < len(chunks):
            chunk, score = chunks[idx]
            excerpt = chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text']
            citations.append({
                "document_name": chunk['document_name'],
                "page_number": chunk['page_number'],
                "text_excerpt": excerpt,
                "relevance_score": score
            })
    
    if not citations:
        for chunk, score in chunks[:3]:
            excerpt = chunk['text'][:200] + "..." if len(chunk['text']) > 200 else chunk['text']
            citations.append({
                "document_name": chunk['document_name'],
                "page_number": chunk['page_number'],
                "text_excerpt": excerpt,
                "relevance_score": score
            })
    
    return {
        "answer": result.get("answer", "Unable to generate answer."),
        "confidence": min(max(result.get("confidence", 0.5), 0), 1),
        "citations": citations,
        "processing_time_ms": 0
    }

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == "/api/health" or path == "/api":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                "status": "healthy",
                "documents_loaded": len(documents_store),
                "chunks_loaded": len(chunks_store)
            }
            self.wfile.write(json.dumps(response).encode())
            
        elif path == "/api/documents":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            response = {
                "documents": list(documents_store.values()),
                "total_count": len(documents_store)
            }
            self.wfile.write(json.dumps(response).encode())
            
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        
        if path == "/api/upload":
            try:
                # Parse multipart form data
                content_type = self.headers.get('Content-Type', '')
                
                if 'multipart/form-data' in content_type:
                    # Extract boundary
                    boundary = content_type.split('boundary=')[1].encode()
                    body = self.rfile.read(content_length)
                    
                    # Parse multipart
                    parts = body.split(b'--' + boundary)
                    file_content = None
                    filename = "document.pdf"
                    
                    for part in parts:
                        if b'filename=' in part:
                            # Extract filename
                            header_end = part.find(b'\r\n\r\n')
                            if header_end != -1:
                                header = part[:header_end].decode('utf-8', errors='ignore')
                                if 'filename="' in header:
                                    filename = header.split('filename="')[1].split('"')[0]
                                file_content = part[header_end + 4:]
                                # Remove trailing boundary markers
                                if file_content.endswith(b'\r\n'):
                                    file_content = file_content[:-2]
                                if file_content.endswith(b'--'):
                                    file_content = file_content[:-2]
                                if file_content.endswith(b'\r\n'):
                                    file_content = file_content[:-2]
                    
                    if not file_content:
                        raise Exception("No file found in request")
                    
                    if not filename.lower().endswith('.pdf'):
                        raise Exception("Only PDF files are supported")
                    
                    document_id = str(uuid.uuid4())
                    
                    # Process PDF
                    chunks, page_count = process_pdf(file_content, document_id, filename)
                    
                    if not chunks:
                        raise Exception("Could not extract text from PDF")
                    
                    # Generate embeddings
                    client = get_openai_client()
                    texts = [chunk['text'] for chunk in chunks]
                    embeddings = embed_texts(client, texts)
                    
                    # Store
                    chunks_store.extend(chunks)
                    embeddings_store.extend(embeddings)
                    documents_store[document_id] = {
                        "document_id": document_id,
                        "filename": filename,
                        "page_count": page_count,
                        "chunk_count": len(chunks)
                    }
                    
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    response = {
                        "document_id": document_id,
                        "filename": filename,
                        "page_count": page_count,
                        "chunk_count": len(chunks),
                        "message": "Document uploaded and processed successfully"
                    }
                    self.wfile.write(json.dumps(response).encode())
                else:
                    raise Exception("Expected multipart/form-data")
                    
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"detail": str(e)}).encode())
                
        elif path == "/api/query":
            try:
                import time
                start_time = time.time()
                
                body = self.rfile.read(content_length)
                data = json.loads(body)
                question = data.get('question', '')
                
                if not question:
                    raise Exception("Question is required")
                
                if not chunks_store:
                    raise Exception("No documents uploaded. Please upload a PDF first.")
                
                client = get_openai_client()
                
                # Embed query
                query_embeddings = embed_texts(client, [question])
                if not query_embeddings:
                    raise Exception("Failed to embed query")
                
                # Search
                results = search_similar(query_embeddings[0], TOP_K)
                
                if not results:
                    raise Exception("No relevant information found.")
                
                # Generate answer
                response = generate_answer(client, question, results)
                response['processing_time_ms'] = int((time.time() - start_time) * 1000)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"detail": str(e)}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path.startswith("/api/documents/"):
            document_id = path.split("/api/documents/")[1]
            
            if document_id not in documents_store:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({"detail": "Document not found"}).encode())
                return
            
            global chunks_store, embeddings_store
            indices_to_remove = [i for i, c in enumerate(chunks_store) if c['document_id'] == document_id]
            chunks_store = [c for i, c in enumerate(chunks_store) if i not in indices_to_remove]
            embeddings_store = [e for i, e in enumerate(embeddings_store) if i not in indices_to_remove]
            del documents_store[document_id]
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"document_id": document_id, "message": "Document deleted"}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
