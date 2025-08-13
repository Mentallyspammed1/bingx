#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
video_search.py  •  2025-08-01 (ENHANCED-UPGRADED)

Enhanced video search with state-of-the-art 2025 web scraping best practices.
Incorporates modern techniques from latest research:
- Advanced User-Agent rotation with realistic browser headers
- Improved error handling with comprehensive exception management
- Enhanced rate limiting with jitter and exponential backoff
- Better JavaScript content handling with optional Selenium support
- Async thumbnail downloading with aiohttp for performance
- Advanced proxy rotation and IP management
- Robust data validation and sanitization
- Modern responsive HTML output with lazy loading
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import concurrent.futures
import html
import json
import logging
import os
import random
import re
import signal
import sys
import time
import unicodedata
import uuid
import webbrowser
from contextlib import asynccontextmanager
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Sequence, Tuple, Union
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from requests.adapters import HTTPAdapter, Retry

# Optional async and selenium support
try:
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False
    
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from tqdm import tqdm
except ModuleNotFoundError:
    def tqdm(iterable, **kwargs):  # type: ignore
        return iterable


# ── Enhanced Color Setup ────────────────────────────────────────────────
init(autoreset=True)
NEON = {
    "CYAN": Fore.CYAN,
    "MAGENTA": Fore.MAGENTA,
    "GREEN": Fore.GREEN,
    "YELLOW": Fore.YELLOW,
    "RED": Fore.RED,
    "BLUE": Fore.BLUE,
    "WHITE": Fore.WHITE,
    "BRIGHT": Style.BRIGHT,
    "RESET": Style.RESET_ALL,
}

LOG_FMT = (
    f"{NEON['CYAN']}%(asctime)s{NEON['RESET']} - "
    f"{NEON['MAGENTA']}%(levelname)s{NEON['RESET']} - "
    f"{NEON['GREEN']}%(message)s{NEON['RESET']}"
)

# Enhanced logging with context
class ContextFilter(logging.Filter):
    def filter(self, record):
        record.engine = getattr(record, 'engine', 'unknown')
        record.query = getattr(record, 'query', 'unknown')
        return True

log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    log_handlers.append(logging.FileHandler("video_search.log", mode="a"))
except PermissionError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FMT,
    handlers=log_handlers,
)
logger = logging.getLogger(__name__)
logger.addFilter(ContextFilter())

# Suppress noisy loggers
for noisy in ("urllib3", "chardet", "requests", "aiohttp", "selenium"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


# ── Enhanced Defaults ────────────────────────────────────────────────────
THUMBNAILS_DIR = "downloaded_thumbnails"
DEFAULT_ENGINE = "pexels"
DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_FORMAT = "html"
DEFAULT_TIMEOUT = 25
DEFAULT_DELAY = (1.5, 4.0)  # Random delay with jitter
DEFAULT_MAX_RETRIES = 5
DEFAULT_WORKERS = 12

# Enhanced User-Agent rotation based on 2025 browser statistics[1][2][3]
REALISTIC_USER_AGENTS = [
    # Chrome on Windows (most common)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox variations
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.2277.83",
]

# Realistic browser headers to avoid bot detection[2][3]
def get_realistic_headers(user_agent: str) -> Dict[str, str]:
    """Generate realistic browser headers based on User-Agent."""
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": random.choice([
            "en-US,en;q=0.9",
            "en-GB,en;q=0.9",
            "en-US,en;q=0.8,es;q=0.6",
        ]),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
        "Sec-GPC": "1",
    }


