# WORKFLOW MEMORY — Build Context (Single Source of Truth)

## Product Name: Workflow Memory

## One-liner
Convert workflow recordings into structured, queryable operational playbooks for humans and coding agents.

## Pitch (30 sec)
"Every team records knowledge transfers, onboarding sessions, and walkthroughs. But those videos are impossible to reuse later. We convert those recordings into structured workflow memory so anyone — or any coding agent — can reproduce the process without rewatching the video."

## Core Insight
- NOT summarizing videos
- CONVERTING demonstrations into reusable workflow memory
- "Watch and rewind" → "Search, follow, and execute"
- Docs tell you what's possible. A demonstrated playbook tells you what actually worked.

## Problem
Workflow knowledge is trapped in KT recordings, Looms, Zoom walkthroughs. Later, these are:
- Linear, hard to skim/search
- Hard to follow while implementing
- Full of filler mixed with critical steps
- Poor at preserving exact commands, configs, order

## Product Outputs
1. **Structured Playbook** — ordered steps with title, summary, commands, configs, timestamps, frames
2. **Queryable Assistant** — ask operational questions ("what command?", "which namespace?", "what next?")
3. **Source-Grounded Evidence** — every step links to transcript snippet + timestamp + frame
4. **Enhanced Step Visuals** — NanoBanana-cleaned frames for key steps (clarity layer, not source of truth)
5. **Agent-Ready Export** — structured JSON playbook for coding agents as reusable context

## UI Layout (3-column, single screen)
- **LEFT**: Workflow steps list (numbered, clickable, with step type icons)
- **CENTER**: Step detail card (summary, command, verification, visual, source timestamp)
- **RIGHT**: AI assistant chat + "Where Am I?" feature

## Demo Flow (3 minutes)
1. Show upload screen → upload KT video
2. Show processing animation (extracting transcript, identifying steps, etc.)
3. Reveal generated playbook with steps
4. Click a step → show command + visual + timestamp
5. Ask assistant a question → get grounded answer
6. Use "Where am I?" → paste terminal output → get next step
7. Show "Export for AI Agents" → download JSON
8. Briefly show Team Workflow Library concept

## Technical Pipeline
1. Ingest video → Gemini 3.1 (native video understanding, 1M token context)
2. Extract: timestamped transcript, procedural segments, steps, commands, configs
3. Extract frames at key timestamps (ffmpeg)
4. Optional: NanoBanana enhance 1-2 key frames
5. Build structured playbook JSON
6. Serve via Next.js UI + chat assistant API

## Playbook JSON Schema
```json
{
  "workflow_title": "...",
  "workflow_summary": "...",
  "total_duration": "...",
  "steps": [
    {
      "step_id": 1,
      "title": "...",
      "summary": "...",
      "commands": ["..."],
      "files_modified": ["..."],
      "config_changes": ["..."],
      "tool_context": "terminal|browser|IDE|dashboard",
      "step_type": "command|config_edit|verification|navigation|explanation",
      "timestamp_start": "00:05:12",
      "timestamp_end": "00:05:44",
      "transcript_snippet": "...",
      "dependencies": [],
      "verification": "...",
      "keywords": ["..."],
      "frame_file": "frame_step1.png",
      "enhanced_visual": null
    }
  ],
  "all_commands": ["..."],
  "tools_used": ["..."],
  "environments": ["..."]
}
```

## Models Used
- **Gemini 3.1 Pro Preview**: Video understanding, transcript extraction, step extraction, chat assistant
- **NanoBanana 2 (gemini-3.1-flash-image-preview)**: Optional enhanced step visuals
- **Lyria**: NOT used (doesn't fit the product)

## Key Guardrails
- NanoBanana = clarity layer, NOT source of truth (keep original frames)
- NOT autonomous agent execution — agent-READY workflow memory
- NOT perfect live tracking — state-aware next-step guidance
- Every step must be source-grounded (transcript + timestamp + frame)

## Positioning
- Category: Operational Memory Infrastructure
- Vision: Memory layer for how work actually gets done
- Evolution: KT→Playbook → Team Libraries → Coding Agent Context → Live Guidance
