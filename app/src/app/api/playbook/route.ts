import { NextResponse } from "next/server";
import { readFileSync, existsSync } from "fs";
import { join } from "path";

export async function GET() {
  // Look for playbook in the parent experiments directory
  const playbookPath = join(process.cwd(), "..", "playbook_data", "playbook.json");

  if (!existsSync(playbookPath)) {
    return NextResponse.json(
      { error: "Playbook not found. Run process_video.py first." },
      { status: 404 }
    );
  }

  const data = JSON.parse(readFileSync(playbookPath, "utf-8"));
  return NextResponse.json(data);
}
