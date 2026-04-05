"""Main LangGraph workflow."""
from typing import Literal

from langgraph.graph import END, StateGraph

from src.agents.review_editor import ReviewEditorAgent
from src.agents.security_guard import SecurityGuardAgent
from src.agents.supervisor import SupervisorAgent
from src.agents.technical_report import TechnicalReportAgent
from src.core.logging import get_logger
from src.graphs.state import AppState, ReportType
from src.parsers.parser_manager import ParserManager

logger = get_logger(__name__)


def parse_document_node(state: AppState) -> AppState:
    """Parse the uploaded document."""
    logger.info("node_parse_document", document_id=state.get("document_id"))
    
    try:
        parser_manager = ParserManager()
        file_path = state.get("original_file_path")
        
        result = parser_manager.parse(file_path)
        
        # Update state with parsed content
        state["normalized_content"] = result.content
        state["extracted_sections"] = result.sections
        state["extracted_tables"] = result.tables
        state["extracted_metadata"] = result.metadata
        state["parsing_warnings"] = result.warnings
        state["current_node"] = "parse_document"
        state["ui_status"] = "Document parsed successfully"
        state["ui_progress"] = 0.2
        
    except Exception as e:
        logger.error("parsing_failed", error=str(e))
        state["errors"] = state.get("errors", []) + [f"Parsing failed: {str(e)}"]
    
    return state


def security_scan_node(state: AppState) -> AppState:
    """Scan document for security threats."""
    logger.info("node_security_scan", document_id=state.get("document_id"))
    
    agent = SecurityGuardAgent()
    return agent.scan(state)


def analyze_document_node(state: AppState) -> AppState:
    """Analyze document content."""
    logger.info("node_analyze_document", document_id=state.get("document_id"))
    
    # Simplified analysis - in production, use a dedicated agent
    content = state.get("normalized_content", "")
    
    # Basic analysis
    word_count = len(content.split())
    summary = f"Document contains {word_count} words."
    
    state["analysis_status"] = "completed"
    state["analysis_summary"] = summary
    state["current_node"] = "analyze_document"
    state["ui_status"] = "Analysis complete"
    state["ui_progress"] = 0.4
    
    return state


def generate_report_node(state: AppState) -> AppState:
    """Generate the requested report."""
    logger.info("node_generate_report", document_id=state.get("document_id"))
    
    report_type = state.get("selected_report_type")
    
    # Route to appropriate agent based on report type
    # For now, using technical report as default
    agent = TechnicalReportAgent()
    return agent.generate(state)


def review_report_node(state: AppState) -> AppState:
    """Review the generated report."""
    logger.info("node_review_report", document_id=state.get("document_id"))
    
    agent = ReviewEditorAgent()
    return agent.review(state)


def export_report_node(state: AppState) -> AppState:
    """Export report to multiple formats."""
    logger.info("node_export_report", document_id=state.get("document_id"))
    
    # Simplified export - in production, use dedicated export agent
    report = state.get("generated_report_markdown", "")
    document_id = state.get("document_id")
    
    # Save markdown
    md_path = f"exports/{document_id}.md"
    state["export_paths"] = {"markdown": md_path}
    state["export_status"] = "completed"
    state["current_node"] = "export_report"
    state["ui_status"] = "Export complete"
    state["ui_progress"] = 1.0
    
    return state


def supervisor_router(state: AppState) -> Literal["parse_document", "security_scan", "analyze_document", "generate_report", "review_report", "export_report", END]:
    """Route to next node based on supervisor decision."""
    supervisor = SupervisorAgent()
    decision = supervisor.decide_next_step(state)
    
    next_node = decision.get("next_node")
    
    # Update UI state
    state["ui_status"] = decision.get("ui_status", "")
    state["ui_progress"] = decision.get("ui_progress", 0.0)
    
    logger.info("supervisor_routing", next_node=next_node)
    
    if next_node == "finish":
        return END
    
    return next_node


def create_workflow() -> StateGraph:
    """Create the main LangGraph workflow."""
    workflow = StateGraph(AppState)
    
    # Add nodes
    workflow.add_node("parse_document", parse_document_node)
    workflow.add_node("security_scan", security_scan_node)
    workflow.add_node("analyze_document", analyze_document_node)
    workflow.add_node("generate_report", generate_report_node)
    workflow.add_node("review_report", review_report_node)
    workflow.add_node("export_report", export_report_node)
    
    # Set entry point
    workflow.set_entry_point("parse_document")
    
    # Add conditional edges through supervisor
    workflow.add_conditional_edges(
        "parse_document",
        supervisor_router,
    )
    workflow.add_conditional_edges(
        "security_scan",
        supervisor_router,
    )
    workflow.add_conditional_edges(
        "analyze_document",
        supervisor_router,
    )
    workflow.add_conditional_edges(
        "generate_report",
        supervisor_router,
    )
    workflow.add_conditional_edges(
        "review_report",
        supervisor_router,
    )
    workflow.add_conditional_edges(
        "export_report",
        supervisor_router,
    )
    
    return workflow.compile()
