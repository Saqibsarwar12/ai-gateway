/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    serverActions: { allowedOrigins: ["*"] },
  },
  async rewrites() {
    return [
      {
        source: "/api/proxy/:path*",
        destination: "http://api:8000/api/v1/:path*",
      },
    ];
  },
};
module.exports = nextConfig;
