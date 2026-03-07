import { ChromaClient } from "chromadb";

let client: ChromaClient | null = null;

export function getChromaClient(): ChromaClient {
  if (!client) {
    client = new ChromaClient({
      path: "https://api.trychroma.com:8000",
      auth: {
        provider: "token",
        credentials: process.env.CHROMA_API_KEY!,
      },
      tenant: process.env.CHROMA_TENANT!,
      database: process.env.CHROMA_DATABASE!,
    });
  }
  return client;
}

export const WORKFLOW_STEPS_COLLECTION = "workflow_steps";
export const WORKFLOW_LIBRARY_COLLECTION = "workflow_library";
