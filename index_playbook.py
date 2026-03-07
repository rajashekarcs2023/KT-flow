"""
Index playbook steps into Chroma Cloud for semantic search.
Run after process_video_v2.py completes.

Usage: venv/bin/python index_playbook.py
"""
import json
import os
import chromadb
from dotenv import load_dotenv

load_dotenv()

PLAYBOOK_PATH = "playbook_data/playbook.json"
COLLECTION_NAME = "workflow_steps"

CHROMA_API_KEY = os.getenv("CHROMA_API_KEY")
CHROMA_TENANT = "de3af88e-5eda-4016-913b-a6cab0df6ddf"
CHROMA_DATABASE = "Demo"

def main():
    # Load playbook
    with open(PLAYBOOK_PATH) as f:
        playbook = json.load(f)

    print(f"Indexing: {playbook['workflow_title']}")
    print(f"Steps: {len(playbook['steps'])}")

    # Connect to Chroma Cloud
    client = chromadb.CloudClient(
        api_key=CHROMA_API_KEY,
        tenant=CHROMA_TENANT,
        database=CHROMA_DATABASE,
    )
    print(f"Connected to Chroma Cloud (tenant: {CHROMA_TENANT}, db: {CHROMA_DATABASE})")

    # Delete existing collection if present (re-index)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Index each step
    documents = []
    metadatas = []
    ids = []

    for step in playbook["steps"]:
        # Build rich text document for embedding
        doc_parts = [
            f"Step {step['step_id']}: {step['title']}",
            f"Summary: {step['summary']}",
            f"Type: {step['step_type']}",
        ]
        if step.get("commands"):
            doc_parts.append(f"Commands: {'; '.join(step['commands'])}")
        if step.get("files_modified"):
            doc_parts.append(f"Files: {'; '.join(step['files_modified'])}")
        if step.get("config_changes"):
            doc_parts.append(f"Config changes: {'; '.join(step['config_changes'])}")
        if step.get("transcript_snippet"):
            doc_parts.append(f"Transcript: {step['transcript_snippet']}")
        if step.get("what_is_on_screen"):
            doc_parts.append(f"On screen: {step['what_is_on_screen']}")
        if step.get("verification"):
            doc_parts.append(f"Verification: {step['verification']}")
        if step.get("keywords"):
            doc_parts.append(f"Keywords: {', '.join(step['keywords'])}")

        documents.append("\n".join(doc_parts))
        metadatas.append({
            "step_id": step["step_id"],
            "title": step["title"],
            "step_type": step["step_type"],
            "timestamp_start": step.get("timestamp_start", ""),
            "timestamp_end": step.get("timestamp_end", ""),
            "tool_context": step.get("tool_context", ""),
            "frame_file": step.get("frame_file", ""),
            "workflow_id": "kt-agents-k8s",
            "workflow_title": playbook["workflow_title"],
        })
        ids.append(f"step-{step['step_id']}")

    # Also index transcript segments if available
    for i, seg in enumerate(playbook.get("transcript_segments", [])):
        documents.append(f"Transcript ({seg['timestamp_start']}-{seg['timestamp_end']}): {seg['text']}")
        metadatas.append({
            "step_id": 0,
            "title": f"transcript-{i}",
            "step_type": "transcript",
            "timestamp_start": seg.get("timestamp_start", ""),
            "timestamp_end": seg.get("timestamp_end", ""),
            "tool_context": "",
            "frame_file": "",
            "workflow_id": "kt-agents-k8s",
            "workflow_title": playbook["workflow_title"],
        })
        ids.append(f"transcript-{i}")

    # Also index the all_commands list
    if playbook.get("all_commands"):
        for i, cmd in enumerate(playbook["all_commands"]):
            documents.append(f"Command: {cmd}")
            metadatas.append({
                "step_id": 0,
                "title": f"command-{i}",
                "step_type": "command",
                "timestamp_start": "",
                "timestamp_end": "",
                "tool_context": "terminal",
                "frame_file": "",
                "workflow_id": "kt-agents-k8s",
                "workflow_title": playbook["workflow_title"],
            })
            ids.append(f"command-{i}")

    # Add all documents to ChromaDB
    collection.add(documents=documents, metadatas=metadatas, ids=ids)

    print(f"Indexed {len(documents)} documents into ChromaDB collection '{COLLECTION_NAME}'")

    # Quick test
    results = collection.query(query_texts=["How do I deploy an agent?"], n_results=3)
    print(f"\nTest query: 'How do I deploy an agent?'")
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        print(f"  -> [{meta['step_type']}] {meta['title']}: {doc[:100]}...")

    # Index mock workflows for the Team Library demo
    mock_collection = client.get_or_create_collection(
        name="workflow_library",
        metadata={"hnsw:space": "cosine"},
    )
    
    mock_workflows = [
        {
            "id": "kt-agents-k8s",
            "title": playbook["workflow_title"],
            "summary": playbook["workflow_summary"],
            "steps_count": len(playbook["steps"]),
            "duration": playbook.get("total_duration_minutes", 0),
            "tools": ", ".join(playbook.get("tools_used", [])),
            "real": True,
        },
        {
            "id": "setup-stripe-webhooks",
            "title": "Setting Up Stripe Payment Webhooks",
            "summary": "Configure Stripe webhooks for payment processing, including endpoint setup, event filtering, and signature verification in a Node.js backend.",
            "steps_count": 14,
            "duration": 28,
            "tools": "Stripe Dashboard, VS Code, Terminal, Postman",
            "real": False,
        },
        {
            "id": "configure-auth0-sso",
            "title": "Configuring Auth0 SSO for Internal Tools",
            "summary": "Set up Single Sign-On using Auth0 for internal dashboards, including tenant configuration, application registration, and role-based access control.",
            "steps_count": 18,
            "duration": 35,
            "tools": "Auth0 Dashboard, VS Code, Chrome DevTools",
            "real": False,
        },
        {
            "id": "deploy-ml-pipeline",
            "title": "Deploying ML Pipeline on Vertex AI",
            "summary": "End-to-end deployment of a machine learning training pipeline on Google Cloud Vertex AI, from data preprocessing to model serving.",
            "steps_count": 22,
            "duration": 45,
            "tools": "Google Cloud Console, VS Code, Terminal, Docker",
            "real": False,
        },
        {
            "id": "setup-monitoring-stack",
            "title": "Setting Up Prometheus + Grafana Monitoring",
            "summary": "Deploy and configure a monitoring stack with Prometheus for metrics collection and Grafana for visualization on a Kubernetes cluster.",
            "steps_count": 16,
            "duration": 32,
            "tools": "Kubernetes, Helm, Grafana, Terminal",
            "real": False,
        },
    ]

    mock_docs = []
    mock_metas = []
    mock_ids = []
    for wf in mock_workflows:
        mock_docs.append(f"{wf['title']}: {wf['summary']} Tools: {wf['tools']}")
        mock_metas.append({
            "workflow_id": wf["id"],
            "title": wf["title"],
            "summary": wf["summary"],
            "steps_count": wf["steps_count"],
            "duration": wf["duration"],
            "tools": wf["tools"],
            "real": str(wf["real"]),
        })
        mock_ids.append(wf["id"])

    try:
        mock_collection.delete(ids=mock_ids)
    except Exception:
        pass
    mock_collection.add(documents=mock_docs, metadatas=mock_metas, ids=mock_ids)
    print(f"\nIndexed {len(mock_workflows)} workflows into library collection")


if __name__ == "__main__":
    main()
