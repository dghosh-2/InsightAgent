export interface Citation {
  document_name: string;
  page_number: number;
  text_excerpt: string;
  relevance_score: number;
}

export interface QueryResponse {
  answer: string;
  confidence: number;
  citations: Citation[];
  processing_time_ms: number;
}

export interface DocumentInfo {
  document_id: string;
  filename: string;
  upload_time: string;
  page_count: number;
  chunk_count: number;
  file_size: number;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  page_count: number;
  chunk_count: number;
  message: string;
}

export interface DocumentListResponse {
  documents: DocumentInfo[];
  total_count: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  embedding_model: string;
  documents_loaded: number;
}

export interface ApiError {
  detail: string;
}
