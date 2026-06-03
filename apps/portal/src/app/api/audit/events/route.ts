import { NextRequest, NextResponse } from "next/server";
const GOVERNANCE_URL = process.env.GOVERNANCE_URL || "http://localhost:8003";
export async function GET(req: NextRequest) {
  const limit = req.nextUrl.searchParams.get("limit") ?? "50";
  try {
    const res = await fetch(`${GOVERNANCE_URL}/audit/events?limit=${limit}`);
    return NextResponse.json(await res.json());
  } catch { return NextResponse.json({ events: [] }); }
}
