"""FastAPI application entry point."""
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.core.config import get_settings
from src.core.logging import get_logger, setup_logging

settings = get_settings()
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("application_starting", version=settings.app_version)
    os.makedirs(settings.storage_local_path, exist_ok=True)
    os.makedirs("exports", exist_ok=True)
    os.makedirs("reports", exist_ok=True)
    # Initialize SQLite database
    from src.infrastructure.database import init_db
    init_db()
    logger.info("database_initialized", path="reports/relatorios.db")
    yield
    logger.info("application_shutting_down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Sistema profissional de análise documental e geração de relatórios com IA",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "version": settings.app_version}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Import and include routers
from src.api.v1.routes import auth, documents, reports

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "endpoints": {
            "auth": "/api/v1/auth/login",
            "upload": "/api/v1/documents/upload",
            "analyze": "/api/v1/documents/{document_id}/analyze",
            "generate": "/api/v1/reports/generate",
            "report": "/api/v1/reports/{report_id}",
            "export_md": "/api/v1/reports/{report_id}/export/md",
        },
    }
