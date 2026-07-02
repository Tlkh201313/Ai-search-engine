/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    // Optional dev convenience: proxy /api-proxy/* to the backend so the browser
    // can hit a same-origin path. The app uses NEXT_PUBLIC_API_URL directly by
    // default; this is only a fallback.
    const api = process.env.API_INTERNAL_URL;
    if (!api) return [];
    return [{ source: '/api-proxy/:path*', destination: `${api}/:path*` }];
  },
};

export default nextConfig;
