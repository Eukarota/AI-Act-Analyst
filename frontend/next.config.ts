import path from "node:path";
import type { NextConfig } from "next";

const apiOrigin = process.env.BOUSSOLE_API_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  outputFileTracingRoot: path.join(__dirname),
  async rewrites() {
    return [
      { source: "/api/assess", destination: `${apiOrigin}/assess` },
      {
        source: "/api/assess/:run_id/export.:format",
        destination: `${apiOrigin}/assess/:run_id/export.:format`,
      },
      { source: "/api/extract", destination: `${apiOrigin}/extract` },
      { source: "/api/trace/:run_id", destination: `${apiOrigin}/trace/:run_id` },
      { source: "/api/health", destination: `${apiOrigin}/health` },
      { source: "/api/ready", destination: `${apiOrigin}/ready` },
    ];
  },
};

export default nextConfig;
