from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
from pathlib import Path
from time import perf_counter
import re
import uuid

import fitz

from app.models.schemas import ChunkMetadata


DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 100
SENTENCE_SPLIT_PATTERN = re.compile(r"(?<=[.!?])\s+")
WHITESPACE_PATTERN = re.compile(r"\s+")


def _clean_text(text: str) -> str:
    cleaned = "".join(char for char in text if char >= " " or char in "\n\t")
    cleaned = WHITESPACE_PATTERN.sub(" ", cleaned)
    return cleaned.strip()


def _regex_sliding_window_chunks(text: str, chunk_size: int, chunk_overlap: int) -> list[tuple[int, int, str]]:
    if not text:
        return []

    if chunk_overlap >= chunk_size:
        chunk_overlap = max(chunk_size // 5, 1)

    step = max(chunk_size - chunk_overlap, 1)
    chunks: list[tuple[int, int, str]] = []

    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        candidate = text[start:end]

        # Try to finish on sentence boundary if a complete sentence exists.
        parts = SENTENCE_SPLIT_PATTERN.split(candidate)
        if len(parts) > 1:
            candidate = " ".join(parts[:-1]).strip() or candidate
            end = start + len(candidate)

        candidate = candidate.strip()
        if candidate:
            chunks.append((start, end, candidate))

        if end >= text_length:
            break
        start += step

    return chunks


def process_single_pdf(
    file_path: str,
    document_id: str,
    filename: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> dict:
    """
    Process one PDF and return chunk payloads serializable across process boundaries.
    """
    page_count = 0
    serialized_chunks: list[dict] = []

    doc = fitz.open(file_path)
    try:
        chunk_index = 0
        for page_num in range(len(doc)):
            page_count += 1
            text = _clean_text(doc[page_num].get_text("text"))
            if not text:
                continue

            for start_char, end_char, chunk_text in _regex_sliding_window_chunks(
                text=text,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            ):
                serialized_chunks.append(
                    {
                        "chunk_id": str(uuid.uuid4()),
                        "document_id": document_id,
                        "document_name": filename,
                        "page_number": page_num + 1,
                        "chunk_index": chunk_index,
                        "start_char": start_char,
                        "end_char": end_char,
                        "text": chunk_text,
                    }
                )
                chunk_index += 1
    finally:
        doc.close()

    return {
        "document_id": document_id,
        "filename": filename,
        "page_count": page_count,
        "chunks": serialized_chunks,
    }


def batch_process_pdfs(
    file_paths: list[tuple[Path, str, str]],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> tuple[list[ChunkMetadata], float]:
    """
    Process PDFs concurrently and return all chunks + throughput in pages/sec.
    """
    if not file_paths:
        return [], 0.0

    total_pages = 0
    all_chunks: list[ChunkMetadata] = []
    workers = max(1, min(len(file_paths), cpu_count()))
    started_at = perf_counter()

    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                process_single_pdf,
                str(path),
                document_id,
                filename,
                chunk_size,
                chunk_overlap,
            )
            for path, document_id, filename in file_paths
        ]

        for future in as_completed(futures):
            result = future.result()
            total_pages += int(result["page_count"])
            all_chunks.extend(ChunkMetadata(**chunk) for chunk in result["chunks"])

    elapsed = perf_counter() - started_at
    throughput = total_pages / elapsed if elapsed > 0 else 0.0
    return all_chunks, throughput
