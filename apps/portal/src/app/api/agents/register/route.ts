import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

const GOVERNANCE_URL = process.env.GOVERNANCE_URL || "http://localhost:8003";

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const userRes = await fetch(`${GOVERNANCE_URL}/users/by-email/${encodeURIComponent(session.user.email)}`);
  const userData = userRes.ok ? await userRes.json() : null;

  const body = await req.json();
  try {
    const res = await fetch(`${GOVERNANCE_URL}/a2a/agents`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-user-role": userData?.role ?? "business-user",
      },
      body: JSON.stringify(body),
    });
    return NextResponse.json(await res.json(), { status: res.status });
  } catch {
    return NextResponse.json({ error: "Failed to register agent" }, { status: 500 });
  }
}
