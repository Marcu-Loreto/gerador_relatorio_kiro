import { useRef, useState } from "react";
import {
  Upload,
  CheckCircle,
  AlertCircle,
  Loader2,
  ChevronDown,
  Moon,
  Sun,
  FileSearch,
  X,
  Plus,
  Files,
} from "lucide-react";
import { useAppStore } from "../store/appStore";
import {
  uploadDocument,
  analyzeDocument,
  generateReport,
} from "../services/api";
import {
  REPORT_TYPE_LABELS,
  REPORT_TYPE_CATEGORIES,
  type ReportType,
  type Document,
} from "../types";

const ACCEPTED = ".pdf,.docx,.xlsx,.xls,.csv,.txt,.pptx,.md";

interface UploadedFile {
  file: File;
  doc: Document | null;
  status: "pending" | "uploading" | "analyzing" | "ready" | "error";
  error?: string;
  uploadProgress?: number;
  statusMessage?: string;
}

export function Sidebar() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);

  const {
    darkMode,
    toggleDarkMode,
    selectedReportType,
    setSelectedReportType,
    isGenerating,
    setIsGenerating,
    setReport,
    setError,
    setActiveTab,
    addTimelineStep,
    updateTimelineStep,
    clearTimeline,
  } = useAppStore();

  const updateFile = (idx: number, patch: Partial<UploadedFile>) =>
    setUploadedFiles((prev) =>
      prev.map((f, i) => (i === idx ? { ...f, ...patch } : f)),
    );

  async function processFile(file: File, idx: number) {
    // Upload
    updateFile(idx, {
      status: "uploading",
      uploadProgress: 0,
      statusMessage: "Enviando arquivo...",
    });
    try {
      const doc = await uploadDocument(file, (percent) => {
        updateFile(idx, {
          uploadProgress: percent,
          statusMessage:
            percent < 100 ? `Enviando... ${percent}%` : "Upload concluído",
        });
      });
      updateFile(idx, {
        doc,
        status: "analyzing",
        uploadProgress: 100,
        statusMessage: "Analisando conteúdo...",
      });

      // Analyze
      await analyzeDocument(doc.document_id);
      updateFile(idx, {
        status: "ready",
        doc: { ...doc, status: "analyzed" },
        statusMessage: `✓ Pronto · ${(file.size / 1024).toFixed(0)} KB`,
      });
    } catch (e: any) {
      const msg =
        e?.response?.data?.detail || e?.message || "Falha no processamento";
      updateFile(idx, { status: "error", error: msg, statusMessage: msg });
    }
  }

  async function handleFiles(files: FileList | File[]) {
    const arr = Array.from(files);
    if (!arr.length) return;
    setError(null);
    clearTimeline();
    setReport(null);

    // Adicionar todos à lista imediatamente (dialog fecha na hora)
    const startIdx = uploadedFiles.length;
    const newEntries: UploadedFile[] = arr.map((f) => ({
      file: f,
      doc: null,
      status: "uploading",
    }));
    setUploadedFiles((prev) => [...prev, ...newEntries]);

    // Reset input para permitir re-selecionar o mesmo arquivo
    if (fileRef.current) fileRef.current.value = "";

    // Processar em background (não bloqueia a UI)
    arr.forEach((file, i) => {
      processFile(file, startIdx + i);
    });
  }

  function removeFile(idx: number) {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== idx));
  }

  function clearAll() {
    setUploadedFiles([]);
    setReport(null);
    setError(null);
    clearTimeline();
    if (fileRef.current) fileRef.current.value = "";
  }

  async function handleGenerate() {
    const readyFiles = uploadedFiles.filter(
      (f) => f.status === "ready" && f.doc,
    );
    if (!readyFiles.length) return;

    setError(null);
    setIsGenerating(true);
    setActiveTab("timeline");

    // Usar TODOS os arquivos prontos para gerar o relatório consolidado
    const allDocIds = readyFiles.map((f) => f.doc!.document_id);

    addTimelineStep({
      id: "generate",
      label: `Gerando ${REPORT_TYPE_LABELS[selectedReportType]}...`,
      status: "running",
      timestamp: new Date().toLocaleTimeString(),
    });
    if (readyFiles.length > 1) {
      addTimelineStep({
        id: "multi",
        label: `Consolidando ${readyFiles.length} arquivos`,
        status: "running",
        timestamp: new Date().toLocaleTimeString(),
      });
    }
    addTimelineStep({
      id: "review",
      label: "Revisão editorial...",
      status: "running",
      timestamp: new Date().toLocaleTimeString(),
    });

    try {
      const report = await generateReport(allDocIds, selectedReportType);
      updateTimelineStep("generate", {
        status: "done",
        message: "Relatório gerado",
      });
      if (readyFiles.length > 1) {
        updateTimelineStep("multi", {
          status: "done",
          message: `${readyFiles.length} documentos consolidados`,
        });
      }
      updateTimelineStep("review", {
        status: "done",
        message: `Score: ${report.quality_score ?? "N/A"}`,
      });
      addTimelineStep({
        id: "done",
        label: "Pronto para exportação",
        status: "done",
        timestamp: new Date().toLocaleTimeString(),
      });
      setReport(report);
      setActiveTab("preview");
    } catch (e: any) {
      const msg = e?.response?.data?.detail || "Falha na geração";
      updateTimelineStep("generate", { status: "error", message: msg });
      setError(msg);
    } finally {
      setIsGenerating(false);
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) handleFiles(e.dataTransfer.files);
  };

  const readyCount = uploadedFiles.filter((f) => f.status === "ready").length;
  const busyCount = uploadedFiles.filter(
    (f) =>
      f.status === "pending" ||
      f.status === "uploading" ||
      f.status === "analyzing",
  ).length;
  const canGenerate = readyCount > 0 && busyCount === 0 && !isGenerating;

  const border = darkMode ? "border-gray-700" : "border-gray-200";
  const bg = darkMode
    ? "bg-gray-900 border-gray-700 text-gray-100"
    : "bg-white border-gray-200 text-gray-900";

  return (
    <aside
      className={`w-72 flex-shrink-0 flex flex-col border-r h-screen overflow-y-auto ${bg}`}
    >
      {/* Header */}
      <div
        className={`flex items-center justify-between px-4 py-4 border-b ${border}`}
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

      <div className="flex-1 p-4 space-y-4">
        {/* Upload area */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Documentos
            </label>
            {uploadedFiles.length > 0 && (
              <button
                onClick={clearAll}
                className="text-xs text-red-500 hover:text-red-600 transition-colors"
              >
                Limpar tudo
              </button>
            )}
          </div>

          {/* Drop zone */}
          <div
            onClick={() => fileRef.current?.click()}
            onDrop={onDrop}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            className={`relative border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all
              ${dragOver ? "border-blue-400 bg-blue-50 dark:bg-blue-900/20" : ""}
              ${
                darkMode
                  ? "border-gray-600 hover:border-blue-500 hover:bg-gray-800"
                  : "border-gray-300 hover:border-blue-400 hover:bg-gray-50"
              }`}
          >
            {busyCount > 0 ? (
              <Loader2 className="w-7 h-7 mx-auto mb-1.5 text-blue-500 animate-spin" />
            ) : (
              <div className="flex items-center justify-center gap-1 mb-1.5">
                <Upload className="w-6 h-6 text-gray-400" />
                {uploadedFiles.length > 0 && (
                  <Plus className="w-4 h-4 text-gray-400" />
                )}
              </div>
            )}
            <p className="text-sm font-medium">
              {busyCount > 0
                ? `Processando ${busyCount} arquivo(s)...`
                : uploadedFiles.length > 0
                  ? "Adicionar mais arquivos"
                  : "Arraste ou clique para enviar"}
            </p>
            <p className="text-xs text-gray-400 mt-0.5">
              PDF, DOCX, XLSX, XLS, CSV, TXT, PPTX, MD
            </p>
            <p className="text-xs text-blue-500 mt-0.5 font-medium">
              Múltiplos arquivos suportados
            </p>
            <input
              ref={fileRef}
              type="file"
              accept={ACCEPTED}
              multiple
              className="hidden"
              onChange={(e) => e.target.files && handleFiles(e.target.files)}
            />
          </div>
        </div>

        {/* File list */}
        {uploadedFiles.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <Files className="w-3.5 h-3.5" />
              <span>
                {uploadedFiles.length} arquivo(s) — {readyCount} pronto(s)
              </span>
            </div>
            {uploadedFiles.map((uf, idx) => (
              <div
                key={idx}
                className={`flex items-start gap-2 rounded-xl p-2.5 text-xs
                  ${darkMode ? "bg-gray-800" : "bg-gray-50"}`}
              >
                {/* Status icon */}
                <div className="flex-shrink-0 mt-0.5">
                  {uf.status === "pending" ||
                  uf.status === "uploading" ||
                  uf.status === "analyzing" ? (
                    <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />
                  ) : uf.status === "ready" ? (
                    <CheckCircle className="w-4 h-4 text-green-500" />
                  ) : (
                    <AlertCircle className="w-4 h-4 text-red-500" />
                  )}
                </div>
                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{uf.file.name}</p>
                  <p
                    className={`mt-0.5 ${uf.status === "error" ? "text-red-400" : "text-gray-400"}`}
                  >
                    {uf.statusMessage ||
                      (uf.status === "uploading"
                        ? `Enviando... ${uf.uploadProgress ?? 0}%`
                        : uf.status === "analyzing"
                          ? "Analisando..."
                          : uf.status === "ready"
                            ? `✓ Pronto · ${(uf.file.size / 1024).toFixed(0)} KB`
                            : uf.error || "Erro")}
                  </p>
                  {(uf.status === "uploading" || uf.status === "analyzing") && (
                    <div className="mt-1 w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full transition-all duration-300 ${
                          uf.status === "analyzing"
                            ? "bg-amber-500 animate-pulse"
                            : "bg-blue-500"
                        }`}
                        style={{
                          width:
                            uf.status === "analyzing"
                              ? "100%"
                              : `${uf.uploadProgress ?? 0}%`,
                        }}
                      />
                    </div>
                  )}
                </div>
                {/* Remove */}
                <button
                  onClick={() => removeFile(idx)}
                  className="flex-shrink-0 p-0.5 rounded hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                >
                  <X className="w-3.5 h-3.5 text-gray-400" />
                </button>
              </div>
            ))}
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
              disabled={isGenerating}
              className={`w-full appearance-none rounded-xl px-3 py-2.5 pr-8 text-sm border transition-colors
                focus:outline-none focus:ring-2 focus:ring-blue-500
                ${darkMode ? "bg-gray-800 border-gray-600 text-gray-100" : "bg-white border-gray-300 text-gray-900"}
                ${isGenerating ? "opacity-50 cursor-not-allowed" : ""}`}
            >
              {REPORT_TYPE_CATEGORIES.map((cat) => (
                <optgroup key={cat.label} label={cat.label}>
                  {cat.types.map((value) => (
                    <option key={value} value={value}>
                      {REPORT_TYPE_LABELS[value]}
                    </option>
                  ))}
                </optgroup>
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
          ) : readyCount > 1 ? (
            `Gerar Relatório (${readyCount} arquivos)`
          ) : (
            "Gerar Relatório"
          )}
        </button>

        {/* Hint */}
        {readyCount === 0 && uploadedFiles.length === 0 && (
          <p className="text-xs text-center text-gray-400 px-2">
            Envie um ou mais arquivos para gerar um relatório consolidado
          </p>
        )}
      </div>
    </aside>
  );
}
