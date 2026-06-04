"use client";

import { useEffect, useState } from "react";
import { Plus, Shield, Building2, CheckCircle, XCircle } from "lucide-react";
import { useUser } from "@/components/user-context";
import { ROLE_LABELS, type UserRole } from "@/lib/roles";
import { cn } from "@/lib/cn";

interface Team { id: string; name: string; display_name: string; team_type: string; created_at: string; }
interface User { id: string; email: string; display_name: string | null; role: string; team_name: string | null; is_active: number; }
interface A2ARequest {
  id: string; requested_by: string; created_at: string;
  agent_name: string; agent_display_name: string; model: string;
  requester_team_name: string; requester_team_display_name: string;
  agent_team_name: string;
}

const TEAM_TYPE_COLORS: Record<string, string> = {
  "ai-devops":  "bg-blue-900/50 text-blue-300 border-blue-700",
  "app-devops": "bg-cyan-900/50 text-cyan-300 border-cyan-700",
  "business":   "bg-amber-900/50 text-amber-300 border-amber-700",
  "platform":   "bg-purple-900/50 text-purple-300 border-purple-700",
};

type Tab = "teams" | "users" | "a2a";

export default function AdminPage() {
  const { profile }             = useUser();
  const [teams, setTeams]       = useState<Team[]>([]);
  const [users, setUsers]       = useState<User[]>([]);
  const [requests, setRequests] = useState<A2ARequest[]>([]);
  const [tab, setTab]           = useState<Tab>("teams");
  const [loading, setLoading]   = useState(true);
  const [deciding, setDeciding] = useState<Record<string, "approving" | "denying">>({});
  const [decided, setDecided]   = useState<Record<string, "approved" | "denied">>({});

  useEffect(() => {
    Promise.all([
      fetch("/api/admin/teams").then(r => r.json()),
      fetch("/api/admin/users").then(r => r.json()),
      fetch("/api/a2a/pending").then(r => r.json()),
    ]).then(([t, u, a]) => {
      setTeams(Array.isArray(t) ? t : []);
      setUsers(Array.isArray(u) ? u : []);
      setRequests(a.requests ?? []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (profile?.role !== "ai-devops" && profile?.role !== "ai-architect") {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <Shield className="w-12 h-12 text-gray-700 mx-auto mb-3" />
          <p className="text-gray-400">Access restricted to AI DevOps and AI Architects.</p>
        </div>
      </div>
    );
  }

  const canEdit = profile?.role === "ai-devops";

  async function decide(requestId: string, action: "approve" | "deny") {
    setDeciding(d => ({ ...d, [requestId]: action === "approve" ? "approving" : "denying" }));
    try {
      await fetch(`/api/a2a/${requestId}/${action}`, { method: "PUT" });
      setDecided(d => ({ ...d, [requestId]: action === "approve" ? "approved" : "denied" }));
    } catch { /* leave unchanged on error */ }
    finally {
      setDeciding(d => { const n = { ...d }; delete n[requestId]; return n; });
    }
  }

  const pendingCount = requests.filter(r => !decided[r.id]).length;

  const TABS: { key: Tab; label: string; badge?: number }[] = [
    { key: "teams", label: "Teams" },
    { key: "users", label: "Users" },
    { key: "a2a",   label: "A2A Approvals", badge: pendingCount },
  ];

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Platform Admin</h1>
        <p className="text-gray-400 text-sm mt-1">Manage teams, users, and A2A access control</p>
      </div>

      <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-xl p-1 w-fit">
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={cn("flex items-center gap-2 px-4 py-2 text-sm rounded-lg transition-colors capitalize",
              tab === t.key ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
            )}>
            {t.label}
            {t.badge != null && t.badge > 0 && (
              <span className={cn("text-xs rounded-full px-1.5 py-0.5 font-medium",
                tab === t.key ? "bg-white/20 text-white" : "bg-amber-500 text-black")}>
                {t.badge}
              </span>
            )}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-16 text-gray-500">Loading…</div>
      ) : tab === "teams" ? (
        <div className="space-y-4">
          {canEdit && (
            <div className="flex justify-end">
              <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg">
                <Plus className="w-4 h-4" /> New Team
              </button>
            </div>
          )}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {teams.map(team => (
              <div key={team.id} className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-gray-800 flex items-center justify-center">
                      <Building2 className="w-4 h-4 text-gray-400" />
                    </div>
                    <div>
                      <p className="text-white font-medium">{team.display_name}</p>
                      <p className="text-gray-500 text-xs">{team.name}</p>
                    </div>
                  </div>
                  <span className={cn("text-xs border rounded-full px-2 py-0.5", TEAM_TYPE_COLORS[team.team_type] ?? "bg-gray-800 text-gray-400 border-gray-700")}>
                    {team.team_type}
                  </span>
                </div>
                <p className="text-gray-500 text-xs">Created {new Date(team.created_at).toLocaleDateString()}</p>
              </div>
            ))}
          </div>
        </div>

      ) : tab === "users" ? (
        <div className="space-y-4">
          {canEdit && (
            <div className="flex justify-end">
              <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg">
                <Plus className="w-4 h-4" /> Add User
              </button>
            </div>
          )}
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-800">
                <tr>{["User", "Role", "Team", "Status"].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-gray-400 font-medium text-xs">{h}</th>
                ))}</tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {users.map(user => (
                  <tr key={user.id} className="hover:bg-gray-800/50">
                    <td className="px-4 py-3">
                      <p className="text-white">{user.display_name ?? user.email}</p>
                      <p className="text-gray-500 text-xs">{user.email}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-300">{ROLE_LABELS[user.role as UserRole] ?? user.role}</td>
                    <td className="px-4 py-3 text-gray-400">{user.team_name ?? "–"}</td>
                    <td className="px-4 py-3">
                      <span className={cn("text-xs", user.is_active ? "text-green-400" : "text-gray-500")}>
                        {user.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

      ) : (
        <div className="space-y-4">
          {requests.filter(r => !decided[r.id]).length === 0 ? (
            <div className="text-center py-16">
              <CheckCircle className="w-12 h-12 text-gray-700 mx-auto mb-3" />
              <p className="text-gray-400 font-medium">No pending requests</p>
              <p className="text-gray-600 text-sm mt-1">All A2A access requests have been reviewed.</p>
            </div>
          ) : (
            requests.map(req => {
              const d = deciding[req.id];
              const done = decided[req.id];
              if (done) return null;
              return (
                <div key={req.id} className="bg-gray-900 border border-gray-700 rounded-xl p-5 space-y-2">
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1 flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-white font-medium">{req.agent_display_name}</span>
                        <span className="text-gray-500 text-xs font-mono">({req.agent_name})</span>
                        <span className="text-xs bg-gray-800 text-gray-400 border border-gray-700 rounded-full px-2 py-0.5">{req.model}</span>
                      </div>
                      <p className="text-gray-400 text-sm">
                        <span className="text-cyan-400">{req.requester_team_display_name ?? req.requester_team_name}</span>
                        {" → "}
                        <span className="text-blue-400">{req.agent_team_name}</span>
                        {" agent"}
                      </p>
                      <p className="text-gray-600 text-xs">
                        By {req.requested_by} · {new Date(req.created_at).toLocaleString()}
                      </p>
                    </div>
                    {canEdit && (
                      <div className="flex gap-2 shrink-0">
                        <button disabled={!!d} onClick={() => decide(req.id, "deny")}
                          className={cn("flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border transition-colors",
                            d ? "opacity-50 cursor-wait" : "text-red-400 border-red-800 hover:bg-red-900/20")}>
                          <XCircle className="w-4 h-4" />
                          {d === "denying" ? "Denying…" : "Deny"}
                        </button>
                        <button disabled={!!d} onClick={() => decide(req.id, "approve")}
                          className={cn("flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg border transition-colors",
                            d ? "opacity-50 cursor-wait" : "text-green-400 border-green-800 hover:bg-green-900/20")}>
                          <CheckCircle className="w-4 h-4" />
                          {d === "approving" ? "Approving…" : "Approve"}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
