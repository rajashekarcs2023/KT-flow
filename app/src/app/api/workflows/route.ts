import { NextResponse } from "next/server";
import { getChromaClient, WORKFLOW_LIBRARY_COLLECTION } from "@/lib/chroma";

export async function GET() {
  try {
    const client = getChromaClient();
    const collection = await client.getCollection({ name: WORKFLOW_LIBRARY_COLLECTION });

    const all = await collection.get();

    const workflows = (all.ids || []).map((id, i) => ({
      id,
      title: all.metadatas?.[i]?.title || "",
      summary: all.metadatas?.[i]?.summary || "",
      steps_count: all.metadatas?.[i]?.steps_count || 0,
      duration: all.metadatas?.[i]?.duration || 0,
      tools: all.metadatas?.[i]?.tools || "",
      real: all.metadatas?.[i]?.real === "True",
    }));

    return NextResponse.json({ workflows });
  } catch (error) {
    console.error("Workflows error:", error);
    return NextResponse.json({ workflows: [] });
  }
}
