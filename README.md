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
