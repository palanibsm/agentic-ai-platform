"use client";

import { useEffect, useState } from "react";
import { Users, Plus, Shield, Building2 } from "lucide-react";
import { useUser } from "@/components/user-context";
import { ROLE_LABELS, type UserRole } from "@/lib/roles";
import { cn } from "@/lib/cn";

interface Team { id: string; name: string; display_name: string; team_type: string; created_at: string; }
interface User { id: string; email: string; display_name: string | null; role: string; team_name: string | null; is_active: number; }

const TEAM_TYPE_COLORS: Record<string, string> = {
  "ai-devops":   "bg-blue-900/50 text-blue-300 border-blue-700",
  "app-devops":  "bg-cyan-900/50 text-cyan-300 border-cyan-700",
  "business":    "bg-amber-900/50 text-amber-300 border-amber-700",
  "platform":    "bg-purple-900/50 text-purple-300 border-purple-700",
};

export default function AdminPage() {
  const { profile } = useUser();
  const [teams, setTeams]   = useState<Team[]>([]);
  const [users, setUsers]   = useState<User[]>([]);
  const [tab, setTab]       = useState<"teams" | "users">("teams");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetch("/api/admin/teams").then(r => r.json()),
      fetch("/api/admin/users").then(r => r.json()),
    ]).then(([t, u]) => {
      setTeams(Array.isArray(t) ? t : []);
      setUsers(Array.isArray(u) ? u : []);
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

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Platform Admin</h1>
        <p className="text-gray-400 text-sm mt-1">Manage teams, users, and platform configuration</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-xl p-1 w-fit">
        {(["teams", "users"] as const).map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={cn("px-4 py-2 text-sm rounded-lg transition-colors capitalize",
              tab === t ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
            )}>
            {t}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-16 text-gray-500">Loading…</div>
      ) : tab === "teams" ? (
        <div className="space-y-4">
          {canEdit && (
            <div className="flex justify-end">
              <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg transition-colors">
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
      ) : (
        <div className="space-y-4">
          {canEdit && (
            <div className="flex justify-end">
              <button className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm px-4 py-2 rounded-lg transition-colors">
                <Plus className="w-4 h-4" /> Add User
              </button>
            </div>
          )}
          <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b border-gray-800">
                <tr>
                  {["User", "Role", "Team", "Status"].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-gray-400 font-medium text-xs">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {users.map(user => (
                  <tr key={user.id} className="hover:bg-gray-800/50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="text-white">{user.display_name ?? user.email}</p>
                      <p className="text-gray-500 text-xs">{user.email}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-gray-300">{ROLE_LABELS[user.role as UserRole] ?? user.role}</span>
                    </td>
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
      )}
    </div>
  );
}
