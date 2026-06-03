// GET /api/user — resolves the current user's role and team from governance.
// Called by the portal on load to determine navigation and permissions.

import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

const GOVERNANCE_URL = process.env.GOVERNANCE_URL || "http://localhost:8003";

export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) {
    return NextResponse.json({ error: "Unauthenticated" }, { status: 401 });
  }

  try {
    const res = await fetch(
      `${GOVERNANCE_URL}/users/by-email/${encodeURIComponent(session.user.email)}`,
      { next: { revalidate: 60 } } // cache for 60s
    );
    const data = await res.json();
    return NextResponse.json({
      email:        session.user.email,
      name:         session.user.name,
      image:        session.user.image,
      role:         data.role ?? "business-user",
      team_id:      data.team_id ?? null,
      team_name:    data.team_name ?? null,
      registered:   data.role !== undefined,
    });
  } catch {
    // Governance unreachable — return minimum role
    return NextResponse.json({
      email:      session.user.email,
      name:       session.user.name,
      image:      session.user.image,
      role:       "business-user",
      team_id:    null,
      team_name:  null,
      registered: false,
    });
  }
}
