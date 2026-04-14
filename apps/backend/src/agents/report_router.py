"""Routes report generation to the correct specialist agent."""
from src.core.logging import get_logger
from src.graphs.state import AppState, ReportType

logger = get_logger(__name__)


def get_report_agent(report_type: str):
    """Return the correct agent instance for the given report type."""
    from src.agents.technical_report import TechnicalReportAgent
    from src.agents.analytical_summary import AnalyticalSummaryAgent
    from src.agents.finep_report import FinepReportAgent
    from src.agents.technical_opinion import TechnicalOpinionAgent
    from src.agents.scientific_report import ScientificReportAgent
    from src.agents.academic_longform import AcademicLongformAgent
    from src.agents.requirements_test_doc import RequirementsTestDocAgent

    agents = {
        ReportType.TECHNICAL_REPORT:      TechnicalReportAgent,
        ReportType.ANALYTICAL_SUMMARY:    AnalyticalSummaryAgent,
        ReportType.FINEP_REPORT:          FinepReportAgent,
        ReportType.TECHNICAL_OPINION:     TechnicalOpinionAgent,
        ReportType.SCIENTIFIC_REPORT:     ScientificReportAgent,
        ReportType.ACADEMIC_LONGFORM:     AcademicLongformAgent,
        ReportType.REQUIREMENTS_TEST_DOC: RequirementsTestDocAgent,
        # string fallbacks
        "technical_report":      TechnicalReportAgent,
        "analytical_summary":    AnalyticalSummaryAgent,
        "finep_report":          FinepReportAgent,
        "technical_opinion":     TechnicalOpinionAgent,
        "scientific_report":     ScientificReportAgent,
        "academic_longform":     AcademicLongformAgent,
        "requirements_test_doc": RequirementsTestDocAgent,
    }

    agent_class = agents.get(report_type, TechnicalReportAgent)
    logger.info("report_agent_selected", report_type=report_type, agent=agent_class.__name__)
    return agent_class()


def generate_report(state: AppState) -> AppState:
    """Route to the correct specialist agent and generate the report."""
    report_type = state.get("selected_report_type", "technical_report")
    agent = get_report_agent(report_type)
    return agent.generate(state)
