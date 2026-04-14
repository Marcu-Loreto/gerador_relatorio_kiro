"""Generates Plotly charts as inline base64 PNG for embedding in Markdown reports."""
from __future__ import annotations

import base64
import io
from typing import Optional

import pandas as pd

try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from src.core.logging import get_logger

logger = get_logger(__name__)

_PASS_VALS = {"PASSOU", "PASSED", "APROVADO", "TRUE", "1", "PASS", "OK", "SIM", "YES"}
_FAIL_VALS = {"FALHOU", "FAILED", "REPROVADO", "FALSE", "0", "FAIL", "NÃO", "NO", "NAO"}

_LAYOUT = dict(
    template="plotly_white",
    font=dict(family="Arial, sans-serif", size=13),
    margin=dict(l=40, r=40, t=50, b=40),
    paper_bgcolor="white",
    plot_bgcolor="white",
)


def _to_base64_png(fig) -> str:
    """Convert a Plotly figure to a base64-encoded PNG string."""
    img_bytes = fig.to_image(format="png", width=900, height=480, scale=1.5)
    return base64.b64encode(img_bytes).decode("utf-8")


def _md_image(b64: str, title: str) -> str:
    return f"![{title}](data:image/png;base64,{b64})\n"


# ──────────────────────────────────────────────
# Column detection helpers
# ──────────────────────────────────────────────

def _detect_result_col(df: pd.DataFrame) -> Optional[str]:
    keywords = ["resultado", "result", "pass", "status", "aprovado", "situacao", "situação"]
    return next((c for c in df.columns if any(k in c.lower() for k in keywords)), None)


def _detect_category_col(df: pd.DataFrame) -> Optional[str]:
    keywords = ["categoria", "category", "tema", "theme", "grupo", "group", "tipo", "type", "area", "área"]
    return next((c for c in df.columns if any(k in c.lower() for k in keywords)), None)


def _detect_question_col(df: pd.DataFrame) -> Optional[str]:
    keywords = ["pergunta", "question", "query", "teste", "test", "caso", "case", "descricao", "descrição"]
    return next((c for c in df.columns if any(k in c.lower() for k in keywords)), None)


def _detect_expected_col(df: pd.DataFrame) -> Optional[str]:
    keywords = ["esperado", "expected", "gabarito", "resposta_esperada", "expected_answer"]
    return next((c for c in df.columns if any(k in c.lower() for k in keywords)), None)


def _detect_received_col(df: pd.DataFrame) -> Optional[str]:
    keywords = ["recebido", "received", "resposta", "response", "answer", "obtido", "actual"]
    return next((c for c in df.columns if any(k in c.lower() for k in keywords)), None)


def _detect_criteria_col(df: pd.DataFrame) -> Optional[str]:
    keywords = ["criterio", "critério", "criteria", "criterion", "metrica", "métrica"]
    return next((c for c in df.columns if any(k in c.lower() for k in keywords)), None)


