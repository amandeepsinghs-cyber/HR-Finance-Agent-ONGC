#!/usr/bin/env python3
"""Precomputes text embeddings for all 89 certified queries using Vertex AI text-embedding-004.
Saves the vectors to certified/embeddings.json so runtime routing is instant (<1ms lookup).
"""

import json
from pathlib import Path
import time
from google import genai
import yaml

BACKEND_DIR = Path(__file__).resolve().parent.parent
CERTIFIED_DIR = BACKEND_DIR / "certified"
LIBRARY_PATH = CERTIFIED_DIR / "library.yaml"
OUTPUT_PATH = CERTIFIED_DIR / "embeddings.json"

PROJECT_ID = "ongc-hr-finance-agent"
LOCATION = "us-central1"
MODEL_NAME = "text-embedding-004"


def precompute():
    print(f"Loading certified query library from {LIBRARY_PATH}...")
    with open(LIBRARY_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    queries = data.get("queries", [])
    print(f"Precomputing embeddings for {len(queries)} certified queries via Vertex AI...")

    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    # Prepare texts to embed
    texts_to_embed = []
    qids = []
    for q in queries:
        qid = q["id"]
        qids.append(qid)
        keywords_str = " ".join(q.get("intent_keywords", []))
        text = f"{q['canonical_question']} | Intent: {q.get('intent_description', '')} | Keywords: {keywords_str}"
        texts_to_embed.append(text)

    # Batch embed
    t0 = time.perf_counter()
    batch_size = 20
    all_embeddings = {}

    for i in range(0, len(texts_to_embed), batch_size):
        chunk_texts = texts_to_embed[i:i + batch_size]
        chunk_ids = qids[i:i + batch_size]
        res = client.models.embed_content(model=MODEL_NAME, contents=chunk_texts)
        for qid, emb in zip(chunk_ids, res.embeddings):
            all_embeddings[qid] = emb.values
        print(f"Embedded {min(i + batch_size, len(texts_to_embed))}/{len(texts_to_embed)} queries...")

    elapsed = time.perf_counter() - t0
    print(f"Embedding completed in {elapsed:.2f}s")

    payload = {
        "model": MODEL_NAME,
        "dimension": len(next(iter(all_embeddings.values()))),
        "total_queries": len(all_embeddings),
        "embeddings": all_embeddings,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f)

    print(f"✓ Saved precomputed embeddings to {OUTPUT_PATH}")


if __name__ == "__main__":
    precompute()
