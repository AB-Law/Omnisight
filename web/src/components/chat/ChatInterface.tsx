"use client";

import React, {
  useState,
  useEffect,
  useRef,
  useCallback,
  useMemo,
} from "react";
import { useRouter, useSearchParams } from "next/navigation";
import MessageBubble, { BubbleMessage, StreamingToolCall } from "./MessageBubble";
import ChatInput from "./ChatInput";
import {
  createSession,
  getSession,
  listSessions,
  deleteSession,
  sendMessage,
  parseSSEStream,
  updateSessionTitle,
  ChatSession,
  ChatMessage,
} from "@/lib/api";

// ── Helpers ────────────────────────────────────────────────────────────────────

/**
 * Convert a flat DB message list into renderable BubbleMessages.
 *
 * DB ordering is always: user → [tool, tool, …] → assistant
 * (tool records are written before the final assistant text message).
 * We buffer pending tool results and attach them to the assistant bubble
 * that follows them.
 */
function dbMessagesToBubbles(messages: ChatMessage[]): BubbleMessage[] {
  const bubbles: BubbleMessage[] = [];
  const pendingTools: StreamingToolCall[] = [];

  for (const m of messages) {
    if (m.role === "user") {
      bubbles.push({
        id: m.id,
        role: "user",
        content: m.content ?? "",
        created_at: m.created_at,
      });
    } else if (m.role === "tool") {
      const r = m.tool_result;
      if (r?.viz) {
        pendingTools.push({
          name: m.tool_name ?? "",
          label: "",
          args: m.tool_args ?? undefined,
          status: "done",
          viz: r.viz,
          sources: r.sources ?? [],
        });
      }
    } else if (m.role === "assistant") {
      bubbles.push({
        id: m.id,
        role: "assistant",
        content: m.content ?? "",
        toolCalls: pendingTools.length > 0 ? [...pendingTools] : undefined,
        sources: m.metadata_json?.sources as string[] | undefined,
        confidence: m.metadata_json?.confidence as number | null | undefined,
        created_at: m.created_at,
      });
      pendingTools.length = 0;
    }
  }

  return bubbles;
}

// ── SessionDrawer ──────────────────────────────────────────────────────────────

function SessionDrawer({
  sessions,
  currentId,
  onSelect,
  onNew,
  onDelete,
  onClose,
}: {
  sessions: ChatSession[];
  currentId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onClose: () => void;
}) {
  return (
    <aside
      className="absolute inset-y-0 left-0 z-30 w-72 flex flex-col"
      style={{
        background: "rgba(10,18,26,0.97)",
        borderRight: "1px solid rgba(255,255,255,0.08)",
        backdropFilter: "blur(12px)",
      }}
    >
      <div className="flex items-center justify-between px-4 py-4 border-b border-white/8">
        <h2 className="text-xs font-bold uppercase tracking-widest text-slate-400">
          Chat History
        </h2>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors"
          aria-label="Close history"
        >
          <span className="material-symbols-outlined text-lg">close</span>
        </button>
      </div>

      <button
        onClick={onNew}
        className="mx-3 mt-3 flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm font-medium transition-colors text-primary border border-primary/20 hover:bg-primary/10"
      >
        <span className="material-symbols-outlined text-base">add</span>
        New conversation
      </button>

      <div className="flex-1 overflow-y-auto p-3 space-y-1 mt-2">
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`group flex items-center gap-2 rounded-xl px-3 py-2.5 cursor-pointer transition-all ${
              s.id === currentId
                ? "bg-primary/10 border border-primary/20 text-primary"
                : "hover:bg-white/5 text-slate-400 hover:text-slate-200"
            }`}
            onClick={() => onSelect(s.id)}
          >
            <span className="material-symbols-outlined text-sm shrink-0">chat</span>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {s.title ?? "New conversation"}
              </p>
              <p className="text-[10px] text-slate-600 font-mono">
                {new Date(s.created_at).toLocaleDateString()}
                {s.message_count !== undefined ? ` · ${s.message_count} msgs` : ""}
              </p>
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(s.id);
              }}
              className="opacity-0 group-hover:opacity-100 p-0.5 rounded text-slate-600 hover:text-red-400 transition-all"
              aria-label="Delete session"
            >
              <span className="material-symbols-outlined text-sm">delete</span>
            </button>
          </div>
        ))}
        {sessions.length === 0 && (
          <p className="text-slate-600 text-xs px-3 py-4">No conversations yet.</p>
        )}
      </div>
    </aside>
  );
}

// ── Main ChatInterface ─────────────────────────────────────────────────────────

