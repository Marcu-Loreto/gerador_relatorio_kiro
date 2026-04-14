"""
Script de teste: gera relatório analítico do arquivo XLSX e salva como PDF.
Uso: python test_generate_report.py
"""
import sys, os
sys.path.insert(0, "apps/backend")

# Load env
from dotenv import load_dotenv
load_dotenv(".env")

FILE_PATH = "V2_resultado_500_perguntas_sisu_salesforce.xlsx"
OUTPUT_PDF = "resultado_relatorio.pdf"

print("1. Gerando artefatos analíticos (gráficos + tabela)...")
from src.agents.chart_builder import build_analytics_artifacts
artifacts = build_analytics_artifacts(FILE_PATH)
charts_md   = artifacts["charts_md"]
appendix_md = artifacts["appendix_md"]
stats       = artifacts["stats"]

print(f"   Gráficos gerados: {bool(charts_md)}")
print(f"   Apêndice gerado: {bool(appendix_md)}")
print(f"   Stats: {stats}")

print("\n2. Gerando relatório via LLM (AnalyticalSummaryAgent)...")
from src.agents.analytical_summary import AnalyticalSummaryAgent
from src.graphs.state import AppState, AnalysisStatus

state: AppState = {
    "request_id": "test-001",
    "user_id": "test",
    "document_id": "test-001",
    "document_name": os.path.basename(FILE_PATH),
    "document_type": "xlsx",
    "original_file_path": FILE_PATH,
    "normalized_content": "",
    "extracted_sections": [],
    "extracted_tables": [],
    "analysis_status": AnalysisStatus.COMPLETED,
    "analysis_summary": f"Arquivo com {stats.get('total', 0)} registros de testes SISU/Salesforce",
    "selected_report_type": "analytical_summary",
    "generated_report_markdown": "",
    "review_feedback": "",
    "revision_count": 0,
    "errors": [],
    "current_node": "generate_report",
}

agent = AnalyticalSummaryAgent()
state = agent.generate(state)

if state.get("errors"):
    print(f"ERRO: {state['errors']}")
    sys.exit(1)

markdown = state["generated_report_markdown"]
print(f"   Relatório gerado: {len(markdown)} caracteres")

print("\n3. Salvando markdown temporário...")
md_path = "resultado_relatorio.md"
with open(md_path, "w", encoding="utf-8") as f:
    f.write(markdown)
print(f"   Salvo: {md_path}")

print("\n4. Convertendo para PDF...")
from src.exporters.pdf_exporter import md_to_pdf
pdf_path = md_to_pdf(md_path, OUTPUT_PDF)
print(f"   PDF salvo: {pdf_path}")
print(f"   Tamanho: {os.path.getsize(pdf_path) / 1024:.1f} KB")

print(f"\n✅ Concluído! Abra o arquivo: {OUTPUT_PDF}")
