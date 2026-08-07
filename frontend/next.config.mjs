/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: { ignoreDuringBuilds: true },
  reactStrictMode: true,
  images: { unoptimized: true },
  trailingSlash: true,
  output: 'export',
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || '',
  },
};
export default nextConfig;
