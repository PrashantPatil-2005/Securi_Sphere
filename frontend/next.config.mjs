/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    optimizePackageImports: ["lucide-react", "recharts", "framer-motion"],
  },
  async rewrites() {
    // In Docker, the frontend container must reach the backend by service name, not localhost.
    const raw =
      process.env.BACKEND_INTERNAL_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://localhost:8000";

    // Normalize the backend URL: strip accidental whitespace/tabs and trailing slashes.
    const api = String(raw).trim().replace(/\/+$/, "");

    // Validate so malformed configuration fails loudly with a clear message instead of
    // producing an invalid rewrite destination (e.g. one starting with a tab).
    if (!/^https?:\/\//i.test(api)) {
      throw new Error(
        `Invalid backend URL "${raw}". NEXT_PUBLIC_API_URL/BACKEND_INTERNAL_URL must be an ` +
          `absolute URL starting with http:// or https:// (got trimmed value: "${api}")`,
      );
    }

    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains; preload" },
          { key: "X-XSS-Protection", value: "1; mode=block" },
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
        ],
      },
    ];
  },
};

export default nextConfig;
