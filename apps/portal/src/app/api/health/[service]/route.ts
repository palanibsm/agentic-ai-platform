import { NextRequest, NextResponse } from "next/server";

const SERVICE_URLS: Record<string, string> = {
  "agent-core":  process.env.AGENT_CORE_URL  || "http://localhost:8002",
  "rag-service": process.env.RAG_SERVICE_URL || "http://localhost:8001",
  "governance":  process.env.GOVERNANCE_URL  || "http://localhost:8003",
  "llm-gateway": process.env.LLM_GATEWAY_URL || "http://localhost:4000",
};

export async function GET(req: NextRequest, { params }: { params: { service: string } }) {
  const url = SERVICE_URLS[params.service];
  if (!url) return NextResponse.json({ error: "Unknown service" }, { status: 404 });
  try {
    const res = await fetch(`${url}/health`, { signal: AbortSignal.timeout(5000) });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json({ status: "error" }, { status: 503 });
  }
}
