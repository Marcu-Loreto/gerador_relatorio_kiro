"""Technical report generation agent — QA Científico."""
import os
import re
from datetime import datetime
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.core.config import get_settings
from src.core.logging import get_logger
from src.core.model_selector import TaskType, get_model_selector
from src.graphs.state import AppState

logger = get_logger(__name__)
settings = get_settings()

_PROMPT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__),
                 "../../../../packages/prompts/technical_report_qa_prompt.md")
)


def _load_prompt() -> str:
    try:
        if os.path.exists(_PROMPT_PATH):
            with open(_PROMPT_PATH, "r", encoding="utf-8") as f:
                return f.read()
    except Exception:
        pass
    return (
        "Você é especialista em QA e IA Generativa. "
        "Gere um relatório técnico-científico completo em Português do Brasil. "
        "Siga: Sumário Executivo, Metodologia, Resultados, Métricas, Análise, "
        "Recomendações, Conclusão e Anexos. NÃO invente dados."
    )


class TechnicalReportAgent:
    """Gera relatórios técnico-científicos de testes."""

    def __init__(self) -> None:
        self.model_selector = get_model_selector()
        self.system_prompt = _load_prompt()

    # ── Geração principal ─────────────────────────────────────────────────

    def generate(self, state: AppState) -> AppState:
        logger.info("generating_technical_report", document_id=state.get("document_id"))

        content         = state.get("normalized_content", "")
        analysis        = state.get("analysis_summary", "")
        metadata        = state.get("extracted_metadata")
        review_feedback = state.get("review_feedback", "")

        llm = ChatOpenAI(
            model=settings.complex_model,
            temperature=0.2,
            max_tokens=8000,
            api_key=settings.openai_api_key,
        )
        logger.info("model_selected_for_report", model=settings.complex_model,
                    provider="openai", cost_tier="premium")

        enriched = self._enrich_csv_context(state)

        context_parts = [
            "## INSTRUÇÃO DE IDIOMA",
            "Todo o relatório DEVE ser escrito em Português do Brasil (pt-BR). Não use inglês.",
            "",
        ]

        if enriched:
            context_parts += ["## Dados Estruturados do Documento (pré-processados)", enriched]
        else:
            context_parts += ["## Conteúdo do Documento Fonte", content[:12000]]

        context_parts += ["", "## Resumo da Análise", analysis]

        if metadata:
            context_parts += [
                "", "## Metadados do Documento",
                f"Nome do arquivo: {metadata.filename}",
                f"Tipo: {metadata.file_type}",
                f"Contagem de palavras: {metadata.word_count}",
            ]

        if review_feedback:
            context_parts += [
                "", "## Feedback da Revisão Anterior",
                "Corrija estes problemas (em Português do Brasil):",
                review_feedback,
            ]

        extension = (
            "\n\n**INSTRUÇÃO DE EXTENSÃO:** Gere o relatório COMPLETO e DETALHADO. "
            "Preencha TODAS as seções com profundidade. "
            "A seção 5 deve ter tabela por categoria (não por teste individual). "
            "A seção 6 deve ter pelo menos 3 parágrafos. "
            "Não resuma nem omita seções. Mínimo de 2.500 palavras."
        )

        context = "\n".join(context_parts) + extension

        try:
            response = llm.invoke([
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=context),
            ])
            report_markdown = response.content
            report_markdown = self._inject_annexes(report_markdown, state)
            state["generated_report_markdown"] = report_markdown
            state["current_node"] = "generate_report"
            logger.info("technical_report_generated",
                        document_id=state.get("document_id"),
                        length=len(report_markdown))
        except Exception as e:
            logger.error("technical_report_generation_failed", error=str(e))
            state["errors"] = state.get("errors", []) + [f"Falha na geração: {str(e)}"]

        return state

    # ── Enriquecimento de contexto CSV ────────────────────────────────────

    def _enrich_csv_context(self, state: AppState) -> str:
        file_path = state.get("original_file_path", "")
        if not file_path or not file_path.lower().endswith(".csv"):
            return ""
        try:
            import pandas as pd

            df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
            has_pass  = "pass"  in df.columns
            has_score = "score" in df.columns
            if not (has_pass or has_score):
                return ""

            df["score"]   = pd.to_numeric(df["score"],   errors="coerce").fillna(0.0)
            df["latency"] = pd.to_numeric(df.get("latency", 0), errors="coerce").fillna(0)

            total   = len(df)
            n_pass  = int(df["pass"].sum()) if has_pass else 0
            n_fail  = total - n_pass
            s_med   = df["score"].mean()
            lat_med = df["latency"].mean() / 1000
            tok_med = df["tokensUsed_total"].mean() if "tokensUsed_total" in df.columns else 0

            plugin_col = next(
                (c for c in ["plugin", "Tema da pergunta"] if c in df.columns), None
            )

            # Tabela por categoria
            plugin_block = ""
            if plugin_col:
                ps = (df.groupby(plugin_col)
                      .agg(qtd=("pass", "count"),
                           aprovados=("pass", "sum"),
                           score_med=("score", "mean"),
                           falhas=("pass", lambda x: (~x).sum()))
                      .round(4).sort_values("score_med").reset_index())
                ps["taxa"] = (ps["aprovados"] / ps["qtd"] * 100).round(1)
                linhas = [
                    "| # | Categoria | Testes | Aprovados | Falhas | Taxa Pass | Score Médio |",
                    "|---|-----------|--------|-----------|--------|-----------|-------------|",
                ]
                for i, row in ps.iterrows():
                    linhas.append(
                        f"| {i+1} | {row[plugin_col]} | {int(row['qtd'])} | "
                        f"{int(row['aprovados'])} | {int(row['falhas'])} | "
                        f"{row['taxa']:.1f}% | {row['score_med']:.4f} |"
                    )
                plugin_block = "\n".join(linhas)

            # Casos de falha — 1 por categoria, traduzidos
            falhas_df = df[~df["pass"]].copy() if has_pass else df[df["score"] < 0.5].copy()
            sample = (falhas_df.groupby(plugin_col).first().reset_index().head(30)
                      if plugin_col else falhas_df.head(30))

            reason_col = "reason" if "reason" in df.columns else None
            translated: dict[int, str] = {}
            if reason_col and not sample.empty:
                try:
                    reasons_raw = [str(row[reason_col])[:300] for _, row in sample.iterrows()]
                    batch = "\n---ITEM---\n".join(reasons_raw)
                    prompt = (
                        "Traduza cada item para Português do Brasil de forma técnica. "
                        "Separe com ---ITEM---\n\n" + batch
                    )
                    _llm = ChatOpenAI(model=settings.complex_model, temperature=0.1,
                                      max_tokens=3000, api_key=settings.openai_api_key)
                    resp = _llm.invoke([HumanMessage(content=prompt)])
                    for j, part in enumerate(resp.content.split("---ITEM---")):
                        translated[j] = part.strip()
                    logger.info("reasons_translated", count=len(translated))
                except Exception as te:
                    logger.warning("reason_translation_failed", error=str(te))

            q_col = next((c for c in ["adversarial_prompt", "question", "Pergunta realizada"]
                          if c in df.columns), None)
            r_col = next((c for c in ["received_answer", "Resposta obtida do chatbot"]
                          if c in df.columns), None)
            e_col = next((c for c in ["expected_answer", "Resposta esperada"]
                          if c in df.columns), None)

            casos = []
            for i, (_, row) in enumerate(sample.iterrows()):
                q      = str(row[q_col])[:200] if q_col else "N/D"
                r      = str(row[r_col])[:200] if r_col else "N/D"
                e      = str(row[e_col])[:150] if e_col else "N/D"
                reason = translated.get(i) or (str(row[reason_col])[:200] if reason_col else "N/D")
                cat    = str(row[plugin_col]) if plugin_col else f"Caso {i+1}"
                score_v = f"{row['score']:.2f}"
                lat_v   = f"{row['latency']/1000:.1f}s"
                casos.append(
                    f"- **{cat}** | Score: {score_v} | Latência: {lat_v}\n"
                    f"  Prompt: {q}\n"
                    f"  Resposta obtida: {r}\n"
                    f"  Resposta esperada: {e}\n"
                    f"  Avaliação (pt-BR): {reason}"
                )

            # Distribuição por tipo
            tipo_map = {
                "xstest": "Segurança (Falso Positivo)",
                "competitors": "Funcional",
                "pii": "Segurança / Privacidade",
                "harmful:graphic": "Segurança / Conteúdo",
                "harmful:cybercrime": "Segurança",
                "harmful:misinformation": "Alucinação / Desinformação",
                "harmful:insults": "Segurança / Conteúdo",
                "harmful:copyright": "Funcional / Legal",
                "harmful:profanity": "Segurança / Conteúdo",
            }
            dist: dict = {}
            for _, row in falhas_df.iterrows():
                p = str(row.get(plugin_col, "")) if plugin_col else ""
                t = next((v for k, v in tipo_map.items() if k in p), "Segurança / Conteúdo")
                dist[t] = dist.get(t, 0) + 1
            dist_str = "\n".join(
                f"- {k}: {v} falhas ({v/n_fail*100:.1f}%)"
                for k, v in sorted(dist.items(), key=lambda x: -x[1])
            ) if n_fail > 0 else "Nenhuma falha"

            return (
                f"### Estatísticas Gerais\n"
                f"- Total de testes: {total}\n"
                f"- Aprovados: {n_pass} ({n_pass/total*100:.1f}%)\n"
                f"- Falhas: {n_fail} ({n_fail/total*100:.1f}%)\n"
                f"- Score médio: {s_med:.4f}\n"
                f"- Latência média: {lat_med:.1f}s\n"
                f"- Tokens médios: {tok_med:.0f}\n"
                f"- Categorias testadas: {df[plugin_col].nunique() if plugin_col else 'N/D'}\n\n"
                f"### Distribuição de Falhas por Tipo\n{dist_str}\n\n"
                f"### Resultados por Categoria\n{plugin_block}\n\n"
                f"### Casos de Falha Representativos (1 por categoria)\n"
                + "\n\n".join(casos) +
                "\n\n### Critério de Aceitação\n"
                "- pass=True / score≥0.5: aprovado\n"
                "- pass=False / score<0.5: falhou\n"
                "- Score 1.0 = aprovação total | Score 0.0 = falha total\n"
            )
        except Exception as e:
            logger.warning("csv_enrichment_failed", error=str(e))
            return ""

    # ── Injeção de Anexos reais ───────────────────────────────────────────

    def _inject_annexes(self, report: str, state: AppState) -> str:
        file_path = state.get("original_file_path", "")
        if not file_path or not file_path.lower().endswith(".csv"):
            return report
        try:
            import pandas as pd

            df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
            has_pass  = "pass"  in df.columns
            has_score = "score" in df.columns
            if not (has_pass or has_score):
                return report

            df["score"]   = pd.to_numeric(df["score"],   errors="coerce").fillna(0.0)
            df["latency"] = pd.to_numeric(df.get("latency", 0), errors="coerce").fillna(0)

            plugin_col = next((c for c in ["plugin", "Tema da pergunta"] if c in df.columns), None)
            q_col      = next((c for c in ["adversarial_prompt", "question", "Pergunta realizada"]
                               if c in df.columns), None)
            r_col      = next((c for c in ["received_answer", "Resposta obtida do chatbot"]
                               if c in df.columns), None)
            reason_col = "reason" if "reason" in df.columns else None

            falhas_df = df[~df["pass"]].copy() if has_pass else df[df["score"] < 0.5].copy()
            sample_a  = (falhas_df.groupby(plugin_col).first().reset_index()
                         if plugin_col else falhas_df.head(30))

            # Traduzir reasons do Anexo A (~26 itens)
            translated: dict[int, str] = {}
            if reason_col and not sample_a.empty:
                try:
                    reasons_raw = [str(row[reason_col])[:300] for _, row in sample_a.iterrows()]
                    batch = "\n---ITEM---\n".join(reasons_raw)
                    prompt = (
                        "Traduza cada item para Português do Brasil de forma técnica. "
                        "Separe com ---ITEM---\n\n" + batch
                    )
                    _llm = ChatOpenAI(model=settings.complex_model, temperature=0.1,
                                      max_tokens=3000, api_key=settings.openai_api_key)
                    resp = _llm.invoke([HumanMessage(content=prompt)])
                    for j, part in enumerate(resp.content.split("---ITEM---")):
                        translated[j] = part.strip()
                    logger.info("annex_reasons_translated", count=len(translated))
                except Exception as te:
                    logger.warning("annex_translation_failed", error=str(te))

            # ── Anexo A — Evidências por categoria (resumido) ─────────────
            linhas_a = [
                f"\n## Anexo A — Evidências por Categoria de Falha\n",
                f"> {len(sample_a)} categorias com falha | Um caso representativo por categoria\n",
            ]
            for idx, (_, row) in enumerate(sample_a.iterrows()):
                cat    = str(row[plugin_col]) if plugin_col else f"Caso {idx+1}"
                prompt = str(row[q_col]).strip()[:300] if q_col else "N/D"
                resp   = str(row[r_col]).strip()[:300] if r_col else "N/D"
                just   = translated.get(idx) or (str(row[reason_col])[:300] if reason_col else "N/D")
                score  = f"{row['score']:.2f}"
                lat    = f"{row['latency']/1000:.1f}s"
                n_f    = int(falhas_df[falhas_df[plugin_col] == row[plugin_col]].shape[0]) if plugin_col else 1
                linhas_a.append(
                    f"\n#### {idx+1}. `{cat}` — {n_f} falha(s) | Score: {score} | Latência: {lat}\n\n"
                    f"**Prompt:** {prompt}\n\n"
                    f"**Resposta recebida:** {resp}\n\n"
                    f"**Justificativa (pt-BR):** {just}\n\n---"
                )

            # ── Anexo B — Lista completa (sem tradução) ───────────────────
            linhas_b = [
                f"\n## Anexo B — Lista Completa dos {len(df)} Testes\n",
                "> ✅ = Aprovado | ❌ = Falhou\n",
                "| # | Categoria | Prompt (resumo) | Status | Score | Latência |",
                "|---|-----------|-----------------|--------|-------|----------|",
            ]
            for i, row in df.iterrows():
                cat    = str(row[plugin_col])[:40] if plugin_col else f"Caso {i+1}"
                prompt = str(row[q_col])[:80].replace("|", "\\|").replace("\n", " ") if q_col else "N/D"
                status = "✅" if row["pass"] else "❌"
                score  = f"{row['score']:.2f}"
                lat    = f"{row['latency']/1000:.1f}s"
                linhas_b.append(f"| {i+1} | {cat} | {prompt} | {status} | {score} | {lat} |")

            anexos = "\n".join(linhas_a) + "\n\n" + "\n".join(linhas_b)

            # Substituir bloco de Anexos do LLM
            for pattern in [r"### Anexo A.*$", r"## Anexo A.*$", r"## 12\. Anexos.*$"]:
                new_report = re.sub(pattern, anexos, report, flags=re.DOTALL)
                if new_report != report:
                    return new_report

            # Fallback: append
            return report + "\n\n" + anexos

        except Exception as e:
            logger.warning("annex_injection_failed", error=str(e))
            return report
