"""Pydantic models for request/response schemas."""

from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional
from datetime import datetime
from enum import Enum


class SentimentLabel(str, Enum):
    """Sentiment classification labels."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class AnalyzeRequest(BaseModel):
    """Request schema for the analyze endpoint."""
    url: str = Field(..., description="Product URL to scrape reviews from")
    max_reviews: int = Field(default=20, ge=1, le=100, description="Maximum number of reviews to analyze")


class ReviewData(BaseModel):
    """Schema for a single scraped review."""
    id: str = Field(..., description="Unique review identifier")
    author: str = Field(default="Anonymous", description="Review author name")
    rating: Optional[float] = Field(default=None, ge=1, le=5, description="Star rating")
    date: Optional[str] = Field(default=None, description="Review date")
    title: Optional[str] = Field(default=None, description="Review title/headline")
    text: str = Field(..., description="Review body text")
    verified: bool = Field(default=False, description="Whether purchase is verified")
    helpful_count: int = Field(default=0, description="Number of helpful votes")
    sentiment: Optional[SentimentLabel] = Field(default=None, description="Sentiment label")
    sentiment_score: Optional[float] = Field(default=None, ge=-1, le=1, description="Sentiment score (-1 to 1)")
    key_phrases: List[str] = Field(default_factory=list, description="Key phrases extracted")


class ThemeData(BaseModel):
    """Schema for an extracted theme from reviews."""
    name: str = Field(..., description="Theme label")
    count: int = Field(..., description="Number of reviews mentioning this theme")
    sentiment: SentimentLabel = Field(..., description="Overall sentiment of this theme")
    sample_quotes: List[str] = Field(default_factory=list, description="Representative quotes")


class AnalysisSummary(BaseModel):
    """Schema for the overall analysis summary."""
    overall_sentiment: SentimentLabel
    overall_score: float = Field(..., ge=-1, le=1, description="Aggregate sentiment score")
    total_reviews: int
    positive_count: int
    negative_count: int
    neutral_count: int
    average_rating: Optional[float] = None
    summary_text: str = Field(..., description="LLM-generated executive summary")
    strengths: List[str] = Field(default_factory=list, description="Key product strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Key product weaknesses")
    recommendation: str = Field(default="", description="Purchase recommendation")


class AnalyzeResponse(BaseModel):
    """Response schema for the analyze endpoint."""
    success: bool = True
    product_name: Optional[str] = None
    product_image: Optional[str] = None
    source_url: str
    analyzed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    reviews: List[ReviewData]
    themes: List[ThemeData]
    summary: AnalysisSummary


class ErrorResponse(BaseModel):
    """Schema for error responses."""
    success: bool = False
    error: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
