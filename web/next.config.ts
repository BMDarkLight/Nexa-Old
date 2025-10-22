import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: 'standalone',
  env:{
    NEXT_PUBLIC_SERVER_URL: process.env.NEXT_PUBLIC_SERVER_URL ?? "" ,  
    NEXT_PUBLIC_API_PORT: process.env.NEXT_PUBLIC_API_PORT ?? "",
    NEXT_PUBLIC_UI_PORT: process.env.NEXT_PUBLIC_UI_PORT ?? "",
  }
};

export default nextConfig;