def _normalize_result(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.upper()


def _is_pass(val: str) -> bool:
    return val in _PASS_VALS


# ──────────────────────────────────────────────
# Chart generators
# ──────────────────────────────────────────────

def chart_overall_donut(passou: int, falhou: int) -> str:
    """Donut chart: overall pass/fail."""
    fig = go.Figure(go.Pie(
        labels=["Passou ✅", "Falhou ❌"],
        values=[passou, falhou],
        hole=0.55,
        marker_colors=["#22c55e", "#ef4444"],
        textinfo="label+percent+value",
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        title_text="Resultado Geral dos Testes",
        **_LAYOUT,
    )
    return _md_image(_to_base64_png(fig), "Resultado Geral dos Testes")


def chart_category_bar(cat_stats: pd.DataFrame) -> str:
    """Horizontal bar chart: pass rate per category."""
    cat_stats = cat_stats.sort_values("taxa_aprovacao")
    colors = ["#22c55e" if t >= 80 else "#f59e0b" if t >= 60 else "#ef4444"
              for t in cat_stats["taxa_aprovacao"]]
    fig = go.Figure(go.Bar(
        x=cat_stats["taxa_aprovacao"],
        y=cat_stats["categoria"],
        orientation="h",
        marker_color=colors,
        text=[f"{v:.1f}%" for v in cat_stats["taxa_aprovacao"]],
        textposition="outside",
        hovertemplate="%{y}: %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title_text="Taxa de Aprovação por Categoria (%)",
        xaxis=dict(range=[0, 110], title="Taxa de Aprovação (%)"),
        yaxis=dict(title=""),
        **_LAYOUT,
    )
    fig.add_vline(x=80, line_dash="dash", line_color="#6366f1",
                  annotation_text="Meta 80%", annotation_position="top right")
    return _md_image(_to_base64_png(fig), "Taxa de Aprovação por Categoria")


def chart_category_stacked(cat_stats: pd.DataFrame) -> str:
    """Stacked bar: absolute pass/fail per category."""
    cat_stats = cat_stats.sort_values("passou", ascending=False)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Passou ✅", x=cat_stats["categoria"], y=cat_stats["passou"],
        marker_color="#22c55e",
        hovertemplate="%{x}: %{y} passou<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Falhou ❌", x=cat_stats["categoria"], y=cat_stats["falhou"],
        marker_color="#ef4444",
        hovertemplate="%{x}: %{y} falhou<extra></extra>",
    ))
    fig.update_layout(
        barmode="stack",
        title_text="Volume de Testes por Categoria",
        xaxis_title="Categoria",
        yaxis_title="Quantidade de Testes",
        **_LAYOUT,
    )
    return _md_image(_to_base64_png(fig), "Volume de Testes por Categoria")


def chart_quality_gauge(taxa: float) -> str:
    """Gauge chart: overall quality score."""
    color = "#22c55e" if taxa >= 80 else "#f59e0b" if taxa >= 60 else "#ef4444"
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=taxa,
        number={"suffix": "%", "font": {"size": 36}},
        delta={"reference": 80, "suffix": "%"},
        gauge={
            "axis": {"range": [0, 100], "ticksuffix": "%"},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 60], "color": "#fee2e2"},
                {"range": [60, 80], "color": "#fef9c3"},
                {"range": [80, 100], "color": "#dcfce7"},
            ],
            "threshold": {
                "line": {"color": "#6366f1", "width": 3},
                "thickness": 0.75,
                "value": 80,
            },
        },
        title={"text": "Índice de Qualidade Geral"},
    ))
    fig.update_layout(height=350, **_LAYOUT)
    return _md_image(_to_base64_png(fig), "Índice de Qualidade Geral")


# ──────────────────────────────────────────────
# Appendix table builder
# ──────────────────────────────────────────────

def build_test_appendix(df: pd.DataFrame) -> str:
    """Build a Markdown appendix with test results grouped by category."""
    res_col = _detect_result_col(df)
    cat_col = _detect_category_col(df)
    q_col = _detect_question_col(df)
    exp_col = _detect_expected_col(df)
    rec_col = _detect_received_col(df)
    crit_col = _detect_criteria_col(df)

    if not res_col:
        return ""

    norm = _normalize_result(df[res_col])
    df = df.copy()
    df["_status"] = norm.apply(lambda v: "✅ Passou" if _is_pass(v) else "❌ Falhou")

    lines = [
        "",
        "---",
        "",
        "## Anexo — Lista de Testes Realizados",
        "",
        "> Tabela resumida dos testes executados, agrupados por categoria.",
        "",
    ]

    def _trunc(val, n=80) -> str:
        s = str(val) if str(val) not in ("nan", "None", "") else "—"
        return s[:n] + "…" if len(s) > n else s

    # Build header based on available columns
    headers = ["#"]
    cols_map: list[tuple[str, str]] = []  # (header_label, df_col)
    if q_col:
        headers.append("Pergunta / Teste")
        cols_map.append(("Pergunta / Teste", q_col))
    if exp_col:
        headers.append("Resposta Esperada")
        cols_map.append(("Resposta Esperada", exp_col))
    if crit_col:
        headers.append("Critério")
        cols_map.append(("Critério", crit_col))
    if rec_col:
        headers.append("Resposta Recebida")
        cols_map.append(("Resposta Recebida", rec_col))
    headers.append("Status")

    sep = "|".join(["---"] * len(headers))
    header_row = "| " + " | ".join(headers) + " |"
    sep_row = "| " + sep + " |"

    groups = df.groupby(cat_col) if cat_col else [("Todos os Testes", df)]

    for cat, group in groups:
        passou_n = (group["_status"] == "✅ Passou").sum()
        total_n = len(group)
        taxa = passou_n / total_n * 100 if total_n else 0
        badge = "🟢" if taxa >= 80 else "🟡" if taxa >= 60 else "🔴"

        lines += [
            f"### {badge} {cat}",
            f"*{passou_n}/{total_n} aprovados — {taxa:.1f}%*",
            "",
            header_row,
            sep_row,
        ]

        for i, (_, row) in enumerate(group.iterrows(), 1):
            cells = [str(i)]
            for _, dcol in cols_map:
                cells.append(_trunc(row.get(dcol, "—")))
            cells.append(row["_status"])
            lines.append("| " + " | ".join(cells) + " |")

        lines.append("")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────

