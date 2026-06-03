"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Bot, MessageSquare, Store, Shield, BarChart2,
  Activity, CheckCircle, AlertCircle, Clock,
  Users, Cpu, GitBranch, ArrowRight,
} from "lucide-react";
import { useUser } from "@/components/user-context";
import { getRoleLabel, type UserRole } from "@/lib/roles";
import { cn } from "@/lib/cn";

interface ServiceStatus { name: string; status: "ok" | "error" | "unknown"; }

function StatCard({ label, value, icon: Icon, color, href }: {
  label: string; value: string | number; icon: React.ElementType; color: string; href?: string;
}) {
  const content = (
    <div className={cn("bg-gray-900 border border-gray-800 rounded-xl p-5 flex items-start gap-4", href && "hover:border-gray-700 transition-colors cursor-pointer")}>
      <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center shrink-0", color)}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div>
        <p className="text-gray-400 text-sm">{label}</p>
        <p className="text-white text-2xl font-bold mt-0.5">{value}</p>
      </div>
    </div>
  );
  return href ? <Link href={href}>{content}</Link> : content;
}

function ServiceBadge({ name, status }: ServiceStatus) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
      <span className="text-gray-300 text-sm">{name}</span>
      {status === "ok" ? (
        <span className="flex items-center gap-1 text-green-400 text-xs"><CheckCircle className="w-3 h-3" /> Healthy</span>
      ) : status === "error" ? (
        <span className="flex items-center gap-1 text-red-400 text-xs"><AlertCircle className="w-3 h-3" /> Error</span>
      ) : (
        <span className="flex items-center gap-1 text-gray-500 text-xs"><Clock className="w-3 h-3" /> Checking…</span>
      )}
    </div>
  );
}

function QuickAction({ label, description, href, icon: Icon, color }: {
  label: string; description: string; href: string; icon: React.ElementType; color: string;
}) {
  return (
    <Link href={href} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center gap-4 hover:border-gray-700 transition-colors group">
      <div className={cn("w-10 h-10 rounded-lg flex items-center justify-center shrink-0", color)}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-white text-sm font-medium">{label}</p>
        <p className="text-gray-500 text-xs truncate">{description}</p>
      </div>
      <ArrowRight className="w-4 h-4 text-gray-600 group-hover:text-gray-400 transition-colors shrink-0" />
    </Link>
  );
}

function PlatformDashboard({ services }: { services: ServiceStatus[] }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Services Healthy" value={`${services.filter(s => s.status === "ok").length}/${services.length}`} icon={Activity} color="bg-blue-600" />
        <StatCard label="Teams" value="3" icon={Users} color="bg-purple-600" href="/admin" />
        <StatCard label="Agents" value="–" icon={Bot} color="bg-cyan-600" href="/agents" />
        <StatCard label="Models" value="4" icon={Cpu} color="bg-amber-600" href="/models" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4 flex items-center gap-2"><Activity className="w-4 h-4 text-blue-400" /> Platform Health</h3>
          {services.map(s => <ServiceBadge key={s.name} {...s} />)}
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <QuickAction label="Register Team" description="Onboard a new application team" href="/admin" icon={Users} color="bg-purple-600" />
            <QuickAction label="Assign User Role" description="Set roles for platform users" href="/admin" icon={Shield} color="bg-blue-600" />
            <QuickAction label="View Observability" description="Platform metrics and traces" href="/observability" icon={BarChart2} color="bg-amber-600" />
          </div>
        </div>
      </div>
    </div>
  );
}

