# InsightAgent — Agent Guide

> A comprehensive reference for AI agents working in this codebase. Read this before making any changes.

---

## What This Project Is

**InsightAgent** is a full-stack **PDF question-answering (RAG)** web application. Users upload PDFs, ask natural-language questions, and receive grounded answers with source citations and confidence scores.

**Core flow:**
1. User uploads a PDF → text is extracted, chunked, and embedded via OpenAI
2. Embeddings are stored in a FAISS vector index persisted to disk
3. User asks a question → top matching chunks are retrieved
4. OpenAI GPT generates a structured JSON answer with citations

---

## Repository Layout

```
InsightAgent/                  ← repo root (has package.json)
├── package.json               # Root: concurrently runs both servers
├── vercel.json                # Vercel: build frontend + rewrite /api/* to serverless
├── README.md
├── .cursorrules               # Coding conventions for AI agents
│
├── backend/                   # FastAPI app (local/full-featured)
│   ├── requirements.txt
│   └── app/
│       ├── main.py            # FastAPI entry point + lifespan hooks
│       ├── core/config.py     # Settings via pydantic-settings
│       ├── routes/
│       │   ├── documents.py   # Upload, list, delete endpoints
│       │   └── query.py       # Q&A endpoint
│       ├── services/
│       │   ├── pdf_service.py       # PyMuPDF extraction + chunking
│       │   ├── embedding_service.py # OpenAI embedding calls
│       │   ├── vector_store.py      # FAISS CRUD + disk persistence
│       │   ├── search_service.py    # Retrieval wrapper
│       │   └── llm_service.py       # OpenAI chat + JSON parsing
│       └── models/
│           └── schemas.py     # ⚠️  MISSING — must be created (see below)
│
├── api/                       # Vercel serverless handler (duplicate logic)
│   ├── index.py               # Monolithic BaseHTTPRequestHandler
│   └── requirements.txt
│
└── frontend/                  # React + Vite SPA
    ├── package.json
    ├── vite.config.ts         # Dev proxy: /api → http://localhost:8000
    ├── tailwind.config.js
    └── src/
        ├── App.tsx
        ├── main.tsx
        ├── types/index.ts     # TypeScript mirrors of backend Pydantic models
        ├── services/api.ts    # Axios API client
        └── components/
            ├── Header.tsx
            ├── FileUpload.tsx
            ├── DocumentList.tsx
            ├── QuestionInput.tsx
            └── AnswerDisplay.tsx
```

### Runtime data (created automatically, gitignored)
```
backend/data/
├── uploads/        {document_id}.pdf
├── faiss_index/    index.faiss
└── metadata/       chunks.json, documents.json
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, uvicorn, Pydantic v2, pydantic-settings |
| PDF parsing | PyMuPDF (`fitz`) |
| Vector search | FAISS `IndexFlatIP` (cosine via L2-normalized vectors) |
| Embeddings | OpenAI `text-embedding-3-small` (1536-dim) |
| LLM | OpenAI `gpt-4o-mini`, `response_format: json_object`, temp 0.1 |
| Frontend | React 18, TypeScript (strict), Vite 5 |
| Styling | Tailwind CSS 3, DM Sans / Outfit / JetBrains Mono fonts |
| HTTP client | Axios |
| Root tooling | `concurrently` for parallel dev |
| Deploy | Vercel (static SPA + Python serverless) |

---

## API Endpoints

All routes prefixed `/api`. FastAPI routers + a root health check.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Status, version, model name, document count |
| `POST` | `/api/upload` | Multipart `file` (PDF only). Returns `document_id`, `filename`, `page_count`, `chunk_count` |
| `GET` | `/api/documents` | List all uploaded documents |
| `DELETE` | `/api/documents/{document_id}` | Remove document, FAISS vectors, and metadata |
| `POST` | `/api/query` | Body: `{ "question": "string" }`. Returns `answer`, `confidence`, `citations[]`, `processing_time_ms` |

**Errors:** FastAPI `HTTPException` → `{ "detail": "..." }`. Frontend reads `error.response.data.detail`.

---

## Data Models

These are defined in `backend/app/models/schemas.py` (currently missing) and mirrored in `frontend/src/types/index.ts`.

```python
class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    chunk_index: int
    start_char: int
    end_char: int
    text: str

class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    upload_time: str
    page_count: int
    chunk_count: int
    file_size: int

class Citation(BaseModel):
    document_name: str
    page_number: int
    excerpt: str        # first 200 chars of chunk text
    relevance_score: float

class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str
    confidence: float
    citations: list[Citation]
    processing_time_ms: float

class UploadResponse(BaseModel):
    document_id: str
    filename: str
    page_count: int
    chunk_count: int
    message: str

class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]

class DeleteResponse(BaseModel):
    message: str
    document_id: str
