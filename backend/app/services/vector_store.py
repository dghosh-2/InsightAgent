import json
import numpy as np
import faiss
from pathlib import Path
from datetime import datetime
from typing import Optional

from app.core.config import Settings
from app.models.schemas import ChunkMetadata, DocumentInfo
from app.services.embedding_service import EmbeddingService


class VectorStore:
    """
    FAISS-based vector store with file persistence.
    
    Stores embeddings in FAISS index and metadata in JSON files.
    Uses Inner Product (IP) similarity which is equivalent to cosine
    similarity when vectors are normalized.
    """
    
    def __init__(self, settings: Settings, embedding_service: EmbeddingService):
        self.settings = settings
        self.embedding_service = embedding_service
        self.dimension = settings.embedding_dimension
        
        # File paths
        self.index_path = settings.faiss_dir / "index.faiss"
        self.metadata_path = settings.metadata_dir / "chunks.json"
        self.documents_path = settings.metadata_dir / "documents.json"
        
        # Initialize or load
        self.index: Optional[faiss.Index] = None
        self.chunks: list[ChunkMetadata] = []
        self.documents: dict[str, DocumentInfo] = {}
        
        self._load_or_initialize()
    
    def _load_or_initialize(self) -> None:
        """Load existing index and metadata or create new ones."""
        if self.index_path.exists() and self.metadata_path.exists():
            self._load()
        else:
            self._initialize()
    
    def _initialize(self) -> None:
        """Initialize empty index and metadata."""
        self.index = self._create_flat_index()
        self.chunks = []
        self.documents = {}
        print("Initialized new FAISS index")

    def _create_flat_index(self) -> faiss.IndexFlatIP:
        return faiss.IndexFlatIP(self.dimension)

    def _resolve_nlist(self, sample_count: int) -> int:
        configured_nlist = max(1, int(getattr(self.settings, "faiss_nlist", 100)))
        if sample_count <= configured_nlist:
            return max(1, min(configured_nlist, max(16, sample_count // 4)))
        return configured_nlist

    def _create_ivfpq_index(self, sample_count: int) -> faiss.IndexIVFPQ:
        nlist = self._resolve_nlist(sample_count)
        m = int(getattr(self.settings, "faiss_m", 16))
        nbits = int(getattr(self.settings, "faiss_nbits", 8))
        quantizer = faiss.IndexFlatIP(self.dimension)
        return faiss.IndexIVFPQ(quantizer, self.dimension, nlist, m, nbits)

    def _should_use_ivfpq(self, sample_count: int) -> bool:
        if not bool(getattr(self.settings, "faiss_use_ivfpq", True)):
            return False
        return sample_count >= max(16, int(getattr(self.settings, "faiss_nlist", 100)))
    
    def _load(self) -> None:
        """Load index and metadata from disk."""
        try:
            # Load FAISS index
            self.index = faiss.read_index(str(self.index_path))
            
            # Load chunk metadata
            with open(self.metadata_path, "r") as f:
                chunks_data = json.load(f)
                self.chunks = [ChunkMetadata(**c) for c in chunks_data]
            
            # Load document metadata
            if self.documents_path.exists():
                with open(self.documents_path, "r") as f:
                    docs_data = json.load(f)
                    self.documents = {
                        doc_id: DocumentInfo(**doc) 
                        for doc_id, doc in docs_data.items()
                    }
            
            print(f"Loaded FAISS index with {self.index.ntotal} vectors")
            print(f"Loaded {len(self.documents)} documents")
            
        except Exception as e:
            print(f"Error loading index: {e}. Initializing new index.")
            self._initialize()
    
    def save(self) -> None:
        """Save index and metadata to disk."""
        if self.index is None:
            return
        
        # Save FAISS index
        faiss.write_index(self.index, str(self.index_path))
        
        # Save chunk metadata
        chunks_data = [c.model_dump() for c in self.chunks]
        with open(self.metadata_path, "w") as f:
            json.dump(chunks_data, f, indent=2, default=str)
        
        # Save document metadata
        docs_data = {
            doc_id: doc.model_dump() 
            for doc_id, doc in self.documents.items()
        }
        with open(self.documents_path, "w") as f:
            json.dump(docs_data, f, indent=2, default=str)
        
        print(f"Saved FAISS index with {self.index.ntotal} vectors")
    
    @property
    def document_count(self) -> int:
        """Get number of documents in the store."""
        return len(self.documents)
    
    def add_document(
        self,
        document_id: str,
        filename: str,
        chunks: list[ChunkMetadata],
        file_size: int
    ) -> None:
        """
        Add a document's chunks to the vector store.
        
        Args:
            document_id: Unique document identifier
            filename: Original filename
            chunks: List of text chunks with metadata
            file_size: Size of the original file in bytes
        """
        if not chunks:
            return

        # Store chunk metadata first so rebuilds have the full dataset.
        self.chunks.extend(chunks)

        # Generate embeddings for new chunks
        texts = [chunk.text for chunk in chunks]
        embeddings = self.embedding_service.embed_texts(texts).astype(np.float32)

        if self._should_use_ivfpq(len(self.chunks)):
            if isinstance(self.index, faiss.IndexIVFPQ) and self.index.is_trained:
                self.index.add(embeddings)
            else:
                self._rebuild_ivfpq_index()
        else:
            if not isinstance(self.index, faiss.IndexFlatIP):
                self.index = self._create_flat_index()
                if len(self.chunks) > len(chunks):
                    existing_texts = [chunk.text for chunk in self.chunks[:-len(chunks)]]
                    if existing_texts:
                        existing_embeddings = self.embedding_service.embed_texts(existing_texts).astype(np.float32)
                        self.index.add(existing_embeddings)
            self.index.add(embeddings)

        # Store document info
        self.documents[document_id] = DocumentInfo(
            document_id=document_id,
            filename=filename,
            upload_time=datetime.now(),
            page_count=max(c.page_number for c in chunks),
            chunk_count=len(chunks),
            file_size=file_size
        )
        
        # Persist changes
        self.save()

    def _rebuild_ivfpq_index(self) -> None:
        if not self.chunks:
            self.index = self._create_flat_index()
            return

        all_texts = [chunk.text for chunk in self.chunks]
        all_embeddings = self.embedding_service.embed_texts(all_texts).astype(np.float32)
        sample_count = all_embeddings.shape[0]

        if not self._should_use_ivfpq(sample_count):
            self.index = self._create_flat_index()
            self.index.add(all_embeddings)
            return

        ivfpq = self._create_ivfpq_index(sample_count)
        if sample_count < ivfpq.nlist:
            self.index = self._create_flat_index()
            self.index.add(all_embeddings)
            return

        ivfpq.train(all_embeddings)
        ivfpq.add(all_embeddings)
        self.index = ivfpq
    
    def remove_document(self, document_id: str) -> None:
        """
        Remove a document and its chunks from the store.
        
        Note: FAISS IndexFlatIP doesn't support removal, so we rebuild the index.
        """
        if document_id not in self.documents:
            return
        
        # Find chunks to keep (not belonging to this document)
        chunks_to_keep = [c for c in self.chunks if c.document_id != document_id]
        
        # Rebuild index with remaining chunks
        self._initialize()
        self.chunks = chunks_to_keep

        if chunks_to_keep:
            if self._should_use_ivfpq(len(chunks_to_keep)):
                self._rebuild_ivfpq_index()
            else:
                texts = [chunk.text for chunk in chunks_to_keep]
                embeddings = self.embedding_service.embed_texts(texts).astype(np.float32)
                self.index.add(embeddings)

        del self.documents[document_id]
        
        # Persist changes
        self.save()
    
    def document_exists(self, document_id: str) -> bool:
        """Check if a document exists in the store."""
        return document_id in self.documents
    
    def list_documents(self) -> list[DocumentInfo]:
        """Get list of all documents."""
        return list(self.documents.values())
    
    def search(
        self,
        query: str,
        top_k: int = 20,
        nprobe: Optional[int] = None
    ) -> list[tuple[ChunkMetadata, float]]:
        """
        Search for similar chunks using the query.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            
        Returns:
            List of (chunk, score) tuples sorted by relevance
        """
        if self.index is None or self.index.ntotal == 0:
            return []
        
        # Embed query
        query_embedding = self.embedding_service.embed_query(query)
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)
        
        # Search FAISS
        if isinstance(self.index, faiss.IndexIVFPQ):
            self.index.nprobe = int(nprobe or getattr(self.settings, "faiss_nprobe", 10))

        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query_embedding, k)
        
        # Get chunks with scores
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.chunks):
                results.append((self.chunks[idx], float(score)))
        
        return results
