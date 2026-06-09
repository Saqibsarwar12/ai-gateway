/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  images: { unoptimized: true },
  trailingSlash: false,
  async rewrites() {
    const API = "https://ai-gateway-7dkh.onrender.com";
    return {
      beforeFiles: [
        // Auth endpoints
        { source: "/admin/auth/:path*", destination: `${API}/admin/auth/:path*` },
      ],
    };
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '',
  },
};
export default nextConfig;
