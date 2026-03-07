import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  serverExternalPackages: [
    "chromadb",
    "@chroma-core/default-embed",
    "@chroma-core/ai-embeddings-common",
    "livekit-server-sdk",
  ],
};

export default nextConfig;
