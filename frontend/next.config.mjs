/** @type {import('next').NextConfig} */
const nextConfig = {
  // NOTE: 'output: export' is removed because Clerk middleware requires
  // Next.js server-side rendering (Edge runtime). The frontend is now
  // served by Next.js standalone server, not as a static export.
  // The Dockerfile builds and runs 'next start' instead of serving static files.
  reactStrictMode: true,
  images: { unoptimized: true },
  trailingSlash: false,
  // Allow Clerk to work in the Edge runtime
  experimental: {},
};
export default nextConfig;
