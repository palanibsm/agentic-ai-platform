import { NextRequest, NextResponse } from "next/server";

const MEMORY_URL = process.env.MEMORY_SERVICE_URL || "";

export async function GET(
  _req: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  if (!MEMORY_URL) return NextResponse.json({ messages: [] });
  try {
    const res = await fetch(`${MEMORY_URL}/session/${params.sessionId}`);
    return NextResponse.json(await res.json());
  } catch {
    return NextResponse.json({ messages: [] });
  }
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  if (!MEMORY_URL) return new NextResponse(null, { status: 204 });
  try {
    await fetch(`${MEMORY_URL}/session/${params.sessionId}`, { method: "DELETE" });
  } catch { /* ignore */ }
  return new NextResponse(null, { status: 204 });
}
