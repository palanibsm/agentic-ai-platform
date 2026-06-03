"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Send, Trash2, ChevronDown } from "lucide-react";
import { useUser } from "@/components/user-context";
import { type UserRole } from "@/lib/roles";
import { cn } from "@/lib/cn";

interface Message {
  id: string; role: "user" | "assistant"; content: string;
  toolCalls?: string[]; error?: boolean;
}

const SKILLS = [
  { value: "", label: "No skill" },
  { value: "secure-coding",      label: "Secure Coding Review" },
  { value: "banking-compliance", label: "Banking Compliance" },
  { value: "terraform-iac",      label: "Terraform / IaC Review" },
  { value: "api-standards",      label: "API Standards Review" },
  { value: "data-privacy",       label: "Data Privacy Review" },
  { value: "cloud-architecture", label: "Cloud Architecture" },
  { value: "threat-modeling",    label: "Threat Modeling" },
  { value: "incident-response",  label: "Incident Response" },
];

export default function ChatPage() {
  const { profile } = useUser();
  const [messages, setMessages]   = useState<Message[]>([]);
  const [input, setInput]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [skill, setSkill]         = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  async function sendMessage() {
    const query = input.trim();
    if (!query || loading) return;
    setMessages(m => [...m, { id: crypto.randomUUID(), role: "user", content: query }]);
    setInput("");
    setLoading(true);
    try {
      const res = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          user_id:    profile?.email ?? "anon",
          user_role:  profile?.role  ?? "business-user",
          team_id:    profile?.team_id ?? undefined,
          skill:      skill || undefined,
          session_id: sessionId,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
      if (data.session_id) setSessionId(data.session_id);
      setMessages(m => [...m, {
        id: crypto.randomUUID(), role: "assistant",
        content: data.answer || "(no response)", toolCalls: data.tool_calls_made,
      }]);
    } catch (err: any) {
      setMessages(m => [...m, { id: crypto.randomUUID(), role: "assistant", content: `Error: ${err.message}`, error: true }]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="border-b border-gray-800 bg-gray-900 px-6 py-3 flex items-center justify-between shrink-0">
        <div>
          <h1 className="text-white font-semibold">AI Chat</h1>
          {sessionId && <p className="text-gray-500 text-xs mt-0.5">Session: {sessionId.slice(0, 8)}…</p>}
        </div>
        <div className="flex items-center gap-3">
          {/* Skill selector */}
          <div className="relative">
            <select
              value={skill}
              onChange={e => setSkill(e.target.value)}
              className="appearance-none bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded-lg px-3 py-1.5 pr-7 focus:outline-none focus:border-blue-500"
            >
              {SKILLS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-500 pointer-events-none" />
          </div>
          <button
            onClick={() => { setMessages([]); setSessionId(undefined); }}
            className="text-gray-500 hover:text-gray-300 transition-colors"
            title="Clear chat"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 gap-4">
            <div className="w-16 h-16 bg-gray-800 rounded-full flex items-center justify-center text-3xl">🤖</div>
            <div>
              <p className="text-gray-300 font-medium">How can I help you today?</p>
              <p className="text-sm mt-1">Ask anything — or select a skill for specialised analysis.</p>
            </div>
            {/* Suggestion chips */}
            <div className="flex flex-wrap gap-2 justify-center max-w-lg">
              {["Review this Python code for security issues", "Check MAS TRM compliance for access control", "Help me write an incident response plan"].map(s => (
                <button key={s} onClick={() => setInput(s)} className="text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 rounded-full px-3 py-1.5 transition-colors text-left">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map(msg => (
          <div key={msg.id} className={cn("flex", msg.role === "user" ? "justify-end" : "justify-start")}>
            {msg.role === "assistant" ? (
              <div className={cn("max-w-3xl bg-gray-800 border border-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 prose prose-sm prose-invert max-w-none", msg.error && "border-red-800 bg-red-950/50")}>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                {msg.toolCalls && msg.toolCalls.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-700 flex flex-wrap gap-1">
                    {Array.from(new Set(msg.toolCalls)).map(tc => (
                      <span key={tc} className="text-xs bg-gray-700 text-gray-400 px-2 py-0.5 rounded-full">🔧 {tc}</span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="max-w-2xl bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm">{msg.content}</div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-tl-sm px-4 py-3 flex gap-1">
              {[0,1,2].map(i => <span key={i} className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />)}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-800 bg-gray-900 px-6 py-4 shrink-0">
        <div className="flex gap-3 max-w-4xl mx-auto">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
            placeholder="Ask a question… (Enter to send, Shift+Enter for new line)"
            rows={2}
            className="flex-1 resize-none bg-gray-800 border border-gray-700 text-white placeholder-gray-500 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-blue-500 transition-colors"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-xl transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
