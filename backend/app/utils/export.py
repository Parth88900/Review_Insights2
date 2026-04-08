"""Data export utilities for structured output."""

import json
import csv
import io
import logging
from typing import List

import pandas as pd

from app.models.schemas import AnalyzeResponse, ReviewData

logger = logging.getLogger(__name__)


def to_dataframe(reviews: List[ReviewData]) -> pd.DataFrame:
    """Convert review data to a Pandas DataFrame."""
    records = []
    for review in reviews:
        records.append({
            "id": review.id,
            "author": review.author,
            "rating": review.rating,
            "date": review.date,
            "title": review.title,
            "text": review.text[:500],  # Truncate for readability
            "verified": review.verified,
            "helpful_count": review.helpful_count,
            "sentiment": review.sentiment.value if review.sentiment else None,
            "sentiment_score": review.sentiment_score,
            "key_phrases": ", ".join(review.key_phrases) if review.key_phrases else "",
        })
    return pd.DataFrame(records)


def to_json(response: AnalyzeResponse) -> str:
    """Export full analysis response to formatted JSON string."""
    return response.model_dump_json(indent=2)


def to_csv(reviews: List[ReviewData]) -> str:
    """Export reviews to CSV format string."""
    df = to_dataframe(reviews)
    output = io.StringIO()
    df.to_csv(output, index=False, quoting=csv.QUOTE_ALL)
    return output.getvalue()


def save_results(response: AnalyzeResponse, filepath: str = "data/results.json"):
    """Save analysis results to a JSON file."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(to_json(response))
        logger.info(f"Results saved to {filepath}")
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
