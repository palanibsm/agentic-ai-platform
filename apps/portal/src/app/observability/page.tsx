"use client";

import { useEffect, useState } from "react";
import { Activity, BarChart2, AlertCircle, CheckCircle } from "lucide-react";

interface AuditEvent {
  event_type: string; user_id: string; session_id: string; created_at?: string;
}

export default function ObservabilityPage() {
  const [events, setEvents]   = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/audit/events?limit=50")
      .then(r => r.json())
      .then(d => setEvents(d.events ?? []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, []);

  const skillRuns    = events.filter(e => e.event_type === "agent.run.start").length;
  const completedRuns = events.filter(e => e.event_type === "agent.run.complete").length;
  const violations   = events.filter(e => e.event_type?.includes("violation") || e.event_type?.includes("denied")).length;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Observability</h1>
        <p className="text-gray-400 text-sm mt-1">Platform audit events and usage metrics</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[
          { label: "Agent Runs", value: skillRuns, icon: Activity, color: "bg-blue-600" },
          { label: "Completed", value: completedRuns, icon: CheckCircle, color: "bg-green-600" },
          { label: "Policy Violations", value: violations, icon: AlertCircle, color: "bg-red-600" },
        ].map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-start gap-4">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${color}`}>
              <Icon className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-gray-400 text-sm">{label}</p>
              <p className="text-white text-2xl font-bold">{value}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-800 flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-blue-400" />
          <h3 className="text-white font-semibold">Recent Audit Events</h3>
        </div>
        {loading ? (
          <div className="p-8 text-center text-gray-500">Loading events…</div>
        ) : events.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No audit events recorded yet.</div>
        ) : (
          <div className="divide-y divide-gray-800">
            {events.slice(0, 20).map((evt, i) => (
              <div key={i} className="px-5 py-3 flex items-center gap-4">
                <span className="text-xs bg-gray-800 text-gray-400 border border-gray-700 rounded px-2 py-0.5 font-mono shrink-0">
                  {evt.event_type}
                </span>
                <span className="text-gray-400 text-sm truncate">{evt.user_id}</span>
                <span className="text-gray-600 text-xs ml-auto shrink-0 font-mono">{evt.session_id?.slice(0, 8)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
