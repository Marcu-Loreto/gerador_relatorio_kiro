"""Agent for generating test requirements documents (criteria + CSV test cases).

Strategy:
  1. First LLM call: generate the full report (no CSV section).
  2. Parallel LLM calls: generate CSV batches concurrently (asyncio.gather).
  3. CSV saved as separate file; markdown stays clean.
"""
import asyncio
import os
import re

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.agents.prompt_loader import load_prompt
from src.core.config import get_settings
from src.core.logging import get_logger
from src.graphs.state import AppState

logger = get_logger(__name__)
settings = get_settings()

CSV_HEADER = (
    "ID_CASO_TESTE,CATEGORIA,SUBCATEGORIA,PRIORIDADE,OBJETIVO_DO_TESTE,"
    "PERFIL_DO_USUARIO,CONTEXTO,PERGUNTA_DE_TESTE,TIPO_DE_TESTE,"
    "RESPOSTA_ESPERADA,CRITERIO_DE_ACEITACAO,FONTE_OU_JUSTIFICATIVA,"
    "RESPOSTA_RECEBIDA,RESULTADO_DO_TESTE"
)

_BATCH_SIZE = 50
_TOTAL_ROWS = 300
_NUM_BATCHES = _TOTAL_ROWS // _BATCH_SIZE  # 6 parallel calls


def _make_llm(temperature: float) -> ChatOpenAI:
    """Build LLM — MiniMax if model is minimax, else OpenAI."""
    model = settings.simple_model
    minimax_key = settings.minimax_api_key
    if minimax_key and model.lower().startswith("minimax"):
        return ChatOpenAI(
            model=model, temperature=temperature, max_tokens=8000,
            api_key=minimax_key, base_url="https://api.minimax.io/v1",
        )
    return ChatOpenAI(
        model=model, temperature=temperature, max_tokens=8000,
        api_key=settings.openai_api_key,
    )


def _strip_fences(text: str) -> str:
    text = re.sub(r"^```[^\n]*\n?", "", text.strip())
    return re.sub(r"\n?```$", "", text).strip()


def _extract_csv_rows(text: str) -> list[str]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("ID_CASO_TESTE"):
            continue
        rows.append(line)
    return rows


# CSV batch categories for diversity
_BATCH_CATEGORIES = [
    "Funcional, Negativo, Ambíguo",
    "Desinformação, Fora de escopo, Segurança",
    "UX conversacional, Encaminhamento, Qualidade da resposta",
    "Incompleto, Conformidade, Caixa-preta",
    "Funcional, Negativo, Qualidade da resposta",
    "Desinformação, UX conversacional, Fora de escopo",
]


async def _generate_csv_batch(
    llm: ChatOpenAI,
    batch_index: int,
    doc_context: str,
) -> list[str]:
    """Generate one batch of CSV rows asynchronously."""
    start_id = batch_index * _BATCH_SIZE + 1
    end_id = start_id + _BATCH_SIZE - 1
    categories = _BATCH_CATEGORIES[batch_index % len(_BATCH_CATEGORIES)]

    prompt = (
        f"## CONTEXTO DO DOCUMENTO\n{doc_context}\n\n"
        f"## INSTRUÇÃO\n"
        f"Gere EXATAMENTE {_BATCH_SIZE} casos de teste em formato CSV.\n"
        f"IDs de {start_id} a {end_id}.\n"
        f"Foque nos tipos: {categories}.\n"
        f"Use perguntas realistas baseadas no documento.\n\n"
        f"## FORMATO\n"
        f"Retorne APENAS o CSV, sem texto extra, sem markdown.\n"
        f"Primeira linha DEVE ser:\n{CSV_HEADER}\n\n"
        f"Regras:\n"
        f"- Campos com vírgula devem ser envolvidos em aspas duplas\n"
        f"- RESPOSTA_RECEBIDA e RESULTADO_DO_TESTE ficam em branco\n"
        f"- Gere exatamente {_BATCH_SIZE} linhas de dados\n"
    )

    try:
        resp = await llm.ainvoke([
            SystemMessage(content=(
                "Você é especialista em testes de chatbots e IA generativa. "
                "Gere casos de teste CSV estruturados e realistas. "
                "Responda APENAS com o CSV, sem texto adicional."
            )),
            HumanMessage(content=prompt),
        ])
        rows = _extract_csv_rows(_strip_fences(resp.content))
        logger.info("csv_batch_done", batch=batch_index + 1, rows=len(rows))
        return rows
    except Exception as e:
        logger.error("csv_batch_failed", batch=batch_index + 1, error=str(e))
        return []


