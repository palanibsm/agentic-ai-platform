import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

const GOVERNANCE_URL = process.env.GOVERNANCE_URL || "http://localhost:8003";

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const userRes = await fetch(`${GOVERNANCE_URL}/users/by-email/${encodeURIComponent(session.user.email)}`);
  const userData = userRes.ok ? await userRes.json() : null;

  try {
    const res = await fetch(`${GOVERNANCE_URL}/a2a/requests/pending`, {
      headers: { "x-user-role": userData?.role ?? "business-user" },
    });
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ requests: [] });
  }
}
