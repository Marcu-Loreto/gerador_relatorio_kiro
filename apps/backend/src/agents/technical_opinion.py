"""Agente: Parecer Técnico."""
from src.agents.base_report_agent import BaseReportAgent


class TechnicalOpinionAgent(BaseReportAgent):
    report_type = "technical_opinion"
