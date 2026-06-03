import { NextResponse } from "next/server";

const GOVERNANCE_URL = process.env.GOVERNANCE_URL || "http://localhost:8003";

export async function GET() {
  try {
    const res = await fetch(`${GOVERNANCE_URL}/a2a/marketplace`, { next: { revalidate: 30 } });
    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json({ agents: [] });
  }
}
