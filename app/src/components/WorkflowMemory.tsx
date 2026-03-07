"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Play,
  Terminal,
  FileText,
  CheckCircle2,
  Compass,
  Settings,
  Search,
  Send,
  Copy,
  Check,
  ExternalLink,
  ChevronRight,
  Upload,
  Loader2,
  Download,
  MapPin,
  Clock,
  MessageSquare,
  Zap,
  Bot,
  Image as ImageIcon,
  ArrowRight,
  Monitor,
} from "lucide-react";
import CopilotPanel from "./CopilotPanel";

// ─── Types ─────────────────────────────────────────────
interface PlaybookStep {
  step_id: number;
  title: string;
  summary: string;
  step_type: string;
  commands: string[];
  files_modified: string[];
  config_changes: string[];
  tool_context: string;
  what_is_on_screen: string;
  timestamp_start: string;
  timestamp_end: string;
  transcript_snippet: string;
  dependencies: number[];
  verification: string | null;
  keywords: string[];
  important_visual_moment: boolean;
  visual_description: string;
  frame_file?: string;
  enhanced_visual?: string | null;
}

interface Playbook {
  workflow_title: string;
  workflow_summary: string;
  speaker_name?: string;
  total_duration_minutes: number;
  tools_used: string[];
  environments: string[];
  steps: PlaybookStep[];
  all_commands: string[];
  key_timestamps_for_frames: { timestamp: string; reason: string; step_id: number }[];
  transcript_segments?: { timestamp_start: string; timestamp_end: string; text: string }[];
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  stepRef?: number;
}

// ─── Step type styling ─────────────────────────────────
const STEP_ICONS: Record<string, { icon: typeof Terminal; color: string; label: string }> = {
  command: { icon: Terminal, color: "#22d3ee", label: "Command" },
  config_edit: { icon: Settings, color: "#f59e0b", label: "Config" },
  verification: { icon: CheckCircle2, color: "#10b981", label: "Verify" },
  navigation: { icon: Compass, color: "#6366f1", label: "Navigate" },
  explanation: { icon: MessageSquare, color: "#6b6b80", label: "Explain" },
  setup: { icon: Settings, color: "#f59e0b", label: "Setup" },
  deployment: { icon: Zap, color: "#f43f5e", label: "Deploy" },
  debugging: { icon: Search, color: "#f43f5e", label: "Debug" },
};

type AppState = "upload" | "processing" | "playbook";

// ─── Processing stages for animation ──────────────────
const PROCESSING_STAGES = [
  { label: "Extracting transcript from recording", duration: 2000 },
  { label: "Identifying workflow steps", duration: 2500 },
  { label: "Detecting commands and configurations", duration: 2000 },
  { label: "Extracting key frames", duration: 1500 },
  { label: "Building structured playbook", duration: 2000 },
  { label: "Indexing for search and queries", duration: 1000 },
];

