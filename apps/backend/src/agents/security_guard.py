"""Security guard agent."""
from src.core.config import get_settings
from src.core.logging import get_logger
from src.graphs.state import AppState, SecurityDecision, SecurityFlags
from src.security.prompt_injection_detector import PromptInjectionDetector

logger = get_logger(__name__)
settings = get_settings()


class SecurityGuardAgent:
    """Scans content for security threats."""
    
    def __init__(self) -> None:
        """Initialize security guard."""
        self.detector = PromptInjectionDetector()
    
    def scan(self, state: AppState) -> AppState:
        """Scan document content for security threats."""
        logger.info("security_scan_started", document_id=state.get("document_id"))
        
        content = state.get("normalized_content", "")
        
        if not settings.enable_security_guard:
            logger.info("security_guard_disabled")
            state["input_security_decision"] = SecurityDecision.SAFE
            state["input_security_flags"] = SecurityFlags()
            return state
        
        # Detect prompt injection
        is_suspicious, risk_score, details = self.detector.detect(content)
        
        # Create security flags
        flags = SecurityFlags(
            has_prompt_injection=is_suspicious,
            risk_score=risk_score,
            details=details,
        )
        
        # Make decision
        if risk_score >= 0.8:
            decision = SecurityDecision.BLOCKED
            logger.warning(
                "security_threat_blocked",
                document_id=state.get("document_id"),
                risk_score=risk_score,
            )
        elif risk_score >= 0.4:
            decision = SecurityDecision.SUSPICIOUS
            logger.warning(
                "security_threat_suspicious",
                document_id=state.get("document_id"),
                risk_score=risk_score,
            )
        else:
            decision = SecurityDecision.SAFE
            logger.info("security_scan_passed", document_id=state.get("document_id"))
        
        # Update state
        state["input_security_flags"] = flags
        state["input_security_decision"] = decision
        state["current_node"] = "security_scan"
        
        if decision == SecurityDecision.BLOCKED:
            state["errors"] = state.get("errors", []) + ["Document blocked by security scan"]
        
        return state
