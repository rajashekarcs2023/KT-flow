import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI } from "@google/genai";
import { readFileSync, existsSync } from "fs";
import { join } from "path";
import { getChromaClient, WORKFLOW_STEPS_COLLECTION } from "@/lib/chroma";

const ai = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY! });
const FRAMES_DIR = join(process.cwd(), "..", "playbook_data", "frames");

// Retrieve relevant steps from Chroma Cloud via semantic search
async function retrieveContext(query: string, nResults = 6) {
  try {
    const client = getChromaClient();
    const collection = await client.getCollection({ name: WORKFLOW_STEPS_COLLECTION });
    const results = await collection.query({ queryTexts: [query], nResults });
    return (results.documents?.[0] || []).map((doc, i) => ({
      document: doc,
      metadata: results.metadatas?.[0]?.[i] || {},
      distance: results.distances?.[0]?.[i] || 0,
    }));
  } catch (e) {
    console.error("ChromaDB retrieval failed, falling back:", e);
    return null;
  }
}

export async function POST(req: NextRequest) {
  try {
    const { message, playbook, selectedStepId, userScreenshot } = await req.json();

    if (!message || !playbook) {
      return NextResponse.json({ error: "Missing message or playbook" }, { status: 400 });
    }

    // Use ChromaDB semantic search to find relevant steps
    const chromaResults = await retrieveContext(message);
    const relevantStepIds = new Set<number>();

    let contextBlock = "";
    if (chromaResults && chromaResults.length > 0) {
      // Collect step IDs from ChromaDB results
      for (const r of chromaResults) {
        const sid = Number(r.metadata?.step_id);
        if (sid > 0) relevantStepIds.add(sid);
      }
      // Always include selected step and neighbors
      if (selectedStepId) {
        relevantStepIds.add(selectedStepId);
        relevantStepIds.add(selectedStepId - 1);
        relevantStepIds.add(selectedStepId + 1);
      }

      // Build context from ChromaDB results + full step data for matched steps
      const matchedSteps = playbook.steps.filter((s: any) => relevantStepIds.has(s.step_id));
      contextBlock = `RETRIEVED CONTEXT (via Chroma Cloud semantic search — most relevant to the question):
${chromaResults.map((r) => r.document).join("\n\n")}

FULL STEP DETAILS FOR MATCHED STEPS:
${matchedSteps
  .map(
    (s: any) =>
      `Step ${s.step_id}: ${s.title}
  Summary: ${s.summary}
  Type: ${s.step_type}
  Commands: ${s.commands?.join(", ") || "none"}
  Files: ${s.files_modified?.join(", ") || "none"}
  Config changes: ${s.config_changes?.join(", ") || "none"}
  Timestamp: ${s.timestamp_start} - ${s.timestamp_end}
  Verification: ${s.verification || "none"}
  Transcript: "${s.transcript_snippet || ""}"
  What's on screen: ${s.what_is_on_screen || "unknown"}
  Tool: ${s.tool_context || "unknown"}`
  )
  .join("\n\n")}`;
    } else {
      // Fallback: send all steps if ChromaDB unavailable
      contextBlock = `ALL STEPS:
${playbook.steps
  .map(
    (s: any) =>
      `Step ${s.step_id}: ${s.title} — ${s.summary} [${s.timestamp_start}-${s.timestamp_end}] Commands: ${s.commands?.join(", ") || "none"}`
  )
  .join("\n")}`;
    }

    const systemPrompt = `You are a workflow assistant with VISUAL understanding, powered by Chroma Cloud for semantic memory retrieval. You help users understand and reproduce a workflow extracted from a screen recording.

You can SEE the actual screenshots from the workflow. When images are provided, reference what you see in them to give precise, grounded answers.

WORKFLOW: ${playbook.workflow_title}
SUMMARY: ${playbook.workflow_summary}
TOTAL STEPS: ${playbook.steps.length}

${contextBlock}

ALL COMMANDS: ${playbook.all_commands?.join("\n") || "none"}

RULES:
- Answer based on the retrieved workflow data AND the images you can see.
- Always reference the specific step number and timestamp.
- If shown a user's screenshot for "Where Am I?", visually compare it to the workflow frames and identify the closest matching step. Tell them exactly where they are and what to do next.
- Keep answers concise and actionable. Engineers want direct answers.
- When you see a frame, describe what you observe to show you understand the visual context.
- When referencing a step, always include its step_id number.`;

    // Build multimodal content parts
    const parts: any[] = [{ text: systemPrompt }];

    // Include frames for relevant steps from ChromaDB results
    const frameStepIds = relevantStepIds.size > 0
      ? [...relevantStepIds]
      : selectedStepId ? [selectedStepId - 1, selectedStepId, selectedStepId + 1] : [];

    for (const sid of frameStepIds) {
      const step = playbook.steps.find((s: any) => s.step_id === sid);
      if (step?.frame_file) {
        const framePath = join(FRAMES_DIR, step.frame_file);
        if (existsSync(framePath)) {
          const imgBytes = readFileSync(framePath);
          parts.push({ text: `\n[Step ${step.step_id} screenshot — "${step.title}"]:` });
          parts.push({
            inlineData: {
              data: imgBytes.toString("base64"),
              mimeType: "image/png",
            },
          });
        }
      }
    }

    // If user provided a screenshot for "Where Am I?", include it + several workflow frames
    if (userScreenshot) {
      parts.push({ text: "\n[USER'S CURRENT SCREENSHOT — compare this to the workflow frames below]:" });
      parts.push({
        inlineData: {
          data: userScreenshot,
          mimeType: "image/png",
        },
      });

      const stepCount = playbook.steps.length;
      const stride = Math.max(1, Math.floor(stepCount / 8));
      for (let i = 0; i < stepCount; i += stride) {
        const s = playbook.steps[i];
        if (s?.frame_file) {
          const sPath = join(FRAMES_DIR, s.frame_file);
          if (existsSync(sPath)) {
            const sBytes = readFileSync(sPath);
            parts.push({
              text: `\n[Workflow Step ${s.step_id} at ${s.timestamp_start} — "${s.title}"]:`,
            });
            parts.push({
              inlineData: {
                data: sBytes.toString("base64"),
                mimeType: "image/png",
              },
            });
          }
        }
      }
    }

    // Add the user's question last
    parts.push({ text: "\n\nUser question: " + message });

    const response = await ai.models.generateContent({
      model: "gemini-3.1-pro-preview",
      contents: [{ role: "user", parts }],
      config: {
        temperature: 0.3,
        maxOutputTokens: 1024,
      },
    });

    const text = response.text ?? "I couldn't generate a response.";

    // Extract step reference from the response
    const stepMatch = text.match(/[Ss]tep\s+(\d+)/);
    const stepRef = stepMatch ? parseInt(stepMatch[1]) : undefined;

    return NextResponse.json({
      response: text,
      stepRef,
      chromaUsed: !!chromaResults,
      retrievedSteps: [...relevantStepIds],
    });
  } catch (error) {
    console.error("Chat error:", error);
    return NextResponse.json(
      { response: "Sorry, I encountered an error. Please try again.", error: String(error) },
      { status: 500 }
    );
  }
}
