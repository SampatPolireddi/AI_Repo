"""
Stage 3: Boundary Detection

The aim is when given a list of PageFeatures (from Stage 2),  we hv to determine where one logical
document ends and the next begins within a single file.

Input:  list[PageFeatures] from Stage 2
Output: list[tuple[int, int]] — (start_page, end_page) pairs, 0-indexed, inclusive

Detection signals (priority order):
  1. "Page 1 of Y" markers — most reliable, means a new document starts here
  2. First-page classifier — looks for headers like "Invoice Number", "Trial Balance"
  3. Class shift — the dominant keyword category changes between consecutive pages
  4. Fallback — if nothing triggers, the entire file is one document

Special handling:
  When Stage 2 samples pages (e.g. pages 0,1,18,19 from a 20-page file),
  there's a gap in page numbers. We detect this and avoid false boundaries
  at the gap.
"""
import logging
from models import PageFeatures

log = logging.getLogger(__name__)

def _is_sampling_gap(current:PageFeatures, previous: PageFeatures)-> bool:
    """
    Checking if there's a page sampling gap between two consecutive PageFeatures
    
    When Stage 2 samples pages (first 2 + last 2), we might get pages
    with page_num [0, 1, 18, 19]. The jump from 1 to 18 is a sampling gap,
    NOT a document boundary. Without this check, the content difference
    between page 1 and page 18 could trigger a false boundary.

    Returns True if there's a gap (pages were skipped between them).
    """
    return current.page_num-previous.page_num > 1

def _dominant_class(pf: PageFeatures) -> str:
    """
    Which document class has the highest keyword score for this page?
    Returns "ambiguous" if all scores are below 0.1.
    """
    scores = {
        "invoice": pf.invoice_kw_score,
        "pms": pf.pms_kw_score,
        "payroll": pf.payroll_kw_score,
        "str": pf.str_kw_score,
    }
    max_score = max(scores.values())
    if max_score < 0.1:
        return "ambiguous"
    return max(scores, key=scores.get)

def detect_boundaries(pages:list[PageFeatures])-> list[tuple[int,int]]:
    """
    Identifies logical document boundaries within a sequence of pages
    
    Args:
        pages: Ordered list of PageFeatures from Stage 2
    
    Returns:
        List of (start_page, end_page) tuples, 0-indexed, inclusive.
        Each tuple defines one logical document segment.

    Examples:
        Single-page file → [(0, 0)]
        10-page file, boundary at page 3 → [(0, 2), (3, 9)]
        Sampled file (pages 0,1,18,19), no real boundary → [(0, 19)]
    """
    if not pages:
        return []
    if len(pages) == 1:
        return [(0,0)]
    
    boundaries = []
    current_start = pages[0].page_num
    
    for i in range(1,len(pages)):
        pf = pages[i]
        prev = pages[i-1]
        
        # Skip boundary detection across sampling gaps
        # A gap means Stage 2 skipped pages — we can't know what's in between
        if _is_sampling_gap(pf, prev):
            log.debug(
                f"  Sampling gap: page {prev.page_num} → {pf.page_num}, skipping boundary check"
            )
            continue

        is_boundary = False
    
    # ── Signal 1: "Page 1 of Y" marker ──
        # Most reliable. If this page says "Page 1 of N",
        # a new document definitely starts here.
        if pf.page_x == 1 and pf.has_page_x_of_y:
            is_boundary = True
            log.debug(f"  Boundary at page {pf.page_num}: Page 1 of {pf.page_y}")

    # ── Signal 2: First-page classifier ──
        # The page has strong "beginning of document" signals
        elif pf.is_likely_first_page:

            # Previous page was the last of its document (Page N of N)
            if prev.has_page_x_of_y and prev.page_x == prev.page_y:
                is_boundary = True
                log.debug(
                    f"  Boundary at page {pf.page_num}: "
                    f"prev was last page ({prev.page_x}/{prev.page_y})"
                )
       
            # Dominant keyword class changed (invoice → PMS report, etc.)
            elif (_dominant_class(pf) != _dominant_class(prev)
                  and _dominant_class(pf) != "ambiguous"):
                is_boundary = True
                log.debug(
                    f"  Boundary at page {pf.page_num}: "
                    f"class shift {_dominant_class(prev)} → {_dominant_class(pf)}"
                )

            # Strong first-page signal here, none on previous page
            elif not prev.is_likely_first_page:
                is_boundary = True
                log.debug(f"  Boundary at page {pf.page_num}: first-page signal detected")

        # ── Signal 3: Keyword score shift without first-page signal ──
        # Both pages have strong scores but in different categories
        elif i > 0:
            max_prev = max(prev.invoice_kw_score, prev.pms_kw_score, prev.payroll_kw_score)
            max_curr = max(pf.invoice_kw_score, pf.pms_kw_score, pf.payroll_kw_score)
            if max_prev > 0.3 and max_curr > 0.3:
                if _dominant_class(pf) != _dominant_class(prev):
                    is_boundary = True
                    log.debug(f"  Boundary at page {pf.page_num}: score shift detected")
        
        if is_boundary:
            boundaries.append((current_start, prev.page_num))
            current_start = pf.page_num
        
    # Close the last segment
    boundaries.append((current_start, pages[-1].page_num))

    log.info(f"  Found {len(boundaries)} document segment(s) across {len(pages)} pages")
    return boundaries

        