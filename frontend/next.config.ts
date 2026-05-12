import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // @ts-ignore - Next.js internal dev option
  allowedDevOrigins: ["46.202.155.132", "192.168.56.1", "localhost:3000"],
  // To silence the Turbopack root warning
  serverExternalPackages: [], 
};

export default nextConfig;
