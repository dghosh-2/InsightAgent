from pathlib import Path
import fitz  # PyMuPDF
import uuid
from typing import Optional

from app.core.config import Settings
from app.models.schemas import ChunkMetadata


class PDFService:
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.chunk_size = settings.chunk_size
        self.chunk_overlap = settings.chunk_overlap
    
    def process_pdf(
        self,
        file_path: Path,
        document_id: str,
        filename: str
    ) -> list[ChunkMetadata]:
        """
        Extract text from PDF and split into chunks with metadata.
        
        Args:
            file_path: Path to the PDF file
            document_id: Unique identifier for the document
            filename: Original filename
            
        Returns:
            List of ChunkMetadata objects
        """
        chunks: list[ChunkMetadata] = []
        
        doc = fitz.open(file_path)
        
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text("text")
                
                if not text.strip():
                    continue
                
                # Clean text
                text = self._clean_text(text)
                
                # Split page text into chunks
                page_chunks = self._create_chunks(
                    text=text,
                    document_id=document_id,
                    document_name=filename,
                    page_number=page_num + 1,  # 1-indexed
                    start_chunk_index=len(chunks)
                )
                
                chunks.extend(page_chunks)
        finally:
            doc.close()
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        import re
        
        # Remove null bytes and control characters (keep newlines, tabs, spaces)
        text = ''.join(char for char in text if char >= ' ' or char in '\n\t')
        
        # Replace multiple whitespace with single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def _create_chunks(
        self,
        text: str,
        document_id: str,
        document_name: str,
        page_number: int,
        start_chunk_index: int
    ) -> list[ChunkMetadata]:
        """
        Split text into overlapping chunks.
        
        Uses a sliding window approach with configurable size and overlap.
        Tries to break at sentence boundaries when possible.
        """
        chunks: list[ChunkMetadata] = []
        
        if len(text) <= self.chunk_size:
            # Text fits in single chunk
            chunk = ChunkMetadata(
                chunk_id=str(uuid.uuid4()),
                document_id=document_id,
                document_name=document_name,
                page_number=page_number,
                chunk_index=start_chunk_index,
                start_char=0,
                end_char=len(text),
                text=text
            )
            return [chunk]
        
        # Split into sentences for better chunking
        sentences = self._split_into_sentences(text)
        
        current_chunk = ""
        current_start = 0
        char_position = 0
        chunk_index = start_chunk_index
        
        for sentence in sentences:
            sentence_with_space = sentence + " "
            
            if len(current_chunk) + len(sentence_with_space) <= self.chunk_size:
                current_chunk += sentence_with_space
            else:
                # Save current chunk if not empty
                if current_chunk.strip():
                    chunk = ChunkMetadata(
                        chunk_id=str(uuid.uuid4()),
                        document_id=document_id,
                        document_name=document_name,
                        page_number=page_number,
                        chunk_index=chunk_index,
                        start_char=current_start,
                        end_char=current_start + len(current_chunk.strip()),
                        text=current_chunk.strip()
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = self._get_overlap_text(current_chunk)
                current_start = char_position - len(overlap_text)
                current_chunk = overlap_text + sentence_with_space
            
            char_position += len(sentence_with_space)
        
        # Don't forget the last chunk
        if current_chunk.strip():
            chunk = ChunkMetadata(
                chunk_id=str(uuid.uuid4()),
                document_id=document_id,
                document_name=document_name,
                page_number=page_number,
                chunk_index=chunk_index,
                start_char=current_start,
                end_char=current_start + len(current_chunk.strip()),
                text=current_chunk.strip()
            )
            chunks.append(chunk)
        
        return chunks
    
    def _split_into_sentences(self, text: str) -> list[str]:
        """Split text into sentences."""
        import re
        # Simple sentence splitting on common terminators
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    def _get_overlap_text(self, text: str) -> str:
        """Get the overlap portion from the end of text."""
        if len(text) <= self.chunk_overlap:
            return text
        
        # Try to break at word boundary
        overlap_start = len(text) - self.chunk_overlap
        space_pos = text.find(' ', overlap_start)
        
        if space_pos != -1 and space_pos < len(text):
            return text[space_pos + 1:]
        
        return text[-self.chunk_overlap:]
