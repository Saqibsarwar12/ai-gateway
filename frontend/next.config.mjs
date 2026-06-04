/** @type {import('next').NextConfig} */
const nextConfig = {
  // standalone output: Next.js bundles everything needed to run with 'node server.js'
  // This is required for Clerk middleware (Edge runtime) to work on Render.
  output: 'standalone',
  reactStrictMode: true,
  images: { unoptimized: true },
  trailingSlash: false,
};
export default nextConfig;
