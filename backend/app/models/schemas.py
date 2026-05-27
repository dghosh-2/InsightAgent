from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    chunk_index: int
    start_char: int
    end_char: int
    text: str


class Citation(BaseModel):
    document_name: str
    page_number: int
    text_excerpt: str
    relevance_score: float


class QueryRequest(BaseModel):
    question: str
    nprobe: int | None = None


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


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    upload_time: datetime
    page_count: int
    chunk_count: int
    file_size: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total_count: int


class DeleteResponse(BaseModel):
    document_id: str
    message: str


class ExtractedInsight(BaseModel):
    answer: str
    citations: list[str] = Field(
        default_factory=list,
        description="Chunk IDs used to support the answer.",
    )
    confidence_score: float = Field(ge=0.0, le=1.0)
