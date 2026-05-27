/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  // Do NOT use `env:` here — that bakes values at build time.
  // Server-side env vars (AGENT_CORE_URL, GOVERNANCE_URL) are read at runtime
  // from the container environment set by docker-compose.
};

export default nextConfig;
