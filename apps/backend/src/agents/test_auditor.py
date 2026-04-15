"""Test Auditor Agent.

Reads a test results spreadsheet (.xlsx/.csv), evaluates each row via LLM,
fills RESULTADO_DO_TESTE (OK/NOK) and OBSERVACOES, saves a new .xlsx file,
and generates a Markdown audit report.
"""
import asyncio
import concurrent.futures
import json
import os

import pandas as pd
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.agents.prompt_loader import load_prompt
from src.core.config import get_settings
from src.core.logging import get_logger
from src.graphs.state import AppState

logger = get_logger(__name__)
settings = get_settings()

# Columns expected in the test spreadsheet
_RESULT_COL = "RESULTADO_DO_TESTE"
_OBS_COL = "OBSERVACOES"
_BATCH_SIZE = 20  # rows per LLM call


def _make_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.complex_model,
        temperature=0.1,
        max_tokens=8000,
        api_key=settings.openai_api_key,
    )


def _row_to_text(row: pd.Series) -> str:
    """Serialize a DataFrame row to readable text for the LLM."""
    parts = []
    for col, val in row.items():
        if pd.notna(val) and str(val).strip():
            parts.append(f"  {col}: {str(val).strip()}")
    return "\n".join(parts)


async def _evaluate_batch(
    llm: ChatOpenAI,
    system_prompt: str,
    rows: list[tuple[int, pd.Series]],
) -> list[dict]:
    """Ask LLM to evaluate a batch of test rows. Returns list of {index, resultado, observacao}."""
    rows_text = "\n\n".join(
        f"--- CASO {idx + 1} (linha {orig_idx}) ---\n{_row_to_text(row)}"
        for idx, (orig_idx, row) in enumerate(rows)
    )

    prompt = (
        "Avalie cada caso de teste abaixo e retorne um JSON array.\n"
        "Para cada caso, retorne um objeto com:\n"
        '  "linha": número da linha original\n'
        '  "resultado": "OK" ou "NOK"\n'
        '  "observacao": justificativa curta (obrigatória para NOK, opcional para OK)\n\n'
        "Retorne APENAS o JSON array, sem texto adicional, sem markdown.\n\n"
        f"CASOS DE TESTE:\n{rows_text}"
    )

    try:
        resp = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt),
        ])
        raw = resp.content.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1] if "\n" in raw else raw[3:]
            raw = raw.rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except Exception as e:
        logger.error("batch_evaluation_failed", error=str(e))
        # Fallback: mark all as NOK with error note
        return [
            {"linha": orig_idx, "resultado": "NOK", "observacao": f"Erro na avaliação: {str(e)[:80]}"}
            for orig_idx, _ in rows
        ]


