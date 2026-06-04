import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

const GOVERNANCE_URL = process.env.GOVERNANCE_URL || "http://localhost:8003";

export async function PUT(
  _req: NextRequest,
  { params }: { params: { requestId: string; action: string } }
) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.email) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { requestId, action } = params;
  if (action !== "approve" && action !== "deny") {
    return NextResponse.json({ error: "Invalid action" }, { status: 400 });
  }

  const userRes = await fetch(`${GOVERNANCE_URL}/users/by-email/${encodeURIComponent(session.user.email)}`);
  const userData = userRes.ok ? await userRes.json() : null;

  try {
    const res = await fetch(`${GOVERNANCE_URL}/a2a/requests/${requestId}/${action}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "x-user-role": userData?.role ?? "business-user",
      },
      body: JSON.stringify({ granted_by: session.user.email }),
    });
    return NextResponse.json(await res.json(), { status: res.status });
  } catch {
    return NextResponse.json({ error: "Failed to process decision" }, { status: 500 });
  }
}
