"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

// ── Types ─────────────────────────────────────────────────────────────────────

type Role   = "developer" | "senior-engineer" | "architect" | "admin";
type Skill  = "none" | "banking-compliance" | "incident-response" | "secure-coding"
            | "cloud-architecture" | "terraform-iac" | "threat-modeling" | "data-privacy";

interface Message {
  id:         string;
  role:       "user" | "assistant";
  content:    string;
  toolCalls?: string[];
  error?:     boolean;
  ts:         number;
}

interface Session {
  id:        string;       // session_id from agent-core (or local uuid)
  agentId?:  string;       // session_id returned by agent-core
  title:     string;       // first user message (truncated)
  messages:  Message[];
  createdAt: number;
  role:      Role;
  skill:     Skill;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const STORAGE_KEY = "ide-chat-sessions";
const MAX_SESSIONS = 30;

const ROLES: { value: Role; label: string; color: string }[] = [
  { value: "developer",       label: "Developer",       color: "#4fc3f7" },
  { value: "senior-engineer", label: "Senior Engineer", color: "#ce93d8" },
  { value: "architect",       label: "Architect",       color: "#ffb74d" },
  { value: "admin",           label: "Admin",           color: "#ef9a9a" },
];

const SKILLS: { value: Skill; label: string }[] = [
  { value: "none",               label: "No skill" },
  { value: "banking-compliance", label: "Banking Compliance" },
  { value: "incident-response",  label: "Incident Response" },
  { value: "secure-coding",      label: "Secure Coding" },
  { value: "cloud-architecture", label: "Cloud Architecture" },
  { value: "terraform-iac",      label: "Terraform IaC" },
  { value: "threat-modeling",    label: "Threat Modeling" },
  { value: "data-privacy",       label: "Data Privacy" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function loadSessions(): Session[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveSessions(sessions: Session[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.slice(0, MAX_SESSIONS)));
}

function truncate(s: string, n = 42) {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

function fmtTime(ts: number) {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function fmtDate(ts: number) {
  const d = new Date(ts);
  const today = new Date();
  if (d.toDateString() === today.toDateString()) return "Today";
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (d.toDateString() === yesterday.toDateString()) return "Yesterday";
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

// ── Code block renderer ───────────────────────────────────────────────────────

function CodeBlock({ language, children }: { language?: string; children: string }) {
  const [copied, setCopied] = useState(false);

  function copy() {
    navigator.clipboard.writeText(children).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <div className="relative group my-2 rounded overflow-hidden border border-ide-border text-xs">
      <div className="flex items-center justify-between px-3 py-1 bg-[#2d2d2d] text-ide-muted">
        <span>{language || "code"}</span>
        <button
          onClick={copy}
          className="opacity-0 group-hover:opacity-100 transition-opacity text-xs hover:text-ide-text"
        >
          {copied ? "✓ copied" : "copy"}
        </button>
      </div>
      <SyntaxHighlighter
        language={language || "text"}
        style={vscDarkPlus}
        customStyle={{ margin: 0, borderRadius: 0, fontSize: "0.8rem", background: "#1e1e1e" }}
        PreTag="div"
      >
        {children}
      </SyntaxHighlighter>
    </div>
  );
}

// ── Markdown renderer ─────────────────────────────────────────────────────────

const mdComponents = {
  code({ node, inline, className, children, ...props }: any) {
    const match = /language-(\w+)/.exec(className || "");
    if (!inline && (match || String(children).includes("\n"))) {
      return <CodeBlock language={match?.[1]} children={String(children).replace(/\n$/, "")} />;
    }
    return <code className="bg-[#333] text-[#ce9178] px-1 py-0.5 rounded text-[0.82em] font-mono" {...props}>{children}</code>;
  },
};

// ── Main component ────────────────────────────────────────────────────────────

export default function IdeChatPage() {
  const [sessions,       setSessions]      = useState<Session[]>([]);
  const [activeId,       setActiveId]      = useState<string | null>(null);
  const [input,          setInput]         = useState("");
  const [loading,        setLoading]       = useState(false);
  const [userRole,       setUserRole]      = useState<Role>("developer");
  const [skill,          setSkill]         = useState<Skill>("none");
  const [sidebarOpen,    setSidebarOpen]   = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Load sessions from localStorage on mount
  useEffect(() => {
    const stored = loadSessions();
    setSessions(stored);
    if (stored.length > 0) setActiveId(stored[0].id);
  }, []);

  // Auto-scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [sessions, loading, activeId]);

  const activeSession = sessions.find((s) => s.id === activeId) ?? null;
  const messages      = activeSession?.messages ?? [];

  // ── New chat ────────────────────────────────────────────────────────────────

  function newChat() {
    const id = crypto.randomUUID();
    const session: Session = {
      id,
      title:     "New chat",
      messages:  [],
      createdAt: Date.now(),
      role:      userRole,
      skill,
    };
    const updated = [session, ...sessions];
    setSessions(updated);
    saveSessions(updated);
    setActiveId(id);
    setInput("");
    textareaRef.current?.focus();
  }

  // ── Delete session ──────────────────────────────────────────────────────────

  function deleteSession(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    const updated = sessions.filter((s) => s.id !== id);
    setSessions(updated);
    saveSessions(updated);
    if (activeId === id) setActiveId(updated[0]?.id ?? null);
  }

  // ── Restore role/skill when switching sessions ──────────────────────────────

  function switchSession(id: string) {
    setActiveId(id);
    const s = sessions.find((x) => x.id === id);
    if (s) { setUserRole(s.role); setSkill(s.skill); }
  }

  // ── Send message ────────────────────────────────────────────────────────────

  const sendMessage = useCallback(async () => {
    const query = input.trim();
    if (!query || loading) return;

    // Ensure there's an active session
    let targetId = activeId;
    let currentSessions = sessions;

    if (!targetId) {
      const newSession: Session = {
        id:        crypto.randomUUID(),
        title:     truncate(query),
        messages:  [],
        createdAt: Date.now(),
        role:      userRole,
        skill,
      };
      currentSessions = [newSession, ...sessions];
      setSessions(currentSessions);
      saveSessions(currentSessions);
      targetId = newSession.id;
      setActiveId(targetId);
    }

    const userMsg: Message = {
      id:      crypto.randomUUID(),
      role:    "user",
      content: query,
      ts:      Date.now(),
    };

    // Optimistic update
    const updatedSessions = currentSessions.map((s) => {
      if (s.id !== targetId) return s;
      const msgs = [...s.messages, userMsg];
      return {
        ...s,
        messages: msgs,
        title: s.messages.length === 0 ? truncate(query) : s.title,
      };
    });
    setSessions(updatedSessions);
    saveSessions(updatedSessions);
    setInput("");
    setLoading(true);

    const session = updatedSessions.find((s) => s.id === targetId);

    try {
      const res = await fetch("/api/run", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          user_id:    "ide-user",
          user_role:  userRole,
          skill:      skill === "none" ? undefined : skill,
          session_id: session?.agentId,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);

      const assistantMsg: Message = {
        id:        crypto.randomUUID(),
        role:      "assistant",
        content:   data.answer || "(no response)",
        toolCalls: data.tool_calls_made,
        ts:        Date.now(),
      };

      setSessions((prev) => {
        const next = prev.map((s) => {
          if (s.id !== targetId) return s;
          return {
            ...s,
            agentId:  data.session_id ?? s.agentId,
            messages: [...s.messages, assistantMsg],
          };
        });
        saveSessions(next);
        return next;
      });
    } catch (err: any) {
      const errMsg: Message = {
        id:      crypto.randomUUID(),
        role:    "assistant",
        content: `Error: ${err.message}`,
        error:   true,
        ts:      Date.now(),
      };
      setSessions((prev) => {
        const next = prev.map((s) =>
          s.id === targetId ? { ...s, messages: [...s.messages, errMsg] } : s
        );
        saveSessions(next);
        return next;
      });
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  }, [input, loading, activeId, sessions, userRole, skill]);

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  // ── Group sessions by date ──────────────────────────────────────────────────

  const groupedSessions = sessions.reduce<Record<string, Session[]>>((acc, s) => {
    const label = fmtDate(s.createdAt);
    if (!acc[label]) acc[label] = [];
    acc[label].push(s);
    return acc;
  }, {});

  const roleInfo = ROLES.find((r) => r.value === userRole)!;

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-screen overflow-hidden bg-ide-bg">

      {/* ── Sidebar ─────────────────────────────────────────────────────────── */}
      {sidebarOpen && (
        <aside className="w-60 flex-shrink-0 flex flex-col bg-ide-sidebar border-r border-ide-border">

          {/* Sidebar header */}
          <div className="flex items-center justify-between px-3 py-3 border-b border-ide-border">
            <span className="text-xs font-semibold text-ide-muted uppercase tracking-widest">Sessions</span>
            <button
              onClick={newChat}
              className="text-xs text-ide-accent hover:text-ide-accent-hover px-2 py-1 rounded hover:bg-ide-active transition-colors"
              title="New chat (Ctrl+N)"
            >
              + New
            </button>
          </div>

          {/* Session list */}
          <div className="flex-1 overflow-y-auto py-1">
            {sessions.length === 0 && (
              <p className="text-xs text-ide-muted px-3 py-4 text-center">No sessions yet.<br />Start a new chat.</p>
            )}
            {Object.entries(groupedSessions).map(([date, group]) => (
              <div key={date}>
                <p className="text-[10px] text-ide-muted uppercase tracking-widest px-3 pt-3 pb-1">{date}</p>
                {group.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => switchSession(s.id)}
                    className={`session-item group ${s.id === activeId ? "active" : ""}`}
                  >
                    <div className="flex-1 min-w-0">
                      <p className="truncate text-[11px]">{s.title}</p>
                      <p className="text-[10px] text-ide-muted mt-0.5">
                        {fmtTime(s.createdAt)} · {s.role}
                      </p>
                    </div>
                    <button
                      onClick={(e) => deleteSession(s.id, e)}
                      className="opacity-0 group-hover:opacity-100 text-ide-muted hover:text-red-400 transition-opacity text-xs"
                      title="Delete session"
                    >
                      ✕
                    </button>
                  </div>
                ))}
              </div>
            ))}
          </div>

          {/* Sidebar footer */}
          <div className="px-3 py-2 border-t border-ide-border">
            <p className="text-[10px] text-ide-muted">Agentic AI Platform</p>
            <p className="text-[10px] text-ide-muted">IDE Chat v0.1</p>
          </div>
        </aside>
      )}

      {/* ── Main area ───────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* ── Top bar ─────────────────────────────────────────────────────── */}
        <header className="flex items-center gap-3 px-4 py-2 bg-ide-sidebar border-b border-ide-border flex-shrink-0">

          {/* Toggle sidebar */}
          <button
            onClick={() => setSidebarOpen((v) => !v)}
            className="text-ide-muted hover:text-ide-text transition-colors text-sm"
            title="Toggle sidebar"
          >
            ☰
          </button>

          <div className="flex items-center gap-1">
            <span className="text-[10px] font-bold text-ide-accent tracking-wider">IDE</span>
            <span className="text-[10px] text-ide-muted">CHAT</span>
          </div>

          <div className="flex-1" />

          {/* Role selector */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-ide-muted">Role</span>
            <select
              value={userRole}
              onChange={(e) => setUserRole(e.target.value as Role)}
              className="text-[11px] bg-ide-input border border-ide-border text-ide-text rounded px-2 py-0.5 focus:outline-none focus:border-ide-accent"
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>{r.label}</option>
              ))}
            </select>
            <span
              className="text-[10px] px-1.5 py-0.5 rounded-full font-mono"
              style={{ color: roleInfo.color, border: `1px solid ${roleInfo.color}40`, background: `${roleInfo.color}15` }}
            >
              {roleInfo.label}
            </span>
          </div>

          {/* Skill selector */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-ide-muted">Skill</span>
            <select
              value={skill}
              onChange={(e) => setSkill(e.target.value as Skill)}
              className="text-[11px] bg-ide-input border border-ide-border text-ide-text rounded px-2 py-0.5 focus:outline-none focus:border-ide-accent"
            >
              {SKILLS.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          {/* New chat button */}
          <button
            onClick={newChat}
            className="text-[11px] bg-ide-accent hover:bg-ide-accent-hover text-white px-3 py-1 rounded transition-colors"
          >
            New Chat
          </button>
        </header>

        {/* ── Messages ────────────────────────────────────────────────────── */}
        <main className="flex-1 overflow-y-auto px-6 py-4 space-y-4">

          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center gap-4">
              <div className="w-14 h-14 rounded-lg bg-ide-panel border border-ide-border flex items-center justify-center text-2xl">
                🤖
              </div>
              <div>
                <p className="text-ide-text font-medium">Agentic AI Platform</p>
                <p className="text-ide-muted text-sm mt-1">
                  Ask about banking compliance, code review, incidents, or architecture.
                </p>
              </div>
              <div className="flex flex-wrap gap-2 justify-center mt-2">
                {["Explain MAS TRM requirements", "Review this Python function", "Draft an incident response plan", "What are PDPA obligations?"].map((q) => (
                  <button
                    key={q}
                    onClick={() => { setInput(q); textareaRef.current?.focus(); }}
                    className="text-xs px-3 py-1.5 bg-ide-panel border border-ide-border text-ide-muted hover:text-ide-text hover:border-ide-accent rounded-lg transition-colors"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className="flex flex-col gap-1 max-w-[85%]">
                {msg.role === "user" ? (
                  <div className="bubble-user">{msg.content}</div>
                ) : (
                  <div className={`bubble-assistant ${msg.error ? "border-red-700 bg-red-950 text-red-300" : ""}`}>
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={mdComponents as any}
                    >
                      {msg.content}
                    </ReactMarkdown>
                    {msg.toolCalls && msg.toolCalls.length > 0 && (
                      <div className="mt-2 pt-2 border-t border-ide-border flex flex-wrap gap-1.5">
                        {Array.from(new Set(msg.toolCalls)).map((tc) => (
                          <span key={tc} className="tool-badge">⚙ {tc}</span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                <span className="text-[10px] text-ide-muted px-1">
                  {fmtTime(msg.ts)}
                </span>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bubble-assistant flex items-center gap-1 text-ide-muted">
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-ide-accent animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-ide-accent animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="inline-block w-1.5 h-1.5 rounded-full bg-ide-accent animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </main>

        {/* ── Input ───────────────────────────────────────────────────────── */}
        <footer className="px-4 py-3 bg-ide-sidebar border-t border-ide-border flex-shrink-0">
          {activeSession?.agentId && (
            <p className="text-[10px] text-ide-muted mb-1.5 font-mono">
              session: {activeSession.agentId.slice(0, 8)}…
            </p>
          )}
          <div className="flex gap-2 items-end">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything… (Enter to send · Shift+Enter for new line)"
              rows={3}
              className="flex-1 resize-none bg-ide-input border border-ide-border text-ide-text text-sm rounded px-3 py-2 focus:outline-none focus:border-ide-accent placeholder-ide-muted font-mono"
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="px-4 py-2 bg-ide-accent hover:bg-ide-accent-hover text-white text-sm rounded transition-colors disabled:opacity-30 disabled:cursor-not-allowed self-end mb-0"
            >
              {loading ? "…" : "▶ Run"}
            </button>
          </div>
          <p className="text-[10px] text-ide-muted mt-1.5">
            ⌨ Enter to send · Shift+Enter for new line
          </p>
        </footer>
      </div>
    </div>
  );
}
