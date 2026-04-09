import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, FileText, Trash2, Download, Eye, Loader2 } from "lucide-react";
import { listReports, deleteReport, getExportUrl } from "../services/api";
import { useAppStore } from "../store/appStore";
import { REPORT_TYPE_LABELS, type ReportType } from "../types";

export function ReportHistory() {
  const { darkMode, setReport, setActiveTab } = useAppStore();
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["reports", search, typeFilter, page],
    queryFn: () =>
      listReports({
        search: search || undefined,
        report_type: typeFilter || undefined,
        page,
        page_size: 15,
      }),
  });

  const border = darkMode ? "border-gray-700" : "border-gray-200";
  const rowHover = darkMode ? "hover:bg-gray-800" : "hover:bg-gray-50";

  async function handleDelete(id: string) {
    if (!confirm("Remover este relatório?")) return;
    await deleteReport(id);
    refetch();
  }

  async function handleOpen(report: any) {
    try {
      const { getReport } = await import("../services/api");
      const full = await getReport(report.report_id);
      setReport({ ...full, markdown: full.markdown ?? "" });
    } catch {
      setReport({ ...report, markdown: report.markdown ?? "" });
    }
    setActiveTab("editor");
  }

  return (
    <div className="p-6 h-full flex flex-col">
      <h2 className="text-lg font-semibold mb-4">Histórico de Relatórios</h2>

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <div
          className={`flex items-center gap-2 flex-1 rounded-xl border px-3 py-2 ${border} ${darkMode ? "bg-gray-800" : "bg-white"}`}
        >
          <Search className="w-4 h-4 text-gray-400 flex-shrink-0" />
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Buscar por nome do documento..."
            className="flex-1 bg-transparent text-sm focus:outline-none"
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value);
            setPage(1);
          }}
          className={`rounded-xl border px-3 py-2 text-sm focus:outline-none ${border}
            ${darkMode ? "bg-gray-800 text-gray-100" : "bg-white text-gray-900"}`}
        >
          <option value="">Todos os tipos</option>
          {Object.entries(REPORT_TYPE_LABELS).map(([v, l]) => (
            <option key={v} value={v}>
              {l}
            </option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className={`flex-1 overflow-auto rounded-xl border ${border}`}>
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-6 h-6 animate-spin text-blue-500" />
          </div>
        ) : !data?.results.length ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-400">
            <FileText className="w-8 h-8 mb-2 opacity-30" />
            <p className="text-sm">Nenhum relatório encontrado.</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr
                className={`border-b ${border} ${darkMode ? "bg-gray-800" : "bg-gray-50"}`}
              >
                <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs uppercase">
                  Documento
                </th>
                <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs uppercase">
                  Tipo
                </th>
                <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs uppercase">
                  Status
                </th>
                <th className="text-left px-4 py-3 font-medium text-gray-500 text-xs uppercase">
                  Data
                </th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {data.results.map((r) => (
                <tr
                  key={r.report_id}
                  className={`border-b ${border} ${rowHover} transition-colors`}
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="w-4 h-4 text-blue-500 flex-shrink-0" />
                      <span className="truncate max-w-[200px]">
                        {r.document_name}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {REPORT_TYPE_LABELS[r.report_type as ReportType] ||
                      r.report_type}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium
                      ${
                        r.status === "final" || r.status === "generated"
                          ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                          : r.status === "edited"
                            ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                            : "bg-gray-100 text-gray-600"
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 text-xs">
                    {r.created_at
                      ? new Date(r.created_at).toLocaleDateString("pt-BR")
                      : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 justify-end">
                      <button
                        onClick={() => handleOpen(r)}
                        title="Abrir"
                        className="p-1.5 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-500 transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <a
                        href={getExportUrl(r.report_id, "md")}
                        download
                        title="Baixar .md"
                        className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                      <button
                        onClick={() => handleDelete(r.report_id)}
                        title="Remover"
                        className="p-1.5 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      {data && data.total > 15 && (
        <div className="flex items-center justify-between mt-3 text-sm text-gray-500">
          <span>{data.total} relatório(s)</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 rounded-lg border disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              Anterior
            </button>
            <span className="px-3 py-1">Página {page}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={page * 15 >= data.total}
              className="px-3 py-1 rounded-lg border disabled:opacity-40 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              Próxima
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
