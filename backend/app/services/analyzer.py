"""LLM-powered review analysis service using OpenAI-compatible API."""

import json
import logging
from typing import Dict, List, Optional, Tuple

from openai import AsyncOpenAI, APIConnectionError, RateLimitError, APIStatusError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings
from app.models.schemas import (
    AnalysisSummary,
    ReviewData,
    SentimentLabel,
    ThemeData,
)
from app.services.preprocessor import clean_text, prepare_reviews_for_analysis

logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = AsyncOpenAI(
    api_key=settings.openai_api_key,
    base_url=settings.openai_base_url
)


SENTIMENT_SYSTEM_PROMPT = """You are an expert product review analyst. Analyze the sentiment of each review and provide structured output.

For each review, determine:
1. Sentiment: "positive", "negative", "neutral", or "mixed"
2. Sentiment score: A float from -1.0 (most negative) to 1.0 (most positive)
3. Key phrases: 2-4 short phrases capturing the main points

IMPORTANT: Respond ONLY with valid JSON in this exact format:
{
  "reviews": [
    {
      "index": 1,
      "sentiment": "positive",
      "score": 0.85,
      "key_phrases": ["great battery life", "excellent display"]
    }
  ]
}"""

SUMMARY_SYSTEM_PROMPT = """You are a senior product analyst writing an executive review summary. Based on the provided reviews and sentiment data, create a comprehensive analysis.

IMPORTANT: Respond ONLY with valid JSON in this exact format:
{
  "summary_text": "A 2-3 sentence executive summary of the product based on reviews",
  "strengths": ["strength 1", "strength 2", "strength 3"],
  "weaknesses": ["weakness 1", "weakness 2"],
  "recommendation": "A one-sentence purchase recommendation",
  "themes": [
    {
      "name": "Theme Name",
      "count": 5,
      "sentiment": "positive",
      "sample_quotes": ["relevant quote from a review"]
    }
  ]
}"""


class LLMAnalyzer:
    """Handles all LLM-based analysis of product reviews."""

    def __init__(self):
        self.model = settings.openai_model

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Retrying LLM call (attempt {retry_state.attempt_number})..."
        ),
    )
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Make a rate-limited, retrying call to the LLM API."""
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )
            return response.choices[0].message.content
        except RateLimitError:
            logger.warning("Rate limit hit, will retry...")
            raise
        except APIConnectionError:
            logger.warning("API connection error, will retry...")
            raise
        except APIStatusError as e:
            logger.error(f"API error: {e.status_code} - {e.message}")
            raise LLMError(f"API error: {e.message}")
        except Exception as e:
            logger.error(f"Unexpected LLM error: {str(e)}")
            raise LLMError(f"LLM analysis failed: {str(e)}")

    async def analyze_sentiments(self, reviews: List[ReviewData]) -> List[ReviewData]:
        """Analyze sentiment for each review using the LLM."""
        if not reviews:
            return reviews

        # Prepare review texts for the LLM
        review_texts = []
        for i, review in enumerate(reviews, 1):
            cleaned = clean_text(review.text)
            entry = f"[Review {i}]"
            if review.title:
                entry += f" Title: {review.title}."
            entry += f" {cleaned}"
            review_texts.append(entry)

        combined = "\n\n".join(review_texts)

        # Process in batches if there are many reviews
        batch_size = 50
        for batch_start in range(0, len(reviews), batch_size):
            batch_end = min(batch_start + batch_size, len(reviews))
            batch_texts = review_texts[batch_start:batch_end]
            batch_combined = "\n\n".join(batch_texts)

            prompt = f"Analyze the sentiment of these {len(batch_texts)} product reviews:\n\n{batch_combined}"

            try:
                result = await self._call_llm(SENTIMENT_SYSTEM_PROMPT, prompt)
                parsed = json.loads(result)

                for item in parsed.get("reviews", []):
                    idx = item.get("index", 0) - 1 + batch_start
                    if 0 <= idx < len(reviews):
                        reviews[idx].sentiment = SentimentLabel(item.get("sentiment", "neutral"))
                        reviews[idx].sentiment_score = max(-1, min(1, float(item.get("score", 0))))
                        reviews[idx].key_phrases = item.get("key_phrases", [])

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM sentiment response: {e}")
                # Fallback: assign neutral sentiment
                for i in range(batch_start, batch_end):
                    if reviews[i].sentiment is None:
                        reviews[i].sentiment = self._fallback_sentiment(reviews[i])
                        reviews[i].sentiment_score = 0.0
            except LLMError:
                # Fallback to heuristic sentiment
                for i in range(batch_start, batch_end):
                    if reviews[i].sentiment is None:
                        reviews[i].sentiment = self._fallback_sentiment(reviews[i])
                        reviews[i].sentiment_score = self._fallback_score(reviews[i])

        # Ensure all reviews have sentiment
        for review in reviews:
            if review.sentiment is None:
                review.sentiment = self._fallback_sentiment(review)
                review.sentiment_score = self._fallback_score(review)

        return reviews

    async def generate_summary(
        self, reviews: List[ReviewData]
    ) -> Tuple[AnalysisSummary, List[ThemeData]]:
        """Generate an executive summary and extract themes from reviews."""
        # Compute basic stats (using fallbacks if sentiment is not yet populated sequentially)
        sentiments = [r.sentiment or self._fallback_sentiment(r) for r in reviews]
        scores = [r.sentiment_score if r.sentiment_score is not None else self._fallback_score(r) for r in reviews]
        ratings = [r.rating for r in reviews if r.rating is not None]

        positive_count = sum(1 for s in sentiments if s == SentimentLabel.POSITIVE)
        negative_count = sum(1 for s in sentiments if s == SentimentLabel.NEGATIVE)
        neutral_count = sum(1 for s in sentiments if s in (SentimentLabel.NEUTRAL, SentimentLabel.MIXED))

        avg_score = sum(scores) / len(scores) if scores else 0.0
        avg_rating = sum(ratings) / len(ratings) if ratings else None

        # Determine overall sentiment
        if avg_score > 0.3:
            overall = SentimentLabel.POSITIVE
        elif avg_score < -0.3:
            overall = SentimentLabel.NEGATIVE
        elif positive_count > 0 and negative_count > 0:
            overall = SentimentLabel.MIXED
        else:
            overall = SentimentLabel.NEUTRAL

        # Prepare context for LLM summary
        review_context = []
        for r in reviews:
            r_sentiment = r.sentiment or self._fallback_sentiment(r)
            r_score = r.sentiment_score if r.sentiment_score is not None else self._fallback_score(r)
            entry = f"Rating: {r.rating}/5" if r.rating else "No rating"
            entry += f" | Sentiment: {r_sentiment.value}"
            entry += f" | Score: {r_score:.2f}"
            if r.title:
                entry += f"\nTitle: {r.title}"
            entry += f"\nReview: {clean_text(r.text)[:300]}"
            if r.key_phrases:
                entry += f"\nKey phrases: {', '.join(r.key_phrases)}"
            review_context.append(entry)

        prompt = f"""Product reviews summary request:

