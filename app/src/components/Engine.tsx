"use client";

import { useState, useRef, useCallback } from "react";
import { Send, Loader2, Volume2, VolumeX, ImageIcon, Brain, Music } from "lucide-react";

type Phase = "idle" | "analyzing" | "creating" | "complete";

interface AnalysisData {
  reasoning: string;
  mood: string;
  musicParams: Record<string, unknown>;
  imagePrompt: string;
}

export default function Engine() {
  const [input, setInput] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [analysis, setAnalysis] = useState<AnalysisData | null>(null);
  const [imageData, setImageData] = useState<string | null>(null);
  const [musicPlaying, setMusicPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const generate = useCallback(async () => {
    if (!input.trim() || phase !== "idle") return;

    setPhase("analyzing");
    setAnalysis(null);
    setImageData(null);
    setError(null);
    setMusicPlaying(false);

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ input: input.trim() }),
      });

      if (!res.body) throw new Error("No response stream");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const msg = JSON.parse(line.slice(6));

            switch (msg.type) {
              case "status":
                if (msg.phase === "analyzing") setPhase("analyzing");
                else if (msg.phase === "creating") setPhase("creating");
                else if (msg.phase === "complete") setPhase("complete");
                break;

              case "analysis":
                setAnalysis({
                  reasoning: msg.reasoning,
                  mood: msg.mood,
                  musicParams: msg.musicParams,
                  imagePrompt: msg.imagePrompt,
                });
                break;

              case "music":
                if (msg.data) {
                  const wavBytes = Uint8Array.from(atob(msg.data), (c) =>
                    c.charCodeAt(0)
                  );
                  const blob = new Blob([wavBytes], { type: "audio/wav" });
                  const url = URL.createObjectURL(blob);

                  if (audioRef.current) {
                    audioRef.current.pause();
                    URL.revokeObjectURL(audioRef.current.src);
                  }
                  const audio = new Audio(url);
                  audio.loop = true;
                  audioRef.current = audio;
                  audio.play();
                  setMusicPlaying(true);
                }
                break;

              case "image":
                if (msg.data) {
                  setImageData(msg.data);
                }
                break;

              case "error":
                console.error("Server error:", msg.message);
                setError(msg.message);
                break;
            }
          } catch {
            // skip unparseable lines
          }
        }
      }
    } catch (err) {
      setError(String(err));
      setPhase("idle");
    }
  }, [input, phase]);

  const reset = () => {
    setPhase("idle");
    setAnalysis(null);
    setImageData(null);
    setError(null);
    setMusicPlaying(false);
    setInput("");
    if (audioRef.current) {
      audioRef.current.pause();
      URL.revokeObjectURL(audioRef.current.src);
      audioRef.current = null;
    }
  };

  const toggleMusic = () => {
    if (!audioRef.current) return;
    if (audioRef.current.paused) {
      audioRef.current.play();
      setMusicPlaying(true);
    } else {
      audioRef.current.pause();
      setMusicPlaying(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-[var(--border)] px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[var(--accent)] flex items-center justify-center">
            <Brain className="w-4 h-4 text-white" />
          </div>
          <h1 className="text-lg font-semibold tracking-tight">
            Resonance Engine
          </h1>
          <span className="text-xs text-[var(--dim)] font-mono">
            AI Creative Director
          </span>
        </div>
        {phase !== "idle" && (
          <button
            onClick={reset}
            className="text-sm text-[var(--dim)] hover:text-[var(--foreground)] transition-colors"
          >
            Reset
          </button>
        )}
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center p-6 gap-8 max-w-5xl mx-auto w-full">
        {/* Input Area */}
        {phase === "idle" && (
          <div className="w-full max-w-2xl animate-fade-in">
            <p className="text-center text-[var(--dim)] text-sm mb-6">
              Describe a scene, moment, place, or concept. The AI will create a
              matched visual and original soundtrack.
            </p>
            <div className="relative">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    generate();
                  }
                }}
                placeholder="A rainy Tokyo street at 2am, neon signs reflecting off wet pavement..."
                className="w-full bg-[var(--surface)] border border-[var(--border)] rounded-xl px-5 py-4 pr-14 text-base resize-none focus:outline-none focus:border-[var(--accent)] transition-colors placeholder:text-[var(--dim)] min-h-[120px]"
                rows={3}
              />
              <button
                onClick={generate}
                disabled={!input.trim()}
                className="absolute bottom-4 right-4 w-10 h-10 rounded-lg bg-[var(--accent)] flex items-center justify-center hover:opacity-90 transition-opacity disabled:opacity-30"
              >
                <Send className="w-4 h-4 text-white" />
              </button>
            </div>
          </div>
        )}

        {/* Loading / Active State */}
        {phase !== "idle" && (
          <div className="w-full animate-fade-in flex flex-col gap-6">
            {/* Input echo */}
            <div className="text-center">
              <p className="text-sm text-[var(--dim)]">Creating experience for</p>
              <p className="text-lg font-medium mt-1 italic">&ldquo;{input}&rdquo;</p>
            </div>

            {/* Status indicators */}
            <div className="flex items-center justify-center gap-6">
              <StatusPill
                icon={<Brain className="w-3.5 h-3.5" />}
                label="Analysis"
                active={phase === "analyzing"}
                done={!!analysis}
              />
              <StatusPill
                icon={<Music className="w-3.5 h-3.5" />}
                label="Score"
                active={phase === "creating" && !musicPlaying}
                done={musicPlaying}
              />
              <StatusPill
                icon={<ImageIcon className="w-3.5 h-3.5" />}
                label="Visual"
                active={phase === "creating" && !imageData}
                done={!!imageData}
              />
            </div>

            {/* Analysis Panel */}
            {analysis && (
              <div className="animate-fade-in bg-[var(--surface)] border border-[var(--border)] rounded-xl p-6 max-w-2xl mx-auto w-full">
                <div className="flex items-center gap-2 mb-3">
                  <Brain className="w-4 h-4 text-[var(--accent)]" />
                  <span className="text-xs font-mono text-[var(--accent)] uppercase tracking-wider">
                    Creative Direction
                  </span>
                  <span className="ml-auto text-xs font-mono text-[var(--dim)]">
                    mood: {analysis.mood}
                  </span>
                </div>
                <p className="text-sm leading-relaxed text-[var(--foreground)] opacity-90">
                  {analysis.reasoning}
                </p>
              </div>
            )}

            {/* Image Display */}
            {imageData ? (
              <div className="animate-fade-in w-full max-w-4xl mx-auto">
                <div className="relative rounded-xl overflow-hidden border border-[var(--border)]">
                  <img
                    src={`data:image/png;base64,${imageData}`}
                    alt="Generated visual"
                    className="w-full h-auto"
                  />
                  {/* Music control overlay */}
                  {musicPlaying !== undefined && audioRef.current && (
                    <button
                      onClick={toggleMusic}
                      className="absolute bottom-4 right-4 w-10 h-10 rounded-full bg-black/60 backdrop-blur flex items-center justify-center hover:bg-black/80 transition-colors"
                    >
                      {musicPlaying ? (
                        <Volume2 className="w-4 h-4 text-white" />
                      ) : (
                        <VolumeX className="w-4 h-4 text-white" />
                      )}
                    </button>
                  )}
                </div>
              </div>
            ) : phase === "creating" ? (
              <div className="w-full max-w-4xl mx-auto aspect-video rounded-xl shimmer-loading" />
            ) : null}

            {/* Error */}
            {error && (
              <p className="text-center text-red-400 text-sm">{error}</p>
            )}

            {/* Complete state */}
            {phase === "complete" && (
              <div className="text-center animate-fade-in">
                <button
                  onClick={reset}
                  className="text-sm text-[var(--accent)] hover:underline"
                >
                  Create another experience
                </button>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function StatusPill({
  icon,
  label,
  active,
  done,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  done: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono transition-all ${
        done
          ? "bg-[var(--accent)]/15 text-[var(--accent)]"
          : active
          ? "bg-[var(--surface2)] text-[var(--foreground)] animate-pulse-glow"
          : "bg-[var(--surface)] text-[var(--dim)]"
      }`}
    >
      {active && !done ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : icon}
      {label}
      {done && <span className="text-[var(--accent2)]">✓</span>}
    </div>
  );
}
