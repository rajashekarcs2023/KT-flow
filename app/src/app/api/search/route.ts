import { NextRequest, NextResponse } from "next/server";
import { getChromaClient, WORKFLOW_STEPS_COLLECTION } from "@/lib/chroma";

export async function POST(req: NextRequest) {
  try {
    const { query, nResults = 5 } = await req.json();

    if (!query) {
      return NextResponse.json({ error: "Missing query" }, { status: 400 });
    }

    const client = getChromaClient();
    const collection = await client.getCollection({ name: WORKFLOW_STEPS_COLLECTION });

    const results = await collection.query({
      queryTexts: [query],
      nResults: Math.min(nResults, 10),
    });

    const hits = (results.documents?.[0] || []).map((doc, i) => ({
      document: doc,
      metadata: results.metadatas?.[0]?.[i] || {},
      distance: results.distances?.[0]?.[i] || 0,
      id: results.ids?.[0]?.[i] || "",
    }));

    return NextResponse.json({ results: hits });
  } catch (error) {
    console.error("Search error:", error);
    return NextResponse.json(
      { error: "Search failed", detail: String(error) },
      { status: 500 }
    );
  }
}
