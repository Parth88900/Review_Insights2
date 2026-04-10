import asyncio
import time
from app.services.scraper import ReviewScraper
from app.services.analyzer import LLMAnalyzer
from app.models.schemas import AnalyzeRequest
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    url = "https://www.amazon.in/Apple-New-iPhone-12-128GB/dp/B08L5TNJHG/"
    scraper = ReviewScraper()
    analyzer = LLMAnalyzer()
    
    t0 = time.time()
    reviews, name, img = await scraper.scrape(url, 20)
    t1 = time.time()
    print(f"Scraping took {t1-t0:.2f} seconds. Got {len(reviews)} reviews.")
    
    reviews = await analyzer.analyze_sentiments(reviews)
    t2 = time.time()
    print(f"Sentiment analysis took {t2-t1:.2f} seconds.")
    
    summary, themes = await analyzer.generate_summary(reviews)
    t3 = time.time()
    print(f"Summary took {t3-t2:.2f} seconds.")
    print(f"Total time: {t3-t0:.2f} seconds.")

if __name__ == "__main__":
    asyncio.run(main())
