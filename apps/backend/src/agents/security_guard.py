"""Security guard agent — multi-layer adversarial content scanner."""
from src.core.config import get_settings
from src.core.logging import get_logger
from src.graphs.state import AppState, SecurityDecision, SecurityFlags
from src.security.prompt_injection_detector import PromptInjectionDetector

logger = get_logger(__name__)
settings = get_settings()

_detector = PromptInjectionDetector()  # lazy — scanners only init on first scan call

# Thresholds
_BLOCK_THRESHOLD = 0.75
_SUSPICIOUS_THRESHOLD = 0.35


class SecurityGuardAgent:
    """Scans document content for adversarial inputs before LLM processing."""

    def __init__(self) -> None:
        self.detector = _detector  # shared singleton — scanners are expensive to init

    def scan(self, state: AppState) -> AppState:
        logger.info("security_scan_started", document_id=state.get("document_id"))

        if not settings.enable_security_guard:
            logger.info("security_guard_disabled")
            state["input_security_decision"] = SecurityDecision.SAFE
            state["input_security_flags"] = SecurityFlags()
            return state

        content = state.get("normalized_content", "")

        is_suspicious, risk_score, details = self.detector.detect(content)

        # Map detail strings to flag fields
        categories = {d.split("]")[0].lstrip("[") for d in details if "]" in d}

        flags = SecurityFlags(
            has_prompt_injection=(
                "direct_injection" in categories
                or "indirect_injection" in categories
                or "llm_guard" in categories
            ),
            has_prompt_hiding=(
                "hidden_text" in categories
                or "control_tokens" in categories
            ),
            has_suspicious_instructions="social_engineering" in categories,
            has_malicious_content="code_execution" in categories,
            risk_score=risk_score,
            details=details,
        )

        if risk_score >= _BLOCK_THRESHOLD:
            decision = SecurityDecision.BLOCKED
            logger.warning(
                "security_threat_blocked",
                document_id=state.get("document_id"),
                risk_score=round(risk_score, 3),
                categories=list(categories),
            )
        elif risk_score >= _SUSPICIOUS_THRESHOLD:
            decision = SecurityDecision.SUSPICIOUS
            logger.warning(
                "security_threat_suspicious",
                document_id=state.get("document_id"),
                risk_score=round(risk_score, 3),
                categories=list(categories),
            )
        else:
            decision = SecurityDecision.SAFE
            logger.info("security_scan_passed", document_id=state.get("document_id"))

        state["input_security_flags"] = flags
        state["input_security_decision"] = decision
        state["current_node"] = "security_scan"

        if decision == SecurityDecision.BLOCKED:
            state["errors"] = state.get("errors", []) + [
                f"Documento bloqueado pela verificação de segurança (score={risk_score:.2f})"
            ]

        return state