Total reviews: {len(reviews)}
Average rating: {f'{avg_rating:.1f}/5' if avg_rating else 'N/A'}
Positive: {positive_count} | Negative: {negative_count} | Neutral: {neutral_count}
Average sentiment score: {avg_score:.2f}

Reviews:
{'---'.join(review_context)}

Generate a comprehensive product analysis summary with themes, strengths, weaknesses, and a recommendation."""

        themes = []
        summary_text = ""
        strengths = []
        weaknesses = []
        recommendation = ""

        try:
            result = await self._call_llm(SUMMARY_SYSTEM_PROMPT, prompt)
            parsed = json.loads(result)

            summary_text = parsed.get("summary_text", "")
            strengths = parsed.get("strengths", [])
            weaknesses = parsed.get("weaknesses", [])
            recommendation = parsed.get("recommendation", "")

            for theme_data in parsed.get("themes", []):
                themes.append(ThemeData(
                    name=theme_data.get("name", "Unknown"),
                    count=theme_data.get("count", 1),
                    sentiment=SentimentLabel(theme_data.get("sentiment", "neutral")),
                    sample_quotes=theme_data.get("sample_quotes", []),
                ))

        except (json.JSONDecodeError, LLMError) as e:
            logger.error(f"Failed to generate LLM summary: {e}")
            summary_text = self._fallback_summary(reviews, positive_count, negative_count, avg_rating)
            recommendation = "Based on the available reviews, consider researching further before making a purchase decision."

        summary = AnalysisSummary(
            overall_sentiment=overall,
            overall_score=round(avg_score, 2),
            total_reviews=len(reviews),
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            average_rating=round(avg_rating, 1) if avg_rating else None,
            summary_text=summary_text,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendation=recommendation,
        )

        return summary, themes

    def _fallback_sentiment(self, review: ReviewData) -> SentimentLabel:
        """Simple heuristic-based sentiment when LLM is unavailable."""
        if review.rating is not None:
            if review.rating >= 4:
                return SentimentLabel.POSITIVE
            elif review.rating <= 2:
                return SentimentLabel.NEGATIVE
            else:
                return SentimentLabel.NEUTRAL

        # Keyword-based fallback
        text = review.text.lower()
        positive_words = {"great", "excellent", "amazing", "love", "perfect", "awesome", "best", "good", "fantastic", "wonderful"}
        negative_words = {"terrible", "awful", "worst", "hate", "horrible", "bad", "poor", "disappointing", "waste", "broken"}

        pos = sum(1 for w in positive_words if w in text)
        neg = sum(1 for w in negative_words if w in text)

        if pos > neg:
            return SentimentLabel.POSITIVE
        elif neg > pos:
            return SentimentLabel.NEGATIVE
        return SentimentLabel.NEUTRAL

    def _fallback_score(self, review: ReviewData) -> float:
        """Simple heuristic-based sentiment score."""
        if review.rating is not None:
            return (review.rating - 3) / 2  # Maps 1-5 to -1 to 1
        if review.sentiment == SentimentLabel.POSITIVE:
            return 0.5
        elif review.sentiment == SentimentLabel.NEGATIVE:
            return -0.5
        return 0.0

    def _fallback_summary(
        self,
        reviews: List[ReviewData],
        positive: int,
        negative: int,
        avg_rating: Optional[float],
    ) -> str:
        """Generate a basic summary when LLM is unavailable."""
        total = len(reviews)
        parts = [f"Analysis of {total} product reviews."]
        if avg_rating:
            parts.append(f"The average rating is {avg_rating:.1f} out of 5.")
        parts.append(f"{positive} reviews are positive, {negative} are negative, and {total - positive - negative} are neutral/mixed.")
        return " ".join(parts)


class LLMError(Exception):
    """Custom exception for LLM analysis failures."""
    pass
