/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  images: { unoptimized: true },
  trailingSlash: false,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://ai-gateway-7dkh.onrender.com',
  },
};
export default nextConfig;
