"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import {
  LayoutDashboard, MessageSquare, Store, Bot, Shield,
  BarChart2, DollarSign, FileSearch, Cpu, Plug,
  GitBranch, FileText, LogOut, ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { getNavItems, getRoleLabel, ROLE_COLORS, type UserRole } from "@/lib/roles";
import { useUser } from "./user-context";

const ICON_MAP: Record<string, React.ElementType> = {
  LayoutDashboard, MessageSquare, Store, Bot, Shield,
  BarChart2, DollarSign, FileSearch, Cpu, Plug,
  GitBranch, FileText,
};

export function Sidebar() {
  const pathname       = usePathname();
  const { profile, loading } = useUser();

  const role     = (profile?.role ?? "business-user") as UserRole;
  const navItems = getNavItems(role);

  return (
    <aside className="w-60 min-h-screen bg-gray-900 border-r border-gray-800 flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-sm font-bold text-white shrink-0">
            AI
          </div>
          <div className="min-w-0">
            <p className="text-white font-semibold text-sm leading-tight truncate">Agentic AI</p>
            <p className="text-gray-500 text-xs truncate">Platform</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon    = ICON_MAP[item.icon] ?? LayoutDashboard;
          const active  = pathname === item.href ||
                          (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                active
                  ? "bg-blue-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-gray-800"
              )}
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span className="flex-1 truncate">{item.label}</span>
              {item.badge && (
                <span className="text-xs bg-blue-500 text-white rounded-full px-1.5 py-0.5">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* User info + sign out */}
      <div className="px-3 py-4 border-t border-gray-800 space-y-3">
        {!loading && profile && (
          <>
            <div className="flex items-center gap-3 px-2">
              {profile.image ? (
                <img src={profile.image} alt="" className="w-7 h-7 rounded-full shrink-0" />
              ) : (
                <div className="w-7 h-7 rounded-full bg-gray-700 flex items-center justify-center text-xs text-gray-300 shrink-0">
                  {profile.email[0]?.toUpperCase()}
                </div>
              )}
              <div className="min-w-0 flex-1">
                <p className="text-white text-xs font-medium truncate">
                  {profile.display_name ?? profile.email}
                </p>
                <p className="text-gray-500 text-xs truncate">{profile.email}</p>
              </div>
            </div>
            <span className={cn("inline-block text-xs rounded-full px-2 py-0.5 ml-2", ROLE_COLORS[role])}>
              {getRoleLabel(role)}
            </span>
          </>
        )}
        <button
          onClick={() => signOut({ callbackUrl: "/auth/signin" })}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  );
}
