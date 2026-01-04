/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // =========================================================================
  // Image Optimization
  // =========================================================================
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'avatars.githubusercontent.com',
      },
      {
        protocol: 'https',
        hostname: 'github.com',
      },
    ],
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 60 * 60 * 24, // 24 hours
  },

  // =========================================================================
  // API Rewrites
  // =========================================================================
  async rewrites() {
    return [
      {
        source: '/api/rra/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ];
  },

  // =========================================================================
  // Bundle Optimization
  // =========================================================================

  // Compiler optimizations
  compiler: {
    // Remove console.log in production
    removeConsole: process.env.NODE_ENV === 'production',
  },

  // Experimental features for smaller bundles
  experimental: {
    // Optimize package imports - only import what's used
    optimizePackageImports: [
      'lucide-react',
      'date-fns',
      '@tanstack/react-query',
      'clsx',
    ],
  },

  // Webpack configuration for bundle optimization
  webpack: (config, { isServer, dev }) => {
    // Fix for pino-pretty and async-storage warnings from wagmi/rainbowkit
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        'pino-pretty': false,
        '@react-native-async-storage/async-storage': false,
      };
    }

    // Only apply optimizations in production
    if (!dev && !isServer) {
      // Split chunks more aggressively
      config.optimization.splitChunks = {
        chunks: 'all',
        minSize: 20000,
        maxSize: 244000, // ~244KB per chunk
        cacheGroups: {
          // Separate Web3 libraries (wagmi, viem, rainbowkit)
          web3: {
            test: /[\\/]node_modules[\\/](wagmi|viem|@rainbow-me|@walletconnect)[\\/]/,
            name: 'web3',
            priority: 30,
            reuseExistingChunk: true,
          },
          // Separate React Query
          query: {
            test: /[\\/]node_modules[\\/](@tanstack)[\\/]/,
            name: 'react-query',
            priority: 25,
            reuseExistingChunk: true,
          },
          // Separate UI utilities
          ui: {
            test: /[\\/]node_modules[\\/](lucide-react|clsx|tailwind-merge|date-fns)[\\/]/,
            name: 'ui-utils',
            priority: 20,
            reuseExistingChunk: true,
          },
          // Default vendor chunk
          vendor: {
            test: /[\\/]node_modules[\\/]/,
            name: 'vendor',
            priority: 10,
            reuseExistingChunk: true,
          },
        },
      };

      // Tree shaking improvements
      config.optimization.usedExports = true;
      config.optimization.sideEffects = true;
    }

    return config;
  },

  // =========================================================================
  // Headers for caching
  // =========================================================================
  async headers() {
    return [
      {
        // Security headers for wallet connections (RainbowKit/WalletConnect)
        source: '/:path*',
        headers: [
          {
            key: 'Cross-Origin-Opener-Policy',
            value: 'same-origin-allow-popups',
          },
          {
            key: 'Cross-Origin-Embedder-Policy',
            value: 'credentialless',
          },
        ],
      },
      {
        // Cache static assets aggressively
        source: '/_next/static/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        // Cache images
        source: '/images/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=86400, stale-while-revalidate=604800',
          },
        ],
      },
    ];
  },

  // =========================================================================
  // Output Configuration
  // =========================================================================

  // Generate smaller output
  output: 'standalone',

  // Reduce source map size in production
  productionBrowserSourceMaps: false,

  // Compress responses
  compress: true,
};

module.exports = nextConfig;
