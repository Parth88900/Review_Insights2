"""API route definitions."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    ErrorResponse,
    HealthResponse,
)
from app.services.scraper import ReviewScraper, ScrapingError
from app.services.analyzer import LLMAnalyzer, LLMError
from app.utils.export import save_results

logger = logging.getLogger(__name__)

router = APIRouter()

# Service instances
scraper = ReviewScraper()
analyzer = LLMAnalyzer()


@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    tags=["Analysis"],
)
async def analyze_reviews(request: AnalyzeRequest):
    """
    Analyze product reviews from the given URL.

    Steps:
    1. Scrape reviews from the product page
    2. Preprocess and clean review text
    3. Analyze sentiment using LLM
    4. Generate executive summary and extract themes
    5. Return structured results
    """
    logger.info(f"Starting analysis for URL: {request.url}")

    # Step 1: Scrape reviews
    try:
        reviews, product_name, product_image = await scraper.scrape(
            request.url, request.max_reviews
        )
    except ScrapingError as e:
        logger.error(f"Scraping failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected scraping error: {e}")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while scraping reviews. Please try again.",
        )

    if not reviews:
        raise HTTPException(
            status_code=400,
            detail="No reviews found on the provided page. Please check the URL and try again.",
        )

    logger.info(f"Scraped {len(reviews)} reviews for: {product_name or 'Unknown Product'}")

    # Step 2 & 3: Analyze sentiment
    try:
        reviews = await analyzer.analyze_sentiments(reviews)
    except LLMError as e:
        logger.warning(f"LLM analysis partially failed (using fallbacks): {e}")
    except Exception as e:
        logger.error(f"Sentiment analysis error: {e}")
        # Continue with whatever sentiment data we have

    # Step 4: Generate summary and themes
    try:
        summary, themes = await analyzer.generate_summary(reviews)
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        # Create a minimal summary
        from app.models.schemas import AnalysisSummary, SentimentLabel

        pos = sum(1 for r in reviews if r.sentiment == SentimentLabel.POSITIVE)
        neg = sum(1 for r in reviews if r.sentiment == SentimentLabel.NEGATIVE)
        scores = [r.sentiment_score for r in reviews if r.sentiment_score is not None]
        avg = sum(scores) / len(scores) if scores else 0

        summary = AnalysisSummary(
            overall_sentiment=SentimentLabel.NEUTRAL,
            overall_score=round(avg, 2),
            total_reviews=len(reviews),
            positive_count=pos,
            negative_count=neg,
            neutral_count=len(reviews) - pos - neg,
            summary_text=f"Analysis of {len(reviews)} reviews. {pos} positive, {neg} negative.",
            recommendation="Review analysis completed with limited insights.",
        )
        themes = []

    # Step 5: Build response
    response = AnalyzeResponse(
        product_name=product_name,
        product_image=product_image,
        source_url=request.url,
        analyzed_at=datetime.utcnow().isoformat(),
        reviews=reviews,
        themes=themes,
        summary=summary,
    )

    # Save results asynchronously
    try:
        save_results(response)
    except Exception:
        pass  # Non-critical

    logger.info(f"Analysis complete: {len(reviews)} reviews processed")
    return response


@router.get("/export/{format}", tags=["Export"])
async def export_results(format: str):
    """Export the last analysis results in the specified format."""
    import os
    from fastapi.responses import PlainTextResponse, JSONResponse

    results_path = "data/results.json"
    if not os.path.exists(results_path):
        raise HTTPException(status_code=404, detail="No results available. Run an analysis first.")

    with open(results_path, "r") as f:
        data = f.read()

    if format == "json":
        return JSONResponse(content=__import__("json").loads(data))
    elif format == "csv":
        from app.utils.export import to_csv
        response_data = AnalyzeResponse.model_validate_json(data)
        csv_content = to_csv(response_data.reviews)
        return PlainTextResponse(content=csv_content, media_type="text/csv")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}. Use 'json' or 'csv'.")
