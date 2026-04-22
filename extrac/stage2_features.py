"""
Stage 2: Feature Extraction from Textract
==========================================
Replaces the old multi-extractor approach. Instead of pdfplumber, Tesseract,
openpyxl, etc., we now parse the Textract JSON response from Stage 1.

What stays from the old stage2:
  - compute_keyword_score() — scores text against keyword dicts (now SVM features)
  - detect_page_x_of_y() — boundary detection still needs this
  - compute_numeric_ratio() — becomes an SVM feature
  - has_table_structure() — becomes an SVM feature
  - has_currency() — becomes an SVM feature
  - looks_like_first_page() — boundary detection still needs this
  - build_page_features() — assembles PageFeatures objects

What's new:
  - extract_from_textract() — parses Textract Block objects grouped by page
  - _extract_tables_for_page() — pulls structured table data from Textract
  - _extract_kv_pairs_for_page() — pulls key-value pairs from Textract
  - sample_pages() — implements page sampling for large files (first 2 + last 2)

Input:  Textract response dict (from Stage 1)
Output: list[PageFeatures] — one per page
"""

import re
import logging
from collections import defaultdict

from models import PageFeatures
from config import (
    INVOICE_KEYWORDS, PMS_KEYWORDS, PAYROLL_KEYWORDS, STR_KEYWORDS,
    MAX_SAMPLE_PAGES,
)

log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Feature computation helpers (KEPT from old stage2)
# These work on any text regardless of where it came from
# ─────────────────────────────────────────────

def compute_keyword_score(text: str, keyword_dict: dict) -> float:
    """
    Scan text for keywords and return a weighted score (0.0 to 1.0).
    Each keyword hit adds its weight, capped at 3 hits per keyword
    to prevent a single repeated word from dominating the score.
    """
    if not text:
        return 0.0
    text_lower = text.lower()
    score = 0
    max_possible = sum(keyword_dict.values())
    for keyword, weight in keyword_dict.items():
        if keyword in text_lower:
            count = min(text_lower.count(keyword), 3)
            score += weight * count
    return min(score / max(max_possible * 0.3, 1), 1.0)


