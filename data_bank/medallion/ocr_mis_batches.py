#!/usr/bin/env python3
"""medallion/ocr_mis_batches.py: Concurrently execute Document AI OCR on all 336 MIS reports.
"""

import time
from google.cloud import documentai, storage
from google.auth import default
from google.cloud.documentai_v1.types import BatchProcessMetadata

credentials, _ = default(quota_project_id="ongc-hr-finance-agent")
client = documentai.DocumentProcessorServiceClient(
    credentials=credentials,
    client_options={"api_endpoint": "asia-south1-documentai.googleapis.com"}
)
processor_name = "projects/89038075859/locations/asia-south1/processors/306037dbdbd42c8e"

storage_client = storage.Client(project="ongc-hr-finance-agent", credentials=credentials)
bucket = storage_client.bucket("ongc-hr-finance-agent-docs")
mis_blobs = list(bucket.list_blobs(prefix="scanned/mis/"))
mis_pdfs = [b.name for b in mis_blobs if b.name.endswith(".pdf")]
mis_pdfs.sort()

batch_size = 50
batches = [mis_pdfs[i:i + batch_size] for i in range(0, len(mis_pdfs), batch_size)]
print(f"Total MIS PDFs: {len(mis_pdfs)}, total batches: {len(batches)}")

# The first 5 operations were already submitted
active_ops = {
    0: "projects/89038075859/locations/asia-south1/operations/10003276572944917763",
    1: "projects/89038075859/locations/asia-south1/operations/5171135944354154680",
    2: "projects/89038075859/locations/asia-south1/operations/16482104083843353719",
    3: "projects/89038075859/locations/asia-south1/operations/5446958413213771868",
    4: "projects/89038075859/locations/asia-south1/operations/5171135944354155613",
}

next_batch_idx = 5
completed_ops = set()

while len(completed_ops) < len(batches):
    for idx in list(active_ops.keys()):
        if idx in completed_ops:
            continue
        op_name = active_ops[idx]
        op = client.transport.operations_client.get_operation(op_name)
        if op.done:
            print(f"Batch {idx} FINISHED! Error: {op.error.message if op.error else 'None'}")
            completed_ops.add(idx)
            del active_ops[idx]

            # Launch next pending batch if any
            if next_batch_idx < len(batches):
                b_idx = next_batch_idx
                next_batch_idx += 1
                batch = batches[b_idx]
                gcs_docs = [
                    documentai.GcsDocument(
                        gcs_uri=f"gs://ongc-hr-finance-agent-docs/{p}",
                        mime_type="application/pdf"
                    )
                    for p in batch
                ]
                input_config = documentai.BatchDocumentsInputConfig(
                    gcs_documents=documentai.GcsDocuments(documents=gcs_docs)
                )
                output_config = documentai.DocumentOutputConfig(
                    gcs_output_config=documentai.DocumentOutputConfig.GcsOutputConfig(
                        gcs_uri=f"gs://ongc-hr-finance-agent-docs/_docai_output/mis/batch_{b_idx}/"
                    )
                )
                req = documentai.BatchProcessRequest(
                    name=processor_name,
                    input_documents=input_config,
                    document_output_config=output_config
                )
                new_op = client.batch_process_documents(request=req)
                print(f"Launched MIS batch {b_idx} ({len(batch)} docs): {new_op.operation.name}")
                active_ops[b_idx] = new_op.operation.name

    # Print progress
    print(f"Active: {len(active_ops)}, Completed: {len(completed_ops)}/{len(batches)}")
    if len(completed_ops) < len(batches):
        time.sleep(10)

print("ALL 7 MIS OCR BATCHES COMPLETE!")
