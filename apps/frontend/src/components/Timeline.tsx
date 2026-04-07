import { CheckCircle, XCircle, Loader2, Clock } from "lucide-react";
import { useAppStore } from "../store/appStore";
import type { TimelineStep } from "../types";

function StepIcon({ status }: { status: TimelineStep["status"] }) {
  if (status === "done")
    return <CheckCircle className="w-5 h-5 text-green-500" />;
  if (status === "error") return <XCircle className="w-5 h-5 text-red-500" />;
  if (status === "running")
    return <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />;
  return <Clock className="w-5 h-5 text-gray-400" />;
}

export function Timeline() {
  const { timeline, darkMode } = useAppStore();

  if (timeline.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <Clock className="w-12 h-12 mb-3 opacity-30" />
        <p className="text-sm">Nenhuma execução ainda.</p>
        <p className="text-xs mt-1">
          Faça upload de um documento para começar.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h2 className="text-lg font-semibold mb-6">Log de Execução</h2>
      <div className="relative">
        {/* Vertical line */}
        <div
          className={`absolute left-[18px] top-0 bottom-0 w-0.5
          ${darkMode ? "bg-gray-700" : "bg-gray-200"}`}
        />

        <div className="space-y-4">
          {timeline.map((step) => (
            <div key={step.id} className="flex items-start gap-4 relative">
              <div className="flex-shrink-0 z-10 bg-white dark:bg-gray-900">
                <StepIcon status={step.status} />
              </div>
              <div className="flex-1 min-w-0 pb-2">
                <div className="flex items-center justify-between gap-2">
                  <span
                    className={`text-sm font-medium
                    ${step.status === "error" ? "text-red-500" : ""}`}
                  >
                    {step.label}
                  </span>
                  {step.timestamp && (
                    <span className="text-xs text-gray-400 flex-shrink-0">
                      {step.timestamp}
                    </span>
                  )}
                </div>
                {step.message && (
                  <p
                    className={`text-xs mt-0.5
                    ${step.status === "error" ? "text-red-400" : "text-gray-500"}`}
                  >
                    {step.message}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
