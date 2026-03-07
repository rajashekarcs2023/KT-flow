"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import {
  Send,
  Monitor,
  MonitorOff,
  Minimize2,
  Maximize2,
  Loader2,
  Camera,
  Zap,
  ChevronRight,
  X,
  Mic,
  MicOff,
  PhoneOff,
  Phone,
  Volume2,
  Expand,
  Shrink,
} from "lucide-react";

// ─── Types ──────────────────────────────────────────────
interface Playbook {
  workflow_title: string;
  workflow_summary: string;
  steps: any[];
  all_commands?: string[];
  [key: string]: any;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  stepRef?: number;
  hasScreenshot?: boolean;
}

type CopilotSize = "side" | "full" | "minimized";

interface CopilotPanelProps {
  playbook: Playbook;
  onStepSelect: (stepId: number) => void;
  onClose: () => void;
  isFullScreen?: boolean;
}

// ─── Audio Visualizer ───────────────────────────────────
function AudioVisualizer({ isActive }: { isActive: boolean }) {
  return (
    <div className="flex items-center gap-0.5 h-4">
      {[...Array(5)].map((_, i) => (
        <div
          key={i}
          className={`w-1 rounded-full transition-all duration-150 ${
            isActive ? "bg-[var(--accent)] animate-pulse" : "bg-[var(--border)]"
          }`}
          style={{
            height: isActive ? `${8 + Math.random() * 12}px` : "4px",
            animationDelay: `${i * 0.1}s`,
          }}
        />
      ))}
    </div>
  );
}

