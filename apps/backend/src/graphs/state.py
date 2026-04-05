"""LangGraph state definition."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class ReportType(str, Enum):
    """Available report types."""
    ANALYTICAL_SUMMARY = "analytical_summary"
    TECHNICAL_REPORT = "technical_report"
    FINEP_REPORT = "finep_report"
    TECHNICAL_OPINION = "technical_opinion"
    SCIENTIFIC_REPORT = "scientific_report"
    ACADEMIC_LONGFORM = "academic_longform"


class AnalysisStatus(str, Enum):
    """Analysis status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewStatus(str, Enum):
    """Review status."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class SecurityDecision(str, Enum):
    """Security scan decision."""
    SAFE = "safe"
    SUSPICIOUS = "suspicious"
    BLOCKED = "blocked"


class ExtractedSection(BaseModel):
    """Extracted document section."""
    title: str
    content: str
    level: int = 1
    page: Optional[int] = None


class ExtractedTable(BaseModel):
    """Extracted table data."""
    headers: List[str]
    rows: List[List[str]]
    caption: Optional[str] = None
    page: Optional[int] = None


class DocumentMetadata(BaseModel):
    """Document metadata."""
    filename: str
    file_type: str
    file_size: int
    page_count: Optional[int] = None
    word_count: Optional[int] = None
    language: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[datetime] = None


class SecurityFlags(BaseModel):
    """Security scan flags."""
    has_prompt_injection: bool = False
    has_prompt_hiding: bool = False
    has_suspicious_instructions: bool = False
    has_malicious_content: bool = False
    risk_score: float = 0.0
    details: List[str] = Field(default_factory=list)


class AuditLogEntry(BaseModel):
    """Audit log entry."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    node: str
    action: str
    details: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None


class AppState(TypedDict, total=False):
    """Main application state for LangGraph."""
    
    # Identifiers
    request_id: str
    user_id: str
    session_id: str
    document_id: str
    
    # Document info
    document_name: str
    document_type: str
    original_file_path: str
    
    # Parsed content
    normalized_content: str
    extracted_sections: List[ExtractedSection]
    extracted_tables: List[ExtractedTable]
    extracted_metadata: DocumentMetadata
    parsing_warnings: List[str]
    
    # Security
    input_security_flags: SecurityFlags
    input_security_decision: SecurityDecision
    
    # Analysis
    analysis_status: AnalysisStatus
    analysis_summary: str
    analysis_key_topics: List[str]
    analysis_insights: Dict[str, Any]
    
    # Report generation
    selected_report_type: ReportType
    generated_report_markdown: str
    generated_report_structured: Dict[str, Any]
    
    # Review
    review_status: ReviewStatus
    review_feedback: str
    quality_score: float
    revision_count: int
    
    # Export
    export_status: str
    export_paths: Dict[str, str]
    
    # UI feedback
    ui_status: str
    ui_progress: float
    ui_current_step: str
    
    # Error handling
    errors: List[str]
    warnings: List[str]
    
    # Audit
    audit_log: List[AuditLogEntry]
    timestamps: Dict[str, datetime]
    
    # Flow control
    current_node: str
    next_node: Optional[str]
    should_retry: bool
    retry_count: int


def create_initial_state(
    request_id: str,
    user_id: str,
    document_id: str,
    document_name: str,
    document_type: str,
    file_path: str,
    selected_report_type: ReportType,
) -> AppState:
    """Create initial state for a new request."""
    return AppState(
        request_id=request_id,
        user_id=user_id,
        session_id=f"session_{request_id}",
        document_id=document_id,
        document_name=document_name,
        document_type=document_type,
        original_file_path=file_path,
        normalized_content="",
        extracted_sections=[],
        extracted_tables=[],
        parsing_warnings=[],
        input_security_flags=SecurityFlags(),
        input_security_decision=SecurityDecision.SAFE,
        analysis_status=AnalysisStatus.PENDING,
        analysis_summary="",
        analysis_key_topics=[],
        analysis_insights={},
        selected_report_type=selected_report_type,
        generated_report_markdown="",
        generated_report_structured={},
        review_status=ReviewStatus.PENDING,
        review_feedback="",
        quality_score=0.0,
        revision_count=0,
        export_status="pending",
        export_paths={},
        ui_status="initialized",
        ui_progress=0.0,
        ui_current_step="upload",
        errors=[],
        warnings=[],
        audit_log=[],
        timestamps={"created_at": datetime.utcnow()},
        current_node="start",
        next_node="parse_document",
        should_retry=False,
        retry_count=0,
    )