class RequirementsTestDocAgent:
    """Generates success criteria, acceptance criteria and 300 CSV test cases."""

    report_type: str = "requirements_test_doc"

    def __init__(self) -> None:
        self.SYSTEM_PROMPT = load_prompt(self.report_type)
        self.llm = _make_llm(temperature=0.3)
        self.csv_llm = _make_llm(temperature=0.5)

    def generate(self, state: AppState) -> AppState:
        """Sync entry point — runs async logic safely inside FastAPI's event loop."""
        import concurrent.futures

        def _run_in_thread() -> AppState:
            return asyncio.run(self._async_generate(state))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_run_in_thread)
            return future.result(timeout=600)

    async def _async_generate(self, state: AppState) -> AppState:
        logger.info("generating_requirements_test_doc", document_id=state.get("document_id"))

        content = state.get("normalized_content", "")
        analysis = state.get("analysis_summary", "")
        metadata = state.get("extracted_metadata")

        # ── Step 1: Report (no CSV section) ──────────────────────────────────
        report_prompt = (
            "## INSTRUÇÃO DE IDIOMA\n"
            "Todo o relatório DEVE ser escrito em Português do Brasil (pt-BR).\n\n"
            "## INSTRUÇÃO\n"
            "Gere APENAS as seções 1 a 5 e 8 a 10 (título, resumo executivo, contexto, "
            "Tabela 1 - critérios de sucesso, Tabela 2 - critérios mínimos, "
            "checklist, lacunas e recomendações). NÃO gere CSV agora.\n"
            "Gere o relatório completo AGORA, sem perguntas.\n\n"
            f"## Conteúdo do Documento\n{content[:10000]}\n\n"
            f"## Resumo da Análise\n{analysis}\n"
        )
        if metadata:
            report_prompt += f"\nArquivo: {metadata.filename} | Tipo: {metadata.file_type}\n"

        try:
            resp = await self.llm.ainvoke([
                SystemMessage(content=self.SYSTEM_PROMPT),
                HumanMessage(content=report_prompt),
            ])
            state["generated_report_markdown"] = resp.content
            logger.info("requirements_report_generated", chars=len(resp.content))
        except Exception as e:
            logger.error("requirements_report_failed", error=str(e))
            state["errors"] = state.get("errors", []) + [f"Falha na geração do relatório: {str(e)}"]
            return state

        # ── Step 2: CSV batches in parallel ──────────────────────────────────
        doc_context = (
            f"Documento: {metadata.filename if metadata else 'documento'}\n"
            f"Resumo: {analysis[:2000]}\n"
            f"Conteúdo: {content[:3000]}"
        )

        logger.info("csv_batches_starting", batches=_NUM_BATCHES)
        tasks = [
            _generate_csv_batch(self.csv_llm, i, doc_context)
            for i in range(_NUM_BATCHES)
        ]
        results = await asyncio.gather(*tasks)

        # ── Step 3: Assemble & renumber ───────────────────────────────────────
        all_rows: list[str] = []
        for batch_rows in results:
            all_rows.extend(batch_rows)

        if all_rows:
            renumbered = []
            for i, row in enumerate(all_rows, start=1):
                parts = row.split(",", 1)
                renumbered.append(f"{i},{parts[1]}" if len(parts) == 2 else row)

            state["csv_test_cases_content"] = CSV_HEADER + "\n" + "\n".join(renumbered)
            logger.info("csv_complete", total_rows=len(all_rows))
        else:
            logger.warning("csv_not_generated")

        return state
