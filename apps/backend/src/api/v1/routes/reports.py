"""Report generation, persistence and retrieval routes."""
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

from src.core.logging import get_logger
from src.graphs.state import ReportType
from src.infrastructure.database import (
    count_reports,
    delete_report,
    get_report,
    list_reports,
    save_report,
)
from src.infrastructure.report_storage import (
    delete_report_file,
    read_report_file,
    save_report_file,
)

logger = get_logger(__name__)
router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────

class GenerateReportRequest(BaseModel):
    document_id: str
    report_type: ReportType


class ReportResponse(BaseModel):
    report_id: str
    document_id: str
    document_name: str
    report_type: str
    status: str
    quality_score: Optional[float] = None
    md_path: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    markdown: Optional[str] = None  # populated on demand


class UpdateReportRequest(BaseModel):
    markdown: str


class ReportListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: list[ReportResponse]


# ── Helpers ────────────────────────────────────────────────────────────────

def _to_response(row: dict, include_markdown: bool = False) -> ReportResponse:
    resp = ReportResponse(
        report_id=row["id"],
        document_id=row["document_id"],
        document_name=row["document_name"],
        report_type=row["report_type"],
        status=row["status"],
        quality_score=row.get("quality_score"),
        md_path=row.get("md_path"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )
    if include_markdown:
        resp.markdown = read_report_file(row.get("md_path", ""))
    return resp


# ── Generate ───────────────────────────────────────────────────────────────

@router.post("/generate", response_model=ReportResponse)
async def generate_report(request: GenerateReportRequest):
    """Generate a report from an analyzed document and persist it."""
    from src.api.v1.routes.documents import documents_store
    from src.agents.report_router import get_report_agent
    from src.graphs.state import AppState, AnalysisStatus
    from src.infrastructure.database import save_document

    if request.document_id not in documents_store:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    doc = documents_store[request.document_id]
    if doc["status"] != "analyzed":
        raise HTTPException(status_code=400, detail="Documento precisa ser analisado primeiro")

    analysis = doc.get("analysis")
    if not analysis:
        raise HTTPException(status_code=400, detail="Dados de análise não disponíveis")

    # Persist document metadata to DB
    save_document(doc)

    report_id = str(uuid.uuid4())

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
        "analysis_summary": f"Documento com {analysis['word_count']} palavras",
        "selected_report_type": request.report_type,
        "generated_report_markdown": "",
        "review_feedback": "",
        "revision_count": 0,
        "errors": [],
        "current_node": "generate_report",
    }

    try:
        from src.agents.report_router import get_report_agent
        agent = get_report_agent(request.report_type.value)
        state = agent.generate(state)
    except Exception as e:
        logger.error("report_generation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Falha na geração: {str(e)}")

    if state.get("errors"):
        raise HTTPException(status_code=500, detail=state["errors"][-1])

    markdown = state.get("generated_report_markdown", "")

    # Save file to disk under reports/
    md_path = save_report_file(
        report_id=report_id,
        document_name=doc["filename"],
        report_type=request.report_type.value,
        markdown=markdown,
    )

    # Persist metadata to SQLite
    from datetime import datetime
    now = datetime.utcnow().isoformat()
    record = {
        "report_id": report_id,
        "document_id": request.document_id,
        "document_name": doc["filename"],
        "report_type": request.report_type.value,
        "status": "generated",
        "quality_score": None,
        "md_path": md_path,
        "created_at": now,
    }
    save_report(record)

    logger.info("report_saved", report_id=report_id, path=md_path)

    row = get_report(report_id)
    resp = _to_response(row, include_markdown=True)
    return resp


# ── List / Search ──────────────────────────────────────────────────────────

@router.get("", response_model=ReportListResponse)
async def list_all_reports(
    search: Optional[str] = Query(None, description="Busca por nome do documento"),
    report_type: Optional[str] = Query(None, description="Filtrar por tipo de relatório"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List and search saved reports."""
    offset = (page - 1) * page_size
    rows = list_reports(search=search, report_type=report_type, limit=page_size, offset=offset)
    total = count_reports(search=search, report_type=report_type)

    return ReportListResponse(
        total=total,
        page=page,
        page_size=page_size,
        results=[_to_response(r) for r in rows],
    )


# ── Get single ────────────────────────────────────────────────────────────

@router.get("/{report_id}", response_model=ReportResponse)
async def get_single_report(report_id: str):
    """Get report metadata + markdown content."""
    row = get_report(report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    return _to_response(row, include_markdown=True)


# ── Update (user edits) ────────────────────────────────────────────────────

@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(report_id: str, request: UpdateReportRequest):
    """Save user edits back to disk and DB."""
    from src.infrastructure.database import update_report_content

    row = get_report(report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    # Overwrite file on disk
    md_path = row.get("md_path", "")
    if md_path:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(request.markdown)
    else:
        # Create new file if path missing
        md_path = save_report_file(
            report_id=report_id,
            document_name=row["document_name"],
            report_type=row["report_type"],
            markdown=request.markdown,
        )

    update_report_content(report_id, md_path, status="edited")
    row = get_report(report_id)
    return _to_response(row, include_markdown=True)


# ── Delete ─────────────────────────────────────────────────────────────────

@router.delete("/{report_id}")
async def remove_report(report_id: str):
    """Delete report from DB and disk."""
    row = get_report(report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")

    delete_report_file(row.get("md_path", ""))
    delete_report(report_id)
    return {"deleted": report_id}


# ── Export endpoints ───────────────────────────────────────────────────────

@router.get("/{report_id}/markdown")
async def get_markdown(report_id: str):
    row = get_report(report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    return {"markdown": read_report_file(row.get("md_path", ""))}


@router.get("/{report_id}/export/md")
async def export_md(report_id: str):
    """Download .md file."""
    row = get_report(report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    md_path = row.get("md_path", "")
    if not md_path or not __import__("os").path.exists(md_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado em disco")
    return FileResponse(
        md_path,
        media_type="text/markdown",
        filename=__import__("os").path.basename(md_path),
    )


@router.get("/{report_id}/export/pdf")
async def export_pdf(report_id: str):
    """Export report as PDF."""
    row = get_report(report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    md_path = row.get("md_path", "")
    if not md_path or not __import__("os").path.exists(md_path):
        raise HTTPException(status_code=404, detail="Arquivo markdown não encontrado")
    try:
        from src.exporters.pdf_exporter import md_to_pdf
        pdf_path = md_to_pdf(md_path)
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=__import__("os").path.basename(pdf_path),
        )
    except Exception as e:
        logger.error("pdf_export_failed", report_id=report_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Falha ao gerar PDF: {str(e)}")


@router.get("/{report_id}/export/docx")
async def export_docx(report_id: str):
    """Export report as DOCX using python-docx."""
    row = get_report(report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    md_path = row.get("md_path", "")
    if not md_path or not __import__("os").path.exists(md_path):
        raise HTTPException(status_code=404, detail="Arquivo markdown não encontrado")
    try:
        from src.exporters.docx_exporter import md_to_docx
        docx_path = md_to_docx(md_path)
        return FileResponse(
            docx_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=__import__("os").path.basename(docx_path),
        )
    except Exception as e:
        logger.error("docx_export_failed", report_id=report_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Falha ao gerar DOCX: {str(e)}")
