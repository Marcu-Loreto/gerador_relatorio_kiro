"""Base class for all report generation agents."""
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.core.config import get_settings
from src.core.logging import get_logger
from src.graphs.state import AppState

logger = get_logger(__name__)
settings = get_settings()


class BaseReportAgent:
    """Base class — subclasses define SYSTEM_PROMPT and report_type."""

    SYSTEM_PROMPT: str = ""
    report_type: str = "report"

    def __init__(self) -> None:
        self.llm = ChatOpenAI(
            model=settings.complex_model,
            temperature=0.2,
            max_tokens=8000,
            api_key=settings.openai_api_key,
        )

    def generate(self, state: AppState) -> AppState:
        logger.info(f"generating_{self.report_type}", document_id=state.get("document_id"))

        content        = state.get("normalized_content", "")
        analysis       = state.get("analysis_summary", "")
        metadata       = state.get("extracted_metadata")
        review_feedback = state.get("review_feedback", "")

        # Enrich CSV/XLS context if available
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
