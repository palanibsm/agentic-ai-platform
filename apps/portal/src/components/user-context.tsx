"use client";

import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useSession } from "next-auth/react";
import { type UserProfile, type UserRole } from "@/lib/roles";

interface UserContextType {
  profile: UserProfile | null;
  loading: boolean;
}

const UserContext = createContext<UserContextType>({ profile: null, loading: true });

export function UserContextProvider({ children }: { children: ReactNode }) {
  const { data: session, status } = useSession();
  const [profile, setProfile]    = useState<UserProfile | null>(null);
  const [loading, setLoading]    = useState(true);

  useEffect(() => {
    if (status === "loading") return;
    if (!session) { setLoading(false); return; }

    fetch("/api/user")
      .then((r) => r.json())
      .then((data) => setProfile(data as UserProfile))
      .catch(() => setProfile({
        email: session.user?.email ?? "",
        role: "business-user" as UserRole,
        team_id: null,
        team_name: null,
        display_name: session.user?.name ?? null,
        registered: false,
      }))
      .finally(() => setLoading(false));
  }, [session, status]);

  return (
    <UserContext.Provider value={{ profile, loading }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  return useContext(UserContext);
}
