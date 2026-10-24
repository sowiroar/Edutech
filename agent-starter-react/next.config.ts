import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone',
  outputFileTracingRoot: process.cwd(),
  async headers() {
    return [
      {
        // Only immutable, content-addressed models; manifests/backgrounds can change.
        source:
          '/avatars/:character(lira|nexo|elian|noa|nova|atlas)/:file([a-z]+-[a-f0-9]{64}\\.glb)',
        headers: [{ key: 'Cache-Control', value: 'public, max-age=31536000, immutable' }],
      },
    ];
  },
  eslint: {
    ignoreDuringBuilds: true,
  },
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
