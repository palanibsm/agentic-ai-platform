"use client";

import { useEffect, useState } from "react";
import { Bot, Search, Lock, Globe, ExternalLink } from "lucide-react";
import { cn } from "@/lib/cn";

interface Agent {
  id: string; agent_name: string; display_name: string;
  description: string; skills: string; model: string;
  service_url: string | null; team_name: string; team_display_name: string;
}

export default function MarketplacePage() {
  const [agents, setAgents]   = useState<Agent[]>([]);
  const [search, setSearch]   = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/marketplace")
      .then(r => r.json())
      .then(d => setAgents(d.agents ?? []))
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, []);

  const filtered = agents.filter(a =>
    a.display_name.toLowerCase().includes(search.toLowerCase()) ||
    a.description?.toLowerCase().includes(search.toLowerCase()) ||
    a.team_name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Agent Marketplace</h1>
        <p className="text-gray-400 text-sm mt-1">Discover and access AI agents from across the platform</p>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
        <input
          value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Search agents, teams, skills…"
          className="w-full bg-gray-800 border border-gray-700 text-white placeholder-gray-500 rounded-xl pl-9 pr-4 py-2.5 text-sm focus:outline-none focus:border-blue-500"
        />
      </div>

      {loading ? (
        <div className="text-center py-16 text-gray-500">Loading marketplace…</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16">
          <Bot className="w-12 h-12 text-gray-700 mx-auto mb-3" />
          <p className="text-gray-400 font-medium">No public agents yet</p>
          <p className="text-gray-600 text-sm mt-1">
            App DevOps teams can publish agents to the marketplace from My Agents.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(agent => {
            const skills = (() => { try { return JSON.parse(agent.skills); } catch { return []; } })();
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
                  <span className="text-xs text-gray-500">{agent.model}</span>
                  {agent.service_url ? (
                    <a href={agent.service_url} target="_blank" rel="noreferrer" className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1">
                      Open <ExternalLink className="w-3 h-3" />
                    </a>
                  ) : (
                    <span className="text-xs text-gray-600 flex items-center gap-1"><Lock className="w-3 h-3" /> Not deployed</span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
