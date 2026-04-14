import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { Save, Download, Eye, Edit3, Loader2 } from "lucide-react";
import { useAppStore } from "../store/appStore";
import { updateReport, getExportUrl } from "../services/api";

export function ReportEditor() {
  const { report, setReport, updateReportMarkdown, darkMode, isGenerating } =
    useAppStore();
  const [localMd, setLocalMd] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [viewMode, setViewMode] = useState<"edit" | "preview" | "split">(
    "split",
  );

  // Sync local markdown state whenever the report changes
  useEffect(() => {
    if (report?.markdown != null) {
      setLocalMd(report.markdown);
    } else {
      setLocalMd("");
    }
  }, [report?.markdown]);

  if (isGenerating) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400">
        <Loader2 className="w-12 h-12 mb-3 text-blue-500 animate-spin" />
        <p className="text-sm font-medium">Gerando relatório...</p>
        <p className="text-xs mt-1">Isso pode levar alguns segundos.</p>
      </div>
    );
  }

  if (!report) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-gray-400">
        <Edit3 className="w-12 h-12 mb-3 opacity-30" />
        <p className="text-sm">Nenhum relatório gerado ainda.</p>
        <p className="text-xs mt-1">
          Faça upload de um documento e clique em "Gerar Relatório".
        </p>
      </div>
    );
  }

  async function handleSave() {
    if (!report) return;
    setIsSaving(true);
    try {
      const updated = await updateReport(report.report_id, localMd);
      setReport({ ...updated, markdown: localMd });
    } catch {
      // silent
    } finally {
      setIsSaving(false);
    }
  }

  function handleDownload(format: "md" | "pdf" | "docx") {
    if (!report) return;

    if (format === "md") {
      const blob = new Blob([localMd], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${report.document_name || "relatorio"}.md`;
      a.click();
      URL.revokeObjectURL(url);
    } else {
      window.open(getExportUrl(report.report_id, format), "_blank");
    }
  }

  const border = darkMode ? "border-gray-700" : "border-gray-200";

  return (
    <div className="flex flex-col h-full">
      <div
        className={`flex items-center justify-between px-4 py-2 border-b ${border} flex-shrink-0`}
      >
        <div className="flex items-center gap-1">
          {(["edit", "split", "preview"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                viewMode === mode
                  ? "bg-blue-600 text-white"
                  : darkMode
                    ? "text-gray-400 hover:bg-gray-800"
                    : "text-gray-500 hover:bg-gray-100"
              }`}
            >
              {mode === "edit"
                ? "Editor"
                : mode === "preview"
                  ? "Preview"
                  : "Dividido"}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-green-600 hover:bg-green-700 text-white transition-colors disabled:opacity-50"
          >
            {isSaving ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            Salvar
          </button>

          <div className="flex items-center gap-1">
            {(["md", "pdf", "docx"] as const).map((fmt) => (
              <button
                key={fmt}
                onClick={() => handleDownload(fmt)}
                className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  darkMode
                    ? "bg-gray-800 hover:bg-gray-700 text-gray-300"
                    : "bg-gray-100 hover:bg-gray-200 text-gray-700"
                }`}
              >
                <Download className="w-3 h-3" />.{fmt.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {(viewMode === "edit" || viewMode === "split") && (
          <div
            className={`flex-1 flex flex-col ${
              viewMode === "split" ? `border-r ${border}` : ""
            }`}
          >
            <div
              className={`px-3 py-1.5 text-xs font-medium border-b ${border} ${
                darkMode
                  ? "text-gray-400 bg-gray-800"
                  : "text-gray-500 bg-gray-50"
              }`}
            >
              <Edit3 className="w-3.5 h-3.5 inline mr-1" /> Markdown
            </div>
            <textarea
              value={localMd}
              onChange={(e) => {
                setLocalMd(e.target.value);
                updateReportMarkdown(e.target.value);
              }}
              className={`flex-1 w-full p-4 font-mono text-sm resize-none focus:outline-none ${
                darkMode
                  ? "bg-gray-900 text-gray-100"
                  : "bg-white text-gray-900"
              }`}
              placeholder="O relatório aparecerá aqui..."
              spellCheck={false}
            />
          </div>
        )}

        {(viewMode === "preview" || viewMode === "split") && (
          <div className="flex-1 flex flex-col overflow-hidden">
            <div
              className={`px-3 py-1.5 text-xs font-medium border-b ${border} ${
                darkMode
                  ? "text-gray-400 bg-gray-800"
                  : "text-gray-500 bg-gray-50"
              }`}
            >
              <Eye className="w-3.5 h-3.5 inline mr-1" /> Preview
            </div>
            <div
              className={`flex-1 overflow-y-auto p-6 prose max-w-none ${
                darkMode ? "prose-invert bg-gray-900" : "bg-white"
              } prose-sm prose-headings:font-semibold prose-table:text-xs`}
            >
              <ReactMarkdown>{localMd}</ReactMarkdown>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
