# InsightAgent

A full-stack NLP search and retrieval tool for PDF question-answering. Upload PDFs, ask natural language questions, and get grounded answers with citations.

## Features

- **PDF Upload & Processing**: Upload PDFs that get parsed, chunked, and embedded
- **Semantic Search**: FAISS vector search with local embeddings (BAAI/bge-small-en-v1.5)
- **Cross-Encoder Reranking**: Improved relevance with ms-marco-MiniLM reranker
- **LLM-Powered Answers**: OpenAI GPT generates grounded answers with citations
- **Structured Output**: JSON responses with answer, confidence, and source citations

## Tech Stack

### Backend (Python/FastAPI)
- FastAPI for REST API
- PyMuPDF for PDF extraction
- sentence-transformers for embeddings
- FAISS for vector storage
- cross-encoder for reranking
- OpenAI API for answer generation
- Pydantic for data validation

### Frontend (TypeScript/React)
- React 18 with TypeScript
- Vite for build tooling
- TailwindCSS for styling
- Axios for API calls

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <repo-url>
cd InsightAgent
```

2. Set up environment variables:
```bash
# Create .env file in project root
OPENAI_API_KEY=your_api_key_here
```

3. Install dependencies and run:
```bash
npm run dev
```

This single command will:
- Install Python dependencies
- Install Node dependencies
- Start the FastAPI backend (port 8000)
- Start the React frontend (port 5173)

## API Endpoints

### Upload PDF
```
POST /api/upload
Content-Type: multipart/form-data
Body: file (PDF)
```

### Ask Question
```
POST /api/query
Content-Type: application/json
Body: { "question": "What is...?" }
```

### List Documents
```
GET /api/documents
```

### Delete Document
```
DELETE /api/documents/{doc_id}
```

## Architecture

```
┌──────────────┐
│ PDF Upload   │
└─────┬────────┘
      ↓
┌──────────────────────┐
│ Text Extraction      │
│ + Chunking           │
│ + Metadata           │
└─────┬────────────────┘
      ↓
┌──────────────────────┐
│ Embedding Generation │
│ (BAAI/bge-small)     │
└─────┬────────────────┘
      ↓
┌──────────────────────┐
│ FAISS Vector Store   │
└─────┬────────────────┘
      ↓
┌──────────────────────┐
│ User Question        │
└─────┬────────────────┘
      ↓
┌──────────────────────┐
│ Retrieval + Rerank   │
│ (Cross-Encoder)      │
└─────┬────────────────┘
      ↓
┌──────────────────────┐
│ LLM Answer + JSON    │
│ + Citations          │
└──────────────────────┘
```

## Project Structure

```
InsightAgent/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   ├── services/
│   │   ├── models/
│   │   └── core/
│   ├── data/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── services/
│   │   └── types/
│   └── package.json
├── package.json
└── README.md
```

## License

MIT