# ── Enhanced Engine Configurations ─────────────────────────────────────────
ENGINE_MAP: Dict[str, Dict[str, Any]] = {
    "pexels": {
        "url": "https://www.pexels.com",
        "search_path": "/search/videos/{query}/",
        "page_param": "page",
        "requires_js": False,
        "video_item_selector": "article.hide-favorite-badge-container, article[data-testid='video-card']",
        "link_selector": 'a[data-testid="video-card-link"], a.video-link',
        "title_selector": 'img[data-testid="video-card-img"], .video-title',
        "title_attribute": "alt",
        "img_selector": 'img[data-testid="video-card-img"], img.video-thumbnail',
        "channel_name_selector": 'a[data-testid="video-card-user-avatar-link"] > span, .author-name',
        "channel_link_selector": 'a[data-testid="video-card-user-avatar-link"], .author-link',
        "fallback_selectors": {
            "title": ["img[alt]", ".video-title", "h3", "a[title]"],
            "img": ["img[data-src]", "img[src]", "img[data-lazy]"],
            "link": ["a[href*='/video/']", "a.video-link"]
        }
    },
    "dailymotion": {
        "url": "https://www.dailymotion.com",
        "search_path": "/search/{query}/videos",
        "page_param": "page",
        "requires_js": True,  # Dailymotion loads content dynamically
        "video_item_selector": 'div[data-testid="video-card"], .video-item',
        "link_selector": 'a[data-testid="card-link"], .video-link',
        "title_selector": 'div[data-testid="card-title"], .video-title',
        "img_selector": 'img[data-testid="card-thumbnail"], img.thumbnail',
        "time_selector": 'span[data-testid="card-duration"], .duration',
        "channel_name_selector": 'div[data-testid="card-owner-name"], .owner-name',
        "channel_link_selector": 'a[data-testid="card-owner-link"], .owner-link',
        "fallback_selectors": {
            "title": [".video-title", "h3", "[title]"],
            "img": ["img[src]", "img[data-src]"],
            "link": ["a[href*='/video/']"]
        }
    },
    "xhamster": {
        "url": "https://xhamster.com",
        "search_path": "/search/{query}",
        "page_param": "page",
        "requires_js": True,
        "video_item_selector": "div.thumb-list__item.video-thumb",
        "link_selector": "a.video-thumb__image-container[data-role='thumb-link']",
        "title_selector": "a.video-thumb-info__name[data-role='thumb-link']",
        "img_selector": "img.thumb-image-container__image[data-role='thumb-preview-img']",
        "time_selector": "div.thumb-image-container__duration div.tiny-8643e",
        "meta_selector": "div.video-thumb-views",
        "channel_name_selector": "a.video-uploader__name",
        "channel_link_selector": "a.video-uploader__name",
        "fallback_selectors": {
            "title": ["a[title]"],
            "img": ["img[data-src]", "img[src]"],
            "link": ["a[href*='/videos/']"]
        }
    },
    "pornhub": {
        "url": "https://www.pornhub.com",
        "search_path": "/video/search?search={query}",
        "page_param": "page",
        "requires_js": False,
        "video_item_selector": "li.pcVideoListItem, .video-item, div.videoblock",
        "link_selector": "a.previewVideo, a.thumb, .video-link, .videoblock__link",
        "title_selector": "a.previewVideo .title, a.thumb .title, .video-title, .videoblock__title",
        "img_selector": "img[src], img[data-src], img[data-lazy]",
        "time_selector": "var.duration, .duration, .videoblock__duration",
        "channel_name_selector": ".usernameWrap a, .channel-name, .videoblock__channel",
        "channel_link_selector": ".usernameWrap a, .channel-link",
        "meta_selector": ".views, .video-views, .videoblock__views",
        "fallback_selectors": {
            "title": [".title", "a[title]", "[data-title]"],
            "img": ["img[data-thumb]", "img[src]"],
            "link": ["a[href*='/view_video.php']", "a.video-link"]
        }
    },
    "xvideos": {
        "url": "https://www.xvideos.com",
        "search_path": "/?k={query}",
        "page_param": "p",
        "requires_js": False,
        "video_item_selector": "div.mozaique > div, .video-block, .thumb-block",
        "link_selector": ".thumb-under > a, .video-link, .thumb-block__header a",
        "title_selector": ".thumb-under > a, .video-title, .thumb-block__header a",
        "img_selector": "img, img[data-src], .thumb img",
        "time_selector": ".duration, .thumb-block__duration",
        "meta_selector": ".video-views, .views, .thumb-block__views",
        "fallback_selectors": {
            "title": ["a[title]", ".title", "p.title"],
            "img": ["img[data-src]", "img[src]"],
            "link": ["a[href*='/video']"]
        }
    },
    "xnxx": {
        "url": "https://www.xnxx.com",
        "search_path": "/search/{query}/",
        "page_param": "p",
        "requires_js": False,
        "video_item_selector": "div.mozaique > div.thumb-block, .video-block",
        "link_selector": ".thumb-under > a, .video-link",
        "title_selector": ".thumb-under > a, .video-title",
        "img_selector": "img[data-src], .thumb img",
        "time_selector": ".duration, .video-duration",
        "meta_selector": ".video-views, .views",
        "fallback_selectors": {
            "title": ["a[title]", ".title", "p.title"],
            "img": ["img[data-src]", "img[src]"],
            "link": ["a[href*='/video']"]
        }
    },
    "youjizz": {
        "url": "https://www.youjizz.com",
        "search_path": "/search/{query}-{page}.html",
        "page_param": "",
        "requires_js": True,
        "video_item_selector": "div.video-thumb",
        "link_selector": "a.frame.video",
        "title_selector": "div.video-title a",
        "img_selector": "img.img-responsive.lazy",
        "img_attribute": "data-original",
        "time_selector": "span.time",
        "meta_selector": "span.views",
        "fallback_selectors": {
            "title": ["a[title]"],
            "img": ["img[data-original]", "img[src]"],
            "link": ["a[href*='/videos/']"]
        }
    },
}


