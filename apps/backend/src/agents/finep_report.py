"""Agente: Relatório FINEP."""
from src.agents.base_report_agent import BaseReportAgent


class FinepReportAgent(BaseReportAgent):
    report_type = "finep_report"