export default function ChatInterface() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<BubbleMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [scanStatus, setScanStatus] = useState("Scanning Articles...");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // ── Cycle scan status text ────────────────────────────────────
  useEffect(() => {
    const statuses = [
      "Scanning Articles...",
      "Indexing Intelligence Feeds...",
      "Correlating Market Signals...",
      "Monitoring Entity Mentions...",
    ];
    let i = 0;
    const interval = setInterval(() => {
      i = (i + 1) % statuses.length;
      setScanStatus(statuses[i]);
    }, 3500);
    return () => clearInterval(interval);
  }, []);

  // ── Load sessions list ────────────────────────────────────────
  const refreshSessions = useCallback(async () => {
    try {
      const list = await listSessions(30);
      setSessions(list);
    } catch {
      // Non-critical
    }
  }, []);

  // ── Init: load session from URL or create new ────────────────
  useEffect(() => {
    const urlSession = searchParams.get("session");

    async function init() {
      await refreshSessions();

      if (urlSession) {
        try {
          const s = await getSession(urlSession);
          setSessionId(s.id);
          setMessages(dbMessagesToBubbles(s.messages));
          return;
        } catch {
          // Session not found — fall through to create new
        }
      }

      // Create a brand-new session
      try {
        const s = await createSession();
        setSessionId(s.id);
        router.replace(`/ai-analyst?session=${s.id}`, { scroll: false });
        setSessions((prev) => [s, ...prev]);
      } catch {
        // API not available — show empty state
      }
    }

    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Send message ──────────────────────────────────────────────
  const handleSend = useCallback(async () => {
    if (!input.trim() || isStreaming || !sessionId) return;

    const userText = input.trim();
    setInput("");
    setIsStreaming(true);

    // Add user bubble immediately
    const userBubble: BubbleMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: userText,
      created_at: new Date().toISOString(),
    };

    // Placeholder assistant bubble
    const assistantId = `a-${Date.now()}`;
    const assistantPlaceholder: BubbleMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      toolCalls: [],
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userBubble, assistantPlaceholder]);

    // Auto-generate session title from first user message
    if (messages.filter((m) => m.role === "user").length === 0) {
      updateSessionTitle(sessionId, userText.slice(0, 60)).catch(() => {});
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId ? { ...s, title: userText.slice(0, 60) } : s,
        ),
      );
    }

    try {
      abortRef.current = new AbortController();
      const response = await sendMessage(sessionId, userText);

      if (!response.ok || !response.body) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      let allSources: string[] = [];

      await parseSSEStream(reader, {
        onToolStart(payload) {
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== assistantId) return m;
              const newCall: StreamingToolCall = {
                name: payload.name,
                label: payload.label,
                args: payload.args,
                status: "running",
              };
              return { ...m, toolCalls: [...(m.toolCalls ?? []), newCall] };
            }),
          );
        },

        onToolResult(payload) {
          if (payload.sources) {
            payload.sources.forEach((s) => {
              if (!allSources.includes(s)) allSources.push(s);
            });
          }
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== assistantId) return m;
              const updatedCalls: StreamingToolCall[] = (m.toolCalls ?? []).map((tc) =>
                tc.name === payload.name && tc.status === "running"
                  ? {
                      ...tc,
                      status: (payload.error ? "error" : "done") as StreamingToolCall["status"],
                      viz: payload.viz,
                      sources: payload.sources,
                      errorMsg: payload.error,
                    }
                  : tc,
              );
              return { ...m, toolCalls: updatedCalls };
            }),
          );
        },

        onTextDelta(payload) {
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== assistantId) return m;
              return { ...m, content: (m.content ?? "") + payload.delta };
            }),
          );
        },

        onDone(payload) {
          if (payload.sources) allSources = [...new Set([...allSources, ...payload.sources])];
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== assistantId) return m;
              return {
                ...m,
                id: payload.message_id || m.id,
                isStreaming: false,
                sources: allSources,
                confidence: payload.confidence,
                created_at: new Date().toISOString(),
              };
            }),
          );
          setIsStreaming(false);
        },

        onError(payload) {
          setMessages((prev) =>
            prev.map((m) => {
              if (m.id !== assistantId) return m;
              return {
                ...m,
                content: `⚠️ ${payload.message}`,
                isStreaming: false,
              };
            }),
          );
          setIsStreaming(false);
        },
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      setMessages((prev) =>
        prev.map((m) => {
          if (m.id !== assistantId) return m;
          return { ...m, content: `⚠️ Connection error: ${msg}`, isStreaming: false };
        }),
      );
      setIsStreaming(false);
    }
  }, [input, isStreaming, sessionId, messages]);

  // ── Clear / new session ───────────────────────────────────────
  const handleNewSession = useCallback(async () => {
    if (isStreaming) abortRef.current?.abort();
    setMessages([]);
    setInput("");
    setIsStreaming(false);
    setShowHistory(false);
    try {
      const s = await createSession();
      setSessionId(s.id);
      router.replace(`/ai-analyst?session=${s.id}`, { scroll: false });
      setSessions((prev) => [s, ...prev]);
    } catch {
      setSessionId(null);
    }
  }, [isStreaming, router]);

  // ── Select session from history ───────────────────────────────
  const handleSelectSession = useCallback(
    async (id: string) => {
      setShowHistory(false);
      if (id === sessionId) return;
      setMessages([]);
      setSessionId(id);
      router.replace(`/ai-analyst?session=${id}`, { scroll: false });
      try {
        const s = await getSession(id);
        setMessages(dbMessagesToBubbles(s.messages));
      } catch {
        setMessages([]);
      }
    },
    [sessionId, router],
  );

  // ── Delete session ────────────────────────────────────────────
  const handleDeleteSession = useCallback(
    async (id: string) => {
      try {
        await deleteSession(id);
        setSessions((prev) => prev.filter((s) => s.id !== id));
        if (id === sessionId) await handleNewSession();
      } catch {
        // Non-critical
      }
    },
    [sessionId, handleNewSession],
  );

  const currentSession = useMemo(
    () => sessions.find((s) => s.id === sessionId) ?? null,
    [sessions, sessionId],
  );

  return (
    <div className="relative flex flex-col h-full bg-[#070f17] overflow-hidden">
      {/* Session history drawer */}
      {showHistory && (
        <SessionDrawer
          sessions={sessions}
          currentId={sessionId}
          onSelect={handleSelectSession}
          onNew={handleNewSession}
          onDelete={handleDeleteSession}
          onClose={() => setShowHistory(false)}
        />
      )}

      {/* ── Header ─────────────────────────────────────────────── */}
      <header
        className="flex items-center justify-between px-6 py-3 border-b shrink-0"
        style={{ borderColor: "rgba(255,255,255,0.06)" }}
      >
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowHistory((v) => !v)}
            className="p-1.5 rounded-lg hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors"
            aria-label="Toggle history"
          >
            <span className="material-symbols-outlined text-lg">menu</span>
          </button>
          <h1 className="text-sm font-bold tracking-[0.15em] text-slate-200 uppercase">
            Omni-Intelligence Bot
          </h1>
          <div
            className="flex items-center gap-1.5 px-2 py-1 rounded-full text-[10px] font-bold tracking-widest uppercase"
            style={{
              background: "rgba(236,91,19,0.08)",
              border: "1px solid rgba(236,91,19,0.2)",
              color: "#ec5b13",
            }}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            Live_Stream_Active
          </div>
          {currentSession?.title && (
            <span className="text-slate-600 text-xs hidden sm:block truncate max-w-[200px]">
              · {currentSession.title}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleNewSession}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-all border border-transparent hover:border-white/10"
          >
            <span className="material-symbols-outlined text-sm">clear_all</span>
            Clear Session
          </button>
          <button
            className="p-1.5 rounded-lg hover:bg-white/5 text-slate-500 hover:text-slate-300 transition-colors"
            aria-label="More options"
          >
            <span className="material-symbols-outlined text-lg">more_vert</span>
          </button>
        </div>
      </header>

      {/* ── Message list ───────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-6 text-center">
            <div
              className="w-16 h-16 rounded-2xl flex items-center justify-center"
              style={{
                background: "rgba(0,208,255,0.08)",
                border: "1px solid rgba(0,208,255,0.15)",
              }}
            >
              <span className="material-symbols-outlined text-3xl text-[#00d0ff]">
                smart_toy
              </span>
            </div>
            <div>
              <h2 className="text-lg font-bold text-slate-200 mb-2">Omni-Intelligence Bot</h2>
              <p className="text-slate-500 text-sm max-w-md leading-relaxed">
                Ask me anything about your tracked entities, sentiment trends, market
                correlations, or knowledge graph. I can generate charts and graphs inline.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-md mt-2">
              {[
                "What's the current sentiment on Tesla?",
                "Show me the sector heatmap",
                "Give me recent events for Apple",
                "Show knowledge graph relationships",
              ].map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => {
                    setInput(prompt);
                  }}
                  className="text-left px-3 py-2.5 rounded-xl text-xs text-slate-400 hover:text-slate-200 transition-all"
                  style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)" }}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </main>

      {/* ── Input footer ───────────────────────────────────────── */}
      <footer
        className="px-6 pb-4 pt-3 border-t shrink-0"
        style={{ borderColor: "rgba(255,255,255,0.06)" }}
      >
        <ChatInput
          value={input}
          onChange={setInput}
          onSend={handleSend}
          disabled={isStreaming || !sessionId}
        />
        <div className="flex items-center justify-between mt-2 px-1">
          <div className="flex items-center gap-3 text-[10px] text-slate-600 font-mono">
            <span className="flex items-center gap-1">
              <span className="material-symbols-outlined text-xs">keyboard_return</span>
              ⌘+Enter to send · Shift+Enter for newline
            </span>
            <span className="flex items-center gap-1">
              <span className="material-symbols-outlined text-xs">lock</span>
              AES-256 Encrypted
            </span>
          </div>
          <span className="flex items-center gap-1 text-[10px] text-slate-600 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            {scanStatus}
          </span>
        </div>
      </footer>
    </div>
  );
}
