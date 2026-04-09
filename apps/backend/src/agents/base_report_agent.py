"""Base class for all report generation agents."""
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.agents.prompt_loader import load_prompt
from src.core.config import get_settings
from src.core.logging import get_logger
from src.graphs.state import AppState

logger = get_logger(__name__)
settings = get_settings()


class BaseReportAgent:
    """Base class — subclasses set report_type; SYSTEM_PROMPT is loaded from .prompts/<report_type>.md."""

    # Subclasses may override SYSTEM_PROMPT directly (legacy) or leave it empty
    # to have it loaded automatically from .prompts/<report_type>.md at init time.
    SYSTEM_PROMPT: str = ""
    report_type: str = "report"

    def __init__(self) -> None:
        # Load prompt from file if not hardcoded by subclass
        if not self.SYSTEM_PROMPT and self.report_type != "report":
            self.SYSTEM_PROMPT = load_prompt(self.report_type)

        self.llm = ChatOpenAI(
            model=settings.complex_model,
            temperature=0.2,
            max_tokens=8000,
            api_key=settings.openai_api_key,
        )

    def generate(self, state: AppState) -> AppState:
        logger.info(f"generating_{self.report_type}", document_id=state.get("document_id"))

        content         = state.get("normalized_content", "")
        analysis        = state.get("analysis_summary", "")
        metadata        = state.get("extracted_metadata")
        review_feedback = state.get("review_feedback", "")
        file_path       = state.get("original_file_path", "")

        # Build analytics artifacts (charts + appendix) for CSV/XLS files
        charts_md  = ""
        appendix_md = ""
        analytics_stats: dict = {}
        if file_path and file_path.lower().rsplit(".", 1)[-1] in ("csv", "xlsx", "xls"):
            try:
                from src.agents.chart_builder import build_analytics_artifacts
                artifacts = build_analytics_artifacts(file_path)
                charts_md   = artifacts.get("charts_md", "")
                appendix_md = artifacts.get("appendix_md", "")
                analytics_stats = artifacts.get("stats", {})
                logger.info("analytics_artifacts_built",
                            charts=bool(charts_md), appendix=bool(appendix_md))
            except Exception as e:
                logger.warning("analytics_artifacts_failed", error=str(e))

        # Enrich CSV/XLS context
        enriched = self._enrich_csv_context(state)

        context_parts = [
            "## INSTRUÇÃO DE IDIOMA",
            "Todo o relatório DEVE ser escrito em Português do Brasil (pt-BR). Não use inglês.",
            "## INSTRUÇÃO DE COMPLETUDE",
            "Gere o relatório COMPLETO e DETALHADO agora. NÃO faça perguntas ao usuário.",
            "NÃO peça confirmação. NÃO liste inventário. Gere o relatório diretamente.",
            "",
        ]

        if enriched:
            context_parts += ["## Dados Estruturados do Documento", enriched]
        else:
            context_parts += ["## Conteúdo do Documento Fonte", content[:12000]]

        if analytics_stats:
            context_parts += [
                "", "## Métricas Calculadas (use estes números no relatório)",
                f"- Total de registros: {analytics_stats.get('total', 0)}",
                f"- Aprovados: {analytics_stats.get('passou', 0)} ({analytics_stats.get('taxa_geral', 0):.1f}%)",
                f"- Reprovados: {analytics_stats.get('falhou', 0)}",
                f"- Melhor categoria: {analytics_stats.get('melhor_categoria', 'N/A')} ({analytics_stats.get('melhor_taxa', 0):.1f}%)",
                f"- Pior categoria: {analytics_stats.get('pior_categoria', 'N/A')} ({analytics_stats.get('pior_taxa', 0):.1f}%)",
            ]

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
                "## INSTRUÇÃO SOBRE GRÁFICOS",
                "Os gráficos já foram gerados e serão inseridos automaticamente no relatório.",
                "No corpo do relatório, use o marcador exato `{{CHARTS}}` onde os gráficos devem aparecer.",
                "Use o marcador `{{APPENDIX}}` no final para a tabela de testes.",
            ]

        context_parts += [
            "",
            "**IMPORTANTE: Gere o relatório completo AGORA, sem perguntas, sem inventário, sem confirmações.**",
            f"Mínimo de 1.500 palavras. Formato Markdown. 100% em Português do Brasil.",
        ]

        context = "\n".join(context_parts)

        try:
            response = self.llm.invoke([
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=context),
            ])
            report_markdown = response.content

            # Inject charts and appendix into the report
            if charts_md:
                if "{{CHARTS}}" in report_markdown:
                    report_markdown = report_markdown.replace("{{CHARTS}}", f"\n\n{charts_md}\n\n")
                else:
                    # Auto-inject after first H2 section if marker not used
                    lines = report_markdown.split("\n")
                    inject_at = next(
                        (i for i, l in enumerate(lines) if l.startswith("## ") and i > 2),
                        len(lines) // 4
                    )
                    lines.insert(inject_at, f"\n{charts_md}\n")
                    report_markdown = "\n".join(lines)

            if appendix_md:
                if "{{APPENDIX}}" in report_markdown:
                    report_markdown = report_markdown.replace("{{APPENDIX}}", appendix_md)
                else:
                    report_markdown = report_markdown + "\n\n" + appendix_md

            state["generated_report_markdown"] = report_markdown
            state["current_node"] = "generate_report"
            logger.info(f"{self.report_type}_generated",
                        document_id=state.get("document_id"),
                        length=len(report_markdown))
        except Exception as e:
            logger.error(f"{self.report_type}_failed", error=str(e))
            state["errors"] = state.get("errors", []) + [f"Falha na geração: {str(e)}"]

        return state

    def _enrich_csv_context(self, state: AppState) -> str:
        """Extract structured stats from CSV/XLS files."""
        file_path = state.get("original_file_path", "")
        if not file_path:
            return ""
        ext = file_path.lower().rsplit(".", 1)[-1]
        if ext not in ("csv", "xlsx", "xls"):
            return ""
        try:
            import pandas as pd
            df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip") \
                if ext == "csv" else pd.read_excel(file_path)

            total = len(df)
            # Detect result column
            res_col = next((c for c in df.columns
                            if any(k in c.lower() for k in ["resultado", "result", "pass", "status"])), None)
            passou = falhou = None
            if res_col:
                vals = df[res_col].astype(str).str.upper()
                passou = int(vals.isin(["PASSOU", "PASSED", "APROVADO", "TRUE", "1"]).sum())
                falhou = total - passou

            lines = [
                f"### Dados do Arquivo ({ext.upper()})",
                f"- Total de registros: {total}",
                f"- Colunas: {', '.join(df.columns.tolist()[:15])}",
            ]
            if passou is not None:
                lines += [
                    f"- Passou: {passou} ({passou/total*100:.1f}%)",
                    f"- Falhou: {falhou} ({falhou/total*100:.1f}%)",
                ]

            # Category breakdown
            cat_col = next((c for c in df.columns
                            if any(k in c.lower() for k in ["categoria", "category", "tema", "theme"])), None)
            if cat_col and res_col:
                grp = df.groupby(cat_col)[res_col].apply(
                    lambda x: (x.astype(str).str.upper().isin(
                        ["PASSOU","PASSED","APROVADO","TRUE","1"])).mean() * 100
                ).round(1).sort_values()
                lines.append("\n### Taxa de Aprovação por Categoria")
                for cat, taxa in grp.items():
                    lines.append(f"- {cat}: {taxa:.1f}%")

            # Sample rows
            lines.append("\n### Amostra dos Dados (primeiros 10 registros)")
            for _, row in df.head(10).iterrows():
                lines.append("- " + " | ".join(f"{k}: {str(v)[:60]}" for k, v in row.items()
                                                if str(v) not in ("nan", "None", "")))

            return "\n".join(lines)
        except Exception as e:
            logger.warning("csv_enrich_failed", error=str(e))
            return ""
