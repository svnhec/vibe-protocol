/** @type {import('next').NextConfig} */
const nextConfig = {
  // Ensure we can export if needed, though mostly using standard build
  reactStrictMode: true,
  images: {
    domains: ['images.unsplash.com', 'pbs.twimg.com'], 
  },
};

module.exports = nextConfig;

