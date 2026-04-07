import { create } from "zustand";
import type { Document, Report, ReportType, TimelineStep } from "../types";

interface AppState {
  // Theme
  darkMode: boolean;
  toggleDarkMode: () => void;

  // Document
  document: Document | null;
  setDocument: (doc: Document | null) => void;

  // Report config
  selectedReportType: ReportType;
  setSelectedReportType: (type: ReportType) => void;

  // Report
  report: Report | null;
  setReport: (report: Report | null) => void;
  updateReportMarkdown: (markdown: string) => void;

  // UI state
  isUploading: boolean;
  isAnalyzing: boolean;
  isGenerating: boolean;
  setIsUploading: (v: boolean) => void;
  setIsAnalyzing: (v: boolean) => void;
  setIsGenerating: (v: boolean) => void;

  // Active tab
  activeTab: "editor" | "preview" | "timeline" | "history";
  setActiveTab: (tab: "editor" | "preview" | "timeline" | "history") => void;

  // Timeline
  timeline: TimelineStep[];
  addTimelineStep: (step: TimelineStep) => void;
  updateTimelineStep: (id: string, update: Partial<TimelineStep>) => void;
  clearTimeline: () => void;

  // Error
  error: string | null;
  setError: (msg: string | null) => void;
}

export const useAppStore = create<AppState>((set) => ({
  darkMode: window.matchMedia("(prefers-color-scheme: dark)").matches,
  toggleDarkMode: () => set((s) => ({ darkMode: !s.darkMode })),

  document: null,
  setDocument: (doc) => set({ document: doc }),

  selectedReportType: "technical_report",
  setSelectedReportType: (type) => set({ selectedReportType: type }),

  report: null,
  setReport: (report) => set({ report }),
  updateReportMarkdown: (markdown) =>
    set((s) => (s.report ? { report: { ...s.report, markdown } } : {})),

  isUploading: false,
  isAnalyzing: false,
  isGenerating: false,
  setIsUploading: (v) => set({ isUploading: v }),
  setIsAnalyzing: (v) => set({ isAnalyzing: v }),
  setIsGenerating: (v) => set({ isGenerating: v }),

  activeTab: "editor",
  setActiveTab: (tab) => set({ activeTab: tab }),

  timeline: [],
  addTimelineStep: (step) => set((s) => ({ timeline: [...s.timeline, step] })),
  updateTimelineStep: (id, update) =>
    set((s) => ({
      timeline: s.timeline.map((t) => (t.id === id ? { ...t, ...update } : t)),
    })),
  clearTimeline: () => set({ timeline: [] }),

  error: null,
  setError: (msg) => set({ error: msg }),
}));
