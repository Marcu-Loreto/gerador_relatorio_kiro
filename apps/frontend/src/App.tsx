import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect } from "react";
import { Edit3, Eye, Clock, History, AlertCircle, X } from "lucide-react";
import { Sidebar } from "./components/Sidebar";
import { ReportEditor } from "./components/ReportEditor";
import { Timeline } from "./components/Timeline";
import { ReportHistory } from "./components/ReportHistory";
import { useAppStore } from "./store/appStore";

const queryClient = new QueryClient();

function MainContent() {
  const { darkMode, activeTab, setActiveTab, error, setError } = useAppStore();

  // Sync dark mode with document
  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  const tabs = [
    { id: "editor" as const, label: "Editor", icon: Edit3 },
    { id: "preview" as const, label: "Preview", icon: Eye },
    { id: "timeline" as const, label: "Execução", icon: Clock },
    { id: "history" as const, label: "Histórico", icon: History },
  ];

  const border = darkMode ? "border-gray-700" : "border-gray-200";
  const bg = darkMode
    ? "bg-gray-900 text-gray-100"
    : "bg-gray-50 text-gray-900";

  return (
    <div className={`flex h-screen overflow-hidden ${bg}`}>
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Error banner */}
        {error && (
          <div className="flex items-center gap-3 px-4 py-2.5 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 text-sm flex-shrink-0">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span className="flex-1">{error}</span>
            <button onClick={() => setError(null)}>
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Tab bar */}
        <div
          className={`flex items-center border-b ${border} px-4 flex-shrink-0
          ${darkMode ? "bg-gray-900" : "bg-white"}`}
        >
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors
                ${
                  activeTab === id
                    ? "border-blue-500 text-blue-600 dark:text-blue-400"
                    : `border-transparent ${darkMode ? "text-gray-400 hover:text-gray-200" : "text-gray-500 hover:text-gray-700"}`
                }`}
            >
              <Icon className="w-4 h-4" />
              {label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === "editor" && <ReportEditor />}
          {activeTab === "preview" && <ReportEditor />}
          {activeTab === "timeline" && (
            <div className="h-full overflow-y-auto">
              <Timeline />
            </div>
          )}
          {activeTab === "history" && <ReportHistory />}
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MainContent />
    </QueryClientProvider>
  );
}
