# Workflow Memory

Turn workflow recordings into structured, searchable operational knowledge.

## The Problem

A huge amount of operational knowledge inside companies lives in screen recordings — knowledge transfer sessions, onboarding walkthroughs, setup demos, internal tutorials. These recordings are almost impossible to reuse. When someone needs to reproduce a process, they rewatch long videos, pause constantly, and manually extract steps, commands, and configuration details.

## What This Does

Workflow Memory converts workflow recordings into structured, step-by-step playbooks. Instead of replaying videos, teams get a clear breakdown of how something was actually done — and can interact with it while working.

**Upload a recording → Get a structured playbook → Query it by voice or text → Follow along in real-time.**

## How It Works

1. **Video Understanding** — Gemini 3.1 Pro processes the full recording with multimodal understanding (video + audio + screen content simultaneously), extracting procedural steps, terminal commands, configurations, and representative frames.

2. **Semantic Memory** — Extracted workflow steps are indexed into ChromaDB Cloud as vector embeddings, enabling semantic search across all workflow knowledge. Ask "how do I configure the ingress controller?" and get the exact relevant steps.

3. **Voice Copilot** — A LiveKit-powered voice agent with Gemini Live sits alongside your work. It sees your screen in real-time, hears your questions, and guides you through the workflow using voice — referencing the playbook and retrieving relevant context from ChromaDB as needed.

## Tech Stack

| Component | Technology | Role |
|-----------|-----------|------|
| **Video Processing** | Gemini 3.1 Pro (multimodal) | Understands video, audio, and screen content to extract structured workflow steps |
| **Semantic Search** | ChromaDB Cloud | Vector database for indexing and retrieving workflow steps by meaning |
| **Voice Copilot** | LiveKit Agents + Gemini Live | Real-time voice AI with live screen vision — sees what you're doing and responds by voice |
| **Frontend** | Next.js, TypeScript, Tailwind CSS | 3-column workflow UI with AI chat and copilot panel |

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Video Upload    │────▶│  Gemini 3.1 Pro  │────▶│  Structured     │
│  (screen recording)    │  (multimodal)    │     │  Playbook JSON  │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │  ChromaDB Cloud  │
                                                 │  (vector index)  │
                                                 └────────┬────────┘
                                                          │
                    ┌─────────────────────────────────────┤
                    │                                     │
                    ▼                                     ▼
           ┌─────────────────┐               ┌─────────────────────┐
           │  Next.js UI     │               │  LiveKit Voice Agent │
           │  (3-column view,│               │  (Gemini Live +     │
           │   AI chat)      │               │   screen vision +   │
           └─────────────────┘               │   ChromaDB retrieval)│
                                             └─────────────────────┘
```

## Running Locally

### Prerequisites
- Python 3.12+
- Node.js 18+
- API keys: Gemini, ChromaDB Cloud, LiveKit Cloud

### Setup

```bash
# Python environment
python -m venv venv
source venv/bin/activate
pip install livekit-agents livekit-plugins-google livekit-plugins-silero \
  livekit-plugins-noise-cancellation chromadb google-genai python-dotenv certifi

# Download LiveKit model files
python workflow_copilot_agent.py download-files

# Next.js app
cd app
npm install
```

### Environment Variables

Root `.env`:
```
GEMINI_API_KEY=...
GOOGLE_API_KEY=...
CHROMA_API_KEY=...
LIVEKIT_URL=wss://...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
```

`app/.env.local`:
```
GEMINI_API_KEY=...
CHROMA_API_KEY=...
CHROMA_TENANT=...
CHROMA_DATABASE=...
LIVEKIT_URL=...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
```

### Run

```bash
# Terminal 1: Voice agent
source venv/bin/activate
python workflow_copilot_agent.py dev

# Terminal 2: Web app
cd app
npm run dev
```

Open `http://localhost:3000`.

## Why This Matters

As software development becomes increasingly AI-assisted, structured workflow memory becomes critical infrastructure. Instead of fragmented documentation, developers and coding agents can reuse the exact workflows that previously worked. Every team records workflows — Workflow Memory makes them actually reusable.