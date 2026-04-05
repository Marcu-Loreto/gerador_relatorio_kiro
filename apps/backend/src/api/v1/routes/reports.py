"""Report generation and export routes."""
import os
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.core.config import get_settings
from src.core.logging import get_logger
from src.graphs.state import ReportType

logger = get_logger(__name__)
router = APIRouter()

# In-memory store for demo
reports_store: dict = {}


class GenerateReportRequest(BaseModel):
    """Request to generate a report."""
    document_id: str
    report_type: ReportType


class ReportResponse(BaseModel):
    """Report response model."""
    report_id: str
    document_id: str
    report_type: str
    status: str
    markdown: Optional[str] = None
    quality_score: Optional[float] = None


class UpdateReportRequest(BaseModel):
    """Request to update report content."""
    markdown: str


@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: GenerateReportRequest):
    """Generate a report from an analyzed document."""
    settings = get_settings()

    # Get document from documents store
    from src.api.v1.routes.documents import documents_store

    if request.document_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")

    doc = documents_store[request.document_id]

    if doc["status"] != "analyzed":
        raise HTTPException(status_code=400, detail="Document must be analyzed first")

    analysis = doc.get("analysis")
    if not analysis:
        raise HTTPException(status_code=400, detail="No analysis data available")

    report_id = str(uuid.uuid4())

    # Generate report using the agent
    from src.agents.technical_report import TechnicalReportAgent
    from src.agents.review_editor import ReviewEditorAgent
    from src.graphs.state import AppState, AnalysisStatus

    # Build state
    state: AppState = {
        "request_id": report_id,
        "user_id": "demo_user",
        "document_id": request.document_id,
        "document_name": doc["filename"],
        "document_type": doc["file_type"],
        "original_file_path": doc["file_path"],
        "normalized_content": analysis["content"],
        "extracted_sections": [],
        "extracted_tables": [],
        "analysis_status": AnalysisStatus.COMPLETED,
        "analysis_summary": f"Document with {analysis['word_count']} words",
        "selected_report_type": request.report_type,
        "generated_report_markdown": "",
        "review_feedback": "",
        "revision_count": 0,
        "errors": [],
        "current_node": "generate_report",
    }

    # Generate
    try:
        agent = TechnicalReportAgent()
        state = agent.generate(state)
    except Exception as e:
        logger.error("report_generation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")

    if state.get("errors"):
        raise HTTPException(status_code=500, detail=state["errors"][-1])

    markdown = state.get("generated_report_markdown", "")

    # Store report
    report_data = {
        "report_id": report_id,
        "document_id": request.document_id,
        "report_type": request.report_type.value,
        "status": "generated",
        "markdown": markdown,
        "quality_score": None,
        "review_feedback": None,
    }
    reports_store[report_id] = report_data

    logger.info("report_generated", report_id=report_id, type=request.report_type.value)

    return ReportResponse(
        report_id=report_id,
        document_id=request.document_id,
        report_type=request.report_type.value,
        status="generated",
        markdown=markdown,
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str):
    """Get a report by ID."""
    if report_id not in reports_store:
        raise HTTPException(status_code=404, detail="Report not found")

    r = reports_store[report_id]
    return ReportResponse(**r)


@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(report_id: str, request: UpdateReportRequest):
    """Update report markdown content (user edits)."""
    if report_id not in reports_store:
        raise HTTPException(status_code=404, detail="Report not found")

    reports_store[report_id]["markdown"] = request.markdown
    reports_store[report_id]["status"] = "edited"

    r = reports_store[report_id]
    return ReportResponse(**r)


@router.get("/{report_id}/markdown")
async def get_report_markdown(report_id: str):
    """Get raw markdown of a report."""
    if report_id not in reports_store:
        raise HTTPException(status_code=404, detail="Report not found")

    return {"markdown": reports_store[report_id]["markdown"]}


@router.get("/{report_id}/export/md")
async def export_markdown(report_id: str):
    """Export report as markdown file."""
    from fastapi.responses import Response

    if report_id not in reports_store:
        raise HTTPException(status_code=404, detail="Report not found")

    md = reports_store[report_id]["markdown"]
    filename = f"report_{report_id[:8]}.md"

    return Response(
        content=md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{report_id}/export/pdf")
async def export_pdf(report_id: str):
    """Export report as PDF."""
    if report_id not in reports_store:
        raise HTTPException(status_code=404, detail="Report not found")

    # Simplified: return markdown with note about PDF
    # In production, use WeasyPrint or Pandoc
    return {"status": "pdf_export_not_yet_implemented", "report_id": report_id}


@router.get("/{report_id}/export/docx")
async def export_docx(report_id: str):
    """Export report as DOCX."""
    if report_id not in reports_store:
        raise HTTPException(status_code=404, detail="Report not found")

    return {"status": "docx_export_not_yet_implemented", "report_id": report_id}
