"use client";

import { useEffect, useState } from "react";
import { Bot, Search, Globe, ExternalLink, CheckCircle, Clock, Filter } from "lucide-react";
import { useUser } from "@/components/user-context";
import { cn } from "@/lib/cn";

interface Agent {
  id: string;
  agent_name: string;
  display_name: string;
  description: string;
  skills: string;
  model: string;
  service_url: string | null;
  team_name: string;
  team_display_name: string;
}

type RequestStatus = "idle" | "pending" | "success" | "already" | "public";

export default function MarketplacePage() {
  const { profile } = useUser();
  const [agents, setAgents]           = useState<Agent[]>([]);
  const [search, setSearch]           = useState("");
  const [filterModel, setFilterModel] = useState("");
  const [filterTeam, setFilterTeam]   = useState("");
  const [loading, setLoading]         = useState(true);
  const [reqStatus, setReqStatus]     = useState<Record<string, RequestStatus>>({});

  useEffect(() => {
    fetch("/api/marketplace")
      .then(r => r.json())
      .then(d => setAgents(d.agents ?? []))
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, []);

  const models    = Array.from(new Set(agents.map(a => a.model))).sort();
  const teamNames = Array.from(new Set(agents.map(a => a.team_display_name))).sort();

  const filtered = agents.filter(a => {
    const q = search.toLowerCase();
    const skills = (() => { try { return JSON.parse(a.skills) as string[]; } catch { return [] as string[]; } })();
    const matchSearch =
      a.display_name.toLowerCase().includes(q) ||
      (a.description ?? "").toLowerCase().includes(q) ||
      a.team_name.toLowerCase().includes(q) ||
      skills.some(s => s.toLowerCase().includes(q));
    return matchSearch && (!filterModel || a.model === filterModel) && (!filterTeam || a.team_display_name === filterTeam);
  });

  async function requestAccess(agent: Agent) {
    if (!profile?.team_id) return;
    setReqStatus(s => ({ ...s, [agent.id]: "pending" }));
    try {
      const res = await fetch("/api/a2a/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requester_team_id: profile.team_id, target_agent_id: agent.id }),
      });
      const data = await res.json();
      if (data.status === "public")                    setReqStatus(s => ({ ...s, [agent.id]: "public" }));
      else if (data.message?.includes("already"))      setReqStatus(s => ({ ...s, [agent.id]: "already" }));
      else                                             setReqStatus(s => ({ ...s, [agent.id]: "success" }));
    } catch {
      setReqStatus(s => ({ ...s, [agent.id]: "idle" }));
    }
  }

  const canRequest = profile?.role === "app-devops";

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Agent Marketplace</h1>
        <p className="text-gray-400 text-sm mt-1">Discover and access AI agents from across the platform</p>
      </div>

      {/* Search + filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Search agents, skills, teams…"
            className="w-full bg-gray-800 border border-gray-700 text-white placeholder-gray-500 rounded-xl pl-9 pr-4 py-2.5 text-sm focus:outline-none focus:border-blue-500"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-500" />
          <select
            value={filterModel} onChange={e => setFilterModel(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="">All models</option>
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          <select
            value={filterTeam} onChange={e => setFilterTeam(e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="">All teams</option>
            {teamNames.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
        {(filterModel || filterTeam || search) && (
          <button onClick={() => { setSearch(""); setFilterModel(""); setFilterTeam(""); }}
            className="text-xs text-gray-500 hover:text-gray-300 underline">
            Clear filters
          </button>
        )}
      </div>

      {!loading && agents.length > 0 && (
        <p className="text-gray-500 text-sm">{filtered.length} of {agents.length} agents</p>
      )}

      {loading ? (
        <div className="text-center py-16 text-gray-500">Loading marketplace…</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <Bot className="w-12 h-12 text-gray-700 mx-auto mb-3" />
          <p className="text-gray-400 font-medium">No public agents yet</p>
          <p className="text-gray-600 text-sm mt-1">App DevOps teams can publish agents from My Agents.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(agent => {
            const skills = (() => { try { return JSON.parse(agent.skills) as string[]; } catch { return [] as string[]; } })();
            const st = reqStatus[agent.id] ?? "idle";
            return (
              <div key={agent.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-3 hover:border-gray-700 transition-colors">
                <div className="flex items-start justify-between gap-2">
                  <div className="w-10 h-10 rounded-lg bg-blue-900/50 border border-blue-800 flex items-center justify-center shrink-0">
                    <Bot className="w-5 h-5 text-blue-400" />
                  </div>
                  <span className="flex items-center gap-1 text-xs text-green-400">
                    <Globe className="w-3 h-3" /> Public
                  </span>
                </div>

                <div>
                  <p className="text-white font-medium">{agent.display_name}</p>
                  <p className="text-gray-500 text-xs mt-0.5">{agent.team_display_name}</p>
                  {agent.description && <p className="text-gray-400 text-sm mt-2 line-clamp-2">{agent.description}</p>}
                </div>

                {skills.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {skills.slice(0, 3).map((s: string) => (
                      <span key={s} className="text-xs bg-gray-800 text-gray-400 border border-gray-700 rounded-full px-2 py-0.5">{s}</span>
                    ))}
                    {skills.length > 3 && <span className="text-xs text-gray-500">+{skills.length - 3}</span>}
                  </div>
                )}

                <div className="flex items-center justify-between mt-auto pt-2 border-t border-gray-800">
                  <span className="text-xs text-gray-500 font-mono">{agent.model}</span>
                  <div className="flex items-center gap-2">
                    {agent.service_url && (
                      <a href={agent.service_url} target="_blank" rel="noreferrer"
                        className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">
                        Open <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                    {canRequest && (
                      st === "success" ? (
                        <span className="text-xs text-amber-400 flex items-center gap-1"><Clock className="w-3 h-3" /> Pending review</span>
                      ) : st === "already" ? (
                        <span className="text-xs text-gray-500 flex items-center gap-1"><Clock className="w-3 h-3" /> Already requested</span>
                      ) : st === "public" ? (
                        <span className="text-xs text-green-400 flex items-center gap-1"><CheckCircle className="w-3 h-3" /> Open access</span>
                      ) : (
                        <button
                          onClick={() => requestAccess(agent)}
                          disabled={st === "pending"}
                          className={cn(
                            "text-xs px-2.5 py-1 rounded-lg border transition-colors",
                            st === "pending"
                              ? "text-gray-500 border-gray-700 cursor-wait"
                              : "text-blue-400 border-blue-800 hover:bg-blue-900/30"
                          )}
                        >
                          {st === "pending" ? "Requesting…" : "Request Access"}
                        </button>
                      )
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
