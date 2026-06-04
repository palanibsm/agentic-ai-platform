"use client";

import { useEffect, useState } from "react";
import { Bot, Plus, Globe, Lock, Activity, X, Loader2 } from "lucide-react";
import { useUser } from "@/components/user-context";
import { cn } from "@/lib/cn";

interface Agent {
  id: string; agent_name: string; display_name: string;
  description: string; skills: string; model: string;
  service_url: string | null; is_public: number; is_active: number;
}

const MODELS = ["claude-sonnet", "claude-haiku", "claude-opus", "gpt-4o-mini", "gpt-4o", "gemini-flash"];
const SKILL_SUGGESTIONS = [
  "rag-search", "code-review", "data-analysis", "document-qa",
  "banking-compliance", "incident-response", "api-standards",
];

interface FormState {
  agent_name: string; display_name: string; description: string;
  model: string; service_url: string; is_public: boolean; skills: string[];
}
const EMPTY_FORM: FormState = {
  agent_name: "", display_name: "", description: "",
  model: "claude-sonnet", service_url: "", is_public: false, skills: [],
};

export default function AgentsPage() {
  const { profile }                 = useUser();
  const [agents, setAgents]         = useState<Agent[]>([]);
  const [loading, setLoading]       = useState(true);
  const [showModal, setShowModal]   = useState(false);
  const [form, setForm]             = useState<FormState>(EMPTY_FORM);
  const [skillInput, setSkillInput] = useState("");
  const [saving, setSaving]         = useState(false);
  const [error, setError]           = useState("");

  function loadAgents() {
    if (!profile?.team_id) { setLoading(false); return; }
    fetch(`/api/teams/${profile.team_id}/agents`)
      .then(r => r.json())
      .then(d => setAgents(d.agents ?? (Array.isArray(d) ? d : [])))
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }

  useEffect(() => { loadAgents(); }, [profile?.team_id]);

  const canEdit = profile?.role === "app-devops" || profile?.role === "ai-devops";

  function addSkill(s: string) {
    const t = s.trim().toLowerCase().replace(/\s+/g, "-");
    if (t && !form.skills.includes(t)) setForm(f => ({ ...f, skills: [...f.skills, t] }));
    setSkillInput("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!profile?.team_id) return;
    setSaving(true); setError("");
    try {
      const res = await fetch("/api/agents/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          team_id: profile.team_id,
          agent_name: form.agent_name,
          display_name: form.display_name,
          description: form.description,
          model: form.model,
          service_url: form.service_url || null,
          is_public: form.is_public,
          skills: form.skills,
        }),
      });
      if (!res.ok) {
        const d = await res.json();
        setError(d.detail ?? d.error ?? "Registration failed"); return;
      }
      setShowModal(false); setForm(EMPTY_FORM);
      setLoading(true); loadAgents();
    } catch { setError("Network error — try again"); }
    finally { setSaving(false); }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">
            {profile?.role === "ai-devops" || profile?.role === "ai-architect" ? "All Agents" : "My Agents"}
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            {profile?.team_name ? `Team: ${profile.team_name}` : "Manage your team's AI agents"}
          </p>
        </div>
        {canEdit && (
          <button
            onClick={() => { setForm(EMPTY_FORM); setError(""); setShowModal(true); }}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" /> Register Agent
          </button>
        )}
      </div>

      {loading ? (
        <div className="text-center py-16 text-gray-500">Loading agents…</div>
      ) : agents.length === 0 ? (
        <div className="text-center py-16">
          <Bot className="w-12 h-12 text-gray-700 mx-auto mb-3" />
          <p className="text-gray-400 font-medium">No agents registered yet</p>
          <p className="text-gray-600 text-sm mt-1">
            {canEdit ? "Register your first agent to get started." : "Your team hasn't registered any agents yet."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {agents.map(agent => {
            const skills = (() => { try { return JSON.parse(agent.skills) as string[]; } catch { return [] as string[]; } })();
            return (
              <div key={agent.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-cyan-900/50 border border-cyan-800 flex items-center justify-center">
                      <Bot className="w-5 h-5 text-cyan-400" />
                    </div>
                    <div>
                      <p className="text-white font-medium">{agent.display_name}</p>
                      <p className="text-gray-500 text-xs font-mono">{agent.model}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={cn("text-xs flex items-center gap-1", agent.is_active ? "text-green-400" : "text-gray-500")}>
                      <Activity className="w-3 h-3" /> {agent.is_active ? "Active" : "Inactive"}
                    </span>
                    {agent.is_public
                      ? <span className="text-xs text-blue-400 flex items-center gap-1"><Globe className="w-3 h-3" /> Public</span>
                      : <span className="text-xs text-gray-500 flex items-center gap-1"><Lock className="w-3 h-3" /> Private</span>
                    }
                  </div>
                </div>
                {agent.description && <p className="text-gray-400 text-sm">{agent.description}</p>}
                {skills.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {skills.map((s: string) => (
                      <span key={s} className="text-xs bg-gray-800 text-gray-400 border border-gray-700 rounded-full px-2 py-0.5">{s}</span>
                    ))}
                  </div>
                )}
                {agent.service_url && <p className="text-xs text-gray-600 truncate">{agent.service_url}</p>}
              </div>
            );
          })}
        </div>
      )}

      {/* Register Agent Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-gray-800">
              <h2 className="text-white font-semibold text-lg">Register Agent</h2>
              <button onClick={() => setShowModal(false)} className="text-gray-500 hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-4">
              {error && (
                <div className="bg-red-900/30 border border-red-800 text-red-300 text-sm rounded-lg px-4 py-2">{error}</div>
              )}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-gray-400 text-xs font-medium">Agent Name *</label>
                  <input required value={form.agent_name}
                    onChange={e => setForm(f => ({ ...f, agent_name: e.target.value.toLowerCase().replace(/\s+/g, "-") }))}
                    placeholder="my-agent"
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 font-mono"
                  />
                  <p className="text-gray-600 text-xs">Unique slug per team</p>
                </div>
                <div className="space-y-1">
                  <label className="text-gray-400 text-xs font-medium">Display Name *</label>
                  <input required value={form.display_name}
                    onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))}
                    placeholder="My Agent"
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-gray-400 text-xs font-medium">Description</label>
                <textarea value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="What does this agent do?"
                  rows={2}
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 resize-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-gray-400 text-xs font-medium">Model</label>
                  <select value={form.model} onChange={e => setForm(f => ({ ...f, model: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                    {MODELS.map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-gray-400 text-xs font-medium">Service URL</label>
                  <input value={form.service_url} onChange={e => setForm(f => ({ ...f, service_url: e.target.value }))}
                    placeholder="https://..."
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <label className="text-gray-400 text-xs font-medium">Skills</label>
                <div className="flex gap-2">
                  <input value={skillInput} onChange={e => setSkillInput(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addSkill(skillInput); } }}
                    placeholder="Type a skill and press Enter"
                    className="flex-1 bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                  />
                  <button type="button" onClick={() => addSkill(skillInput)}
                    className="bg-gray-700 hover:bg-gray-600 text-white text-sm px-3 py-2 rounded-lg">Add</button>
                </div>
                <div className="flex flex-wrap gap-1">
                  {SKILL_SUGGESTIONS.filter(s => !form.skills.includes(s)).map(s => (
                    <button key={s} type="button" onClick={() => addSkill(s)}
                      className="text-xs bg-gray-800 text-gray-500 border border-gray-700 hover:border-gray-500 hover:text-gray-300 rounded-full px-2 py-0.5">
                      + {s}
                    </button>
                  ))}
                </div>
                {form.skills.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {form.skills.map(s => (
                      <span key={s} className="flex items-center gap-1 text-xs bg-blue-900/30 text-blue-300 border border-blue-800 rounded-full px-2 py-0.5">
                        {s}
                        <button type="button" onClick={() => setForm(f => ({ ...f, skills: f.skills.filter(x => x !== s) }))}
                          className="hover:text-white"><X className="w-3 h-3" /></button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <label className="flex items-center gap-3 cursor-pointer">
                <div onClick={() => setForm(f => ({ ...f, is_public: !f.is_public }))}
                  className={cn("w-10 h-5 rounded-full transition-colors relative cursor-pointer", form.is_public ? "bg-blue-600" : "bg-gray-700")}>
                  <div className={cn("absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform", form.is_public ? "translate-x-5" : "translate-x-0.5")} />
                </div>
                <div>
                  <p className="text-white text-sm">Publish to Marketplace</p>
                  <p className="text-gray-500 text-xs">Makes this agent visible to all teams</p>
                </div>
              </label>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)}
                  className="text-gray-400 hover:text-white text-sm px-4 py-2 rounded-lg border border-gray-700">Cancel</button>
                <button type="submit" disabled={saving}
                  className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium px-5 py-2 rounded-lg">
                  {saving && <Loader2 className="w-4 h-4 animate-spin" />}
                  {saving ? "Registering…" : "Register Agent"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
