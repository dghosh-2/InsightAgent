from fastapi import APIRouter, UploadFile, File, HTTPException, Request
import uuid

from app.core.config import get_settings
from app.models.schemas import (
    UploadResponse,
    DocumentListResponse,
    DocumentInfo,
    DeleteResponse
)
from app.services.pdf_service import PDFService
from app.services.batch_processor import batch_process_pdfs
from app.services.vector_store import VectorStore

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(request: Request, file: UploadFile = File(...)):
    """
    Upload a PDF document for processing.
    
    The document will be:
    1. Saved to disk
    2. Text extracted and chunked
    3. Embedded and stored in vector database
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    settings = get_settings()
    vector_store: VectorStore = request.app.state.vector_store
    
    # Generate document ID
    document_id = str(uuid.uuid4())
    
    # Read file content
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    
    # Save file to disk
    file_path = settings.uploads_dir / f"{document_id}.pdf"
    with open(file_path, "wb") as f:
        f.write(content)
    
    try:
        # Process PDF
        pdf_service = PDFService(settings)
        chunks = pdf_service.process_pdf(file_path, document_id, file.filename)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        # Get page count
        page_count = max(chunk.page_number for chunk in chunks)
        
        # Add to vector store
        vector_store.add_document(
            document_id=document_id,
            filename=file.filename,
            chunks=chunks,
            file_size=len(content)
        )
        
        return UploadResponse(
            document_id=document_id,
            filename=file.filename,
            page_count=page_count,
            chunk_count=len(chunks),
            message="Document uploaded and processed successfully"
        )
        
    except Exception as e:
        # Clean up on failure
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(request: Request):
    """List all uploaded documents."""
    vector_store: VectorStore = request.app.state.vector_store
    documents = vector_store.list_documents()
    
    return DocumentListResponse(
        documents=documents,
        total_count=len(documents)
    )


@router.post("/upload/batch")
async def upload_documents_batch(request: Request, files: list[UploadFile] = File(...)):
    """
    Upload and process multiple PDF documents concurrently.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    settings = get_settings()
    vector_store: VectorStore = request.app.state.vector_store

    to_process: list[tuple] = []
    file_sizes: dict[str, int] = {}
    filenames: dict[str, str] = {}
    saved_paths = []

    for file in files:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Only PDF files are supported: {file.filename}")

        document_id = str(uuid.uuid4())
        content = await file.read()
        if len(content) == 0:
            raise HTTPException(status_code=400, detail=f"Empty file uploaded: {file.filename}")

        file_path = settings.uploads_dir / f"{document_id}.pdf"
        with open(file_path, "wb") as handle:
            handle.write(content)

        saved_paths.append(file_path)
        file_sizes[document_id] = len(content)
        filenames[document_id] = file.filename
        to_process.append((file_path, document_id, file.filename))

    try:
        chunks, throughput = batch_process_pdfs(
            to_process,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        if not chunks:
            raise HTTPException(status_code=400, detail="Could not extract text from any uploaded PDF")

        chunks_by_document: dict[str, list] = {}
        for chunk in chunks:
            chunks_by_document.setdefault(chunk.document_id, []).append(chunk)

        uploaded = []
        for document_id, document_chunks in chunks_by_document.items():
            vector_store.add_document(
                document_id=document_id,
                filename=filenames[document_id],
                chunks=document_chunks,
                file_size=file_sizes[document_id],
            )
            uploaded.append(
                {
                    "document_id": document_id,
                    "filename": filenames[document_id],
                    "page_count": max(chunk.page_number for chunk in document_chunks),
                    "chunk_count": len(document_chunks),
                }
            )

        return {
            "message": "Batch upload completed successfully",
            "documents": uploaded,
            "total_documents": len(uploaded),
            "total_chunks": len(chunks),
            "throughput_pages_per_second": throughput,
        }
    except Exception as exc:
        for path in saved_paths:
            if path.exists():
                path.unlink()
        raise HTTPException(status_code=500, detail=f"Error processing batch upload: {exc}")


@router.delete("/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(request: Request, document_id: str):
    """Delete a document and its associated data."""
    settings = get_settings()
    vector_store: VectorStore = request.app.state.vector_store
    
    # Check if document exists
    if not vector_store.document_exists(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Remove from vector store
    vector_store.remove_document(document_id)
    
    # Delete PDF file
    file_path = settings.uploads_dir / f"{document_id}.pdf"
    if file_path.exists():
        file_path.unlink()
    
    return DeleteResponse(
        document_id=document_id,
        message="Document deleted successfully"
    )
