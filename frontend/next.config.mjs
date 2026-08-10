/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: { ignoreDuringBuilds: true },
  reactStrictMode: true,
  images: { unoptimized: true },
  trailingSlash: false,
  output: process.env.NEXT_OUTPUT || 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'https://saki-gateway.indevs.in',
  },
};
export default nextConfig;