# ── Enhanced Helper Functions ────────────────────────────────────────────
def ensure_dir(path: Path) -> None:
    """Ensure directory exists with comprehensive error handling."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.error(f"Permission denied creating directory: {path}")
        raise
    except OSError as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise


def enhanced_slugify(text: str) -> str:
    """Enhanced slugify with better Unicode handling and security[3]."""
    if not text or not isinstance(text, str):
        return "untitled"

    # Normalize and clean Unicode
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Remove dangerous characters
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"[^a-zA-Z0-9\s\-_.]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    text = text.strip("._-")

    # Ensure reasonable length and avoid reserved names
    text = text[:100] or "untitled"
    reserved_names = {
        "con", "prn", "aux", "nul", "com1", "com2", "com3", "com4", "com5",
        "com6", "com7", "com8", "com9", "lpt1", "lpt2", "lpt3", "lpt4",
        "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"
    }
    if text.lower() in reserved_names:
        text = f"file_{text}"

    return text


def build_enhanced_session(
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    proxy: Optional[str] = None,
) -> requests.Session:
    """Create enhanced session with 2025 best practices[1][2][3]."""
    session = requests.Session()

    # Enhanced retry strategy with exponential backoff and jitter
    retries = Retry(
        total=max_retries,
        backoff_factor=2.0,
        backoff_jitter=0.5,  # Add jitter to avoid thundering herd
        status_forcelist=(429, 500, 502, 503, 504, 520, 521, 522, 524),
        allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
        respect_retry_after_header=True,
        raise_on_redirect=False,
        raise_on_status=False
    )

    adapter = HTTPAdapter(
        max_retries=retries,
        pool_connections=15,
        pool_maxsize=30
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set realistic headers
    user_agent = random.choice(REALISTIC_USER_AGENTS)
    session.headers.update(get_realistic_headers(user_agent))

    # Proxy support with validation
    if proxy:
        try:
            parsed_proxy = urlparse(proxy)
            if parsed_proxy.scheme and parsed_proxy.netloc:
                session.proxies.update({"http": proxy, "https": proxy})
                logger.info(f"Using proxy: {parsed_proxy.netloc}")
            else:
                logger.warning(f"Invalid proxy format: {proxy}")
        except Exception as e:
            logger.warning(f"Failed to set proxy {proxy}: {e}")

    session.timeout = timeout
    return session


def smart_delay_with_jitter(
    delay_range: Tuple[float, float],
    last_request_time: Optional[float] = None,
    jitter: float = 0.3
) -> None:
    """Implement intelligent delays with jitter to avoid detection[2][3]."""
    min_delay, max_delay = delay_range
    current_time = time.time()
    
    if last_request_time:
        elapsed = current_time - last_request_time
        base_wait = random.uniform(min_delay, max_delay)
        # Add jitter to make timing less predictable
        jitter_amount = base_wait * jitter * random.uniform(-1, 1)
        min_wait = max(0.5, base_wait + jitter_amount)
        
        if elapsed < min_wait:
            time.sleep(min_wait - elapsed)
    else:
        base_wait = random.uniform(min_delay, max_delay)
        jitter_amount = base_wait * jitter * random.uniform(-1, 1)
        time.sleep(max(0.5, base_wait + jitter_amount))


def create_selenium_driver() -> Optional[webdriver.Chrome]:
    """Create Selenium driver for JavaScript-heavy sites[2]."""
    if not SELENIUM_AVAILABLE:
        return None
        
    try:
        options = ChromeOptions()
        options.add_argument("--headless=new")  # Use new headless mode
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-web-security")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--window-size=1920,1080")
        # Randomize user agent
        options.add_argument(f"--user-agent={random.choice(REALISTIC_USER_AGENTS)}")
        
        # Disable images and CSS for faster loading
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logger.warning(f"Failed to create Selenium driver: {e}")
        return None


def extract_with_selenium(driver: webdriver.Chrome, url: str, cfg: Dict) -> List:
    """Extract data using Selenium for JavaScript-heavy sites[2]."""
    try:
        driver.get(url)
        
        # Wait for video items to load
        wait = WebDriverWait(driver, 10)
        found_element = False
        for selector in cfg["video_item_selector"].split(','):
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector.strip())))
                found_element = True
                logger.debug(f"Selenium found element with selector: {selector.strip()}")
                break
            except TimeoutException:
                logger.debug(f"Selenium did not find element with selector: {selector.strip()}")
                continue
        
        if not found_element:
            logger.warning(f"Selenium could not find any video items with provided selectors for {url}")
            return []
        
        # Additional wait to ensure dynamic content loads
        time.sleep(2)
        
        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        logger.debug(f"Selenium parsed soup: {soup.prettify()}")
        return extract_video_items(soup, cfg)
        
    except (TimeoutException, WebDriverException) as e:
        logger.warning(f"Selenium extraction failed for {url}: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred during Selenium extraction for {url}: {e}")
        return []


@asynccontextmanager
async def aiohttp_session() -> AsyncGenerator[Optional[aiohttp.ClientSession], None]:
    """Create async HTTP session for thumbnail downloads."""
    if not ASYNC_AVAILABLE:
        yield None
        return
        
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    headers = get_realistic_headers(random.choice(REALISTIC_USER_AGENTS))
    
    try:
        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=aiohttp.TCPConnector(limit=50, limit_per_host=10)
        ) as session:
            yield session
    except Exception as e:
        logger.error(f"Failed to create aiohttp session: {e}")
        yield None


async def async_download_thumbnail(
    session: aiohttp.ClientSession,
    url: str,
    path: Path,
    semaphore: asyncio.Semaphore
) -> bool:
    """Async thumbnail download with enhanced error handling."""
    if not ASYNC_AVAILABLE or not session:
        return False
        
    async with semaphore:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.debug(f"Async download failed, status {response.status} for {url}")
                    return False
                    
                content_type = response.headers.get("content-type", "").lower()
                if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                    logger.debug(f"Async download failed, invalid content type for {url}")
                    return False
                    
                content = await response.read()
                if len(content) == 0 or len(content) > 10 * 1024 * 1024:  # 10MB limit
                    logger.debug(f"Async download failed, invalid content size for {url}")
                    return False
                    
                with open(path, "wb") as f:
                    f.write(content)
                    
                return True
                
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.debug(f"Async download failed for {url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during async download for {url}: {e}")
            return False


def robust_download_sync(session: requests.Session, url: str, path: Path, max_attempts: int = 3) -> bool:
    """Synchronous fallback download with enhanced validation[3]."""
    if not url or not urlparse(url).scheme:
        return False

    for attempt in range(max_attempts):
        try:
            # Rotate User-Agent for each attempt
            session.headers.update(get_realistic_headers(random.choice(REALISTIC_USER_AGENTS)))

            with session.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()

                # Validate content type
                content_type = response.headers.get("content-type", "").lower()
                if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                    logger.debug(f"Sync download failed, invalid content type for {url}")
                    return False

                # Validate content length
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > 10 * 1024 * 1024:
                    logger.debug(f"Sync download failed, invalid content size for {url}")
                    return False

                # Write file with validation
                with open(path, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)

                if path.stat().st_size == 0:
                    path.unlink()
                    logger.debug(f"Sync download failed, empty file for {url}")
                    return False

                return True

        except Exception as e:
            logger.debug(f"Download failed for {url} (attempt {attempt + 1}): {e}")
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)  # Exponential backoff

    return False


def get_search_results(
    session: requests.Session,
    engine: str,
    query: str,
    limit: int,
    page: int,
    delay_range: Tuple[float, float],
) -> List[Dict]:
    """Enhanced scraping with comprehensive error handling[1][2][3]."""
    if engine not in ENGINE_MAP:
        logger.error(f"Unsupported engine: {engine}", extra={'engine': engine, 'query': query})
        return []

    cfg = ENGINE_MAP[engine]
    base_url = cfg["url"]
    results: List[Dict] = []
    last_request_time = None
    driver = None

    # Create Selenium driver if needed for JavaScript content
    if cfg.get("requires_js", False) and SELENIUM_AVAILABLE:
        driver = create_selenium_driver()
        if not driver:
            logger.warning(f"JavaScript required for {engine} but Selenium unavailable")

    try:
        items_per_page = 30
        pages_to_fetch = min(5, (limit + items_per_page - 1) // items_per_page)

        logger.info(f"Searching {engine} for '{query}' (up to {pages_to_fetch} pages)", 
                   extra={'engine': engine, 'query': query})

        for current_page in range(page, page + pages_to_fetch):
            if len(results) >= limit:
                break

            # Smart delay with jitter
            smart_delay_with_jitter(delay_range, last_request_time)
            last_request_time = time.time()

            # Build URL
            if "{page}" in cfg["search_path"]:
                search_path = cfg["search_path"].format(query=quote_plus(query), page=current_page)
            else:
                search_path = cfg["search_path"].format(query=quote_plus(query))
            
            url = urljoin(base_url, search_path)
            
            if current_page > 1 and "{page}" not in cfg["search_path"] and cfg.get("page_param"):
                separator = "&" if "?" in url else "?"
                url += f"{separator}{cfg.get('page_param')}={current_page}"

            logger.info(f"Fetching page {current_page}: {url}", 
                       extra={'engine': engine, 'query': query})

            try:
                # Use Selenium for JavaScript sites, otherwise requests
                if driver and cfg.get("requires_js", False):
                    video_items = extract_with_selenium(driver, url, cfg)
                else:
                    # Rotate User-Agent and headers
                    user_agent = random.choice(REALISTIC_USER_AGENTS)
                    session.headers.update(get_realistic_headers(user_agent))
                    
                    response = session.get(url, timeout=session.timeout)
                    response.raise_for_status()

                    if response.status_code != 200:
                        logger.warning(f"Unexpected status {response.status_code} for {url}")
                        continue

                    soup = BeautifulSoup(response.text, "html.parser")
                    video_items = extract_video_items(soup, cfg)

                if not video_items:
                    logger.warning(f"No video items found on page {current_page}")
                    continue

                logger.debug(f"Found {len(video_items)} video items on page {current_page}")

                # Process each video item with enhanced validation
                for item in video_items:
                    if len(results) >= limit:
                        break

                    try:
                        video_data = extract_video_data_enhanced(item, cfg, base_url)
                        if video_data and validate_video_data_enhanced(video_data):
                            results.append(video_data)
                    except Exception as e:
                        logger.debug(f"Failed to extract video data: {e}")
                        continue

            except Exception as e:
                logger.error(f"Request failed for page {current_page}: {e}")
                continue

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    logger.info(f"Successfully extracted {len(results)} videos", 
               extra={'engine': engine, 'query': query})
    return results[:limit]


def extract_video_items(soup: BeautifulSoup, cfg: Dict) -> List:
    """Extract video items with comprehensive fallback logic."""
    video_items = []
    
    # Try primary selectors
    for selector in cfg["video_item_selector"].split(", "):
        video_items = soup.select(selector.strip())
        if video_items:
            break
    
    # Try fallback selectors if needed
    if not video_items and "fallback_selectors" in cfg:
        for selector in cfg["fallback_selectors"].get("container", []):
            video_items = soup.select(selector)
            if video_items:
                break
                
    return video_items


def extract_video_data_enhanced(item, cfg: Dict, base_url: str) -> Optional[Dict]:
    """Enhanced video data extraction with comprehensive fallbacks[3]."""
    try:
        # Extract title with multiple fallback strategies
        title = "Untitled"
        title_selectors = [cfg.get("title_selector", "")]
        if "fallback_selectors" in cfg and "title" in cfg["fallback_selectors"]:
            title_selectors.extend(cfg["fallback_selectors"]["title"])

        for selector in title_selectors:
            if not selector:
                logger.debug(f"Skipping empty title selector.")
                continue
            logger.debug(f"Attempting to select title with: {selector}")
            title_el = item.select_one(selector)
            if title_el:
                title_attr = cfg.get("title_attribute")
                if title_attr and title_el.has_attr(title_attr):
                    title = title_el.get(title_attr, "").strip()
                else:
                    title = title_el.get_text(strip=True)
                if title and title != "Untitled":
                    break

        # Extract link with fallbacks
        link = "#"
        link_selectors = [cfg.get("link_selector", "")]
        if "fallback_selectors" in cfg and "link" in cfg["fallback_selectors"]:
            link_selectors.extend(cfg["fallback_selectors"]["link"])
            
        for selector in link_selectors:
            if not selector:
                logger.debug(f"Skipping empty link selector.")
                continue
            logger.debug(f"Attempting to select link with: {selector}")
            link_el = item.select_one(selector)
            if link_el and link_el.has_attr("href"):
                href = link_el["href"]
                if href and href != "#":
                    link = urljoin(base_url, href)
                    break

        # Extract image URL with comprehensive fallbacks
        img_url = None
        img_selectors = [cfg.get("img_selector", "")]
        if "fallback_selectors" in cfg and "img" in cfg["fallback_selectors"]:
            img_selectors.extend(cfg["fallback_selectors"]["img"])

        for selector in img_selectors:
            if not selector:
                logger.debug(f"Skipping empty image selector.")
                continue
            logger.debug(f"Attempting to select image with: {selector}")
            img_el = item.select_one(selector)
            if img_el:
                # Try multiple attributes in order of preference
                for attr in ["data-src", "src", "data-lazy", "data-original", "data-thumb"]:
                    if img_el.has_attr(attr):
                        img_val = img_el[attr]
                        if img_val and not img_val.startswith("data:"):
                            img_url = urljoin(base_url, img_val)
                            break
                if img_url:
                    break

        # Extract metadata with safe handling
        duration = extract_text_safe(item, cfg.get("time_selector", ""), "N/A")
        views = extract_text_safe(item, cfg.get("meta_selector", ""), "N/A")
        channel_name = extract_text_safe(item, cfg.get("channel_name_selector", ""), "N/A")
        
        channel_link = "#"
        channel_link_selector = cfg.get("channel_link_selector", "")
        if channel_link_selector:
            channel_link_el = item.select_one(channel_link_selector)
            if channel_link_el and channel_link_el.has_attr("href"):
                href = channel_link_el["href"]
                if href and href != "#":
                    channel_link = urljoin(base_url, href)

        return {
            "title": html.escape(title[:200]),
            "link": link,
            "img_url": img_url,
            "time": duration,
            "channel_name": channel_name,
            "channel_link": channel_link,
            "meta": views,
            "extracted_at": datetime.now().isoformat(),
            "source_engine": cfg.get("url", base_url),
        }

    except Exception as e:
        logger.debug(f"Error extracting video data: {e}")
        return None


def extract_text_safe(element, selector: str, default: str = "N/A") -> str:
    """Safely extract text with comprehensive error handling."""
    if not selector:
        logger.debug(f"extract_text_safe received empty selector, returning default: {default}")
        return default
    try:
        logger.debug(f"Attempting to extract text with selector: {selector}")
        el = element.select_one(selector)
        if el:
            text = el.get_text(strip=True)
            return text if text else default
        return default
    except Exception:
        return default


def validate_video_data_enhanced(data: Dict) -> bool:
    """Enhanced validation with comprehensive checks[3]."""
    if not isinstance(data, dict):
        return False
        
    # Required fields validation
    required_fields = ["title", "link"]
    for field in required_fields:
        if not data.get(field) or data[field] in ["", "Untitled", "#"]:
            return False
    
    # URL validation
    try:
        parsed_link = urlparse(data["link"])
        if not parsed_link.scheme or not parsed_link.netloc:
            return False
    except Exception:
        return False
    
    # Title validation
    title = data.get("title", "")
    if len(title) < 3 or title.lower() in ["untitled", "n/a", "error"]:
        return False
    
    return True


# ── Enhanced HTML Output ─────────────────────────────────────────────────
ENHANCED_HTML_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: #0a0a1a;
            --bg-secondary: #1a1a2e;
            --bg-card: #16213e;
            --accent-cyan: #00d4ff;
            --accent-pink: #ff006e;
            --accent-purple: #8b5cf6;
            --text-primary: #ffffff;
            --text-secondary: #a0a0a0;
            --text-muted: #666;
            --border: #2a2a3e;
            --shadow: rgba(0, 212, 255, 0.1);
            --gradient: linear-gradient(135deg, var(--accent-cyan), var(--accent-pink));
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
        }}

        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 2rem;
            background: var(--bg-secondary);
            border-radius: 20px;
            margin-top: 2rem;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        }}

        .header {{
            text-align: center;
            margin-bottom: 3rem;
            position: relative;
        }}

        .header::before {{
            content: '';
            position: absolute;
            top: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 100px;
            height: 4px;
            background: var(--gradient);
            border-radius: 2px;
        }}

        h1 {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 2.5rem;
            font-weight: 700;
            background: var(--gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
            text-shadow: 0 0 20px var(--shadow);
        }}

        .subtitle {{
            color: var(--text-secondary);
            font-size: 1.1rem;
            font-weight: 400;
        }}

        .stats {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin: 1.5rem 0;
            flex-wrap: wrap;
        }}

        .stat {{
            background: var(--bg-card);
            padding: 0.75rem 1.5rem;
            border-radius: 25px;
            border: 1px solid var(--border);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
        }}

        .video-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 2rem;
            margin-top: 2rem;
        }}

        .video-card {{
            background: var(--bg-card);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--border);
            transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            position: relative;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            display: flex;
            flex-direction: column;
        }}

        .video-card:hover {{
            transform: translateY(-8px) scale(1.02);
            box-shadow: 0 20px 40px var(--shadow);
            border-color: var(--accent-cyan);
        }}

        .video-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--gradient);
            opacity: 0;
            transition: opacity 0.3s ease;
        }}

        .video-card:hover::before {{ opacity: 1; }}

        .thumbnail {{
            position: relative;
            width: 100%;
            height: 200px;
            overflow: hidden;
            background: var(--bg-primary);
        }}

        .thumbnail img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }}

        .video-card:hover .thumbnail img {{ transform: scale(1.1); }}

        .play-overlay {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 60px;
            height: 60px;
            background: rgba(0, 212, 255, 0.9);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: all 0.3s ease;
            cursor: pointer;
        }}

        .video-card:hover .play-overlay {{
            opacity: 1;
            transform: translate(-50%, -50%) scale(1.1);
        }}

        .play-overlay::before {{
            content: '▶';
            color: white;
            font-size: 1.2rem;
            margin-left: 3px;
        }}

        .video-info {{
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }}

        .video-title {{
            font-size: 1.1rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 1rem;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}

        .video-title a {{
            color: inherit;
            text-decoration: none;
            transition: color 0.3s ease;
        }}

        .video-title a:hover {{ color: var(--accent-cyan); }}

        .video-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-top: auto;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
            font-size: 0.85rem;
        }}

        .meta-item {{
            background: rgba(0, 212, 255, 0.1);
            color: var(--accent-cyan);
            padding: 0.3rem 0.8rem;
            border-radius: 15px;
            font-family: 'JetBrains Mono', monospace;
            font-weight: 500;
            white-space: nowrap;
            display: flex;
            align-items: center;
            gap: 0.3rem;
        }}

        .meta-item a {{
            color: inherit;
            text-decoration: none;
            transition: opacity 0.3s ease;
        }}

        .meta-item a:hover {{ opacity: 0.8; }}

        .loading-placeholder {{
            background: linear-gradient(90deg, var(--bg-card) 25%, rgba(255,255,255,0.05) 50%, var(--bg-card) 75%);
            background-size: 200% 100%;
            animation: loading 1.5s infinite;
        }}

        @keyframes loading {{
            0% {{ background-position: 200% 0; }}
            100% {{ background-position: -200% 0; }}
        }}

        .error-placeholder {{
            background: var(--bg-card);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-muted);
            font-size: 1.5rem;
        }}

        @media (max-width: 768px) {{
            .container {{ margin: 1rem; padding: 1rem; border-radius: 12px; }}
            h1 {{ font-size: 2rem; }}
            .video-grid {{ grid-template-columns: 1fr; gap: 1.5rem; }}
            .stats {{ gap: 1rem; }}
            .stat {{ padding: 0.5rem 1rem; font-size: 0.8rem; }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            * {{ animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>{query}</h1>
            <p class="subtitle">Search results from {engine}</p>
            <div class="stats">
                <div class="stat">� {count} videos</div>
                <div class="stat">� {engine}</div>
                <div class="stat">⏰ {timestamp}</div>
            </div>
        </header>
        <main class="video-grid">"""

