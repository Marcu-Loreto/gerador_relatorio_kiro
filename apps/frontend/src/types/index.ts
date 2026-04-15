export type ReportType =
  | "analytical_summary"
  | "technical_report"
  | "finep_report"
  | "technical_opinion"
  | "scientific_report"
  | "academic_longform"
  | "requirements_test_doc"
  | "test_auditor";

export const REPORT_TYPE_LABELS: Record<ReportType, string> = {
  analytical_summary: "Resumo Analítico",
  technical_report: "Relatório Técnico",
  finep_report: "Relatório FINEP",
  technical_opinion: "Parecer Técnico",
  scientific_report: "Relato Científico",
  academic_longform: "Documento Acadêmico (Dissertação/Tese)",
  requirements_test_doc: "Criar Plano de Testes",
  test_auditor: "Auditor de Testes IA",
};

export const REPORT_TYPE_CATEGORIES: { label: string; types: ReportType[] }[] =
  [
    {
      label: "📄 Relatórios",
      types: [
        "analytical_summary",
        "technical_report",
        "finep_report",
        "technical_opinion",
        "scientific_report",
        "academic_longform",
      ],
    },
    {
      label: "🧪 Qualidade & Testes",
      types: ["requirements_test_doc", "test_auditor"],
    },
  ];

export interface Document {
  document_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: "uploaded" | "analyzed" | "error";
  analysis_summary?: number;
}

export interface Report {
  report_id: string;
  document_id: string;
  document_name: string;
  report_type: string;
  status: string;
  quality_score?: number;
  md_path?: string;
  csv_path?: string;
  xlsx_path?: string;
  created_at?: string;
  updated_at?: string;
  markdown?: string;
}

export interface ReportListResponse {
  total: number;
  page: number;
  page_size: number;
  results: Report[];
}

export type StepStatus = "pending" | "running" | "done" | "error";

export interface TimelineStep {
  id: string;
  label: string;
  status: StepStatus;
  message?: string;
  timestamp?: string;
}
