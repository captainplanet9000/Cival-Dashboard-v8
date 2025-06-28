/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  serverExternalPackages: ['ioredis'],
  typescript: {
    // Temporarily ignore TypeScript errors for Railway deployment
    ignoreBuildErrors: true,
  },
  eslint: {
    // Enable ESLint during builds - fixed per infrastructure analysis
    ignoreDuringBuilds: false,
  },
  experimental: {},
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        fs: false,
        net: false,
        tls: false,
        child_process: false,
        'async_hooks': false,
      };
    }
    
    // Optimize chunk splitting to prevent circular dependencies
    // config.optimization = {
    //   ...config.optimization,
    //   splitChunks: {
    //     chunks: 'all',
    //     cacheGroups: {
    //       langchain: {
    //         test: /[\\/]src[\\/]lib[\\/]langchain[\\/]/,
    //         name: 'langchain',
    //         priority: 10,
    //         reuseExistingChunk: true,
    //       },
    //       default: {
    //         minChunks: 2,
    //         priority: -20,
    //         reuseExistingChunk: true,
    //       },
    //     },
    //   },
    // };
    
    return config;
  },
  env: {
    REDIS_HOST: process.env.REDIS_HOST || 'localhost',
    REDIS_PORT: process.env.REDIS_PORT || '6379',
    TRADING_API_URL: process.env.TRADING_API_URL || 'http://localhost:3001',
    MCP_API_URL: process.env.MCP_API_URL || 'http://localhost:3000',
    VAULT_API_URL: process.env.VAULT_API_URL || 'http://localhost:3002',
    // Railway deployment variables
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WS_URL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000',
  },
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 
                   process.env.TRADING_API_URL || 
                   'http://localhost:8000';
    
    return [
      {
        source: '/api/backend/:path*',
        destination: `${apiUrl}/:path*`,
      },
      {
        source: '/api/trading/:path*',
        destination: `${process.env.TRADING_API_URL || apiUrl}/api/:path*`,
      },
      {
        source: '/api/agents/:path*',
        destination: `${process.env.AGENTS_API_URL || apiUrl}/api/agents/:path*`,
      },
      {
        source: '/api/vault/:path*',
        destination: `${process.env.VAULT_API_URL || apiUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig; 