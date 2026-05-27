const AGENT_CORE_URL = process.env.AGENT_CORE_URL || "http://localhost:8002";

export interface RunRequest {
  query: string;
  user_id: string;
  user_role: string;
  skill?: string;
  session_id?: string;
}

export interface RunResponse {
  answer: string;
  session_id: string;
  tool_calls_made: string[];
}

export async function runAgent(req: RunRequest): Promise<RunResponse> {
  const res = await fetch(`${AGENT_CORE_URL}/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as any).detail || `Error ${res.status}`);
  }
  return res.json();
}
