"""Web scraping service for extracting product reviews from Amazon and Flipkart."""

import asyncio
import hashlib
import logging
import re
import random
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

from curl_cffi.requests import AsyncSession
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

# Browser impersonation profiles for curl_cffi
BROWSER_PROFILES = ["chrome110", "chrome116", "chrome120", "chrome124"]


def _get_headers() -> Dict[str, str]:
    """Generate realistic browser headers for anti-bot evasion."""
    user_agent = ua.random if ua else (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
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
    else:
        return "generic"


class ReviewScraper:
    """Handles scraping product reviews from Amazon and Flipkart."""

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

    async def _fetch_page(self, url: str, retries: int = 3) -> BeautifulSoup:
        """Fetch a page with retry logic and TLS fingerprint impersonation."""
        last_error = None
        for attempt in range(retries):
            try:
                profile = random.choice(BROWSER_PROFILES)
                async with AsyncSession(
                    impersonate=profile,
                    timeout=30,
                ) as client:
                    response = await client.get(
                        url,
                        headers=_get_headers(),
                    )
                    response.raise_for_status()
                    html = response.text

                    # Check if we got a CAPTCHA/bot detection page
                    if self._is_blocked(html):
                        logger.warning(f"Bot detection on attempt {attempt + 1} for {url}")
                        if attempt < retries - 1:
                            await asyncio.sleep(2 + random.random() * 3)
                            continue
                        raise ScrapingError("Page returned a CAPTCHA/bot detection page. Try again later.")

                    return BeautifulSoup(html, "lxml")
            except ScrapingError:
                raise
            except Exception as e:
                last_error = e
                logger.warning(f"Fetch attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(1 + random.random() * 2)

        raise ScrapingError(f"Failed to fetch page after {retries} attempts: {last_error}")

    def _is_blocked(self, html: str) -> bool:
        """Check if the response indicates bot detection."""
        blocked_indicators = [
            "To discuss automated access to Amazon data",
            "api-services-support@amazon.com",
            "Sorry, we just need to make sure you're not a robot",
            "Enter the characters you see below",
            "Type the characters you see in this image",
        ]
        html_lower = html.lower()
        return any(indicator.lower() in html_lower for indicator in blocked_indicators)

    # ──────────────────────────────────────────────
    #  AMAZON SCRAPER
    # ──────────────────────────────────────────────

    async def _scrape_amazon(
        self, url: str, max_reviews: int
    ) -> Tuple[List[ReviewData], Optional[str], Optional[str]]:
        """Scrape reviews from Amazon product pages."""
        reviews = []
        product_name = None
        product_image = None

        # First, try to get product info from the product page itself
        try:
            product_soup = await self._fetch_page(url)
            product_name, product_image = self._extract_amazon_product_info(product_soup)
        except Exception as e:
            logger.warning(f"Could not fetch product page for info: {e}")

        # Convert product URL to reviews URL
        reviews_url = self._amazon_reviews_url(url)
        logger.info(f"Amazon reviews URL: {reviews_url}")
        page = 1

        while len(reviews) < max_reviews:
            sep = "&" if "?" in reviews_url else "?"
            paged_url = f"{reviews_url}{sep}pageNumber={page}"
            logger.info(f"Fetching Amazon reviews page {page}: {paged_url}")

            try:
                soup = await self._fetch_page(paged_url)
            except ScrapingError as e:
                logger.warning(f"Failed to fetch reviews page {page}: {e}")
                break
            except Exception as e:
                logger.warning(f"Failed to fetch page {page}: {e}")
                break

            # Extract product info from reviews page if not already found
            if page == 1 and not product_name:
                product_name, product_image = self._extract_amazon_product_info_from_reviews(soup)

            # Extract reviews using multiple selector strategies
            review_cards = self._find_amazon_review_cards(soup)
            if not review_cards:
                logger.info(f"No review cards found on page {page}, stopping pagination")
                break

            new_reviews = 0
            for card in review_cards:
                if len(reviews) >= max_reviews:
                    break
                try:
                    review = self._parse_amazon_review(card)
                    if review:
                        # Dedup check
                        if not any(r.id == review.id for r in reviews):
                            reviews.append(review)
                            new_reviews += 1
                except Exception as e:
                    logger.warning(f"Failed to parse review: {e}")
                    continue

            if new_reviews == 0:
                logger.info("No new reviews found, stopping pagination")
                break

            page += 1
            await asyncio.sleep(self.delay + random.random() * 0.1)

            # Safety check
            if page > 10:
                break

        logger.info(f"Scraped {len(reviews)} Amazon reviews")
        return reviews, product_name, product_image

    def _extract_amazon_product_info(self, soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
        """Extract product name and image from an Amazon product page."""
        name = None
        image = None

        # Product name selectors (ordered by specificity)
        name_selectors = [
            "#productTitle",
            "span#productTitle",
            "h1#title span",
            "h1.product-title-word-break",
            "a[data-hook='product-link']",
            "#title span",
        ]
        for sel in name_selectors:
            el = soup.select_one(sel)
            if el:
                name = el.get_text(strip=True)
                if name:
                    break

        # Product image selectors
        img_selectors = [
            "#landingImage",
            "#imgBlkFront",
            "#main-image",
            "img[data-hook='cr-product-image']",
            "#imageBlock img",
            ".a-dynamic-image",
        ]
        for sel in img_selectors:
            el = soup.select_one(sel)
            if el:
                image = el.get("src") or el.get("data-old-hires") or el.get("data-a-dynamic-image", "").split('"')[1] if '"' in el.get("data-a-dynamic-image", "") else el.get("src")
                if image:
                    break

        return name, image

    def _extract_amazon_product_info_from_reviews(self, soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
        """Extract product info from the Amazon reviews page."""
        name = None
        image = None

        title_tag = soup.select_one("a[data-hook='product-link']")
        if title_tag:
            name = title_tag.get_text(strip=True)

        img_tag = soup.select_one("img[data-hook='cr-product-image']")
        if img_tag:
            image = img_tag.get("src")

        # Fallback: look for product title in breadcrumb or heading
        if not name:
            for sel in ["h1 a", ".product-title", ".a-text-bold"]:
                el = soup.select_one(sel)
                if el and len(el.get_text(strip=True)) > 5:
                    name = el.get_text(strip=True)
                    break

        return name, image

    def _amazon_reviews_url(self, url: str) -> str:
        """Convert an Amazon product URL to its reviews page URL."""
        # Extract ASIN from various URL formats
        asin = self._extract_amazon_asin(url)
        if asin:
            parsed = urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            return (
                f"{base}/product-reviews/{asin}"
                f"/ref=cm_cr_dp_d_show_all_btm"
                f"?ie=UTF8&reviewerType=all_reviews&sortBy=recent"
            )
        return url

    def _extract_amazon_asin(self, url: str) -> Optional[str]:
        """Extract ASIN from various Amazon URL formats."""
        patterns = [
            r'/dp/([A-Z0-9]{10})',
            r'/product-reviews/([A-Z0-9]{10})',
            r'/gp/product/([A-Z0-9]{10})',
            r'/gp/aw/d/([A-Z0-9]{10})',
            r'/ASIN/([A-Z0-9]{10})',
            r'asin=([A-Z0-9]{10})',
            r'/([A-Z0-9]{10})(?:[/?]|$)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None

    def _find_amazon_review_cards(self, soup: BeautifulSoup) -> list:
        """Find review card elements using multiple selector strategies."""
        selectors = [
            "div[data-hook='review']",
            "div.review",
            "div[id^='customer_review-']",
            "div.a-section.review",
            "div[data-hook='mob-review']",
        ]
        for selector in selectors:
            cards = soup.select(selector)
            if cards:
                logger.debug(f"Found {len(cards)} reviews with selector: {selector}")
                return cards
        return []

    def _parse_amazon_review(self, card) -> Optional[ReviewData]:
        """Parse a single Amazon review card into ReviewData."""
        # Extract rating
        rating = None
        rating_selectors = [
            "i[data-hook='review-star-rating'] span",
            "i[data-hook='cmps-review-star-rating'] span",
            "i.review-rating span",
            "span.a-icon-alt",
        ]
        for sel in rating_selectors:
            rating_el = card.select_one(sel)
            if rating_el:
                rating_text = rating_el.get_text(strip=True)
                match = re.search(r'(\d+\.?\d*)', rating_text)
                if match:
                    rating = float(match.group(1))
                    if rating > 5:
                        rating = None  # Invalid
                    break

        # Extract title
        title = None
        title_selectors = [
            "a[data-hook='review-title'] span:last-child",
            "span[data-hook='review-title'] span:last-child",
            "a[data-hook='review-title']",
            "span[data-hook='review-title']",
            ".review-title span",
        ]
        for sel in title_selectors:
            title_el = card.select_one(sel)
            if title_el:
                title = title_el.get_text(strip=True)
                # Remove the rating text if it leaked into title
                if title and re.match(r'^\d+\.\d+ out of \d+ stars?$', title):
                    title = None
                    continue
                if title:
                    break

        # Extract review text
        text = None
        text_selectors = [
            "span[data-hook='review-body'] span",
            "span[data-hook='review-body']",
            "div.review-text span",
            "div.review-text",
            ".review-text-content span",
        ]
        for sel in text_selectors:
            text_el = card.select_one(sel)
            if text_el:
                text = text_el.get_text(strip=True)
                if text and len(text) >= 5:
                    break
                text = None

        if not text or len(text) < 5:
            return None

        # Extract author
        author = "Anonymous"
        author_selectors = [
            "span.a-profile-name",
            "a.a-profile[href*='profile'] .a-profile-name",
            ".a-profile-name",
        ]
        for sel in author_selectors:
            author_el = card.select_one(sel)
            if author_el:
                author = author_el.get_text(strip=True)
                break

        # Extract date
        date = None
        date_el = card.select_one("span[data-hook='review-date']")
        if date_el:
            date = date_el.get_text(strip=True)

        # Verified purchase
        verified = bool(
            card.select_one("span[data-hook='avp-badge']") or
            card.select_one("span.a-declarative[data-action='reviews:filter-action:push-state']")
        )

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

    # ──────────────────────────────────────────────
    #  FLIPKART SCRAPER
    # ──────────────────────────────────────────────

    async def _scrape_flipkart(
        self, url: str, max_reviews: int
    ) -> Tuple[List[ReviewData], Optional[str], Optional[str]]:
        """Scrape reviews from Flipkart product pages."""
        reviews = []
        product_name = None
        product_image = None

        # First fetch the product page for info + review link
        try:
            soup = await self._fetch_page(url)
        except Exception as e:
            raise ScrapingError(f"Failed to fetch Flipkart page: {e}")

        # Extract product info
        product_name = self._extract_flipkart_product_name(soup)
        product_image = self._extract_flipkart_product_image(soup)

        # Try to find and navigate to the "all reviews" page
        all_reviews_url = self._find_flipkart_all_reviews_url(url, soup)

        if all_reviews_url:
            # Scrape from the dedicated reviews page (paginated)
            reviews = await self._scrape_flipkart_reviews_pages(all_reviews_url, max_reviews)
        
        # If no reviews from all-reviews page, try scraping from product page itself
        if not reviews:
            reviews = self._extract_flipkart_reviews_from_page(soup, max_reviews)

        logger.info(f"Scraped {len(reviews)} Flipkart reviews")
        return reviews, product_name, product_image

    def _extract_flipkart_product_name(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product name from Flipkart page."""
        selectors = [
            "span.VU-ZEz",
            "span.B_NuCI",
            "h1._6EBuvT",
            "h1 span.VU-ZEz",
            "h1.yhB1nd",
            "div.aMaAEs h1 span",
            "h1._9E25nV",
            "span._35KyD6",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                name = el.get_text(strip=True)
                if name and len(name) > 2:
                    return name

        # Fallback: try the first h1
        h1 = soup.select_one("h1")
        if h1:
            return h1.get_text(strip=True)

        # Fallback: try title tag
        title = soup.select_one("title")
        if title:
            title_text = title.get_text(strip=True)
            # Remove "Buy ... Online at Best ... | Flipkart.com" suffix
            if "Flipkart" in title_text:
                title_text = re.sub(r'\s*[-|].*Flipkart.*$', '', title_text, flags=re.IGNORECASE)
                title_text = re.sub(r'^Buy\s+', '', title_text, flags=re.IGNORECASE)
            return title_text if title_text else None

        return None

    def _extract_flipkart_product_image(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract product image from Flipkart page."""
        selectors = [
            "img._396cs4",
            "img._2r_T1I",
            "img.DByuf4",
            "img._0DkuPH",
            "div._3kidJX img",
            "div.CXW8mj img",
            "img[loading='eager']",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                src = el.get("src") or el.get("data-src")
                if src:
                    return src
        return None

    def _find_flipkart_all_reviews_url(self, product_url: str, soup: BeautifulSoup) -> Optional[str]:
        """Find the 'All Reviews' page URL from a Flipkart product page."""
        parsed = urlparse(product_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # Look for "All Reviews" link
        review_link_selectors = [
            "a[href*='product-reviews']",
            "a[href*='/reviews/']",
            "div._23J90q a",
            "a._1fQZEK",
            "a.geATbz",
        ]
        for sel in review_link_selectors:
            links = soup.select(sel)
            for link in links:
                href = link.get("href", "")
                text = link.get_text(strip=True).lower()
                if href and ("product-reviews" in href or "review" in text):
                    full_url = urljoin(base, href)
                    return full_url

        # Try to construct the reviews URL from the product URL
        # Flipkart review URLs follow pattern: /product-name/product-reviews/itm...
        path = parsed.path
        if "/p/" in path:
            # Try converting /product/p/itmXXX to /product/product-reviews/itmXXX
            reviews_path = path.replace("/p/", "/product-reviews/", 1)
            return f"{base}{reviews_path}?pid={parse_qs(parsed.query).get('pid', [''])[0]}&lid=LSTMOB{parse_qs(parsed.query).get('pid', [''])[0]}&marketplace=FLIPKART&sortOrder=MOST_RECENT"

        return None

    async def _scrape_flipkart_reviews_pages(self, reviews_url: str, max_reviews: int) -> List[ReviewData]:
        """Scrape multiple pages of Flipkart reviews."""
        reviews = []
        page = 1

        while len(reviews) < max_reviews:
            sep = "&" if "?" in reviews_url else "?"
            paged_url = f"{reviews_url}{sep}page={page}"
            logger.info(f"Fetching Flipkart reviews page {page}: {paged_url}")

            try:
                soup = await self._fetch_page(paged_url)
            except Exception as e:
                logger.warning(f"Failed to fetch Flipkart reviews page {page}: {e}")
                break

            page_reviews = self._extract_flipkart_reviews_from_page(soup, max_reviews - len(reviews))
            if not page_reviews:
                break

            new_count = 0
            for review in page_reviews:
                if not any(r.id == review.id for r in reviews):
                    reviews.append(review)
                    new_count += 1

            if new_count == 0:
                break

            page += 1
            await asyncio.sleep(self.delay + random.random() * 0.1)

            if page > 10:
                break

        return reviews

    def _extract_flipkart_reviews_from_page(self, soup: BeautifulSoup, max_reviews: int) -> List[ReviewData]:
        """Extract reviews from a Flipkart page using text sequence parsing."""
        reviews = []

        # Find all text nodes that have readable content
        text_divs = soup.select('div[dir="auto"]')
        if not text_divs:
            # Fallback for old Flipkart UI
            text_divs = soup.find_all('div')
            
        texts = [div.get_text(strip=True) for div in text_divs if div.get_text(strip=True)]
        
        i = 0
        while i < len(texts) - 5 and len(reviews) < max_reviews:
            # Look for rating pattern: number (1.0-5.0 or 1-5) followed by '•' or '★'
            is_rating = False
            if texts[i] in ['1', '2', '3', '4', '5', '1.0', '2.0', '3.0', '4.0', '5.0']:
                if texts[i+1] in ['•', '★', '*']:
                    is_rating = True
                
            if is_rating:
                try:
                    rating = float(texts[i])
                    title = texts[i+2]
                    
                    idx = i + 3
                    if texts[idx].startswith('Review for:'):
                        idx += 1
                        
                    body = texts[idx]
                    author = texts[idx+1]
                    
                    # Prevent catching things that aren't reviews
                    if len(body) < 5 or "ratings and" in body.lower():
                        i += 1
                        continue
                        
                    # Find date and verification
                    date = None
                    verified = False
                    
                    # Scan ahead logic
                    for j in range(idx+2, min(idx+8, len(texts))):
                        if texts[j] == 'Verified Purchase':
                            verified = True
                        elif texts[j].startswith('· '):
                            date = texts[j].lstrip('· ')
                            i = j # Move pointer
                            break
                            
                    reviews.append(ReviewData(
                        id=_generate_review_id(body, author),
                        author=author,
                        rating=rating,
                        date=date,
                        title=title,
                        text=body,
                        verified=verified,
                    ))
                except Exception as e:
                    logger.warning(f"Error parsing Flipkart sequence: {e}")
                    pass
            i += 1
            
        return reviews

    def _find_flipkart_reviews_structural(self, soup: BeautifulSoup) -> list:
        # No longer needed, sequence parsing handles structure
        return []

    def _parse_flipkart_review(self, card) -> Optional[ReviewData]:
        # No longer used in text sequence parsing
        pass

    # ──────────────────────────────────────────────
    #  GENERIC SCRAPER
    # ──────────────────────────────────────────────

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
        for el in soup.find_all(["div", "article", "section"]):
            text = el.get_text(strip=True)
            if 50 < len(text) < 3000:
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
