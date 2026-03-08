"""
Workflow Copilot — LiveKit Voice Agent with Gemini Live + Vision + ChromaDB
 
This agent:
- Connects to LiveKit Cloud
- Uses Gemini Live realtime model with video input (sees user's screen)
- Has the full playbook loaded as context
- Uses ChromaDB Cloud for semantic search when needed
- Responds by voice in real-time
"""

import asyncio
import json
import os
import ssl
import certifi
from pathlib import Path

# Fix SSL certificate verification on macOS — must happen before any
# library (aiohttp, etc.) creates an SSL context
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

_original_create_default_context = ssl.create_default_context
def _patched_create_default_context(purpose=ssl.Purpose.SERVER_AUTH, *, cafile=None, capath=None, cadata=None):
    return _original_create_default_context(
        purpose, cafile=cafile or certifi.where(), capath=capath, cadata=cadata
    )
ssl.create_default_context = _patched_create_default_context

import chromadb
from dotenv import load_dotenv

from livekit import agents, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    get_job_context,
    room_io,
)
from livekit.agents.llm import ChatContext, ImageContent
from livekit.plugins import google, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

load_dotenv(dotenv_path=".env")

# ─── Load playbook ─────────────────────────────────────────
PLAYBOOK_PATH = Path(__file__).parent / "playbook_data" / "playbook.json"
playbook = json.loads(PLAYBOOK_PATH.read_text()) if PLAYBOOK_PATH.exists() else {}

# Build a concise text summary of the playbook for the system prompt
def build_playbook_context(pb: dict) -> str:
    if not pb:
        return "No playbook loaded."
    lines = [
        f"WORKFLOW: {pb.get('workflow_title', 'Unknown')}",
        f"SUMMARY: {pb.get('workflow_summary', '')}",
        f"TOTAL STEPS: {len(pb.get('steps', []))}",
        f"DURATION: {pb.get('total_duration_minutes', '?')} minutes",
        f"TOOLS: {', '.join(pb.get('tools_used', []))}",
        "",
        "STEPS OVERVIEW:",
    ]
    for s in pb.get("steps", []):
        cmds = ", ".join(s.get("commands", [])) or "none"
        lines.append(
            f"  Step {s['step_id']}: {s['title']} — {s['summary'][:120]}... "
            f"[{s.get('timestamp_start', '?')}-{s.get('timestamp_end', '?')}] "
            f"Commands: {cmds}"
        )
    lines.append("")
    all_cmds = pb.get("all_commands", [])
    if all_cmds:
        lines.append("ALL COMMANDS:\n" + "\n".join(f"  $ {c}" for c in all_cmds))
    return "\n".join(lines)


PLAYBOOK_CONTEXT = build_playbook_context(playbook)

# ─── ChromaDB Cloud client ──────────────────────────────────
def get_chroma_client():
    return chromadb.CloudClient(
        api_key=os.getenv("CHROMA_API_KEY", ""),
        tenant=os.getenv("CHROMA_TENANT", "de3af88e-5eda-4016-913b-a6cab0df6ddf"),
        database=os.getenv("CHROMA_DATABASE", "Demo"),
    )


def search_chromadb(query: str, n_results: int = 5) -> str:
    """Search ChromaDB for relevant workflow steps."""
    try:
        client = get_chroma_client()
        collection = client.get_collection("workflow_steps")
        results = collection.query(query_texts=[query], n_results=n_results)
        docs = results.get("documents", [[]])[0]
        if docs:
            return "RETRIEVED CONTEXT FROM CHROMA CLOUD:\n" + "\n---\n".join(docs)
        return "No relevant results found in ChromaDB."
    except Exception as e:
        return f"ChromaDB search failed: {e}"


# ─── Agent Instructions ────────────────────────────────────
INSTRUCTIONS = f"""You are the Workflow Copilot — a voice-controlled AI assistant that helps engineers follow and reproduce operational workflows. You are powered by Gemini Live with real-time vision and ChromaDB semantic memory.

You can SEE the user's screen in real-time. Use what you see to understand their current context — which tool they have open, what terminal output they're looking at, what step they might be on.

{PLAYBOOK_CONTEXT}

YOUR CAPABILITIES:
1. **See the user's screen** — you receive live video from their screen share. Reference what you see.
2. **Voice conversation** — the user speaks to you and you respond by voice. Be concise and actionable.
3. **Workflow memory** — you know every step, command, and configuration from the workflow playbook.

BEHAVIOR:
- When the user asks "where am I?" or "what step is this?", look at their screen and match it to the workflow steps.
- When they ask "what should I do next?", identify their current step from the screen and tell them the next step.
- When they ask about a command, give them the exact command from the playbook.
- Keep responses SHORT and DIRECT — this is a voice conversation, not a text chat. 2-3 sentences max.
- Always reference the specific step number.
- If you see an error on their screen, proactively help debug it using workflow context.
- Be encouraging and supportive, like a senior engineer sitting next to them."""


# ─── LiveKit Agent ──────────────────────────────────────────

class WorkflowCopilot(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=INSTRUCTIONS,
            llm=google.realtime.RealtimeModel(
                voice="Puck",
                temperature=0.3,
                model="gemini-2.0-flash-exp",
            ),
        )

    async def on_enter(self):
        """Called when the agent joins the room."""
        room = get_job_context().room
        # Log participants
        for p in room.remote_participants.values():
            print(f"[Copilot] Participant connected: {p.identity}")

    async def on_user_turn_completed(
        self, turn_ctx: ChatContext, new_message
    ) -> None:
        """
        Called after the user finishes speaking. We inject ChromaDB context
        into the conversation to give the LLM more targeted information.
        """
        # Extract the user's text from the message
        user_text = ""
        if hasattr(new_message, "text_content"):
            user_text = new_message.text_content or ""
        elif hasattr(new_message, "content"):
            for item in (new_message.content if isinstance(new_message.content, list) else [new_message.content]):
                if isinstance(item, str):
                    user_text += item

        if user_text:
            # Search ChromaDB for relevant context
            chroma_context = search_chromadb(user_text)
            if "RETRIEVED CONTEXT" in chroma_context:
                # Add the retrieved context as a system-like message
                turn_ctx.add_message(
                    role="user",
                    content=f"[SYSTEM — ChromaDB retrieval for the question '{user_text}']\n{chroma_context}\n[Use this context to answer more accurately.]",
                )


server = AgentServer()


@server.rtc_session(agent_name="workflow-copilot")
async def workflow_copilot_session(ctx: agents.JobContext):
    session = AgentSession()

    await session.start(
        agent=WorkflowCopilot(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            video_input=True,  # Enable live video — sees user's screen share
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_cancellation.BVC(),
            ),
        ),
    )

    # Greet the user
    await session.generate_reply(
        instructions="Greet the user warmly. Tell them you're their Workflow Copilot and you can see their screen. Ask them to share their screen if they haven't, and ask how you can help them with the workflow."
    )


if __name__ == "__main__":
    agents.cli.run_app(server)