function AppDevOpsDashboard() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label="My Agents" value="–" icon={Bot} color="bg-cyan-600" href="/agents" />
        <StatCard label="Marketplace" value="–" icon={Store} color="bg-purple-600" href="/marketplace" />
        <StatCard label="Chat Sessions" value="–" icon={MessageSquare} color="bg-blue-600" href="/chat" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <QuickAction label="Register Agent" description="Deploy a new AI agent for your team" href="/agents" icon={Bot} color="bg-cyan-600" />
            <QuickAction label="Browse Marketplace" description="Discover agents from other teams" href="/marketplace" icon={Store} color="bg-purple-600" />
            <QuickAction label="Start Chat" description="Talk to an agent" href="/chat" icon={MessageSquare} color="bg-blue-600" />
          </div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4">Getting Started</h3>
          <ol className="space-y-3 text-sm text-gray-400">
            {["Register your agent in My Agents", "Configure skills and model", "Deploy via CI/CD pipeline", "Publish to Marketplace for A2A"].map((s, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center shrink-0 mt-0.5">{i+1}</span>
                {s}
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}

function BusinessOpsDashboard() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard label="Active Workflows" value="–" icon={GitBranch} color="bg-amber-600" href="/workflows" />
        <StatCard label="Pending" value="–" icon={Clock} color="bg-red-600" href="/workflows" />
        <StatCard label="Completed Today" value="–" icon={CheckCircle} color="bg-green-600" href="/workflows" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <QuickAction label="New Workflow" description="Automate a human process with AI" href="/workflows" icon={GitBranch} color="bg-amber-600" />
            <QuickAction label="Chat with Agent" description="Get AI assistance" href="/chat" icon={MessageSquare} color="bg-blue-600" />
            <QuickAction label="Browse Agents" description="Find agents for workflows" href="/marketplace" icon={Store} color="bg-purple-600" />
          </div>
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h3 className="text-white font-semibold mb-4">Supported Workflow Types</h3>
          <div className="space-y-2">
            {["Document review & approval", "Data extraction & reporting", "Customer service / chatbot", "Compliance checks"].map(w => (
              <div key={w} className="flex items-center gap-2 text-sm text-gray-400">
                <CheckCircle className="w-3.5 h-3.5 text-green-500 shrink-0" />{w}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function DefaultDashboard() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <QuickAction label="Start a Chat" description="Ask the AI assistant anything" href="/chat" icon={MessageSquare} color="bg-blue-600" />
        <QuickAction label="Browse Agents" description="Find specialist AI agents" href="/marketplace" icon={Store} color="bg-purple-600" />
        <QuickAction label="Recent Sessions" description="Continue a previous conversation" href="/chat" icon={Clock} color="bg-gray-700" />
      </div>
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
        <Bot className="w-12 h-12 text-blue-400 mx-auto mb-3" />
        <h3 className="text-white font-semibold mb-2">What can I help you with?</h3>
        <p className="text-gray-400 text-sm mb-4 max-w-md mx-auto">Use the AI chat to get answers, review documents, check compliance, or automate tasks.</p>
        <Link href="/chat" className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors">
          <MessageSquare className="w-4 h-4" /> Open Chat
        </Link>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { profile, loading } = useUser();
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: "agent-core", status: "unknown" },
    { name: "rag-service", status: "unknown" },
    { name: "governance", status: "unknown" },
    { name: "llm-gateway", status: "unknown" },
  ]);

  useEffect(() => {
    const names = ["agent-core", "rag-service", "governance", "llm-gateway"];
    Promise.allSettled(names.map(async name => {
      const r = await fetch(`/api/health/${name}`);
      return { name, status: r.ok ? "ok" : "error" } as ServiceStatus;
    })).then(results => {
      setServices(results.map((r, i) => r.status === "fulfilled" ? r.value : { name: names[i], status: "error" }));
    });
  }, []);

  const role = (profile?.role ?? "business-user") as UserRole;

  if (loading) return <div className="flex items-center justify-center min-h-[60vh]"><p className="text-gray-500">Loading…</p></div>;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">
          Welcome back{profile?.display_name ? `, ${profile.display_name.split(" ")[0]}` : ""}
        </h1>
        <p className="text-gray-400 text-sm mt-1">
          {getRoleLabel(role)}{profile?.team_name ? ` · ${profile.team_name}` : ""}
        </p>
      </div>
      {(role === "ai-devops" || role === "ai-architect") && <PlatformDashboard services={services} />}
      {role === "app-devops" && <AppDevOpsDashboard />}
      {role === "business-ops" && <BusinessOpsDashboard />}
      {(role === "business-user" || role === "ba") && <DefaultDashboard />}
    </div>
  );
}
