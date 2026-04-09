"""Review and editorial agent."""
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from src.agents.prompt_loader import load_prompt
from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.model_selector import TaskType, get_model_selector
from src.graphs.state import AppState, ReviewStatus

logger = get_logger(__name__)
settings = get_settings()

REVIEW_PROMPT = load_prompt("review_editor")


class ReviewResult(BaseModel):
    """Review result schema."""
    status: str
    quality_score: float
    feedback: str
    issues: list[str]
    strengths: list[str]


class ReviewEditorAgent:
    """Reviews and validates generated reports."""
    
    def __init__(self) -> None:
        """Initialize agent with model selector."""
        self.model_selector = get_model_selector()
    
    def review(self, state: AppState) -> AppState:
        """Review the generated report."""
        logger.info("reviewing_report", document_id=state.get("document_id"))
        
        report = state.get("generated_report_markdown", "")
        report_type = state.get("selected_report_type")
        original_content = state.get("normalized_content", "")[:5000]
        
        # Review is complex task - uses complex model (GPT-4o)
        llm = self.model_selector.get_llm(
            task_type=TaskType.REVIEW,
            content=report,
            temperature=0.2,  # Low temperature for consistent reviews
        ).with_structured_output(ReviewResult)
        
        model_info = self.model_selector.get_model_info(
            self.model_selector.select_model(TaskType.REVIEW, report)
        )
        logger.info(
            "model_selected_for_review",
            model=model_info["name"],
            provider=model_info["provider"],
            cost_tier=model_info["cost_tier"],
        )
        
        # Build review context
        context = f"""## INSTRUÇÃO DE IDIOMA
Todo o feedback e a revisão DEVEM ser em Português do Brasil (pt-BR).
O relatório revisado também DEVE estar inteiramente em Português do Brasil.

## Tipo de Relatório
{report_type}

## Relatório Gerado (para revisar)
{report}

## Documento Original (trecho)
{original_content}

Por favor, revise este relatório criteriosamente em Português do Brasil.
"""
        
        try:
            messages = [
                SystemMessage(content=REVIEW_PROMPT),
                HumanMessage(content=context),
            ]
            
            result: ReviewResult = llm.invoke(messages)
            
            # Map status
            status_map = {
                "approved": ReviewStatus.APPROVED,
                "rejected": ReviewStatus.REJECTED,
                "needs_revision": ReviewStatus.NEEDS_REVISION,
            }
            review_status = status_map.get(result.status, ReviewStatus.NEEDS_REVISION)
            
            # Update state
            state["review_status"] = review_status
            state["review_feedback"] = result.feedback
            state["quality_score"] = result.quality_score
            state["current_node"] = "review_report"
            
            if review_status != ReviewStatus.APPROVED:
                state["revision_count"] = state.get("revision_count", 0) + 1
            
            logger.info(
                "review_completed",
                document_id=state.get("document_id"),
                status=review_status,
                quality_score=result.quality_score,
            )
            
        except Exception as e:
            logger.error("review_failed", error=str(e))
            # Default to needs revision on error
            state["review_status"] = ReviewStatus.NEEDS_REVISION
            state["review_feedback"] = f"Review process encountered an error: {str(e)}"
            state["quality_score"] = 0.5
        
        return state