```

---

## Configuration & Environment Variables

Create a `.env` file at the repo root (`InsightAgent/.env`). Loaded by `Settings` via pydantic-settings.

| Variable | Default | Notes |
|----------|---------|-------|
| `OPENAI_API_KEY` | `""` | **Required.** Used for embeddings + LLM |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `EMBEDDING_DIMENSION` | `1536` | FAISS index dimension |
| `CHUNK_SIZE` | `512` | Max chars per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between adjacent chunks |
| `TOP_K_RETRIEVAL` | `20` | Defined in config but **not used** in current search flow |
| `TOP_K_RERANK` | `5` | Actual number of chunks returned to LLM |
| `OPENAI_MODEL` | `gpt-4o-mini` | Chat completion model |
| `MAX_TOKENS` | `1024` | LLM max response tokens |

**Frontend:** No env vars. `baseURL` is `/api` (Vite dev proxy rewrites to `:8000`).

**CORS (FastAPI):** Allows `http://localhost:5173` and `http://127.0.0.1:5173`.

---

## How to Run Locally

```bash
# From repo root: InsightAgent/InsightAgent/

# 1. Install everything
npm run install:all

# 2. Create .env with your API key
echo "OPENAI_API_KEY=sk-..." > .env

# 3. Start both servers concurrently
npm run dev
# Backend → http://localhost:8000
# Frontend → http://localhost:5173
```

Individual commands:
```bash
npm run dev:backend   # uvicorn with --reload
npm run dev:frontend  # vite dev server
npm run build         # builds frontend/dist for Vercel
```

---

## Architecture & State Management

- **`EmbeddingService`** and **`VectorStore`** are singleton instances attached to `app.state` via FastAPI `lifespan`. Routes access them via `request.app.state.vector_store`.
- **`PDFService`**, **`SearchService`**, **`LLMService`** are stateless — instantiated per-request.
- FAISS index uses `IndexFlatIP` with L2-normalized embeddings to compute cosine similarity.
- **Deleting** a document rebuilds the entire FAISS index from scratch (no incremental removal).
- All metadata is serialized to JSON files after each mutating operation.

---

## Vercel Deployment

`vercel.json` configures two outputs:
1. **Static build:** `cd frontend && npm install && npm run build` → `frontend/dist`
2. **Serverless function:** `api/index.py` handles all `/api/(.*)` routes

The `api/index.py` is a **monolithic duplicate** of the backend logic using Python's `BaseHTTPRequestHandler`. It uses **in-memory storage only** — all data is lost on cold start or redeployment. Only `OPENAI_API_KEY` needs to be set in the Vercel project settings.

---

## Known Issues & Gaps

| Issue | Impact | Fix |
|-------|--------|-----|
| `backend/app/models/schemas.py` is missing | Backend will not start (import error) | Create the file with the Pydantic models listed above |
| README / `.cursorrules` / footer mention BAAI/bge-small and cross-encoder reranking | Documentation is stale | Code actually uses OpenAI embeddings + simple FAISS top-k — update docs or restore reranking |
| `TOP_K_RETRIEVAL` config value is never read | Dead config | Either wire it into `SearchService.search()` or remove it |
| No tests | Regressions go undetected | Add pytest for services |
| No `.env.example` | Onboarding friction | Add one |
| `api/index.py` duplicates all business logic | Maintenance burden | Extract shared logic or point Vercel to the FastAPI app |

---

## Code Conventions

### Python (backend)
- PEP 8, type hints on all signatures
- Pydantic v2 for all request/response validation
- Thin route handlers — delegate to service classes
- `HTTPException` for all API errors
- `async/await` for I/O; sync for CPU-bound work
- Import order: stdlib → third-party → local

### TypeScript (frontend)
- Strict mode enabled
- Functional components + hooks only
- Named exports for components; default export only for `App`
- All API calls live in `services/api.ts`
- Tailwind CSS only — no inline styles
- Avoid `any` — use the types in `types/index.ts`

### Naming
- Python: `snake_case` functions/variables, `PascalCase` classes
- TypeScript: `camelCase` functions/variables, `PascalCase` components/types
- Python files: `snake_case`; TS component files: `PascalCase.tsx`

---

## Key Files for Common Tasks

| Task | File(s) to edit |
|------|----------------|
| Add a new API endpoint | `backend/app/routes/` + `backend/app/models/schemas.py` + `frontend/src/services/api.ts` + `frontend/src/types/index.ts` |
| Change chunking logic | `backend/app/services/pdf_service.py` |
| Change embedding model | `backend/app/services/embedding_service.py` + `.env` |
| Change retrieval count | `.env` (`TOP_K_RERANK`) or `backend/app/services/search_service.py` |
| Change LLM prompt/model | `backend/app/services/llm_service.py` |
| Add a new UI component | `frontend/src/components/` |
| Change global config defaults | `backend/app/core/config.py` |
| Update Vercel serverless logic | `api/index.py` (keep in sync with backend) |
