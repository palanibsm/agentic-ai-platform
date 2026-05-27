"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// ── Types ────────────────────────────────────────────────────────────────────

type Role = "developer" | "senior-engineer" | "architect" | "admin";
type Skill = "none" | "code-review" | "banking-compliance" | "incident-response" | "terraform-iac";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: string[];
  error?: boolean;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const ROLE_COLORS: Record<Role, string> = {
  developer:        "bg-blue-100 text-blue-800",
  "senior-engineer":"bg-purple-100 text-purple-800",
  architect:        "bg-amber-100 text-amber-800",
  admin:            "bg-red-100 text-red-800",
};

// ── Component ────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const [messages, setMessages]     = useState<Message[]>([]);
  const [input, setInput]           = useState("");
  const [loading, setLoading]       = useState(false);
  const [sessionId, setSessionId]   = useState<string | undefined>();
  const [userRole, setUserRole]     = useState<Role>("developer");
  const [skill, setSkill]           = useState<Skill>("none");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function sendMessage() {
    const query = input.trim();
    if (!query || loading) return;

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: query };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          user_id: "portal-user",
          user_role: userRole,
          skill: skill === "none" ? undefined : skill,
          session_id: sessionId,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || `Error ${res.status}`);
      }

      if (data.session_id) setSessionId(data.session_id);

      const assistantMsg: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.answer || "(no response)",
        toolCalls: data.tool_calls_made,
      };
      setMessages((m) => [...m, assistantMsg]);
    } catch (err: any) {
      setMessages((m) => [
        ...m,
        { id: crypto.randomUUID(), role: "assistant", content: `Error: ${err.message}`, error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  function clearChat() {
    setMessages([]);
    setSessionId(undefined);
  }

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">

      {/* ── Header ── */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-brand rounded-lg flex items-center justify-center">
            <span className="text-white text-sm font-bold">AI</span>
          </div>
          <div>
            <h1 className="font-semibold text-gray-900">Agentic AI Platform</h1>
            <p className="text-xs text-gray-500">Enterprise AI Assistant</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Role selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Role:</span>
            <select
              value={userRole}
              onChange={(e) => setUserRole(e.target.value as Role)}
              className="text-xs border rounded px-2 py-1 bg-white"
            >
              <option value="developer">Developer</option>
              <option value="senior-engineer">Senior Engineer</option>
              <option value="architect">Architect</option>
              <option value="admin">Admin</option>
            </select>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${ROLE_COLORS[userRole]}`}>
              {userRole}
            </span>
          </div>

          {/* Skill selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Skill:</span>
            <select
              value={skill}
              onChange={(e) => setSkill(e.target.value as Skill)}
              className="text-xs border rounded px-2 py-1 bg-white"
            >
              <option value="none">None</option>
              <option value="code-review">Code Review</option>
              <option value="banking-compliance">Banking Compliance</option>
              <option value="incident-response">Incident Response</option>
              <option value="terraform-iac">Terraform IaC</option>
            </select>
          </div>

          <button onClick={clearChat} className="text-xs text-gray-500 hover:text-gray-700 border rounded px-2 py-1">
            Clear
          </button>
        </div>
      </header>

      {/* ── Messages ── */}
      <main className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 gap-3">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center text-3xl">🤖</div>
            <p className="text-lg font-medium text-gray-500">How can I help you today?</p>
            <p className="text-sm">Ask me anything about banking operations, compliance, or code.</p>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div>
              {msg.role === "assistant" && (
                <div className={`chat-bubble-assistant prose prose-sm max-w-none ${msg.error ? "border-red-200 bg-red-50 text-red-800" : ""}`}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                  {msg.toolCalls && msg.toolCalls.length > 0 && (
                    <div className="mt-2 pt-2 border-t border-gray-100 flex flex-wrap gap-1">
                      {Array.from(new Set(msg.toolCalls)).map((tc) => (
                        <span key={tc} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
                          🔧 {tc}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {msg.role === "user" && (
                <div className="chat-bubble-user">{msg.content}</div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="chat-bubble-assistant flex items-center gap-2 text-gray-400">
              <span className="animate-pulse">●</span>
              <span className="animate-pulse delay-75">●</span>
              <span className="animate-pulse delay-150">●</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      {/* ── Input ── */}
      <footer className="px-6 py-4 bg-white border-t">
        {sessionId && (
          <p className="text-xs text-gray-400 mb-2">Session: {sessionId}</p>
        )}
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question… (Enter to send, Shift+Enter for new line)"
            rows={2}
            className="flex-1 resize-none border rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-5 py-2 bg-brand text-white rounded-xl text-sm font-medium hover:bg-brand-dark disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "…" : "Send"}
          </button>
        </div>
      </footer>
    </div>
  );
}