def build_analytics_artifacts(file_path: str) -> dict:
    """
    Load a CSV/XLS file and return:
      - charts_md: inline Markdown with embedded PNG charts
      - appendix_md: Markdown appendix with test table
      - stats: dict with key metrics for prompt injection
    """
    if not PLOTLY_AVAILABLE:
        logger.warning("plotly_not_available", msg="Install plotly and kaleido for charts")
        return {"charts_md": "", "appendix_md": "", "stats": {}}

    ext = file_path.lower().rsplit(".", 1)[-1]
    if ext not in ("csv", "xlsx", "xls"):
        return {"charts_md": "", "appendix_md": "", "stats": {}}

    try:
        df = (pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
              if ext == "csv" else pd.read_excel(file_path))
    except Exception as e:
        logger.warning("analytics_load_failed", error=str(e))
        return {"charts_md": "", "appendix_md": "", "stats": {}}

    res_col = _detect_result_col(df)
    cat_col = _detect_category_col(df)

    total = len(df)
    passou = falhou = 0
    cat_stats = pd.DataFrame()

    if res_col:
        norm = _normalize_result(df[res_col])
        passou = int(norm.apply(_is_pass).sum())
        falhou = total - passou

        if cat_col:
            grp = df.groupby(cat_col).apply(
                lambda g: pd.Series({
                    "passou": int(_normalize_result(g[res_col]).apply(_is_pass).sum()),
                    "total": len(g),
                })
            ).reset_index()
            grp.columns = ["categoria", "passou", "total"]
            grp["falhou"] = grp["total"] - grp["passou"]
            grp["taxa_aprovacao"] = (grp["passou"] / grp["total"] * 100).round(1)
            cat_stats = grp

    taxa_geral = round(passou / total * 100, 1) if total else 0.0

    # Build charts
    charts: list[str] = []
    try:
        charts.append(chart_quality_gauge(taxa_geral))
        if passou or falhou:
            charts.append(chart_overall_donut(passou, falhou))
        if not cat_stats.empty:
            charts.append(chart_category_bar(cat_stats))
            charts.append(chart_category_stacked(cat_stats))
    except Exception as e:
        logger.warning("chart_generation_failed", error=str(e))

    charts_md = "\n\n".join(charts)
    appendix_md = build_test_appendix(df)

    stats = {
        "total": total,
        "passou": passou,
        "falhou": falhou,
        "taxa_geral": taxa_geral,
        "num_categorias": len(cat_stats) if not cat_stats.empty else 0,
        "pior_categoria": (cat_stats.loc[cat_stats["taxa_aprovacao"].idxmin(), "categoria"]
                           if not cat_stats.empty else "N/A"),
        "melhor_categoria": (cat_stats.loc[cat_stats["taxa_aprovacao"].idxmax(), "categoria"]
                             if not cat_stats.empty else "N/A"),
        "pior_taxa": (cat_stats["taxa_aprovacao"].min() if not cat_stats.empty else 0),
        "melhor_taxa": (cat_stats["taxa_aprovacao"].max() if not cat_stats.empty else 0),
    }

    return {"charts_md": charts_md, "appendix_md": appendix_md, "stats": stats}
