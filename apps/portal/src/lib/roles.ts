// Role definitions and navigation configuration for the portal.
// Must stay in sync with governance/policy/engine.py ROLE_LEVELS.

export type UserRole =
  | "ai-architect"
  | "ai-devops"
  | "app-devops"
  | "business-ops"
  | "ba"
  | "business-user";

export interface NavItem {
  label: string;
  href: string;
  icon: string; // lucide icon name
  badge?: string;
}

export interface UserProfile {
  email: string;
  role: UserRole;
  team_id: string | null;
  team_name: string | null;
  display_name: string | null;
  registered: boolean;
}

// ── Navigation items per role ─────────────────────────────────────────────────

const COMMON_NAV: NavItem[] = [
  { label: "Dashboard",        href: "/",            icon: "LayoutDashboard" },
  { label: "Chat",             href: "/chat",         icon: "MessageSquare" },
  { label: "Marketplace",      href: "/marketplace",  icon: "Store" },
];

const NAV_BY_ROLE: Record<UserRole, NavItem[]> = {
  "ai-architect": [
    ...COMMON_NAV,
    { label: "All Agents",     href: "/agents",        icon: "Bot" },
    { label: "Observability",  href: "/observability", icon: "BarChart2" },
    { label: "Cost & Usage",   href: "/costs",         icon: "DollarSign" },
    { label: "Audit Logs",     href: "/audit",         icon: "FileSearch" },
  ],
  "ai-devops": [
    ...COMMON_NAV,
    { label: "All Agents",     href: "/agents",        icon: "Bot" },
    { label: "Platform Admin", href: "/admin",         icon: "Shield" },
    { label: "Observability",  href: "/observability", icon: "BarChart2" },
    { label: "Cost & Usage",   href: "/costs",         icon: "DollarSign" },
    { label: "Model Management", href: "/models",      icon: "Cpu" },
    { label: "MCP Hub",        href: "/mcp",           icon: "Plug" },
  ],
  "app-devops": [
    ...COMMON_NAV,
    { label: "My Agents",      href: "/agents",        icon: "Bot" },
    { label: "Observability",  href: "/observability", icon: "BarChart2" },
  ],
  "business-ops": [
    ...COMMON_NAV,
    { label: "Workflows",      href: "/workflows",     icon: "GitBranch" },
  ],
  "ba": [
    ...COMMON_NAV,
    { label: "Requirements",   href: "/requirements",  icon: "FileText" },
  ],
  "business-user": [
    ...COMMON_NAV,
  ],
};

export function getNavItems(role: UserRole): NavItem[] {
  return NAV_BY_ROLE[role] ?? COMMON_NAV;
}

// ── Role display helpers ───────────────────────────────────────────────────────

export const ROLE_LABELS: Record<UserRole, string> = {
  "ai-architect":  "AI Architect",
  "ai-devops":     "AI DevOps",
  "app-devops":    "App DevOps",
  "business-ops":  "Business Ops",
  "ba":            "Business Analyst",
  "business-user": "Business User",
};

export const ROLE_COLORS: Record<UserRole, string> = {
  "ai-architect":  "bg-purple-900/50 text-purple-300 border border-purple-700",
  "ai-devops":     "bg-blue-900/50 text-blue-300 border border-blue-700",
  "app-devops":    "bg-cyan-900/50 text-cyan-300 border border-cyan-700",
  "business-ops":  "bg-amber-900/50 text-amber-300 border border-amber-700",
  "ba":            "bg-green-900/50 text-green-300 border border-green-700",
  "business-user": "bg-gray-800 text-gray-300 border border-gray-700",
};

export function getRoleLabel(role: UserRole): string {
  return ROLE_LABELS[role] ?? role;
}

export function canManagePlatform(role: UserRole): boolean {
  return role === "ai-devops";
}

export function canViewAll(role: UserRole): boolean {
  return role === "ai-devops" || role === "ai-architect";
}

export function canManageAgents(role: UserRole): boolean {
  return ["ai-devops", "ai-architect", "app-devops"].includes(role);
}
