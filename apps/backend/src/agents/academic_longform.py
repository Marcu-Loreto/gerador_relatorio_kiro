"""Agente: Documento Acadêmico Longo (Dissertação/Tese)."""
from src.agents.base_report_agent import BaseReportAgent


class AcademicLongformAgent(BaseReportAgent):
    report_type = "academic_longform"