export default function CopilotPanel({
  playbook,
  onStepSelect,
  onClose,
  isFullScreen: externalFullScreen,
}: CopilotPanelProps) {
  // ─── State ─────────────────────────────────────────────
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [panelSize, setPanelSize] = useState<CopilotSize>(
    externalFullScreen ? "full" : "side"
  );

  // LiveKit connection state
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isMicOn, setIsMicOn] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const [userSpeaking, setUserSpeaking] = useState(false);
  const [transcription, setTranscription] = useState("");

  // Screen capture for text-chat fallback
  const [lastScreenshot, setLastScreenshot] = useState<string | null>(null);
  const screenStreamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // LiveKit room ref
  const roomRef = useRef<any>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, transcription]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (screenStreamRef.current) {
        screenStreamRef.current.getTracks().forEach((t) => t.stop());
      }
      disconnectLiveKit();
    };
  }, []);

  // ─── LiveKit Connection ─────────────────────────────────
  const audioElementsRef = useRef<Map<string, HTMLAudioElement>>(new Map());

  const connectLiveKit = useCallback(async () => {
    setIsConnecting(true);
    try {
      // Get token from our API
      const tokenRes = await fetch("/api/livekit-token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          identity: `user-${Date.now()}`,
          roomName: "workflow-copilot",
        }),
      });
      const { token, url } = await tokenRes.json();

      if (!token || !url) {
        throw new Error("Failed to get LiveKit token");
      }

      // Dynamic import of livekit-client to avoid SSR issues
      const { Room, RoomEvent, Track } = await import("livekit-client");

      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
        audioCaptureDefaults: { autoGainControl: true, noiseSuppression: true, echoCancellation: true },
      });

      // Handle remote audio tracks — CRITICAL for hearing the agent
      room.on(
        RoomEvent.TrackSubscribed,
        (track: any, publication: any, participant: any) => {
          if (track.kind === Track.Kind.Audio) {
            const audioEl = track.attach();
            audioEl.id = `lk-audio-${participant.identity}-${track.sid}`;
            document.body.appendChild(audioEl);
            audioElementsRef.current.set(track.sid, audioEl);
            console.log("[Copilot] Agent audio track attached:", track.sid);
          }
        }
      );

      room.on(
        RoomEvent.TrackUnsubscribed,
        (track: any) => {
          if (track.kind === Track.Kind.Audio) {
            const el = audioElementsRef.current.get(track.sid);
            if (el) {
              track.detach(el);
              el.remove();
              audioElementsRef.current.delete(track.sid);
            }
          }
        }
      );

      room.on(RoomEvent.Disconnected, () => {
        setIsConnected(false);
        setIsMicOn(false);
        setIsScreenSharing(false);
        // Clean up audio elements
        audioElementsRef.current.forEach((el, sid) => {
          el.remove();
        });
        audioElementsRef.current.clear();
      });

      // Handle transcriptions from the agent
      room.on(
        RoomEvent.TranscriptionReceived,
        (segments: any[], participant: any) => {
          for (const seg of segments) {
            if (seg.final) {
              const text = seg.text?.trim();
              if (!text) continue;
              if (participant?.isLocal) {
                setMessages((prev) => [
                  ...prev,
                  { role: "user", content: text },
                ]);
              } else {
                // Agent transcription
                setMessages((prev) => [
                  ...prev,
                  { role: "assistant", content: text },
                ]);
                // Extract step references
                const stepMatch = text.match(/[Ss]tep\s+(\d+)/);
                if (stepMatch) onStepSelect(parseInt(stepMatch[1]));
              }
              setTranscription("");
            } else {
              setTranscription(seg.text || "");
            }
          }
        }
      );

      // Track agent speaking state
      room.on(RoomEvent.ActiveSpeakersChanged, (speakers: any[]) => {
        const localSpeaking = speakers.some((s: any) => s.isLocal);
        const remoteSpeaking = speakers.some((s: any) => !s.isLocal);
        setUserSpeaking(localSpeaking);
        setAgentSpeaking(remoteSpeaking);
      });

      // Log participant events for debugging
      room.on(RoomEvent.ParticipantConnected, (participant: any) => {
        console.log("[Copilot] Participant connected:", participant.identity);
      });

      room.on(RoomEvent.DataReceived, (payload: any, participant: any) => {
        console.log("[Copilot] Data received from:", participant?.identity);
      });

      // Connect to the room
      await room.connect(url, token);
      console.log("[Copilot] Connected to room:", room.name, "participants:", room.numParticipants);

      setIsConnected(true);
      setIsConnecting(false);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Voice connected! I'm your Workflow Copilot. Share your screen and speak to me — I can see what you're doing and guide you through the workflow.",
        },
      ]);

      // Enable microphone
      await room.localParticipant.setMicrophoneEnabled(true);
      setIsMicOn(true);

      roomRef.current = room;
    } catch (err) {
      console.error("LiveKit connection failed:", err);
      setIsConnecting(false);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Voice connection failed: ${err}. Make sure the Python agent is running (python workflow_copilot_agent.py dev). You can still use text chat.`,
        },
      ]);
    }
  }, [onStepSelect]);

  const disconnectLiveKit = useCallback(() => {
    // Clean up audio elements
    audioElementsRef.current.forEach((el) => el.remove());
    audioElementsRef.current.clear();
    if (roomRef.current) {
      roomRef.current.disconnect();
      roomRef.current = null;
    }
    setIsConnected(false);
    setIsMicOn(false);
    setIsScreenSharing(false);
  }, []);

  const toggleMic = useCallback(async () => {
    if (!roomRef.current) return;
    const newState = !isMicOn;
    await roomRef.current.localParticipant.setMicrophoneEnabled(newState);
    setIsMicOn(newState);
  }, [isMicOn]);

  // ─── Screen Sharing via LiveKit ─────────────────────────
  const toggleScreenShare = useCallback(async () => {
    if (!roomRef.current) {
      // Fallback: use native screen capture for text-chat mode
      if (isScreenSharing) {
        if (screenStreamRef.current) {
          screenStreamRef.current.getTracks().forEach((t) => t.stop());
          screenStreamRef.current = null;
        }
        setIsScreenSharing(false);
      } else {
        try {
          const stream = await navigator.mediaDevices.getDisplayMedia({
            video: { displaySurface: "monitor" } as any,
          });
          screenStreamRef.current = stream;
          if (videoRef.current) {
            videoRef.current.srcObject = stream;
            await videoRef.current.play();
          }
          setIsScreenSharing(true);
          stream.getVideoTracks()[0].addEventListener("ended", () => {
            setIsScreenSharing(false);
            screenStreamRef.current = null;
          });
        } catch (err) {
          console.error("Screen capture failed:", err);
        }
      }
      return;
    }

    // LiveKit screen share
    const newState = !isScreenSharing;
    try {
      await roomRef.current.localParticipant.setScreenShareEnabled(newState);
      setIsScreenSharing(newState);
    } catch (err) {
      console.error("Screen share toggle failed:", err);
    }
  }, [isScreenSharing]);

  // ─── Text chat with screenshot fallback ─────────────────
  const takeScreenshot = useCallback((): string | null => {
    if (!videoRef.current || !canvasRef.current || !isScreenSharing) return null;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0);
    const dataUrl = canvas.toDataURL("image/jpeg", 0.7);
    const base64 = dataUrl.split(",")[1];
    setLastScreenshot(dataUrl);
    return base64;
  }, [isScreenSharing]);

  const handleSend = useCallback(
    async (overrideMsg?: string) => {
      const msg = overrideMsg ?? input;
      if (!msg.trim()) return;

      let screenshot: string | undefined;
      if (isScreenSharing && !isConnected) {
        const base64 = takeScreenshot();
        if (base64) screenshot = base64;
      }

      const userMsg: ChatMessage = {
        role: "user",
        content: msg.trim(),
        hasScreenshot: !!screenshot,
      };
      setMessages((prev) => [...prev, userMsg]);
      setInput("");
      setIsLoading(true);

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: msg.trim(),
            playbook,
            userScreenshot: screenshot,
          }),
        });
        const data = await res.json();
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: data.response, stepRef: data.stepRef },
        ]);
        if (data.stepRef) onStepSelect(data.stepRef);
      } catch {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Sorry, something went wrong." },
        ]);
      } finally {
        setIsLoading(false);
      }
    },
    [input, playbook, isScreenSharing, isConnected, takeScreenshot, onStepSelect]
  );

  // ─── Size classes ───────────────────────────────────────
  if (panelSize === "minimized") {
    return (
      <div
        className="fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full bg-[var(--accent)] shadow-2xl
          flex items-center justify-center cursor-pointer hover:scale-110 transition-transform group"
        onClick={() => setPanelSize("side")}
      >
        <Zap className="w-6 h-6 text-white" />
        {isConnected && (
          <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-green-500 animate-pulse" />
        )}
        {isScreenSharing && (
          <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-red-500 animate-pulse" />
        )}
        <span className="absolute -top-8 right-0 bg-[var(--surface)] text-[10px] px-2 py-1 rounded-md border border-[var(--border)] opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
          Workflow Copilot
        </span>
      </div>
    );
  }

  const isFull = panelSize === "full";

  const panelClasses = isFull
    ? "fixed inset-0 z-50"
    : "h-full w-full border-l";

  return (
    <div
      className={`${panelClasses} bg-[var(--background)] border-[var(--border)] shadow-2xl flex flex-col overflow-hidden`}
    >
      {/* Hidden video/canvas for fallback screen capture */}
      <video ref={videoRef} className="hidden" muted playsInline />
      <canvas ref={canvasRef} className="hidden" />

      {/* ─── Header ─────────────────────────────────────── */}
      <div className="px-4 py-3 border-b border-[var(--border)] bg-[var(--surface)] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <div
            className={`w-8 h-8 rounded-lg flex items-center justify-center ${
              isConnected ? "bg-green-500" : "bg-[var(--accent)]"
            }`}
          >
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-bold">Workflow Copilot</h3>
            <p className="text-[10px] text-[var(--dim)]">
              {isConnected
                ? isScreenSharing
                  ? "Voice active · Watching your screen"
                  : "Voice active · Share screen for context"
                : "Text mode · Connect voice for full experience"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setPanelSize(isFull ? "side" : "full")}
            className="p-1.5 rounded-lg hover:bg-[var(--surface2)] transition-colors"
            title={isFull ? "Side panel" : "Full screen"}
          >
            {isFull ? (
              <Shrink className="w-3.5 h-3.5" />
            ) : (
              <Expand className="w-3.5 h-3.5" />
            )}
          </button>
          <button
            onClick={() => setPanelSize("minimized")}
            className="p-1.5 rounded-lg hover:bg-[var(--surface2)] transition-colors"
          >
            <Minimize2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => {
              disconnectLiveKit();
              onClose();
            }}
            className="p-1.5 rounded-lg hover:bg-[var(--surface2)] transition-colors"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* ─── Controls Bar ───────────────────────────────── */}
      <div className="px-4 py-2.5 border-b border-[var(--border)] bg-[var(--surface)] flex items-center gap-2 shrink-0">
        {/* Voice connect/disconnect */}
        {!isConnected ? (
          <button
            onClick={connectLiveKit}
            disabled={isConnecting}
            className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg transition-all
              bg-green-500/10 text-green-400 border border-green-500/30 hover:bg-green-500/20
              disabled:opacity-50"
          >
            {isConnecting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Connecting...
              </>
            ) : (
              <>
                <Phone className="w-3.5 h-3.5" />
                Connect Voice
              </>
            )}
          </button>
        ) : (
          <button
            onClick={disconnectLiveKit}
            className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg transition-all
              bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20"
          >
            <PhoneOff className="w-3.5 h-3.5" />
            Disconnect
          </button>
        )}

        {/* Mic toggle */}
        {isConnected && (
          <button
            onClick={toggleMic}
            className={`p-1.5 rounded-lg transition-all border ${
              isMicOn
                ? "bg-[var(--accent)]/10 text-[var(--accent)] border-[var(--accent)]/30"
                : "bg-red-500/10 text-red-400 border-red-500/30"
            }`}
            title={isMicOn ? "Mute" : "Unmute"}
          >
            {isMicOn ? (
              <Mic className="w-3.5 h-3.5" />
            ) : (
              <MicOff className="w-3.5 h-3.5" />
            )}
          </button>
        )}

        {/* Screen share toggle */}
        <button
          onClick={toggleScreenShare}
          className={`flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg transition-all border ${
            isScreenSharing
              ? "bg-red-500/10 text-red-400 border-red-500/30"
              : "bg-[rgba(99,102,241,0.1)] text-[var(--accent)] border-[rgba(99,102,241,0.25)]"
          }`}
        >
          {isScreenSharing ? (
            <>
              <MonitorOff className="w-3.5 h-3.5" />
              Stop Screen
            </>
          ) : (
            <>
              <Monitor className="w-3.5 h-3.5" />
              Share Screen
            </>
          )}
        </button>

        {/* Status indicators */}
        <div className="flex-1" />
        {isConnected && (
          <div className="flex items-center gap-2">
            {isScreenSharing && (
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                <span className="text-[10px] text-red-400">LIVE</span>
              </div>
            )}
            <AudioVisualizer isActive={agentSpeaking || userSpeaking} />
          </div>
        )}
      </div>

      {/* ─── Voice Status Banner ────────────────────────── */}
      {isConnected && (agentSpeaking || userSpeaking) && (
        <div
          className={`px-4 py-2 text-xs flex items-center gap-2 shrink-0 ${
            agentSpeaking
              ? "bg-[var(--accent)]/5 text-[var(--accent)]"
              : "bg-green-500/5 text-green-400"
          }`}
        >
          <Volume2 className="w-3 h-3" />
          {agentSpeaking ? "Copilot is speaking..." : "Listening..."}
          {transcription && (
            <span className="text-[var(--dim)] italic ml-1 truncate">
              {transcription}
            </span>
          )}
        </div>
      )}

      {/* ─── Quick Actions (when empty) ────────────────── */}
      {messages.length === 0 && (
        <div className="px-4 py-4 space-y-2 shrink-0">
          <p className="text-xs text-[var(--dim)] mb-2">
            {isConnected
              ? "Just speak to me! Or tap a quick action:"
              : "Connect voice above, or use text chat:"}
          </p>
          {[
            "Where am I in this workflow?",
            "What should I do next?",
            "What command should I run?",
            "Explain what's on my screen",
          ].map((q) => (
            <button
              key={q}
              onClick={() => handleSend(q)}
              className="w-full text-left text-xs px-3 py-2 rounded-lg
                bg-[var(--surface2)] hover:bg-[var(--surface3)] border border-[var(--border)]
                hover:border-[var(--border-light)] transition-all flex items-center gap-2"
            >
              <ChevronRight className="w-3 h-3 text-[var(--accent)] shrink-0" />
              {q}
            </button>
          ))}
        </div>
      )}

      {/* ─── Messages ──────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`text-xs leading-relaxed ${
              msg.role === "user" ? "text-right" : "text-left"
            }`}
          >
            <div
              className={`inline-block max-w-[85%] px-3 py-2 rounded-xl ${
                msg.role === "user"
                  ? "bg-[var(--accent)] text-white"
                  : "bg-[var(--surface2)] text-[var(--foreground)]"
              }`}
            >
              {msg.hasScreenshot && (
                <div className="flex items-center gap-1 mb-1 opacity-70 text-[10px]">
                  <Camera className="w-2.5 h-2.5" />
                  Screenshot attached
                </div>
              )}
              <div className="whitespace-pre-wrap">{msg.content}</div>
              {msg.stepRef && msg.role === "assistant" && (
                <button
                  onClick={() => onStepSelect(msg.stepRef!)}
                  className="mt-1.5 flex items-center gap-1 text-[10px] opacity-70 hover:opacity-100"
                >
                  <ChevronRight className="w-2.5 h-2.5" />
                  Jump to Step {msg.stepRef}
                </button>
              )}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex items-center gap-2 text-xs text-[var(--dim)]">
            <Loader2 className="w-3 h-3 animate-spin" />
            Thinking...
          </div>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* ─── Text Input ────────────────────────────────── */}
      <div className="px-3 py-3 border-t border-[var(--border)] bg-[var(--surface)] shrink-0">
        <div className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder={
              isConnected
                ? "Type or just speak..."
                : isScreenSharing
                  ? "Ask about what's on your screen..."
                  : "Ask a question..."
            }
            className="flex-1 bg-[var(--surface2)] border border-[var(--border)] rounded-xl px-3 py-2
              text-xs placeholder:text-[var(--dim)] focus:outline-none focus:border-[var(--accent)]"
          />
          <button
            onClick={() => handleSend()}
            disabled={isLoading || !input.trim()}
            className="p-2 rounded-xl bg-[var(--accent)] text-white disabled:opacity-40 hover:brightness-110 transition"
          >
            <Send className="w-3.5 h-3.5" />
          </button>
        </div>
        <p className="text-[10px] text-center text-[var(--dim)] mt-1.5">
          {isConnected
            ? "Voice mode active — speak naturally or type"
            : "Connect voice above for the full copilot experience"}
        </p>
      </div>
    </div>
  );
}