def detect_page_x_of_y(text: str) -> tuple:
    """
    Look for patterns like "Page 2 of 5" or "Page: 1/3".
    Returns (x, y) if found, (None, None) if not.
    This is the strongest boundary detection signal.
    """
    patterns = [
        r"page\s*[:#]?\s*(\d+)\s*(?:of|/)\s*(\d+)",
        r"(\d+)\s*(?:of|/)\s*(\d+)\s*page",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None, None

def compute_numeric_ratio(text: str) -> float:
    """
    What fraction of non-whitespace characters are digits?
    Financial documents tend to have higher ratios.
    """
    if not text:
        return 0.0
    non_ws = re.sub(r"\s", "", text)
    if not non_ws:
        return 0.0
    return sum(c.isdigit() for c in non_ws) / len(non_ws)


def has_table_structure(text: str) -> bool:
    """
    Heuristic: does the text look like a table?
    Checks for 3+ lines with multi-space column gaps.
    Note: Textract also detects tables directly — this is a backup check
    on the raw text for cases where Textract misses informal tables.
    """
    if not text:
        return False
    lines = text.split("\n")
    tabular = sum(1 for line in lines if len(re.findall(r"\s{3,}|\t", line)) >= 2)
    return tabular >= 3


def has_currency(text: str) -> bool:
    """
    Check for currency values like $1,234.56 or standalone decimals like 99.50.
    """
    return bool(re.search(r"[\$€£]\s*[\d,]+\.?\d*|\d+\.\d{2}", text or ""))

def looks_like_first_page(text: str, page_num: int) -> bool:
    """
    Does this page look like the beginning of a new document?
    Used by Stage 3 for boundary detection.
    """
    if not text:
        return page_num == 0

    page_x, _ = detect_page_x_of_y(text)
    if page_x == 1:
        return True

    text_lower = text.lower()
    first_page_signals = [
        r"\binvoice\b.*\b(number|#|no\.?)\b",
        r"\bbill\s+to\b",
        r"\bstatement\s+date\b",
        r"\bpayroll\s+register\b",
        r"\bdaily\s+flash\s+report\b",
        r"\bmanager.?s?\s+report\b",
        r"\bdaily\s+closing\s+report\b",
        r"\bdayend\s+close\s+report\b",
        r"\btrial\s+balance\b",
        r"\bfinal\s+audit\b",
        r"\bnight\s+audit\b",
        r"\bstar\s*monthly\s*report\b",
    ]
    return any(re.search(p, text_lower) for p in first_page_signals)


# ─────────────────────────────────────────────
# PageFeatures builder (KEPT — same logic, now includes Textract data)
# ─────────────────────────────────────────────
def build_page_features(
    text: str,
    page_num: int,
    textract_tables: list = None,
    textract_kv_pairs: list = None,
    bounding_boxes: list = None,
) -> PageFeatures:
    """
    Compute ALL features for one page.
    Takes raw text (from Textract) and optional structured data.
    """
    pf = PageFeatures(page_num=page_num)
    pf.text = text or ""
    pf.extraction_method = "textract"
    pf.char_count = len(pf.text)
    pf.word_count = len(pf.text.split())
    pf.line_count = pf.text.count("\n") + 1

    # Keyword scores — these become input features for the SVM
    pf.invoice_kw_score = compute_keyword_score(pf.text, INVOICE_KEYWORDS)
    pf.pms_kw_score = compute_keyword_score(pf.text, PMS_KEYWORDS)
    pf.payroll_kw_score = compute_keyword_score(pf.text, PAYROLL_KEYWORDS)
    pf.str_kw_score = compute_keyword_score(pf.text, STR_KEYWORDS)

    # Structural signals
    pf.page_x, pf.page_y = detect_page_x_of_y(pf.text)
    pf.has_page_x_of_y = pf.page_x is not None
    pf.numeric_ratio = compute_numeric_ratio(pf.text)

    # Table detection: prefer Textract's table detection, fall back to text heuristic
    pf.textract_tables = textract_tables or []
    pf.has_table_structure = len(pf.textract_tables) > 0 or has_table_structure(pf.text)

    pf.has_currency_values = has_currency(pf.text)
    pf.is_likely_first_page = looks_like_first_page(pf.text, page_num)

    # Textract-specific structured data
    pf.textract_kv_pairs = textract_kv_pairs or []
    pf.bounding_boxes = bounding_boxes or []

    return pf

# ─────────────────────────────────────────────
# Textract JSON parsing (NEW — replaces all old extractors)
# ─────────────────────────────────────────────

def _group_blocks_by_page(blocks: list) -> dict:
    """
    Group Textract Block objects by their page number.
    Returns {page_num: [blocks]} dict.

    Textract blocks have a "Page" field (1-indexed).
    PAGE blocks define the page, LINE blocks contain the text,
    TABLE/CELL blocks contain structured table data,
    KEY_VALUE_SET blocks contain form key-value pairs.
    """
    pages = defaultdict(list)
    for block in blocks:
        page_num = block.get("Page", 1)
        pages[page_num].append(block)
    return dict(pages)


def _extract_text_for_page(blocks: list) -> str:
    """
    Extract raw text from LINE blocks for one page.
    LINE blocks contain the readable text in reading order.
    """
    lines = []
    for block in blocks:
        if block.get("BlockType") == "LINE":
            lines.append(block.get("Text", ""))
    return "\n".join(lines)

def _extract_tables_for_page(blocks: list) -> list:
    """
    Extract structured table data from TABLE and CELL blocks for one page.

    Textract represents tables as:
      TABLE block → has Relationships pointing to CELL blocks
      CELL block → has RowIndex, ColumnIndex, and Text

    Returns a list of tables, each table is a list of rows,
    each row is a list of cell text values.
    """
    # Find all TABLE blocks on this page
    table_blocks = [b for b in blocks if b.get("BlockType") == "TABLE"]
    if not table_blocks:
        return []

    # Build a block ID → block lookup for resolving relationships
    block_map = {b["Id"]: b for b in blocks}

    tables = []
    for table_block in table_blocks:
        # Get the CELL block IDs from the TABLE's relationships
        cell_ids = []
        for rel in table_block.get("Relationships", []):
            if rel.get("Type") == "CHILD":
                cell_ids.extend(rel.get("Ids", []))

        # Build the table grid from cells
        rows = defaultdict(dict)
        for cell_id in cell_ids:
            cell = block_map.get(cell_id)
            if cell and cell.get("BlockType") == "CELL":
                row_idx = cell.get("RowIndex", 1)
                col_idx = cell.get("ColumnIndex", 1)

                # Get cell text from child WORD blocks
                cell_text = ""
                for rel in cell.get("Relationships", []):
                    if rel.get("Type") == "CHILD":
                        words = [block_map.get(wid, {}).get("Text", "")
                                 for wid in rel.get("Ids", [])]
                        cell_text = " ".join(words)
                rows[row_idx][col_idx] = cell_text

        # Convert to list of lists
        if rows:
            max_row = max(rows.keys())
            max_col = max(max(cols.keys()) for cols in rows.values())
            table = []
            for r in range(1, max_row + 1):
                row = [rows.get(r, {}).get(c, "") for c in range(1, max_col + 1)]
                table.append(row)
            tables.append(table)

    return tables

def _extract_kv_pairs_for_page(blocks: list) -> list:
    """
    Extract key-value pairs from KEY_VALUE_SET blocks for one page.

    Textract detects form-like fields:
      KEY block → "Invoice Number"
      VALUE block → "12345"

    Returns list of {"key": "...", "value": "..."} dicts.
    Very useful for invoices (Invoice #, Date, Total Due, etc.)
    """
    block_map = {b["Id"]: b for b in blocks}

    # Find KEY blocks (they have EntityTypes containing "KEY")
    key_blocks = [
        b for b in blocks
        if b.get("BlockType") == "KEY_VALUE_SET"
        and "KEY" in b.get("EntityTypes", [])
    ]

    kv_pairs = []
    for key_block in key_blocks:
        # Get the key text
        key_text = _get_text_from_relationships(key_block, block_map, "CHILD")

        # Find the linked VALUE block
        value_text = ""
        for rel in key_block.get("Relationships", []):
            if rel.get("Type") == "VALUE":
                for val_id in rel.get("Ids", []):
                    val_block = block_map.get(val_id)
                    if val_block:
                        value_text = _get_text_from_relationships(
                            val_block, block_map, "CHILD"
                        )

        if key_text:
            kv_pairs.append({"key": key_text, "value": value_text})

    return kv_pairs

def _get_text_from_relationships(block: dict, block_map: dict, rel_type: str) -> str:
    """Helper: get text from a block's child WORD blocks."""
    words = []
    for rel in block.get("Relationships", []):
        if rel.get("Type") == rel_type:
            for child_id in rel.get("Ids", []):
                child = block_map.get(child_id)
                if child and child.get("BlockType") == "WORD":
                    words.append(child.get("Text", ""))
    return " ".join(words)


def _extract_bounding_boxes_for_page(blocks: list) -> list:
    """
    Extract bounding box coordinates for layout analysis.
    Returns list of {"type": block_type, "bbox": {Left, Top, Width, Height}} dicts.
    Useful for detecting document structure — headers, footers, columns.
    """
    boxes = []
    for block in blocks:
        if block.get("BlockType") in ("LINE", "TABLE", "KEY_VALUE_SET"):
            geo = block.get("Geometry", {}).get("BoundingBox", {})
            if geo:
                boxes.append({
                    "type": block.get("BlockType"),
                    "bbox": geo,
                })
    return boxes

# ─────────────────────────────────────────────
# Page sampling (NEW — for large files)
# ─────────────────────────────────────────────

def _select_sample_pages(total_pages: int) -> list:
    """
    Select which pages to process for large documents.
    Strategy: first 2 + last 2 pages (as recommended by the manager).
    Most classification markers (headers, footers, titles) are on these pages.

    Args:
        total_pages: Total number of pages in the document

    Returns:
        List of page numbers (1-indexed, matching Textract's convention)
    """
    if total_pages <= MAX_SAMPLE_PAGES:
        # Small file — process all pages
        return list(range(1, total_pages + 1))

    # First 2 + last 2
    first_pages = [1, 2]
    last_pages = [total_pages - 1, total_pages]

    # Remove duplicates (if file is 3-4 pages, there could be overlap)
    sample = sorted(set(first_pages + last_pages))
    return sample

# ─────────────────────────────────────────────
# Main entry point (NEW — replaces old extract() dispatcher)
# ─────────────────────────────────────────────

def extract_features(textract_response: dict) -> list[PageFeatures]:
    """
    Parse Textract JSON response into PageFeatures objects.

    This replaces ALL the old extractors (extract_pdf, extract_image, etc.).
    Textract handles every file format, so we only need one parser.

    Args:
        textract_response: Raw Textract API response from Stage 1

    Returns:
        list[PageFeatures] — one per processed page, ready for Stage 3
    """
    blocks = textract_response.get("Blocks", [])
    if not blocks:
        log.warning("Textract returned no blocks")
        return [build_page_features("", 0)]

    # Group blocks by page number
    pages_blocks = _group_blocks_by_page(blocks)
    total_pages = len(pages_blocks)

    # Determine which pages to process (sampling for large files)
    pages_to_process = _select_sample_pages(total_pages)
    if len(pages_to_process) < total_pages:
        log.info(f"  Sampling {len(pages_to_process)}/{total_pages} pages (first 2 + last 2)")

    # Extract features for each selected page
    features = []
    for page_num in pages_to_process:
        page_blocks = pages_blocks.get(page_num, [])

        text = _extract_text_for_page(page_blocks)
        tables = _extract_tables_for_page(page_blocks)
        kv_pairs = _extract_kv_pairs_for_page(page_blocks)
        bboxes = _extract_bounding_boxes_for_page(page_blocks)

        # page_num is 1-indexed from Textract, convert to 0-indexed for our model
        pf = build_page_features(
            text=text,
            page_num=page_num - 1,
            textract_tables=tables,
            textract_kv_pairs=kv_pairs,
            bounding_boxes=bboxes,
        )
        features.append(pf)

    log.info(f"  Extracted features for {len(features)} pages ({total_pages} total in document)")
    return features