async def _async_audit(state: AppState) -> AppState:
    file_path = state.get("original_file_path", "")
    if not file_path or not os.path.exists(file_path):
        state["errors"] = state.get("errors", []) + ["Arquivo de testes não encontrado"]
        return state

    ext = file_path.lower().rsplit(".", 1)[-1]

    # ── Load spreadsheet ──────────────────────────────────────────────────
    try:
        if ext == "csv":
            df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
        else:
            df = pd.read_excel(file_path)
        logger.info("test_sheet_loaded", rows=len(df), cols=list(df.columns))
    except Exception as e:
        state["errors"] = state.get("errors", []) + [f"Erro ao ler planilha: {str(e)}"]
        return state

    # Ensure result columns exist
    if _RESULT_COL not in df.columns:
        df[_RESULT_COL] = ""
    if _OBS_COL not in df.columns:
        df[_OBS_COL] = ""

    system_prompt = load_prompt("test_auditor")
    llm = _make_llm()

    # ── Evaluate in parallel batches ──────────────────────────────────────
    # Only evaluate rows that have RESPOSTA_RECEBIDA filled
    resp_col = next(
        (c for c in df.columns if "resposta_recebida" in c.lower() or "resposta recebida" in c.lower()),
        None,
    )

    if resp_col:
        rows_to_eval = [(i, row) for i, row in df.iterrows()
                        if pd.notna(row.get(resp_col)) and str(row.get(resp_col, "")).strip()]
    else:
        rows_to_eval = list(df.iterrows())

    logger.info("rows_to_evaluate", count=len(rows_to_eval))

    # Split into batches
    batches = [rows_to_eval[i:i + _BATCH_SIZE] for i in range(0, len(rows_to_eval), _BATCH_SIZE)]

    tasks = [_evaluate_batch(llm, system_prompt, batch) for batch in batches]
    results = await asyncio.gather(*tasks)

    # ── Apply results to DataFrame ────────────────────────────────────────
    ok_count = 0
    nok_count = 0
    for batch_results in results:
        for item in batch_results:
            idx = item.get("linha")
            resultado = str(item.get("resultado", "NOK")).upper().strip()
            observacao = str(item.get("observacao", "")).strip()
            if idx is not None and idx in df.index:
                df.at[idx, _RESULT_COL] = resultado
                df.at[idx, _OBS_COL] = observacao
                if resultado == "OK":
                    ok_count += 1
                else:
                    nok_count += 1

    total = ok_count + nok_count
    taxa = (ok_count / total * 100) if total > 0 else 0

    # ── Save XLSX ─────────────────────────────────────────────────────────
    orig_name = os.path.splitext(os.path.basename(file_path))[0]
    month_dir = os.path.dirname(file_path)
    xlsx_path = os.path.join(month_dir, f"resultados_{orig_name}.xlsx")
    df.to_excel(xlsx_path, index=False)
    logger.info("results_xlsx_saved", path=xlsx_path)

    # Store xlsx path in state for the route to save
    state["xlsx_results_path"] = xlsx_path

    # ── Generate audit report ─────────────────────────────────────────────
    # Category breakdown
    cat_col = next((c for c in df.columns if "categoria" in c.lower()), None)
    cat_stats = ""
    if cat_col:
        cat_group = df.groupby(cat_col)[_RESULT_COL].value_counts().unstack(fill_value=0)
        cat_stats = cat_group.to_string()

    report_prompt = (
        "## INSTRUÇÃO\n"
        "Gere o RELATÓRIO DE AUDITORIA DOS TESTES completo em Português do Brasil.\n"
        "Siga exatamente a estrutura obrigatória do prompt.\n\n"
        f"## RESULTADOS DA AVALIAÇÃO\n"
        f"- Total avaliado: {total}\n"
        f"- OK: {ok_count} ({taxa:.1f}%)\n"
        f"- NOK: {nok_count} ({100 - taxa:.1f}%)\n"
        f"- Status geral: {'APROVADO' if taxa >= 90 else 'NÃO APROVADO'}\n\n"
        f"## DISTRIBUIÇÃO POR CATEGORIA\n{cat_stats}\n\n"
        f"## AMOSTRA DOS NOK (primeiros 30)\n"
        + df[df[_RESULT_COL] == "NOK"][[c for c in [cat_col, "PERGUNTA_DE_TESTE", _OBS_COL] if c and c in df.columns]].head(30).to_string()
    )

    try:
        resp = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=report_prompt),
        ])
        state["generated_report_markdown"] = resp.content
        logger.info("audit_report_generated", chars=len(resp.content))
    except Exception as e:
        logger.error("audit_report_failed", error=str(e))
        # Minimal fallback report
        state["generated_report_markdown"] = (
            f"# Relatório de Auditoria\n\n"
            f"**Total:** {total} | **OK:** {ok_count} ({taxa:.1f}%) | **NOK:** {nok_count}\n\n"
            f"**Status:** {'APROVADO' if taxa >= 90 else 'NÃO APROVADO'}\n"
        )

    return state


class TestAuditorAgent:
    """Evaluates test results spreadsheet and generates audit report + results XLSX."""

    report_type: str = "test_auditor"

    def __init__(self) -> None:
        self.SYSTEM_PROMPT = load_prompt(self.report_type)

    def generate(self, state: AppState) -> AppState:
        def _run() -> AppState:
            return asyncio.run(_async_audit(state))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(_run).result(timeout=600)
