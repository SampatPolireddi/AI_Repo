from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class DocClass(str, Enum):
    INVOICE = "invoice"
    PMS_REPORT = "pms_report"
    PAYROLL = "payroll"
    STR_REPORT = "str_report"
    OTHER = "other"


@dataclass
class PageFeatures:
    page_num: int

    # Raw text (extracted from Textract blocks)
    text: str = ""
    char_count: int = 0
    word_count: int = 0
    line_count: int = 0

    # Keyword density scores (0.0 to 1.0)
    # These become INPUT FEATURES for the SVM, not the classifier itself
    invoice_kw_score: float = 0.0
    pms_kw_score: float = 0.0
    payroll_kw_score: float = 0.0
    str_kw_score: float = 0.0

    # Structural signals
    has_page_x_of_y: bool = False
    page_x: Optional[int] = None
    page_y: Optional[int] = None
    numeric_ratio: float = 0.0
    has_table_structure: bool = False
    has_currency_values: bool = False
    
    # Extraction metadata
    is_scanned: bool = False
    extraction_method: str = ""  # "textract", "textract_table", etc.

    # Boundary signal
    is_likely_first_page: bool = False

    # Textract-specific data (extracted from Textract Block objects)
    # Tables detected by Textract on this page — each entry is a list of rows
    textract_tables: list = field(default_factory=list)
    # Key-value pairs detected (e.g. "Invoice Number" → "12345")
    textract_kv_pairs: list = field(default_factory=list)
    # Bounding box info for layout analysis
    bounding_boxes: list = field(default_factory=list)
    
@dataclass
class DocumentSegment:
    source_file: str
    start_page: int   # 0-indexed
    end_page: int     # inclusive
    page_count: int = 0

    # Classification (filled by Phase 1: SVM)
    doc_class: DocClass = DocClass.OTHER
    confidence: float = 0.0
    tags: list = field(default_factory=list)

    # Aggregated keyword scores (used as SVM features)
    total_invoice_score: float = 0.0
    total_pms_score: float = 0.0
    total_payroll_score: float = 0.0
    total_str_score: float = 0.0

    # Preview text
    summary_text: str = ""

    # S3 reference — the original file lives in S3, we only pass the key
    s3_key: str = ""

    # Human-in-the-loop flag
    # Set to True when both SVM and agents are below confidence threshold
    # Marks the document for manual review in MongoDB
    needs_human_review: bool = False

    # Agent reasoning (filled by Phase 2: AutoGen agents)
    # Stores the Manager agent's explanation for its final decision
    agent_reasoning: str = ""
