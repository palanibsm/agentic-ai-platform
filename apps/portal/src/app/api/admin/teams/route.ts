import { NextResponse } from "next/server";
const GOVERNANCE_URL = process.env.GOVERNANCE_URL || "http://localhost:8003";
export async function GET() {
  try {
    const res = await fetch(`${GOVERNANCE_URL}/teams`, { next: { revalidate: 30 } });
    return NextResponse.json(await res.json());
  } catch { return NextResponse.json([]); }
}
