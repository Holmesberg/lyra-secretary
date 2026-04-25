/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  compress: true,
  productionBrowserSourceMaps: false,
  // Apr 25 perf fix: phones over Cloudflare Tunnel were downloading ~12MB
  // unminified dev bundles (operator was serving `next dev` over the tunnel
  // to lyraos.org). Switching to production build + these knobs targets a
  // ~500KB initial chunk. The optimizePackageImports list covers the
  // heaviest tree-shakable packages — radix UI (6), tremor charts, lucide
  // icons, date-fns, framer-motion, cmdk, sonner.
  images: {
    qualities: [75, 85, 95, 100],
  },
  experimental: {
    optimizePackageImports: [
      "@radix-ui/react-checkbox",
      "@radix-ui/react-dialog",
      "@radix-ui/react-label",
      "@radix-ui/react-radio-group",
      "@radix-ui/react-select",
      "@radix-ui/react-slot",
      "@tremor/react",
      "lucide-react",
      "date-fns",
      "motion",
      "cmdk",
      "sonner",
    ],
  },
};
export default nextConfig;
