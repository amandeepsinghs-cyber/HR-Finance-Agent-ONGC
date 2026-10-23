"""P1.8 Part A: embed AR chunks (text-embedding-005, 768-d) and load `hrfin_docs.doc_chunks_ar`.

Steps
1. Read `financial_ssot/out/doc_chunks_ar.jsonl` (output of `chunk_ar.py`).
2. Embed every chunk with Vertex AI `text-embedding-005` (task RETRIEVAL_DOCUMENT), in batches;
   results are cached in `financial_ssot/out/doc_chunks_ar_embeddings.jsonl` (resumable,
   keyed by `text_sha256`).
3. Create the NEW table `hrfin_docs.doc_chunks_ar` (SPEC-01 §8.1 schema) and load it.
   Safety: the script never drops or modifies an existing table. If the table already exists
   it aborts, unless `--allow-existing-empty` is given and the table has 0 rows.
4. `CREATE VECTOR INDEX IF NOT EXISTS ix_doc_chunks_ar ... (IVF, COSINE)`.

Run from the app root with the yukti venv (ADC required):
    python -m financial_ssot.knowledge.embed_load_ar [--embed-only] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
OUT_DIR = PKG_DIR.parent / "out"
CHUNKS = OUT_DIR / "doc_chunks_ar.jsonl"
EMB_CACHE = OUT_DIR / "doc_chunks_ar_embeddings.jsonl"

PROJECT = os.getenv("TARGET_PROJECT") or os.getenv("YUKTI_GCP_PROJECT") or "ongc-hr-finance-agent"
BQ_LOCATION = os.getenv("BQ_LOCATION", "asia-south1")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
DATASET = "hrfin_docs"
TABLE = "doc_chunks_ar"
INDEX = "ix_doc_chunks_ar"
MODEL = "text-embedding-005"
DIM = 768
BATCH = 40              # max texts per request
TOKEN_BUDGET = 11000    # sum of whitespace-token estimates per request (API limit: 20k real tokens)
JOB_LABELS = {"datacloud": "ai-agent", "packet": "p1-8"}


def load_chunks() -> list:
    with CHUNKS.open(encoding="utf-8") as fh:
        return [json.loads(l) for l in fh]


def load_cache() -> dict:
    cache = {}
    if EMB_CACHE.exists():
        with EMB_CACHE.open(encoding="utf-8") as fh:
            for l in fh:
                r = json.loads(l)
                cache[r["text_sha256"]] = r["embedding"]
    return cache


def _batches(todo: list) -> list:
    """Group chunks so each request stays well under the 20k-input-token limit. Real tokenizer
    counts run ~1.5x the whitespace estimate on AR text (numbers, symbols), hence the margin."""
    out, cur, cur_tok = [], [], 0
    for c in todo:
        t = int(c.get("token_estimate") or 600)
        if cur and (cur_tok + t > TOKEN_BUDGET or len(cur) >= BATCH):
            out.append(cur)
            cur, cur_tok = [], 0
        cur.append(c)
        cur_tok += t
    if cur:
        out.append(cur)
    return out


def embed_all(chunks: list) -> dict:
    from google import genai
    from google.genai import types

    client = genai.Client(vertexai=True, project=PROJECT, location=VERTEX_LOCATION)
    cfg = types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT", output_dimensionality=DIM)
    cache = load_cache()
    todo = [c for c in chunks if c["text_sha256"] not in cache]
    print(f"embeddings cached: {len(cache)}; to embed: {len(todo)}", flush=True)

    def call(batch: list) -> list:
        for attempt in range(6):
            try:
                res = client.models.embed_content(model=MODEL, contents=[c["text"] for c in batch], config=cfg)
                return [list(e.values) for e in res.embeddings]
            except Exception as exc:
                msg = str(exc)
                if "input token count" in msg and len(batch) > 1:
                    half = len(batch) // 2
                    return call(batch[:half]) + call(batch[half:])
                wait = 2 ** attempt * 5
                print(f"  {type(exc).__name__}: {msg[:160]} -> retry in {wait}s", flush=True)
                time.sleep(wait)
        raise RuntimeError("embedding failed after retries")

    done = 0
    with EMB_CACHE.open("a", encoding="utf-8") as fh:
        for bi, batch in enumerate(_batches(todo)):
            vecs = call(batch)
            for c, vec in zip(batch, vecs):
                assert len(vec) == DIM
                cache[c["text_sha256"]] = vec
                fh.write(json.dumps({"text_sha256": c["text_sha256"], "embedding": vec}) + "\n")
            fh.flush()
            done += len(batch)
            if bi % 20 == 0:
                print(f"  embedded {done}/{len(todo)}", flush=True)
    return cache


def schema():
    from google.cloud import bigquery as bq

    S = bq.SchemaField
    return [
        S("chunk_id", "STRING", "REQUIRED"),
        S("fiscal_year", "STRING", "REQUIRED"),
        S("source_doc", "STRING", "REQUIRED"),
        S("source_page", "INT64", "REQUIRED", description="1-based physical PDF page (SPEC-01 §4.1)"),
        S("source_page_label", "STRING", description="Printed folio on that page"),
        S("section", "STRING", "REQUIRED"),
        S("note_no", "STRING"),
        S("heading", "STRING"),
        S("text", "STRING", "REQUIRED"),
        S("line_codes", "STRING", "REPEATED"),
        S("entities", "STRING", "REPEATED"),
        S("embedding", "FLOAT64", "REPEATED"),
        S("embedding_model", "STRING"),
        S("text_sha256", "STRING", "REQUIRED"),
        S("token_estimate", "INT64"),
        S("chunker_version", "STRING"),
        S("loaded_at", "TIMESTAMP"),
    ]


def load_bq(chunks: list, cache: dict, allow_existing_empty: bool) -> None:
    from google.api_core.exceptions import NotFound
    from google.cloud import bigquery as bq

    client = bq.Client(project=PROJECT, location=BQ_LOCATION)
    table_id = f"{PROJECT}.{DATASET}.{TABLE}"
    try:
        t = client.get_table(table_id)
        if not (allow_existing_empty and (t.num_rows or 0) == 0):
            raise SystemExit(f"{table_id} already exists ({t.num_rows} rows); refusing to modify it.")
        print(f"{table_id} exists and is empty: loading into it")
    except NotFound:
        t = bq.Table(table_id, schema=schema())
        t.description = ("P1.8 / SPEC-01 §8.1: real ONGC Annual Report text chunks (FY17-19, FY22-26), "
                         "page-bounded, with text-embedding-005 vectors. Source: pdftotext -layout of the AR PDFs.")
        t.clustering_fields = ["fiscal_year", "section"]
        t.labels = {"datacloud": "ai-agent", "packet": "p1-8"}
        client.create_table(t)
        print(f"created {table_id}")

    loaded_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rows = []
    for c in chunks:
        rows.append({
            "chunk_id": c["chunk_id"], "fiscal_year": c["fiscal_year"], "source_doc": c["source_doc"],
            "source_page": c["source_page"], "source_page_label": c["source_page_label"],
            "section": c["section"], "note_no": c["note_no"], "heading": c["heading"], "text": c["text"],
            "line_codes": c["line_codes"], "entities": c["entities"],
            "embedding": cache[c["text_sha256"]], "embedding_model": MODEL,
            "text_sha256": c["text_sha256"], "token_estimate": c["token_estimate"],
            "chunker_version": c["chunker_version"], "loaded_at": loaded_at,
        })
    job_cfg = bq.LoadJobConfig(schema=schema(), write_disposition="WRITE_EMPTY",
                               source_format=bq.SourceFormat.NEWLINE_DELIMITED_JSON, labels=JOB_LABELS)
    job = client.load_table_from_json(rows, table_id, job_config=job_cfg)
    job.result()
    print(f"loaded {job.output_rows} rows into {table_id}")

    ddl = (f"CREATE VECTOR INDEX IF NOT EXISTS {INDEX} ON `{table_id}`(embedding) "
           f"OPTIONS(index_type='IVF', distance_type='COSINE')")
    client.query(ddl, job_config=bq.QueryJobConfig(labels=JOB_LABELS)).result()
    print(f"vector index {INDEX}: create requested")


def update_tags(chunks: list, apply: bool) -> int:
    """Re-tag rows after a chunker change that keeps chunk_id + text identical (e.g. v1 -> v2
    section fix). Compares section/heading/note_no/chunker_version with BigQuery and, only with
    `--apply`, runs ONE parameterised UPDATE on the changed chunk_ids. Text and embeddings are
    never touched; rows whose text_sha256 differs abort the run (that needs a full reload)."""
    from google.cloud import bigquery as bq

    client = bq.Client(project=PROJECT, location=BQ_LOCATION)
    table_id = f"{PROJECT}.{DATASET}.{TABLE}"
    cur = {r["chunk_id"]: dict(r.items()) for r in client.query(
        f"SELECT chunk_id, text_sha256, section, heading, note_no, chunker_version FROM `{table_id}`",
        job_config=bq.QueryJobConfig(labels=JOB_LABELS)).result()}
    local = {c["chunk_id"]: c for c in chunks}
    if set(cur) != set(local):
        raise SystemExit(f"chunk_id sets differ (bq {len(cur)} vs local {len(local)}): full reload needed")
    bad = [k for k in local if local[k]["text_sha256"] != cur[k]["text_sha256"]]
    if bad:
        raise SystemExit(f"{len(bad)} chunks changed text (e.g. {bad[:3]}): full reload needed")
    keys = ("section", "heading", "note_no", "chunker_version")
    changed = [k for k in local if any(local[k][f] != cur[k][f] for f in keys)]
    by = {}
    for k in changed:
        t = (cur[k]["section"], local[k]["section"])
        by[t] = by.get(t, 0) + 1
    print(f"rows to re-tag: {len(changed)}; section moves: {by}")
    if not changed or not apply:
        if changed:
            print("dry run: pass --apply to run the UPDATE")
        return len(changed)
    S = bq.StructQueryParameter
    rows = [S(None, bq.ScalarQueryParameter("chunk_id", "STRING", k),
              *[bq.ScalarQueryParameter(f, "STRING", local[k][f]) for f in keys]) for k in changed]
    sql = (f"UPDATE `{table_id}` t SET section = u.section, heading = u.heading, note_no = u.note_no, "
           f"chunker_version = u.chunker_version FROM UNNEST(@rows) u WHERE t.chunk_id = u.chunk_id")
    job = client.query(sql, job_config=bq.QueryJobConfig(
        query_parameters=[bq.ArrayQueryParameter("rows", "STRUCT", rows)], labels=JOB_LABELS))
    job.result()
    print(f"updated {job.num_dml_affected_rows} rows")
    return len(changed)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--embed-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="read chunks and cache, print counts, no API calls")
    ap.add_argument("--allow-existing-empty", action="store_true")
    ap.add_argument("--update-tags", action="store_true",
                    help="compare section/heading/note_no with the loaded table (dry run unless --apply)")
    ap.add_argument("--apply", action="store_true", help="with --update-tags: run the UPDATE")
    a = ap.parse_args(argv)
    chunks = load_chunks()
    print(f"chunks: {len(chunks)}")
    if a.update_tags:
        update_tags(chunks, a.apply)
        return 0
    if a.dry_run:
        print(f"cached embeddings: {len(load_cache())}")
        return 0
    cache = embed_all(chunks)
    missing = [c["chunk_id"] for c in chunks if c["text_sha256"] not in cache]
    if missing:
        raise SystemExit(f"{len(missing)} chunks without embeddings, e.g. {missing[:3]}")
    if not a.embed_only:
        load_bq(chunks, cache, a.allow_existing_empty)
    return 0


if __name__ == "__main__":
    sys.exit(main())
