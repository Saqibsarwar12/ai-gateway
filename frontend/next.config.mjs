/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  images: { unoptimized: true },
  trailingSlash: false,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '',
  },
  async rewrites() {
    return [
      {
        source: '/v1/:path*',
        destination: 'https://ai-gateway-7dkh.onrender.com/v1/:path*',
      },
      {
        source: '/v2/:path*',
        destination: 'https://ai-gateway-7dkh.onrender.com/v2/:path*',
      },
      {
        source: '/v3/:path*',
        destination: 'https://ai-gateway-7dkh.onrender.com/v3/:path*',
      },
      {
        source: '/admin/:path*',
        destination: 'https://ai-gateway-7dkh.onrender.com/admin/:path*',
      },
      {
        source: '/health',
        destination: 'https://ai-gateway-7dkh.onrender.com/health',
      },
      {
        source: '/openapi.json',
        destination: 'https://ai-gateway-7dkh.onrender.com/openapi.json',
      },
    ];
  },
};
export default nextConfig;
