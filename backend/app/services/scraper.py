"""Web scraping service for extracting product reviews."""

import asyncio
import hashlib
import logging
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

from app.core.config import settings
from app.models.schemas import ReviewData

logger = logging.getLogger(__name__)

# Initialize user agent rotator
try:
    ua = UserAgent()
except Exception:
    ua = None


def _get_headers() -> Dict[str, str]:
    """Generate realistic browser headers for anti-bot evasion."""
    user_agent = ua.random if ua else (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }


def _generate_review_id(text: str, author: str) -> str:
    """Generate a deterministic unique ID for a review."""
    content = f"{author}:{text[:100]}"
    return hashlib.md5(content.encode()).hexdigest()[:12]


def _detect_platform(url: str) -> str:
    """Detect which e-commerce platform the URL belongs to."""
    domain = urlparse(url).netloc.lower()
    if "amazon" in domain:
        return "amazon"
    elif "flipkart" in domain:
        return "flipkart"
    elif "bestbuy" in domain:
        return "bestbuy"
    elif "walmart" in domain:
        return "walmart"
    else:
        return "generic"


class ReviewScraper:
    """Handles scraping product reviews from various e-commerce platforms."""

    def __init__(self):
        self.delay = settings.scrape_delay_seconds

    async def scrape(self, url: str, max_reviews: int = 20) -> Tuple[List[ReviewData], Optional[str], Optional[str]]:
        """
        Scrape reviews from the given URL.

        Returns:
            Tuple of (reviews list, product name, product image URL)
        """
        platform = _detect_platform(url)
        logger.info(f"Detected platform: {platform} for URL: {url}")

        try:
            if platform == "amazon":
                return await self._scrape_amazon(url, max_reviews)
            elif platform == "flipkart":
                return await self._scrape_flipkart(url, max_reviews)
            else:
                return await self._scrape_generic(url, max_reviews)
        except Exception as e:
            logger.error(f"Scraping failed for {url}: {str(e)}")
            raise ScrapingError(f"Failed to scrape reviews: {str(e)}")

    async def _fetch_page(self, url: str) -> BeautifulSoup:
        """Fetch a page and return parsed HTML."""
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=30.0,
            headers=_get_headers()
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
            return BeautifulSoup(response.text, "lxml")

    async def _scrape_amazon(
        self, url: str, max_reviews: int
    ) -> Tuple[List[ReviewData], Optional[str], Optional[str]]:
        """Scrape reviews from Amazon product pages."""
        reviews = []
        product_name = None
        product_image = None

        # Convert product URL to reviews URL if needed
        reviews_url = self._amazon_reviews_url(url)
        page = 1

        while len(reviews) < max_reviews:
            paged_url = f"{reviews_url}&pageNumber={page}" if "?" in reviews_url else f"{reviews_url}?pageNumber={page}"
            logger.info(f"Fetching Amazon page {page}: {paged_url}")

            try:
                soup = await self._fetch_page(paged_url)
            except Exception as e:
                logger.warning(f"Failed to fetch page {page}: {e}")
                break

            # Extract product info from first page
            if page == 1:
                title_tag = soup.select_one("a[data-hook='product-link']")
                if title_tag:
                    product_name = title_tag.get_text(strip=True)
                img_tag = soup.select_one("img[data-hook='cr-product-image']")
                if img_tag:
                    product_image = img_tag.get("src")

            # Extract reviews
            review_cards = soup.select("div[data-hook='review']")
            if not review_cards:
                # Try alternate selectors
                review_cards = soup.select(".review")
                if not review_cards:
                    break

            for card in review_cards:
                if len(reviews) >= max_reviews:
                    break

                try:
                    review = self._parse_amazon_review(card)
                    if review:
                        reviews.append(review)
                except Exception as e:
                    logger.warning(f"Failed to parse review: {e}")
                    continue

            page += 1
            await asyncio.sleep(self.delay)

            # Safety check - don't paginate too far
            if page > 10:
                break

        return reviews, product_name, product_image

    def _amazon_reviews_url(self, url: str) -> str:
        """Convert an Amazon product URL to its reviews page URL."""
        # Extract ASIN
        asin_match = re.search(r'/dp/([A-Z0-9]{10})', url)
        if not asin_match:
            asin_match = re.search(r'/product-reviews/([A-Z0-9]{10})', url)
        if asin_match:
            asin = asin_match.group(1)
            parsed = urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            return f"{base}/product-reviews/{asin}/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews&sortBy=recent"
        return url

    def _parse_amazon_review(self, card) -> Optional[ReviewData]:
        """Parse a single Amazon review card into ReviewData."""
        # Extract rating
        rating = None
        rating_el = card.select_one("i[data-hook='review-star-rating'] span, i[data-hook='cmps-review-star-rating'] span")
        if rating_el:
            rating_text = rating_el.get_text(strip=True)
            match = re.search(r'(\d+\.?\d*)', rating_text)
            if match:
                rating = float(match.group(1))

        # Extract title
        title = None
        title_el = card.select_one("a[data-hook='review-title'] span:last-child, span[data-hook='review-title'] span:last-child")
        if title_el:
            title = title_el.get_text(strip=True)

        # Extract text
        text_el = card.select_one("span[data-hook='review-body'] span")
        if not text_el:
            text_el = card.select_one("span[data-hook='review-body']")
        if not text_el:
            return None
        text = text_el.get_text(strip=True)
        if not text or len(text) < 5:
            return None

        # Extract author
        author = "Anonymous"
        author_el = card.select_one("span.a-profile-name")
        if author_el:
            author = author_el.get_text(strip=True)

        # Extract date
        date = None
        date_el = card.select_one("span[data-hook='review-date']")
        if date_el:
            date = date_el.get_text(strip=True)

        # Verified purchase
        verified = bool(card.select_one("span[data-hook='avp-badge']"))

        # Helpful count
        helpful_count = 0
        helpful_el = card.select_one("span[data-hook='helpful-vote-statement']")
        if helpful_el:
            match = re.search(r'(\d+)', helpful_el.get_text())
            if match:
                helpful_count = int(match.group(1))

        return ReviewData(
            id=_generate_review_id(text, author),
            author=author,
            rating=rating,
            date=date,
            title=title,
            text=text,
            verified=verified,
            helpful_count=helpful_count,
        )

    async def _scrape_flipkart(
        self, url: str, max_reviews: int
    ) -> Tuple[List[ReviewData], Optional[str], Optional[str]]:
        """Scrape reviews from Flipkart product pages."""
        reviews = []
        product_name = None
        product_image = None

        try:
            soup = await self._fetch_page(url)
        except Exception as e:
            raise ScrapingError(f"Failed to fetch Flipkart page: {e}")

        # Product info
        title_tag = soup.select_one("span.VU-ZEz, span.B_NuCI")
        if title_tag:
            product_name = title_tag.get_text(strip=True)

        img_tag = soup.select_one("img._396cs4, img._2r_T1I")
        if img_tag:
            product_image = img_tag.get("src")

        # Reviews
        review_cards = soup.select("div.col.EPCmJX, div._27M-vq")
        for card in review_cards[:max_reviews]:
            try:
                # Rating
                rating = None
                rating_el = card.select_one("div.XQDdHH, div._3LWZlK")
                if rating_el:
                    try:
                        rating = float(rating_el.get_text(strip=True))
                    except ValueError:
                        pass

                # Title
                title = None
                title_el = card.select_one("p.z9E0IG, p._2-N8zT")
                if title_el:
                    title = title_el.get_text(strip=True)

                # Text
                text_el = card.select_one("div.ZmyHeo, div.t-ZTKy div")
                if not text_el:
                    continue
                text = text_el.get_text(strip=True)
                if len(text) < 5:
                    continue

                # Author
                author = "Anonymous"
                author_el = card.select_one("p._2NsDsF, p._2sc7ZR")
                if author_el:
                    author = author_el.get_text(strip=True)

                reviews.append(ReviewData(
                    id=_generate_review_id(text, author),
                    author=author,
                    rating=rating,
                    title=title,
                    text=text,
                ))
            except Exception as e:
                logger.warning(f"Failed to parse Flipkart review: {e}")
                continue

        return reviews, product_name, product_image

    async def _scrape_generic(
        self, url: str, max_reviews: int
    ) -> Tuple[List[ReviewData], Optional[str], Optional[str]]:
        """Generic scraper for unknown platforms using heuristics."""
        try:
            soup = await self._fetch_page(url)
        except Exception as e:
            raise ScrapingError(f"Failed to fetch page: {e}")

        product_name = None
        product_image = None

        # Try to get product name from common selectors
        for selector in ["h1", "h1.product-title", ".product-name h1", "[itemprop='name']"]:
            el = soup.select_one(selector)
            if el:
                product_name = el.get_text(strip=True)
                break

        # Try to get product image
        for selector in ["img[itemprop='image']", ".product-image img", "#product-image img"]:
            el = soup.select_one(selector)
            if el:
                product_image = el.get("src")
                if product_image and not product_image.startswith("http"):
                    product_image = urljoin(url, product_image)
                break

        reviews = []

        # Look for review containers using common patterns
        review_selectors = [
            "[itemprop='review']",
            ".review",
            ".customer-review",
            ".product-review",
            "[data-review]",
            ".review-container",
            ".user-review",
        ]

        review_cards = []
        for selector in review_selectors:
            review_cards = soup.select(selector)
            if review_cards:
                break

        if not review_cards:
            # Fallback: look for clusters of text that might be reviews
            review_cards = self._find_review_clusters(soup)

        for card in review_cards[:max_reviews]:
            try:
                text = card.get_text(strip=True)
                if len(text) < 10:
                    continue

                author = "Anonymous"
                for sel in [".author", "[itemprop='author']", ".reviewer", ".review-author"]:
                    el = card.select_one(sel)
                    if el:
                        author = el.get_text(strip=True)
                        break

                rating = None
                for sel in ["[itemprop='ratingValue']", ".rating", ".stars", ".star-rating"]:
                    el = card.select_one(sel)
                    if el:
                        val = el.get("content") or el.get_text(strip=True)
                        match = re.search(r'(\d+\.?\d*)', str(val))
                        if match:
                            rating = min(float(match.group(1)), 5.0)
                            break

                # Remove author and rating text from review text
                review_text = text
                if author != "Anonymous":
                    review_text = review_text.replace(author, "").strip()

                if len(review_text) < 10:
                    continue

                reviews.append(ReviewData(
                    id=_generate_review_id(review_text, author),
                    author=author,
                    rating=rating,
                    text=review_text[:2000],
                ))
            except Exception as e:
                logger.warning(f"Failed to parse generic review: {e}")
                continue

        return reviews, product_name, product_image

    def _find_review_clusters(self, soup: BeautifulSoup) -> list:
        """Attempt to find review-like text clusters using heuristics."""
        candidates = []
        # Look for div/article elements with substantial text
        for el in soup.find_all(["div", "article", "section"]):
            text = el.get_text(strip=True)
            if 50 < len(text) < 3000:
                # Check if it looks like a review (has rating-like siblings, date patterns, etc.)
                parent_text = el.parent.get_text(strip=True) if el.parent else ""
                if (
                    re.search(r'\d+/5|\d+ star|★|⭐', text + parent_text, re.I)
                    or re.search(r'review|feedback|opinion', text + parent_text, re.I)
                ):
                    candidates.append(el)
        return candidates[:20]


class ScrapingError(Exception):
    """Custom exception for scraping failures."""
    pass
