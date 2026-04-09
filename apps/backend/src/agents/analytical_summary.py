"""Agente: Resumo Analítico com storytelling, estatísticas e gráficos."""
from langchain_core.messages import HumanMessage, SystemMessage

from src.agents.base_report_agent import BaseReportAgent
from src.agents.chart_builder import build_analytics_artifacts
from src.core.logging import get_logger
from src.graphs.state import AppState

logger = get_logger(__name__)


class AnalyticalSummaryAgent(BaseReportAgent):
    report_type = "analytical_summary"
    # SYSTEM_PROMPT loaded automatically from .prompts/analytical_summary.md

    def generate(self, state: AppState) -> AppState:
        logger.info("generating_analytical_summary", document_id=state.get("document_id"))

        file_path = state.get("original_file_path", "")
        artifacts = build_analytics_artifacts(file_path)
        charts_md = artifacts["charts_md"]
        appendix_md = artifacts["appendix_md"]
        stats = artifacts["stats"]

        content = state.get("normalized_content", "")
        analysis = state.get("analysis_summary", "")
        metadata = state.get("extracted_metadata")
        review_feedback = state.get("review_feedback", "")

        context_parts = [
            "## INSTRUÇÃO DE IDIOMA",
            "Todo o relatório DEVE ser escrito em Português do Brasil (pt-BR).",
            "## INSTRUÇÃO DE COMPLETUDE",
            "Gere o relatório COMPLETO e DETALHADO agora. NÃO faça perguntas. NÃO peça confirmação.",
            "",
        ]

        if stats:
            context_parts += [
                "## Estatísticas Computadas (use estes números exatos)",
                f"- Total de testes/registros: {stats['total']}",
                f"- Aprovados (Passou): {stats['passou']} ({stats['taxa_geral']:.1f}%)",
                f"- Reprovados (Falhou): {stats['falhou']} ({100 - stats['taxa_geral']:.1f}%)",
                f"- Número de categorias: {stats['num_categorias']}",
                f"- Melhor categoria: {stats['melhor_categoria']} ({stats['melhor_taxa']:.1f}%)",
                f"- Pior categoria: {stats['pior_categoria']} ({stats['pior_taxa']:.1f}%)",
                "",
            ]

        enriched = self._enrich_csv_context(state)
        if enriched:
            context_parts += ["## Dados Estruturados do Documento", enriched]
        else:
            context_parts += ["## Conteúdo do Documento Fonte", content[:12000]]

        context_parts += ["", "## Resumo da Análise", analysis]

        if metadata:
            context_parts += [
                "", "## Metadados",
                f"Arquivo: {metadata.filename}",
                f"Tipo: {metadata.file_type}",
                f"Palavras: {metadata.word_count}",
            ]

        if review_feedback:
            context_parts += [
                "", "## Feedback da Revisão Anterior (corrija estes pontos):",
                review_feedback,
            ]

        if charts_md:
            context_parts += [
                "",
                "## Nota sobre Gráficos",
                "Os gráficos serão inseridos automaticamente após a seção 3 do relatório. "
                "Referencie-os no texto como 'conforme ilustrado nos gráficos abaixo'.",
            ]

        if appendix_md:
            context_parts += [
                "",
                "## Nota sobre Apêndice",
                "A lista completa de testes será anexada automaticamente ao final. "
                "Referencie-a na metodologia como 'vide Anexo — Lista de Testes Realizados'.",
            ]

        context_parts += [
            "",
            "**IMPORTANTE: Gere o relatório completo AGORA. Mínimo 2.000 palavras. "
            "Formato Markdown. 100% em Português do Brasil.**",
        ]

        context = "\n".join(context_parts)

        try:
            response = self.llm.invoke([
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=context),
            ])
            report_md = response.content

            if charts_md:
                inject_marker = "## 4."
                if inject_marker in report_md:
                    report_md = report_md.replace(
                        inject_marker,
                        f"\n\n## Visualizações\n\n{charts_md}\n\n{inject_marker}",
                        1,
                    )
                else:
                    report_md += f"\n\n## Visualizações\n\n{charts_md}"

            if appendix_md:
                report_md += appendix_md

            state["generated_report_markdown"] = report_md
            state["current_node"] = "generate_report"
            logger.info(
                "analytical_summary_generated",
                document_id=state.get("document_id"),
                length=len(report_md),
                has_charts=bool(charts_md),
                has_appendix=bool(appendix_md),
            )
        except Exception as e:
            logger.error("analytical_summary_failed", error=str(e))
            state["errors"] = state.get("errors", []) + [f"Falha na geração: {str(e)}"]

        return state
