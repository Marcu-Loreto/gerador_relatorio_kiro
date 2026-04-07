import { useRef, useState } from "react";
import {
  Upload,
  FileText,
  CheckCircle,
  AlertCircle,
  Loader2,
  ChevronDown,
  Moon,
  Sun,
  FileSearch,
} from "lucide-react";
import { useAppStore } from "../store/appStore";
import {
  uploadDocument,
  analyzeDocument,
  generateReport,
} from "../services/api";
import { REPORT_TYPE_LABELS, type ReportType } from "../types";

const ACCEPTED = ".pdf,.docx,.xlsx,.csv,.txt,.pptx,.md";

export function Sidebar() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const {
    darkMode,
    toggleDarkMode,
    document,
    setDocument,
    selectedReportType,
    setSelectedReportType,
    isUploading,
    setIsUploading,
    isAnalyzing,
    setIsAnalyzing,
    isGenerating,
    setIsGenerating,
    setReport,
    setError,
    setActiveTab,
    addTimelineStep,
    updateTimelineStep,
    clearTimeline,
  } = useAppStore();

  const addStep = (id: string, label: string) => {
    addTimelineStep({
      id,
      label,
      status: "running",
      timestamp: new Date().toLocaleTimeString(),
    });
  };
  const doneStep = (id: string, msg?: string) =>
    updateTimelineStep(id, { status: "done", message: msg });
  const failStep = (id: string, msg: string) =>
    updateTimelineStep(id, { status: "error", message: msg });

  async function handleFile(file: File) {
    setError(null);
    clearTimeline();
    setDocument(null);
    setReport(null);

    // Upload
    setIsUploading(true);
    addStep("upload", "Enviando documento...");
    try {
      const doc = await uploadDocument(file);
      setDocument(doc);
      doneStep(
        "upload",
        `${doc.filename} (${(doc.file_size / 1024).toFixed(1)} KB)`,
      );
    } catch (e: any) {
      failStep("upload", e?.response?.data?.detail || "Falha no upload");
      setError("Falha no upload do documento.");
      setIsUploading(false);
      return;
    } finally {
      setIsUploading(false);
    }

    // Analyze
    const docId = useAppStore.getState().document?.document_id;
    if (!docId) return;
    setIsAnalyzing(true);
    addStep("analyze", "Analisando documento...");
    try {
      const result = await analyzeDocument(docId);
      doneStep(
        "analyze",
        `${result.word_count} palavras, ${result.sections_count} seções`,
      );
      setDocument({ ...useAppStore.getState().document!, status: "analyzed" });
    } catch (e: any) {
      failStep("analyze", e?.response?.data?.detail || "Falha na análise");
      setError("Falha na análise do documento.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function handleGenerate() {
    const doc = useAppStore.getState().document;
    if (!doc || doc.status !== "analyzed") return;
    setError(null);
    setIsGenerating(true);
    setActiveTab("timeline");

    addStep("generate", `Gerando ${REPORT_TYPE_LABELS[selectedReportType]}...`);
    addStep("review", "Aguardando revisão editorial...");

    try {
      const report = await generateReport(doc.document_id, selectedReportType);
      doneStep("generate", "Relatório gerado");
      doneStep(
        "review",
        `Score de qualidade: ${report.quality_score ?? "N/A"}`,
      );
      addTimelineStep({
        id: "export",
        label: "Pronto para exportação",
        status: "done",
        timestamp: new Date().toLocaleTimeString(),
      });
      setReport(report);
      setActiveTab("preview");
    } catch (e: any) {
      failStep("generate", e?.response?.data?.detail || "Falha na geração");
      setError("Falha na geração do relatório.");
    } finally {
      setIsGenerating(false);
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const isLoading = isUploading || isAnalyzing || isGenerating;
  const canGenerate = document?.status === "analyzed" && !isLoading;

  return (
    <aside
      className={`w-72 flex-shrink-0 flex flex-col border-r h-screen overflow-y-auto
      ${darkMode ? "bg-gray-900 border-gray-700 text-gray-100" : "bg-white border-gray-200 text-gray-900"}`}
    >
      {/* Header */}
      <div
        className={`flex items-center justify-between px-4 py-4 border-b
        ${darkMode ? "border-gray-700" : "border-gray-200"}`}
      >
        <div className="flex items-center gap-2">
          <FileSearch className="w-5 h-5 text-blue-500" />
          <span className="font-semibold text-sm">Gerador de Relatórios</span>
        </div>
        <button
          onClick={toggleDarkMode}
          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          {darkMode ? (
            <Sun className="w-4 h-4" />
          ) : (
            <Moon className="w-4 h-4" />
          )}
        </button>
      </div>

      <div className="flex-1 p-4 space-y-5">
        {/* Upload area */}
        <div>
          <label className="block text-xs font-medium mb-2 text-gray-500 uppercase tracking-wide">
            Documento
          </label>
          <div
            onClick={() => fileRef.current?.click()}
            onDrop={onDrop}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            className={`relative border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all
              ${dragOver ? "border-blue-400 bg-blue-50 dark:bg-blue-900/20" : ""}
              ${
                darkMode
                  ? "border-gray-600 hover:border-blue-500 hover:bg-gray-800"
                  : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
              }`}
          >
            {isUploading ? (
              <Loader2 className="w-8 h-8 mx-auto mb-2 text-blue-500 animate-spin" />
            ) : (
              <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
            )}
            <p className="text-sm font-medium">
              {isUploading ? "Enviando..." : "Arraste ou clique para enviar"}
            </p>
            <p className="text-xs text-gray-400 mt-1">
              PDF, DOCX, XLSX, CSV, TXT, PPTX, MD
            </p>
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPTED}
              className="hidden"
              onChange={(e) =>
                e.target.files?.[0] && handleFile(e.target.files[0])
              }
            />
          </div>
        </div>

        {/* Document status */}
        {document && (
          <div
            className={`rounded-xl p-3 text-sm space-y-1
            ${darkMode ? "bg-gray-800" : "bg-gray-50"}`}
          >
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-500 flex-shrink-0" />
              <span className="font-medium truncate">{document.filename}</span>
            </div>
            <div className="flex items-center gap-2 pl-6">
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 text-yellow-500 animate-spin" />
                  <span className="text-yellow-600 text-xs">Analisando...</span>
                </>
              ) : document.status === "analyzed" ? (
                <>
                  <CheckCircle className="w-3.5 h-3.5 text-green-500" />
                  <span className="text-green-600 text-xs">
                    Análise concluída
                  </span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-3.5 h-3.5 text-gray-400" />
                  <span className="text-gray-400 text-xs">
                    Aguardando análise
                  </span>
                </>
              )}
            </div>
          </div>
        )}

        {/* Report type selector */}
        <div>
          <label className="block text-xs font-medium mb-2 text-gray-500 uppercase tracking-wide">
            Tipo de Relatório
          </label>
          <div className="relative">
            <select
              value={selectedReportType}
              onChange={(e) =>
                setSelectedReportType(e.target.value as ReportType)
              }
              disabled={isLoading}
              className={`w-full appearance-none rounded-xl px-3 py-2.5 pr-8 text-sm border transition-colors
                focus:outline-none focus:ring-2 focus:ring-blue-500
                ${
                  darkMode
                    ? "bg-gray-800 border-gray-600 text-gray-100"
                    : "bg-white border-gray-300 text-gray-900"
                }
                ${isLoading ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              {Object.entries(REPORT_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-2.5 top-3 w-4 h-4 text-gray-400 pointer-events-none" />
          </div>
        </div>

        {/* Generate button */}
        <button
          onClick={handleGenerate}
          disabled={!canGenerate}
          className={`w-full py-2.5 px-4 rounded-xl text-sm font-semibold transition-all
            ${
              canGenerate
                ? "bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow-md"
                : "bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed"
            }`}
        >
          {isGenerating ? (
            <span className="flex items-center justify-center gap-2">
              <Loader2 className="w-4 h-4 animate-spin" /> Gerando...
            </span>
          ) : (
            "Gerar Relatório"
          )}
        </button>
      </div>
    </aside>
  );
}
