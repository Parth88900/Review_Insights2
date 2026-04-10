"""Text preprocessing utilities for cleaning and normalizing review text."""

import re
import html
import unicodedata
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

# Common noise patterns in scraped reviews
NOISE_PATTERNS = [
    r'Read more$',
    r'Was this review helpful\?',
    r'Report abuse',
    r'Verified Purchase',
    r'Reviewed in .+ on .+',
    r'^\d+ people found this helpful\.?$',
    r'See more$',
    r'Show less$',
    r'Helpful$',
    r'^\s*$',
]

COMPILED_NOISE = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in NOISE_PATTERNS]


def clean_text(text: str) -> str:
    """
    Clean and normalize review text.

    Steps:
    1. Decode HTML entities
    2. Normalize unicode characters
    3. Remove excessive whitespace
    4. Remove common noise patterns
    5. Fix encoding issues
    """
    if not text:
        return ""

    # Decode HTML entities
    text = html.unescape(text)

    # Normalize unicode (NFC form)
    text = unicodedata.normalize("NFC", text)

    # Replace common unicode characters with ASCII equivalents
    replacements = {
        '\u2018': "'", '\u2019': "'",  # Smart single quotes
        '\u201c': '"', '\u201d': '"',  # Smart double quotes
        '\u2013': '-', '\u2014': '-',  # En/Em dashes
        '\u2026': '...',               # Ellipsis
        '\u00a0': ' ',                 # Non-breaking space
        '\u200b': '',                  # Zero-width space
        '\ufeff': '',                  # BOM
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove control characters (keep newlines and tabs)
    text = ''.join(
        ch for ch in text
        if ch in ('\n', '\t') or not unicodedata.category(ch).startswith('C')
    )

    # Remove noise patterns
    for pattern in COMPILED_NOISE:
        text = pattern.sub('', text)

    # Collapse multiple newlines into double newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Collapse multiple spaces
    text = re.sub(r' {2,}', ' ', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def chunk_text(text: str, max_tokens: int = 3000, overlap: int = 200) -> List[str]:
    """
    Split long text into overlapping chunks for LLM processing.

    Uses approximate token counting (1 token ≈ 4 chars).
    """
    max_chars = max_tokens * 4
    overlap_chars = overlap * 4

    if len(text) <= max_chars:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chars

        # Try to break at a sentence boundary
        if end < len(text):
            # Look back from end for a period, exclamation, or question mark
            boundary = text.rfind('. ', start + max_chars // 2, end)
            if boundary == -1:
                boundary = text.rfind('! ', start + max_chars // 2, end)
            if boundary == -1:
                boundary = text.rfind('? ', start + max_chars // 2, end)
            if boundary != -1:
                end = boundary + 1

        chunks.append(text[start:end].strip())
        start = end - overlap_chars

    return chunks


def prepare_reviews_for_analysis(reviews_text: List[str]) -> str:
    """
    Combine multiple review texts into a single formatted string for LLM analysis.
    """
    formatted = []
    for i, text in enumerate(reviews_text, 1):
        cleaned = clean_text(text)
        if cleaned:
            formatted.append(f"[Review {i}]: {cleaned}")

    return "\n\n".join(formatted)


def extract_rating_from_text(text: str) -> Optional[float]:
    """Attempt to extract a numeric rating from text."""
    patterns = [
        r'(\d+(?:\.\d+)?)\s*(?:out of|/)\s*5',
        r'(\d+(?:\.\d+)?)\s*star',
        r'rating:\s*(\d+(?:\.\d+)?)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            val = float(match.group(1))
            if 0 <= val <= 5:
                return val
    return None
