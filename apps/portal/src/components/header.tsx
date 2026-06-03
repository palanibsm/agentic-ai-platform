"use client";
import { useSession, signOut } from "next-auth/react";

export function Header() {
  const { data: session } = useSession();

  return (
    <header className="border-b border-gray-800 bg-gray-900 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-sm font-bold text-white">
          AI
        </div>
        <span className="text-white font-semibold text-sm">Agentic AI Platform</span>
      </div>

      {session?.user && (
        <div className="flex items-center gap-3">
          {session.user.image && (
            <img
              src={session.user.image}
              alt={session.user.name ?? "User"}
              className="w-7 h-7 rounded-full"
            />
          )}
          <span className="text-gray-300 text-sm">{session.user.email}</span>
          <button
            onClick={() => signOut({ callbackUrl: "/auth/signin" })}
            className="text-xs text-gray-400 hover:text-white border border-gray-700 rounded px-2 py-1 transition-colors"
          >
            Sign out
          </button>
        </div>
      )}
    </header>
  );
}
