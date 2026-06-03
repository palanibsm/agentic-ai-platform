"use client";

import { useEffect, useState } from "react";
import { Bot, Plus, Globe, Lock, Activity } from "lucide-react";
import { useUser } from "@/components/user-context";
import { cn } from "@/lib/cn";

interface Agent {
  id: string; agent_name: string; display_name: string;
  description: string; skills: string; model: string;
  service_url: string | null; is_public: number; is_active: number;
}

export default function AgentsPage() {
  const { profile } = useUser();
  const [agents, setAgents]   = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!profile?.team_id) { setLoading(false); return; }
    fetch(`/api/teams/${profile.team_id}/agents`)
      .then(r => r.json())
      .then(d => setAgents(Array.isArray(d) ? d : []))
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, [profile?.team_id]);

  const canEdit = profile?.role === "app-devops" || profile?.role === "ai-devops";

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
          <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">
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
            const skills = (() => { try { return JSON.parse(agent.skills); } catch { return []; } })();
            return (
              <div key={agent.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-cyan-900/50 border border-cyan-800 flex items-center justify-center">
                      <Bot className="w-5 h-5 text-cyan-400" />
                    </div>
                    <div>
                      <p className="text-white font-medium">{agent.display_name}</p>
                      <p className="text-gray-500 text-xs">{agent.model}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={cn("text-xs flex items-center gap-1", agent.is_active ? "text-green-400" : "text-gray-500")}>
                      <Activity className="w-3 h-3" /> {agent.is_active ? "Active" : "Inactive"}
                    </span>
                    {agent.is_public ? (
                      <span className="text-xs text-blue-400 flex items-center gap-1"><Globe className="w-3 h-3" /> Public</span>
                    ) : (
                      <span className="text-xs text-gray-500 flex items-center gap-1"><Lock className="w-3 h-3" /> Private</span>
                    )}
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
                {agent.service_url && (
                  <p className="text-xs text-gray-600 truncate">{agent.service_url}</p>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
