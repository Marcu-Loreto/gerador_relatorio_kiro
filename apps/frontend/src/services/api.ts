import axios from "axios";
import type {
  Document,
  Report,
  ReportListResponse,
  ReportType,
} from "../types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300_000,
});

// ── Documents ──────────────────────────────────────────────────────────────

export async function uploadDocument(
  file: File,
  onProgress?: (percent: number) => void,
): Promise<Document> {
  const form = new FormData();
  form.append("file", file);

  const { data } = await api.post<Document>("/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (e) => {
      if (onProgress && e.total) {
        onProgress(Math.round((e.loaded * 100) / e.total));
      }
    },
  });

  return data;
}

export async function analyzeDocument(documentId: string): Promise<{
  document_id: string;
  status: string;
  summary: string;
  word_count: number;
  sections_count: number;
}> {
  const { data } = await api.post(`/documents/${documentId}/analyze`);
  return data;
}

export async function getDocument(documentId: string): Promise<Document> {
  const { data } = await api.get<Document>(`/documents/${documentId}`);
  return data;
}

// ── Reports ────────────────────────────────────────────────────────────────

export async function generateReport(
  documentIds: string[],
  reportType: ReportType,
): Promise<Report> {
  const { data } = await api.post<Report>("/reports/generate", {
    document_ids: documentIds,
    report_type: reportType,
  });
  return data;
}

export async function getReport(reportId: string): Promise<Report> {
  const { data } = await api.get<Report>(`/reports/${reportId}`);
  return data;
}

export async function updateReport(
  reportId: string,
  markdown: string,
): Promise<Report> {
  const { data } = await api.put<Report>(`/reports/${reportId}`, { markdown });
  return data;
}

export async function listReports(params?: {
  search?: string;
  report_type?: string;
  page?: number;
  page_size?: number;
}): Promise<ReportListResponse> {
  const { data } = await api.get<ReportListResponse>("/reports", { params });
  return data;
}

export async function deleteReport(reportId: string): Promise<void> {
  await api.delete(`/reports/${reportId}`);
}

export function getExportUrl(
  reportId: string,
  format: "md" | "pdf" | "docx",
): string {
  return `${API_BASE_URL}/reports/${reportId}/export/${format}`;
}