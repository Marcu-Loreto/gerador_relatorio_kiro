"""Document upload and analysis routes."""
import asyncio
import os
import uuid
from typing import Optional

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.logging import get_logger
from src.security.input_validator import InputValidator

logger = get_logger(__name__)
router = APIRouter()

# In-memory store for demo (use DB in production)
documents_store: dict = {}


class DocumentResponse(BaseModel):
    """Document response model."""
    document_id: str
    filename: str
    file_type: str
    file_size: int
    status: str


class AnalysisResponse(BaseModel):
    """Analysis response model."""
    document_id: str
    status: str
    summary: str
    word_count: int
    sections_count: int


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload a document for analysis."""
    settings = get_settings()
    validator = InputValidator()

    # Validate filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    safe_filename = validator.sanitize_filename(file.filename)
    _, ext = os.path.splitext(safe_filename)

    if ext.lower() not in settings.allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not allowed. Allowed: {settings.allowed_extensions}",
        )

    # Stream file to disk in chunks (avoids loading entire file into memory)
    document_id = str(uuid.uuid4())
    upload_dir = settings.storage_local_path
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{document_id}{ext}")

    file_size = 0
    chunk_size = 1024 * 256  # 256 KB chunks
    async with aiofiles.open(file_path, "wb") as out:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            file_size += len(chunk)
            if file_size > settings.max_upload_size_bytes:
                await out.close()
                os.remove(file_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Max: {settings.max_upload_size_bytes} bytes",
                )
            await out.write(chunk)

    if file_size == 0:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="File is empty")

    # Store metadata
    doc_data = {
        "document_id": document_id,
        "filename": safe_filename,
        "file_type": ext.lstrip("."),
        "file_size": file_size,
        "file_path": file_path,
        "status": "uploaded",
        "analysis": None,
    }
    documents_store[document_id] = doc_data

    # Persist to SQLite in a thread to avoid blocking the event loop
    from src.infrastructure.database import save_document
    await asyncio.to_thread(save_document, doc_data)

    logger.info("document_uploaded", document_id=document_id, filename=safe_filename, size=file_size)

    return DocumentResponse(
        document_id=document_id,
        filename=safe_filename,
        file_type=ext.lstrip("."),
        file_size=file_size,
        status="uploaded",
    )


@router.post("/{document_id}/analyze", response_model=AnalysisResponse)
async def analyze_document(document_id: str):
    """Analyze an uploaded document."""
    if document_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = documents_store[document_id]
    file_path = doc["file_path"]

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    # Parse document in a thread (CPU-bound, avoids blocking event loop)
    from src.parsers.parser_manager import ParserManager
    from src.security.prompt_injection_detector import PromptInjectionDetector

    try:
        parser = ParserManager()
        result = await asyncio.to_thread(parser.parse, file_path)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Security scan in a thread
    detector = PromptInjectionDetector()
    is_suspicious, risk_score, details = await asyncio.to_thread(detector.detect, result.content)

    if risk_score >= 0.8:
        logger.warning("document_blocked", document_id=document_id, risk_score=risk_score)
        raise HTTPException(
            status_code=403,
            detail="Document blocked due to security concerns",
        )

    # Store analysis
    analysis = {
        "content": result.content,
        "sections": [s.model_dump() for s in result.sections],
        "tables": [t.model_dump() for t in result.tables],
        "metadata": result.metadata.model_dump() if result.metadata else {},
        "warnings": result.warnings,
        "word_count": len(result.content.split()),
        "security_risk": risk_score,
        "security_details": details,
    }
    doc["analysis"] = analysis
    doc["status"] = "analyzed"

    logger.info("document_analyzed", document_id=document_id, word_count=analysis["word_count"])

    return AnalysisResponse(
        document_id=document_id,
        status="analyzed",
        summary=f"Document analyzed: {analysis['word_count']} words, {len(result.sections)} sections",
        word_count=analysis["word_count"],
        sections_count=len(result.sections),
    )


@router.get("/{document_id}")
async def get_document(document_id: str):
    """Get document details."""
    if document_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = documents_store[document_id]
    return {
        "document_id": doc["document_id"],
        "filename": doc["filename"],
        "file_type": doc["file_type"],
        "file_size": doc["file_size"],
        "status": doc["status"],
        "analysis_summary": doc["analysis"]["word_count"] if doc.get("analysis") else None,
    }
