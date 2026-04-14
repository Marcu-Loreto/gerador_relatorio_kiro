"""
Requirements Analysis Agent.

Two separate LLM calls:
  1. Report call  — generates the Markdown analysis report (~4k tokens)
  2. CSV call     — generates 100-300 test cases in CSV format (~12k tokens)

This avoids token competition between the narrative report and the test case list.
"""
from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.agents.base_report_agent import BaseReportAgent
from src.agents.prompt_loader import load_prompt
from src.core.config import get_settings
from src.core.logging import get_logger
from src.graphs.state import AppState

logger = get_logger(__name__)
settings = get_settings()

_CSV_HEADER = (
    "ID_CASO_TESTE,CATEGORIA,SUBCATEGORIA,PRIORIDADE,OBJETIVO_DO_TESTE,"
    "PERFIL_DO_USUARIO,CONTEXTO,PERGUNTA_DE_TESTE,TIPO_DE_TESTE,"
    "RESPOSTA_ESPERADA,CRITERIO_DE_ACEITACAO,FONTE_OU_JUSTIFICATIVA"
)

_CSV_SYSTEM_PROMPT = """Você é um especialista em QA e homologação de chatbots de IA.
Sua tarefa é gerar casos de teste em formato CSV puro, sem nenhum texto adicional.
Responda APENAS com o CSV — sem explicações, sem markdown, sem blocos de código.
A primeira linha deve ser exatamente o cabeçalho fornecido."""

_CSV_USER_TEMPLATE = """Com base no documento de requisitos abaixo, gere casos de teste em CSV.

CABEÇALHO OBRIGATÓRIO (primeira linha):
{header}

REGRAS DE VOLUME:
- Documento simples: mínimo 100 casos
- Documento médio: mínimo 150 casos  
- Documento rico: até 300 casos
- NUNCA gere menos de 100 casos

REGRAS DE QUALIDADE:
- Distribua entre TODAS as categorias do documento
- Para cada categoria, inclua: Funcional, Qualidade da resposta, Segurança, Borda, Regressão
- Varie os perfis de usuário identificados no documento
- Inclua casos de borda (perguntas ambíguas, fora do escopo)
- Inclua casos de segurança (jailbreak, perguntas sensíveis)
- Use aspas duplas em campos com vírgulas
- TIPO_DE_TESTE: Funcional | Qualidade da resposta | Segurança | Borda | Regressão
- PRIORIDADE: Alta | Média | Baixa
- FONTE_OU_JUSTIFICATIVA: "Baseado explicitamente no documento" ou "Inferência técnica recomendada"

DOCUMENTO DE REQUISITOS:
{content}

Gere o CSV agora. Apenas o CSV, sem texto adicional."""


class RequirementsAnalysisAgent(BaseReportAgent):
    """
    Generates:
    - Markdown report via base class (call 1)
    - CSV test cases via dedicated LLM call (call 2)
    """

    SYSTEM_PROMPT: str = ""
    report_type: str = "requirements_analysis"

    def __init__(self) -> None:
        super().__init__()
        # Dedicated high-token LLM for CSV generation
        self._csv_llm = ChatOpenAI(
            model=settings.complex_model,
            temperature=0.3,
            max_tokens=14000,
            api_key=settings.openai_api_key,
        )

    def generate(self, state: AppState) -> AppState:
        # ── Call 1: generate the Markdown report ──────────────────────────
        state = super().generate(state)

        report_md = state.get("generated_report_markdown", "")
        if not report_md:
            return state

        # Add download notice to report
        notice = (
            "\n\n> 📥 **Casos de teste disponíveis para download** "
            "— clique em \"Baixar CSV\" no histórico de relatórios.\n"
        )
        state["generated_report_markdown"] = report_md.rstrip() + notice

        # ── Call 2: generate CSV test cases ───────────────────────────────
        content = state.get("normalized_content", "")
        file_path = state.get("original_file_path", "")

        # Use enriched CSV context if available
        enriched = self._enrich_csv_context(state)
        source_text = enriched if enriched else content[:10000]

        try:
            csv_content = self._generate_csv(source_text)
            if csv_content:
                state["requirements_csv"] = csv_content
                row_count = csv_content.count("\n")
                logger.info("requirements_csv_generated",
                            rows=row_count,
                            document_id=state.get("document_id"))
            else:
                logger.warning("requirements_csv_empty")
        except Exception as e:
            logger.error("requirements_csv_failed", error=str(e))

        return state

    def _generate_csv(self, content: str) -> str:
        """Dedicated LLM call to generate test cases CSV."""
        user_msg = _CSV_USER_TEMPLATE.format(
            header=_CSV_HEADER,
            content=content,
        )

        response = self._csv_llm.invoke([
            SystemMessage(content=_CSV_SYSTEM_PROMPT),
            HumanMessage(content=user_msg),
        ])

        raw = response.content.strip()

        # Strip markdown code fences if model wrapped the CSV
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(
                l for l in lines
                if not l.startswith("```")
            ).strip()

        # Ensure header is present
        if not raw.startswith("ID_CASO_TESTE"):
            raw = _CSV_HEADER + "\n" + raw

        return raw