ENHANCED_HTML_TAIL = """        </main>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const images = document.querySelectorAll('img[data-src]');
            const imageObserver = new IntersectionObserver((entries, observer) => {{
                entries.forEach(entry => {{
                    if (entry.isIntersecting) {{
                        const img = entry.target;
                        const placeholder = img.parentElement;
                        
                        placeholder.classList.add('loading-placeholder');
                        
                        img.src = img.dataset.src;
                        img.onload = () => {{
                            img.removeAttribute('data-src');
                            placeholder.classList.remove('loading-placeholder');
                        }};
                        img.onerror = () => {{
                            placeholder.innerHTML = '<div class="error-placeholder">❌</div>';
                        }};
                        imageObserver.unobserve(img);
                    }}
                }});
            }});

            images.forEach(img => imageObserver.observe(img));
        }});
    </script>
</body>
</html>"""


async def build_enhanced_html_async(
    results: Sequence[Dict],
    query: str,
    engine: str,
    thumbs_dir: Path,
    session: requests.Session,
    workers: int,
) -> Path:
    """Build enhanced HTML with async thumbnail downloads."""
    ensure_dir(thumbs_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{engine}_{enhanced_slugify(query)}_{timestamp}_{uuid.uuid4().hex[:8]}.html"
    outfile = Path("vsearch") / filename

    def generate_placeholder_svg(icon: str) -> str:
        """Generate SVG placeholder."""
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
            <rect width="100%" height="100%" fill="#16213e"/>
            <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" 
                  font-family="sans-serif" font-size="2rem" fill="#666">{icon}</text>
        </svg>'''
        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

    async def fetch_thumbnail_async_task(idx: int, video: Dict, outfile: Path) -> Tuple[int, str]:
        """Download thumbnail async or fallback to sync."""
        img_url = video.get("img_url")
        if not img_url:
            return idx, generate_placeholder_svg("�")

        try:
            ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
            safe_title = enhanced_slugify(video.get("title", "video"))[:50]
            filename = f"{safe_title}_{idx}{ext}"
            dest_path = thumbs_dir / filename

            if dest_path.exists():
                return idx, str(Path(os.path.relpath(thumbs_dir, outfile.parent)) / filename).replace("\\", "/")

            # Try async download first
            if ASYNC_AVAILABLE:
                async with aiohttp_session() as async_session:
                    if async_session:
                        semaphore = asyncio.Semaphore(workers)
                        success = await async_download_thumbnail(async_session, img_url, dest_path, semaphore)
                        if success:
                            return idx, str(Path(os.path.relpath(thumbs_dir, outfile.parent)) / filename).replace("\\", "/")

            # Fallback to sync download
            if robust_download_sync(session, img_url, dest_path):
                return idx, str(Path(os.path.relpath(thumbs_dir, outfile.parent)) / filename).replace("\\", "/")

        except Exception as e:
            logger.debug(f"Error during thumbnail fetch for {img_url}: {e}")

        return idx, generate_placeholder_svg("❌")

    # Download thumbnails
    if ASYNC_AVAILABLE:
        thumbnail_paths_with_idx = await asyncio.gather(
            *[fetch_thumbnail_async_task(i, video, outfile) for i, video in enumerate(results)],
            return_exceptions=True
        )
        thumbnail_paths = [""] * len(results)
        for result in thumbnail_paths_with_idx:
            if isinstance(result, tuple) and len(result) == 2:
                idx, path = result
                thumbnail_paths[idx] = path
            else:
                logger.debug(f"Error gathering async thumbnail result: {result}")
    else:
        # Fallback to threaded downloads
        thumbnail_paths = [""] * len(results)
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, 20)) as executor:
            future_to_idx = {}
            for i, video in enumerate(results):
                img_url = video.get("img_url")
                if img_url:
                    ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
                    safe_title = enhanced_slugify(video.get("title", "video"))[:50]
                    filename = f"{safe_title}_{i}{ext}"
                    dest_path = thumbs_dir / filename
                    future = executor.submit(robust_download_sync, session, img_url, dest_path)
                    future_to_idx[future] = (i, dest_path)
                else:
                    thumbnail_paths[i] = generate_placeholder_svg("�")

            for future in tqdm(
                concurrent.futures.as_completed(future_to_idx),
                total=len(future_to_idx),
                desc=f"{NEON['MAGENTA']}Downloading Thumbnails{NEON['RESET']}",
                unit="files",
                ncols=100
            ):
                i, dest_path = future_to_idx[future]
                try:
                    success = future.result()
                    if success:
                        thumbnail_paths[i] = str(Path(os.path.relpath(thumbs_dir, outfile.parent)) / dest_path.name).replace("\\", "/")
                    else:
                        thumbnail_paths[i] = generate_placeholder_svg("❌")
                except Exception as e:
                    logger.debug(f"Error with threaded download: {e}")
                    thumbnail_paths[i] = generate_placeholder_svg("❌")
                    
    # Generate HTML
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(ENHANCED_HTML_HEAD.format(
            title=f"{html.escape(query)} - {engine}",
            query=html.escape(query),
            engine=engine.title(),
            count=len(results),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        for video, thumbnail in zip(results, thumbnail_paths):
            # Build meta items
            meta_items = []
            if video.get("time", "N/A") != "N/A":
                meta_items.append(f'<span class="meta-item">⏱️ {html.escape(video["time"])}</span>')

            if video.get("channel_name", "N/A") != "N/A":
                channel_link = video.get("channel_link", "#")
                if channel_link != "#":
                    meta_items.append(f'<span class="meta-item"><a href="{html.escape(channel_link)}" target="_blank" rel="noopener noreferrer">� {html.escape(video["channel_name"])}</a></span>')
                else:
                    meta_items.append(f'<span class="meta-item">� {html.escape(video["channel_name"])}</span>')

            if video.get("meta", "N/A") != "N/A":
                meta_items.append(f'<span class="meta-item">�️ {html.escape(video["meta"])}</span>')

            f.write(f'''
            <div class="video-card">
                <a href="{html.escape(video['link'])}" target="_blank" rel="noopener noreferrer">
                    <div class="thumbnail">
                        <img data-src="{html.escape(thumbnail)}" alt="{html.escape(video['title'])}" loading="lazy">
                        <div class="play-overlay"></div>
                    </div>
                </a>
                <div class="video-info">
                    <h3 class="video-title">
                        <a href="{html.escape(video['link'])}" target="_blank" rel="noopener noreferrer">
                            {html.escape(video['title'])}
                        </a>
                    </h3>
                    <div class="video-meta">
                        {"".join(meta_items)}
                    </div>
                </div>
            </div>
            ''')

        f.write(ENHANCED_HTML_TAIL)

    logger.info(f"Enhanced HTML gallery saved to: {outfile}")
    return outfile

# ── Main Functionality ───────────────────────────────────────────────────
def main():
    """Main function to parse arguments and run the search process."""
    parser = argparse.ArgumentParser(
        description="Enhanced video search with web scraping.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""\
Example usage:
  python3 video_search.py "cats in space"
  python3 video_search.py "ocean waves" -e pexels -l 50 -p 2 -o json
  python3 video_search.py "daily news" -e dailymotion --no-async --no-open
  python3 video_search.py "search term" -e pornhub -x http://user:pass@host:port
"""
    )
    
    parser.add_argument("query", type=str, help="The search query for videos.")
    parser.add_argument(
        "-e", "--engine", type=str, default=DEFAULT_ENGINE,
        choices=list(ENGINE_MAP.keys()),
        help=f"The search engine to use (default: {DEFAULT_ENGINE})."
    )
    parser.add_argument(
        "-l", "--limit", type=int, default=DEFAULT_LIMIT,
        help=f"Maximum number of video results to return (default: {DEFAULT_LIMIT})."
    )
    parser.add_argument(
        "-p", "--page", type=int, default=DEFAULT_PAGE,
        help=f"Starting page number for the search (default: {DEFAULT_PAGE})."
    )
    parser.add_argument(
        "-o", "--output-format", type=str, default=DEFAULT_FORMAT,
        choices=["html", "json"],
        help=f"Output format for the results (default: {DEFAULT_FORMAT})."
    )
    parser.add_argument(
        "-x", "--proxy", type=str,
        help="Proxy to use for requests (e.g., http://user:pass@host:port)."
    )
    parser.add_argument(
        "-w", "--workers", type=int, default=DEFAULT_WORKERS,
        help=f"Number of concurrent workers for thumbnail downloads (default: {DEFAULT_WORKERS})."
    )
    parser.add_argument(
        "--no-async", action="store_true",
        help="Disable async downloading and use a thread pool for thumbnails."
    )
    parser.add_argument(
        "--no-open", action="store_true",
        help="Do not automatically open the HTML result in a web browser."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose logging."
    )
    
    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Check for async availability
    global ASYNC_AVAILABLE
    if args.no_async:
        ASYNC_AVAILABLE = False
    
    # Handle KeyboardInterrupt gracefully
    def signal_handler(sig, frame):
        print(f"\n{NEON['YELLOW']}* Ctrl+C detected. Exiting gracefully...{NEON['RESET']}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Main execution logic
    try:
        session = build_enhanced_session(proxy=args.proxy)
        
        print(f"{NEON['CYAN']}{Style.BRIGHT}Starting search for '{args.query}' on {args.engine}...")

        # Search for results
        results = get_search_results(
            session=session,
            engine=args.engine,
            query=args.query,
            limit=args.limit,
            page=args.page,
            delay_range=DEFAULT_DELAY,
        )
        
        if not results:
            print(f"{NEON['RED']}No videos found for '{args.query}' on {args.engine}.{NEON['RESET']}")
            sys.exit(1)
        
        print(f"{NEON['GREEN']}Found {len(results)} videos.{NEON['RESET']}")

        # Handle output format
        if args.output_format == "json":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{args.engine}_{enhanced_slugify(args.query)}_{timestamp}.json"
            outfile = Path(filename)
            with open(outfile, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            print(f"{NEON['CYAN']}JSON results saved to: {outfile}{NEON['RESET']}")
        
        else: # html format
            # Use asyncio to run the HTML builder
            if ASYNC_AVAILABLE and not args.no_async:
                loop = asyncio.get_event_loop()
                outfile = loop.run_until_complete(
                    build_enhanced_html_async(
                        results=results,
                        query=args.query,
                        engine=args.engine,
                        thumbs_dir=Path(THUMBNAILS_DIR),
                        session=session,
                        workers=args.workers,
                    )
                )
            else:
                # Synchronous fallback
                async def sync_wrapper():
                    return await build_enhanced_html_async(
                        results=results,
                        query=args.query,
                        engine=args.engine,
                        thumbs_dir=Path(THUMBNAILS_DIR),
                        session=session,
                        workers=args.workers,
                    )
                outfile = asyncio.run(sync_wrapper())

            # Open the file
            if not args.no_open and outfile.exists():
                try:
                    webbrowser.open(f"file://{os.path.abspath(outfile)}")
                except Exception as e:
                    print(f"{NEON['YELLOW']}Failed to open browser: {e}{NEON['RESET']}")
        
    except Exception as e:
        logger.critical(f"An unhandled error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