export default function WorkflowMemory() {
  const [appState, setAppState] = useState<AppState>("upload");
  const [playbook, setPlaybook] = useState<Playbook | null>(null);
  const [selectedStepId, setSelectedStepId] = useState<number>(1);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [copiedCmd, setCopiedCmd] = useState<string | null>(null);
  const [processingStage, setProcessingStage] = useState(0);
  const [showCommands, setShowCommands] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<{ name: string; size: number } | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [copilotMode, setCopilotMode] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  const selectedStep = playbook?.steps.find((s) => s.step_id === selectedStepId) ?? null;

  // ─── Load playbook from API ─────────────────────────
  const loadPlaybook = useCallback(async () => {
    try {
      const res = await fetch("/api/playbook");
      if (!res.ok) throw new Error("Failed to load");
      const data: Playbook = await res.json();
      setPlaybook(data);
      if (data.steps.length > 0) setSelectedStepId(data.steps[0].step_id);
    } catch (err) {
      console.error("Error loading playbook:", err);
    }
  }, []);

  // ─── File selection (real file picker, but processing is pre-baked) ──
  const handleFileSelect = useCallback((file: File) => {
    setUploadedFile({ name: file.name, size: file.size });
  }, []);

  const handleStartProcessing = useCallback(async () => {
    setAppState("processing");
    setProcessingStage(0);

    for (let i = 0; i < PROCESSING_STAGES.length; i++) {
      setProcessingStage(i);
      await new Promise((r) => setTimeout(r, PROCESSING_STAGES[i].duration));
    }

    await loadPlaybook();
    setAppState("playbook");
  }, [loadPlaybook]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && (file.type.startsWith("video/") || file.name.match(/\.(mp4|mov|webm|mkv)$/i))) {
      handleFileSelect(file);
    }
  }, [handleFileSelect]);

  // ─── Chat (multimodal: sends step frames to Gemini) ──
  const handleChat = useCallback(
    async (input?: string, screenshot?: string) => {
      const msg = input ?? chatInput;
      if (!msg.trim() || !playbook) return;
      const userMsg: ChatMessage = {
        role: "user",
        content: screenshot ? `📸 [Screenshot attached]\n${msg.trim()}` : msg.trim(),
      };
      setChatMessages((prev) => [...prev, userMsg]);
      setChatInput("");
      setIsChatLoading(true);

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: msg.trim(),
            playbook,
            selectedStepId,
            userScreenshot: screenshot || undefined,
          }),
        });
        const data = await res.json();
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.response, stepRef: data.stepRef },
        ]);
        if (data.stepRef) setSelectedStepId(data.stepRef);
      } catch {
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Sorry, I had trouble answering. Please try again." },
        ]);
      } finally {
        setIsChatLoading(false);
      }
    },
    [chatInput, playbook, selectedStepId]
  );

  // ─── Where Am I? (screenshot upload) ────────────────
  const handleWhereAmI = useCallback(() => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "image/*";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = (reader.result as string).split(",")[1];
        handleChat(
          "Where am I in this workflow? Look at my screenshot and compare it to the workflow steps. Tell me which step I'm at and what I should do next.",
          base64
        );
      };
      reader.readAsDataURL(file);
    };
    input.click();
  }, [handleChat]);

  // ─── Copy command ───────────────────────────────────
  const copyCmd = (cmd: string) => {
    navigator.clipboard.writeText(cmd);
    setCopiedCmd(cmd);
    setTimeout(() => setCopiedCmd(null), 2000);
  };

  // ─── Agent export ───────────────────────────────────
  const exportForAgents = () => {
    if (!playbook) return;
    const blob = new Blob([JSON.stringify(playbook, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "workflow_playbook.json";
    a.click();
    URL.revokeObjectURL(url);
  };

  // ═══════════════════════════════════════════════════
  // UPLOAD SCREEN
  // ═══════════════════════════════════════════════════
  if (appState === "upload") {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-8">
        <div className="max-w-2xl w-full text-center animate-fade-in">
          <div className="flex items-center justify-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-xl bg-[var(--accent)] flex items-center justify-center">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-3xl font-bold tracking-tight">Workflow Memory</h1>
          </div>
          <p className="text-[var(--dim)] text-lg mb-10 leading-relaxed">
            Turn workflow recordings into structured, searchable operational playbooks
          </p>

          <input
            ref={fileInputRef}
            type="file"
            accept="video/*,.mp4,.mov,.webm,.mkv"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileSelect(file);
            }}
          />

          {!uploadedFile ? (
            <div
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-2xl p-12 cursor-pointer
                transition-all duration-300 group
                ${isDragging
                  ? "border-[var(--accent)] bg-[rgba(99,102,241,0.08)] scale-[1.02]"
                  : "border-[var(--border)] hover:border-[var(--accent)] hover:bg-[var(--surface)]"}`}
            >
              <Upload className="w-12 h-12 mx-auto mb-4 text-[var(--dim)] group-hover:text-[var(--accent)] transition-colors" />
              <p className="text-lg font-medium mb-2">Upload KT / Workflow Recording</p>
              <p className="text-[var(--dim)] text-sm">
                Drag and drop video here, or click to browse
              </p>
              <p className="text-[var(--dim)] text-xs mt-2">
                Supports: Loom / Zoom / Screen recordings (mp4, mov, webm)
              </p>
            </div>
          ) : (
            <div className="border border-[var(--border)] rounded-2xl p-8 bg-[var(--surface)]">
              <div className="flex items-center justify-center gap-4 mb-6">
                <div className="w-12 h-12 rounded-xl bg-[rgba(99,102,241,0.1)] flex items-center justify-center">
                  <Play className="w-6 h-6 text-[var(--accent)]" />
                </div>
                <div className="text-left">
                  <p className="font-semibold text-lg">{uploadedFile.name}</p>
                  <p className="text-[var(--dim)] text-sm">
                    {(uploadedFile.size / (1024 * 1024)).toFixed(1)} MB
                  </p>
                </div>
              </div>
              <button
                onClick={handleStartProcessing}
                className="w-full py-3 px-6 rounded-xl bg-[var(--accent)] text-white font-semibold
                  hover:brightness-110 transition-all duration-200 flex items-center justify-center gap-2"
              >
                <Zap className="w-4 h-4" />
                Generate Workflow Playbook
              </button>
              <button
                onClick={() => { setUploadedFile(null); if (fileInputRef.current) fileInputRef.current.value = ""; }}
                className="mt-3 text-sm text-[var(--dim)] hover:text-[var(--foreground)] transition-colors"
              >
                Choose different file
              </button>
            </div>
          )}

          <div className="flex items-center justify-center gap-8 mt-10 text-sm text-[var(--dim)]">
            <div className="flex items-center gap-2">
              <Play className="w-4 h-4" />
              <span>Recording</span>
            </div>
            <ArrowRight className="w-4 h-4" />
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              <span>Playbook</span>
            </div>
            <ArrowRight className="w-4 h-4" />
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4" />
              <span>Agent-ready workflow</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════
  // PROCESSING SCREEN
  // ═══════════════════════════════════════════════════
  if (appState === "processing") {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-8">
        <div className="max-w-lg w-full animate-fade-in">
          <div className="flex items-center gap-3 mb-2">
            <Loader2 className="w-6 h-6 text-[var(--accent)] animate-spin" />
            <h2 className="text-xl font-semibold">Analyzing Workflow Recording</h2>
          </div>
          {uploadedFile && (
            <p className="text-[var(--dim)] text-sm mb-8 ml-9">
              {uploadedFile.name} ({(uploadedFile.size / (1024 * 1024)).toFixed(1)} MB)
            </p>
          )}
          {!uploadedFile && <div className="mb-8" />}

          <div className="space-y-4">
            {PROCESSING_STAGES.map((stage, i) => (
              <div key={i} className="flex items-center gap-3">
                {i < processingStage ? (
                  <CheckCircle2 className="w-5 h-5 text-[var(--accent-green)] shrink-0" />
                ) : i === processingStage ? (
                  <Loader2 className="w-5 h-5 text-[var(--accent)] animate-spin shrink-0" />
                ) : (
                  <div className="w-5 h-5 rounded-full border border-[var(--border)] shrink-0" />
                )}
                <span
                  className={
                    i <= processingStage ? "text-[var(--foreground)]" : "text-[var(--dim)]"
                  }
                >
                  {stage.label}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-8 h-1 rounded-full bg-[var(--surface2)] overflow-hidden">
            <div
              className="h-full bg-[var(--accent)] transition-all duration-500 rounded-full"
              style={{
                width: `${((processingStage + 1) / PROCESSING_STAGES.length) * 100}%`,
              }}
            />
          </div>
        </div>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════
  // PLAYBOOK SCREEN — 3-column layout
  // ═══════════════════════════════════════════════════
  if (!playbook) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-[var(--accent)]" />
      </div>
    );
  }

  // ─── Copilot Mode: dark bg + panel on right 1/4 ────
  if (copilotMode && playbook) {
    return (
      <div className="h-screen w-screen flex bg-[#0a0a0f]">
        {/* Left 3/4 — empty dark area (user works in other apps) */}
        <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
          <div className="w-12 h-12 rounded-2xl bg-[var(--accent)] flex items-center justify-center mb-4 opacity-30">
            <Zap className="w-6 h-6 text-white" />
          </div>
          <p className="text-[var(--dim)] text-sm opacity-40 max-w-[300px]">
            Workflow Copilot is active. Share your screen and work in your other apps — I can see and hear you.
          </p>
          <button
            onClick={() => setCopilotMode(false)}
            className="mt-6 text-xs text-[var(--dim)] opacity-30 hover:opacity-70 transition-opacity underline"
          >
            Back to Dashboard
          </button>
        </div>
        {/* Right 1/4 — Copilot Panel */}
        <div className="w-[380px] shrink-0 h-full">
          <CopilotPanel
            playbook={playbook}
            onStepSelect={(id) => setSelectedStepId(id)}
            onClose={() => setCopilotMode(false)}
            isFullScreen={false}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      {/* ─── Header ──────────────────────────────── */}
      <header className="h-14 border-b border-[var(--border)] flex items-center justify-between px-5 shrink-0 bg-[var(--surface)]">
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-[var(--accent)] flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="font-semibold text-sm">Workflow Memory</span>
          <span className="text-[var(--dim)] text-xs">|</span>
          <span className="text-[var(--dim)] text-xs truncate max-w-[300px]">
            {playbook.workflow_title}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowCommands(!showCommands)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs
              bg-[var(--surface2)] hover:bg-[var(--surface3)] border border-[var(--border)] transition-colors"
          >
            <Terminal className="w-3.5 h-3.5" />
            Commands ({playbook.all_commands.length})
          </button>
          <button
            onClick={() => setCopilotMode(!copilotMode)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors border ${
              copilotMode
                ? "bg-[var(--accent)] text-white border-[var(--accent)]"
                : "bg-[var(--surface2)] hover:bg-[var(--surface3)] border-[var(--border)]"
            }`}
          >
            <Monitor className="w-3.5 h-3.5" />
            Copilot
          </button>
          <button
            onClick={exportForAgents}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs
              bg-[var(--accent)] hover:opacity-90 text-white transition-opacity"
          >
            <Download className="w-3.5 h-3.5" />
            Export for AI Agents
          </button>
        </div>
      </header>

      {/* ─── Commands Drawer ──────────────────────── */}
      {showCommands && (
        <div className="border-b border-[var(--border)] bg-[var(--surface)] px-5 py-3 animate-fade-in">
          <h3 className="text-xs font-semibold text-[var(--dim)] uppercase tracking-wider mb-2">
            All Commands Used
          </h3>
          <div className="flex flex-wrap gap-2">
            {playbook.all_commands.map((cmd, i) => (
              <button
                key={i}
                onClick={() => copyCmd(cmd)}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[var(--command-bg)]
                  border border-[var(--border)] text-xs font-mono hover:border-[var(--accent2)] transition-colors"
              >
                <span className="text-[var(--accent2)]">$</span>
                {cmd}
                {copiedCmd === cmd ? (
                  <Check className="w-3 h-3 text-[var(--accent-green)]" />
                ) : (
                  <Copy className="w-3 h-3 text-[var(--dim)]" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ─── Timeline Bar ───────────────────────────── */}
      <div className="border-b border-[var(--border)] bg-[var(--surface)] px-5 py-2 flex items-center gap-1 overflow-x-auto shrink-0">
        {playbook.steps.map((step, i) => {
          const isActive = step.step_id === selectedStepId;
          return (
            <div key={step.step_id} className="flex items-center shrink-0">
              <button
                onClick={() => setSelectedStepId(step.step_id)}
                className={`px-2.5 py-1 rounded-md text-[10px] whitespace-nowrap transition-all ${
                  isActive
                    ? "bg-[var(--accent)] text-white font-semibold"
                    : "bg-[var(--surface2)] text-[var(--dim)] hover:text-[var(--foreground)] hover:bg-[var(--surface3)]"
                }`}
              >
                {step.title.length > 20 ? step.title.slice(0, 20) + "…" : step.title}
              </button>
              {i < playbook.steps.length - 1 && (
                <ArrowRight className="w-3 h-3 text-[var(--border)] mx-0.5 shrink-0" />
              )}
            </div>
          );
        })}
      </div>

      {/* ─── Main 3-column layout ─────────────────── */}
      <div className="flex-1 flex overflow-hidden">
        {/* ═══ LEFT: Steps list ═══ */}
        <aside className="w-72 border-r border-[var(--border)] flex flex-col bg-[var(--surface)] shrink-0">
          <div className="p-4 border-b border-[var(--border)]">
            <h2 className="text-sm font-semibold mb-1">{playbook.workflow_title}</h2>
            <p className="text-xs text-[var(--dim)] line-clamp-2">{playbook.workflow_summary}</p>
            <div className="flex items-center gap-2 mt-2 text-xs text-[var(--dim)]">
              <Clock className="w-3 h-3" />
              <span>{playbook.total_duration_minutes} min</span>
              <span className="mx-1">·</span>
              <span>{playbook.steps.length} steps</span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            {playbook.steps.map((step) => {
              const cfg = STEP_ICONS[step.step_type] ?? STEP_ICONS.command;
              const Icon = cfg.icon;
              const isSelected = step.step_id === selectedStepId;
              return (
                <button
                  key={step.step_id}
                  onClick={() => setSelectedStepId(step.step_id)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg mb-1 flex items-start gap-3 transition-all
                    ${isSelected ? "bg-[var(--surface2)] border border-[var(--border-light)]" : "hover:bg-[var(--surface2)] border border-transparent"}`}
                >
                  <div
                    className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 mt-0.5"
                    style={{ backgroundColor: cfg.color + "18" }}
                  >
                    <Icon className="w-3.5 h-3.5" style={{ color: cfg.color }} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-[var(--dim)] font-mono">
                        {String(step.step_id).padStart(2, "0")}
                      </span>
                      <span className="text-xs font-medium truncate">{step.title}</span>
                    </div>
                    <p className="text-[10px] text-[var(--dim)] truncate mt-0.5">
                      {step.timestamp_start} — {step.summary}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </aside>

        {/* ═══ CENTER: Step detail ═══ */}
        <main className="flex-1 overflow-y-auto p-6 bg-[var(--background)]">
          {selectedStep ? (
            <div className="max-w-2xl mx-auto animate-fade-in" key={selectedStep.step_id}>
              {/* Step header */}
              <div className="flex items-center gap-3 mb-4">
                <span className="text-xs font-mono text-[var(--dim)] bg-[var(--surface2)] px-2 py-1 rounded">
                  Step {selectedStep.step_id}
                </span>
                <span
                  className="text-xs px-2 py-1 rounded"
                  style={{
                    backgroundColor:
                      (STEP_ICONS[selectedStep.step_type]?.color ?? "#6b6b80") + "18",
                    color: STEP_ICONS[selectedStep.step_type]?.color ?? "#6b6b80",
                  }}
                >
                  {STEP_ICONS[selectedStep.step_type]?.label ?? selectedStep.step_type}
                </span>
                <span className="text-xs text-[var(--dim)] ml-auto flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {selectedStep.timestamp_start} – {selectedStep.timestamp_end}
                </span>
              </div>

              <h2 className="text-xl font-semibold mb-3">{selectedStep.title}</h2>

              {/* Summary */}
              <p className="text-sm text-[var(--dim)] leading-relaxed mb-5">
                {selectedStep.summary}
              </p>

              {/* Commands */}
              {selectedStep.commands.length > 0 && (
                <div className="mb-5">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--dim)] mb-2">
                    Commands
                  </h3>
                  {selectedStep.commands.map((cmd, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between bg-[var(--command-bg)] border border-[var(--border)]
                        rounded-lg px-4 py-3 mb-2 font-mono text-sm group"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="text-[var(--accent2)]">$</span>
                        <code className="truncate">{cmd}</code>
                      </div>
                      <button
                        onClick={() => copyCmd(cmd)}
                        className="opacity-0 group-hover:opacity-100 transition-opacity ml-3 shrink-0"
                      >
                        {copiedCmd === cmd ? (
                          <Check className="w-4 h-4 text-[var(--accent-green)]" />
                        ) : (
                          <Copy className="w-4 h-4 text-[var(--dim)]" />
                        )}
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Config changes */}
              {selectedStep.config_changes.length > 0 && (
                <div className="mb-5">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--dim)] mb-2">
                    Configuration Changes
                  </h3>
                  <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-4 text-sm">
                    {selectedStep.config_changes.map((c, i) => (
                      <div key={i} className="flex items-start gap-2 mb-1 last:mb-0">
                        <Settings className="w-3.5 h-3.5 text-[var(--accent-amber)] shrink-0 mt-0.5" />
                        <span>{c}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Files modified */}
              {selectedStep.files_modified.length > 0 && (
                <div className="mb-5">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--dim)] mb-2">
                    Files
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedStep.files_modified.map((f, i) => (
                      <span
                        key={i}
                        className="text-xs font-mono bg-[var(--surface2)] border border-[var(--border)] px-2.5 py-1 rounded"
                      >
                        <FileText className="w-3 h-3 inline mr-1.5 text-[var(--dim)]" />
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Verification */}
              {selectedStep.verification && (
                <div className="mb-5">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--dim)] mb-2">
                    Verification
                  </h3>
                  <div className="bg-[rgba(16,185,129,0.1)] border border-[rgba(16,185,129,0.2)] rounded-lg p-4 text-sm flex items-start gap-2">
                    <CheckCircle2 className="w-4 h-4 text-[var(--accent-green)] shrink-0 mt-0.5" />
                    <span>{selectedStep.verification}</span>
                  </div>
                </div>
              )}

              {/* Frame */}
              {selectedStep.frame_file && (
                <div className="mb-5">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--dim)] mb-2">
                    Visual Reference
                  </h3>
                  <div className="border border-[var(--border)] rounded-lg overflow-hidden bg-[var(--surface)]">
                    <img
                      src={`/frames/${selectedStep.frame_file}`}
                      alt={selectedStep.title}
                      className="w-full"
                    />
                  </div>
                  <p className="text-[10px] text-[var(--dim)] mt-1">
                    {selectedStep.what_is_on_screen}
                  </p>
                </div>
              )}

              {/* Transcript snippet */}
              {selectedStep.transcript_snippet && (
                <div className="mb-5">
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-[var(--dim)] mb-2">
                    From Recording
                  </h3>
                  <blockquote className="border-l-2 border-[var(--accent)] pl-4 py-2 text-sm text-[var(--dim)] italic bg-[var(--surface)] rounded-r-lg">
                    &ldquo;{selectedStep.transcript_snippet}&rdquo;
                  </blockquote>
                </div>
              )}

              {/* Keywords */}
              {selectedStep.keywords.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-4">
                  {selectedStep.keywords.map((k, i) => (
                    <span
                      key={i}
                      className="text-[10px] bg-[var(--surface2)] text-[var(--dim)] px-2 py-0.5 rounded-full"
                    >
                      {k}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-[var(--dim)]">
              Select a step to view details
            </div>
          )}
        </main>

        {/* ═══ RIGHT: Chat assistant ═══ */}
        <aside className="w-96 border-l border-[var(--border)] flex flex-col bg-[var(--surface)] shrink-0">
          {/* Chat header */}
          <div className="p-4 border-b border-[var(--border)]">
            <div className="flex items-center gap-2">
              <Bot className="w-4 h-4 text-[var(--accent)]" />
              <h3 className="text-sm font-semibold">Workflow Assistant</h3>
            </div>
            <p className="text-[10px] text-[var(--dim)] mt-1">
              Ask anything about this workflow
            </p>
          </div>

          {/* Quick prompts */}
          {chatMessages.length === 0 && (
            <div className="p-4 space-y-2">
              {[
                "What are the main steps in this workflow?",
                "What commands are used for deployment?",
                "What should I verify after completing the setup?",
              ].map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleChat(q)}
                  className="w-full text-left text-xs px-3 py-2.5 rounded-lg
                    bg-[var(--surface2)] hover:bg-[var(--surface3)] border border-[var(--border)]
                    hover:border-[var(--border-light)] transition-all flex items-center gap-2"
                >
                  <ChevronRight className="w-3 h-3 text-[var(--accent)] shrink-0" />
                  {q}
                </button>
              ))}

              <div className="pt-2 space-y-2">
                <button
                  onClick={handleWhereAmI}
                  className="w-full text-left text-xs px-3 py-2.5 rounded-lg
                    bg-[rgba(99,102,241,0.1)] hover:bg-[rgba(99,102,241,0.15)] border border-[rgba(99,102,241,0.25)]
                    transition-all flex items-center gap-2 text-[var(--accent)]"
                >
                  <MapPin className="w-3 h-3 shrink-0" />
                  Where am I? (upload screenshot)
                </button>
                <button
                  onClick={() => {
                    const desc = prompt("Describe what you see on your screen or paste terminal output:");
                    if (desc) {
                      handleChat(
                        `Where am I in this workflow? Here's my current state:\n\n${desc}\n\nWhat step am I at and what should I do next?`
                      );
                    }
                  }}
                  className="w-full text-left text-xs px-3 py-2.5 rounded-lg
                    bg-[var(--surface2)] hover:bg-[var(--surface3)] border border-[var(--border)]
                    hover:border-[var(--border-light)] transition-all flex items-center gap-2"
                >
                  <MessageSquare className="w-3 h-3 shrink-0" />
                  Where am I? (describe progress)
                </button>
              </div>
            </div>
          )}

          {/* Chat messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {chatMessages.map((msg, i) => (
              <div
                key={i}
                className={`animate-fade-in ${msg.role === "user" ? "flex justify-end" : ""}`}
              >
                <div
                  className={`rounded-lg px-3 py-2.5 text-sm leading-relaxed max-w-[90%] ${
                    msg.role === "user"
                      ? "bg-[var(--accent)] text-white"
                      : "bg-[var(--surface2)] border border-[var(--border)]"
                  }`}
                >
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                  {msg.stepRef && (
                    <button
                      onClick={() => setSelectedStepId(msg.stepRef!)}
                      className="mt-2 text-[10px] flex items-center gap-1 opacity-70 hover:opacity-100 transition-opacity"
                    >
                      <ExternalLink className="w-3 h-3" />
                      Jump to Step {msg.stepRef}
                    </button>
                  )}
                </div>
              </div>
            ))}
            {isChatLoading && (
              <div className="flex items-center gap-2 text-[var(--dim)] text-sm">
                <Loader2 className="w-4 h-4 animate-spin" />
                Thinking...
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Chat input */}
          <div className="p-3 border-t border-[var(--border)]">
            <div className="flex items-center gap-2 bg-[var(--surface2)] border border-[var(--border)] rounded-lg px-3 py-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleChat()}
                placeholder="Ask about this workflow..."
                className="flex-1 bg-transparent text-sm outline-none placeholder:text-[var(--dim)]"
              />
              <button
                onClick={() => handleChat()}
                disabled={!chatInput.trim() || isChatLoading}
                className="p-1.5 rounded-md hover:bg-[var(--surface3)] transition-colors disabled:opacity-30"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        </aside>
      </div>

    </div>
  );
}
