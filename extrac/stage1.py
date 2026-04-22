"""
Stage 1: Ingestion & Pre-processing
====================================
Replaces the old format router. Instead of routing by file extension
and using different extractors, we now:

1. Filter out junk files (same as before)
2. Upload the file to S3 (storage-first — never pass raw bytes between services)
3. Trigger AWS Textract to extract text, tables, and key-value pairs
4. Return the Textract JSON response for Stage 2 to parse

Why Textract instead of pdfplumber + Tesseract?
- Textract handles PDFs, images, and scanned docs natively — no per-format routing
- Returns structured data: tables, key-value pairs, bounding boxes — not just raw text
- 5-10x faster than local Tesseract for OCR
- More accurate on messy scans (hotel receipts, faxed invoices)

Input:  filepath (str)
Output: (s3_key, textract_response) or None if file should be skipped
"""

import os
import logging
from pathlib import Path
import boto3
from config import S3_BUCKET, AWS_REGION, MAX_FILE_SIZE_MB

log = logging.getLogger(__name__)

# Initialize AWS clients
s3_client = boto3.client("s3", region_name=AWS_REGION)
textract_client = boto3.client("textract", region_name=AWS_REGION)


def should_skip(filepath: str) -> bool:
    """
    Check if a file should be skipped entirely.
    Returns True for files that are not real documents.
    """
    fname = Path(filepath).name

    # Hidden files (e.g. .DS_Store) — macOS folder metadata
    if fname.startswith("."):
        return True

    # Office temp/lock files (e.g. ~$irfield Inn INVOICE.docx)
    if fname.startswith("~$"):
        return True

    # macOS zip metadata folder
    if "__MACOSX" in filepath:
        return True

    # Archives and non-document files
    ext = Path(filepath).suffix.lower()
    if ext in {".rar", ".zip", ".7z", ".ds_store"}:
        return True

    return False

def check_file_size(filepath: str) -> bool:
    """
    Check if file is within the size limit.
    Returns True if OK to process, False if too large.
    """
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        log.warning(f"File too large ({size_mb:.1f}MB > {MAX_FILE_SIZE_MB}MB): {filepath}")
        return False
    return True


def upload_to_s3(filepath: str) -> str:
    """
    Upload a file to S3.
    Returns the S3 object key.

    The key uses the original filename so it's human-readable in the bucket.
    Prefixed with a folder to keep things organized.
    """
    fname = Path(filepath).name
    s3_key = f"uploads/{fname}"

    try:
        s3_client.upload_file(filepath, S3_BUCKET, s3_key)
        log.info(f"Uploaded to s3://{S3_BUCKET}/{s3_key}")
        return s3_key
    except Exception as e:
        log.error(f"S3 upload failed for {filepath}: {e}")
        raise

def trigger_textract(s3_key: str) -> dict:
    """
    Run AWS Textract on a file in S3.
    Uses AnalyzeDocument for single-page or StartDocumentAnalysis for multi-page.

    Returns the Textract response containing Block objects with:
    - PAGE blocks (one per page)
    - LINE / WORD blocks (the actual text)
    - TABLE / CELL blocks (structured table data)
    - KEY_VALUE_SET blocks (form field key-value pairs)

    We request FeatureTypes=["TABLES", "FORMS"] to get structured data,
    not just raw text. This gives us table contents and key-value pairs
    that are strong classification signals.
    """
    try:
        # For files under ~5 pages, synchronous call works
        # For larger files, use async (StartDocumentAnalysis + GetDocumentAnalysis)
        response = textract_client.analyze_document(
            Document={
                "S3Object": {
                    "Bucket": S3_BUCKET,
                    "Name": s3_key,
                }
            },
            FeatureTypes=["TABLES", "FORMS"],
        )
        log.info(f"Textract completed for {s3_key}: {len(response.get('Blocks', []))} blocks")
        return response

    except textract_client.exceptions.UnsupportedDocumentException:
        log.warning(f"Textract can't process this file type: {s3_key}")
        return {"Blocks": []}

    except Exception as e:
        # For large multi-page docs, fall back to async Textract
        log.info(f"Trying async Textract for {s3_key}: {e}")
        return _trigger_textract_async(s3_key)

def _trigger_textract_async(s3_key: str) -> dict:
    """
    Async Textract for large/multi-page documents.
    Starts the job, waits for completion, then fetches all result pages.
    """
    import time

    try:
        # Start the job
        start_response = textract_client.start_document_analysis(
            DocumentLocation={
                "S3Object": {
                    "Bucket": S3_BUCKET,
                    "Name": s3_key,
                }
            },
            FeatureTypes=["TABLES", "FORMS"],
        )
        job_id = start_response["JobId"]
        log.info(f"Started async Textract job {job_id} for {s3_key}")

        # Poll for completion
        while True:
            result = textract_client.get_document_analysis(JobId=job_id)
            status = result["JobStatus"]
            if status == "SUCCEEDED":
                break
            elif status == "FAILED":
                log.error(f"Textract job failed for {s3_key}")
                return {"Blocks": []}
            time.sleep(2)

        # Collect all blocks (results can be paginated)
        all_blocks = result.get("Blocks", [])
        next_token = result.get("NextToken")

        while next_token:
            result = textract_client.get_document_analysis(
                JobId=job_id, NextToken=next_token
            )
            all_blocks.extend(result.get("Blocks", []))
            next_token = result.get("NextToken")

        log.info(f"Async Textract completed for {s3_key}: {len(all_blocks)} blocks")
        return {"Blocks": all_blocks}

    except Exception as e:
        log.error(f"Async Textract failed for {s3_key}: {e}")
        return {"Blocks": []}
    
def ingest(filepath: str) -> tuple:
    """
    Main entry point for Stage 1.
    Validates → uploads to S3 → triggers Textract.

    Args:
        filepath: Local path to the document file

    Returns:
        (s3_key, textract_response) tuple
        Returns (None, None) if file should be skipped
    """
    if should_skip(filepath):
        return None, None

    if not check_file_size(filepath):
        return None, None

    s3_key = upload_to_s3(filepath)
    textract_response = trigger_textract(s3_key)

    return s3_key, textract_response
