#!/usr/bin/env python3
"""video_search.py  •  2025-08-01 (ENHANCED-UPGRADED)

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
from collections.abc import AsyncGenerator
from collections.abc import Sequence
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from urllib.parse import urljoin
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from colorama import Fore
from colorama import Style
from colorama import init
from requests.adapters import HTTPAdapter
from requests.adapters import Retry

# Optional async and selenium support
try:
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
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
def get_realistic_headers(user_agent: str) -> dict[str, str]:
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
# Updated with more specific selectors and comprehensive fallbacks for robustness.
ENGINE_MAP: dict[str, dict[str, Any]] = {
    "pexels": {
        "url": "https://www.pexels.com",
        "search_path": "/search/videos/{query}/",
        "page_param": "page",
        "requires_js": False,
        # Primary selectors for video items
        "video_item_selector": "article[data-testid='video-card'], article.hide-favorite-badge-container",
        # Primary selectors for video link, title, image, channel, and metadata
        "link_selector": 'a[data-testid="video-card-link"], a[href*="/videos/"]',
        "title_selector": 'img[data-testid="video-card-img"], .video-title, h3',
        "title_attribute": "alt", # Attribute to get title from if element is an img
        "img_selector": 'img[data-testid="video-card-img"], img.video-thumbnail, img[data-src]',
        "channel_name_selector": 'a[data-testid="video-card-user-avatar-link"] > span, .author-name, .channel-name',
        "channel_link_selector": 'a[data-testid="video-card-user-avatar-link"], .author-link, .channel-link',
        "time_selector": ".video-duration, .duration", # Added time selector
        "meta_selector": ".video-views, .views", # Added views selector
        # Comprehensive fallback selectors for robustness
        "fallback_selectors": {
            "container": ["article", "div[data-testid='video-card']", "div.video-item"], # Fallback for the main container
            "title": ["img[alt]", ".video-title", "h3", "a[title]", "a[data-testid='video-card-link']"],
            "img": ["img[data-src]", "img[src]", "img[data-lazy]", "img[data-original]", "img[data-thumb]"],
            "link": ["a[href*='/video/']", "a.video-link", "a[data-testid='video-card-link']", "a[href*='/videos/']"],
            "channel_name": [".author-name", ".channel-name", "span[data-testid='video-card-user-avatar-link'] > span"],
            "channel_link": [".author-link", ".channel-link", "a[data-testid='video-card-user-avatar-link']"],
            "time": [".duration", ".video-duration", "span.time"],
            "meta": [".views", ".video-views", "span.meta-item"],
        }
    },
    "dailymotion": {
        "url": "https://www.dailymotion.com",
        "search_path": "/search/{query}/videos",
        "page_param": "page",
        "requires_js": False,
        "video_item_selector": "div[data-testid='video-card'], .video-item, article.video-item",
        "link_selector": 'a[data-testid="card-link"], .video-link, a[href*="/video/"]',
        "title_selector": 'div[data-testid="card-title"], .video-title, h3',
        "img_selector": 'img[data-testid="card-thumbnail"], img.thumbnail, img[data-src]',
        "time_selector": 'span[data-testid="card-duration"], .duration, .video-duration',
        "channel_name_selector": 'div[data-testid="card-owner-name"], .owner-name, .channel-name',
        "channel_link_selector": 'a[data-testid="card-owner-link"], .owner-link, .channel-link',
        "meta_selector": 'span[data-testid="card-views"], .views, .video-views',
        "fallback_selectors": {
            "container": ["article", "div[data-testid='video-card']", "div.video-item"],
            "title": [".video-title", "h3", "[title]", "a[data-testid='card-link']"],
            "img": ["img[src]", "img[data-src]", "img[data-lazy]", "img[data-original]"],
            "link": ["a[href*='/video/']", ".video-link", "a[data-testid='card-link']"],
            "channel_name": [".owner-name", ".channel-name", "div[data-testid='card-owner-name']"],
            "channel_link": [".owner-link", ".channel-link", "a[data-testid='card-owner-link']"],
            "time": [".duration", ".video-duration", "span.time"],
            "meta": [".views", ".video-views", "span.meta-item"],
        }
    },
    "xhamster": {
        "url": "https://xhamster.com",
        "search_path": "/search/{query}",
        "page_param": "page",
        "requires_js": True,
        "video_item_selector": "div.thumb-list__item.video-thumb, article.video-item",
        "link_selector": "a.video-thumb__image-container[data-role='thumb-link'], a[href*='/videos/']",
        "title_selector": "a.video-thumb-info__name[data-role='thumb-link'], .video-title, h3",
        "img_selector": "img.thumb-image-container__image[data-role='thumb-preview-img'], img[data-src], img[src]",
        "time_selector": "div.thumb-image-container__duration div.tiny-8643e, .duration, .video-duration",
        "meta_selector": "div.video-thumb-views, .views, .video-views",
        "channel_name_selector": "a.video-uploader__name, .channel-name",
        "channel_link_selector": "a.video-uploader__name, .channel-link",
        "fallback_selectors": {
            "container": ["div.thumb-list__item", "article.video-item", "div.video-block"],
            "title": ["a[title]", ".video-title", "h3", "a[data-role='thumb-link']"],
            "img": ["img[data-src]", "img[src]", "img[data-lazy]", "img[data-original]"],
            "link": ["a[href*='/videos/']", "a.video-thumb__image-container", "a.video-link"],
            "channel_name": [".channel-name", "a.video-uploader__name"],
            "channel_link": [".channel-link", "a.video-uploader__name"],
            "time": [".duration", ".video-duration", "span.time"],
            "meta": [".views", ".video-views", "span.meta-item"],
        }
    },
    "pornhub": {
        "url": "https://www.pornhub.com",
        "search_path": "/video/search?search={query}",
        "page_param": "page",
        "requires_js": False,
        "video_item_selector": "li.pcVideoListItem, .video-item, div.videoblock, article.video-box",
        "link_selector": "a.previewVideo, a.thumb, .video-link, .videoblock__link, article.video-box a[href*='/view_video.php']",
        "title_selector": "a.previewVideo .title, a.thumb .title, .video-title, .videoblock__title, article.video-box .title",
        "img_selector": "img[src], img[data-src], img[data-lazy], img[data-thumb]",
        "time_selector": "var.duration, .duration, .videoblock__duration, .video-duration",
        "channel_name_selector": ".usernameWrap a, .channel-name, .videoblock__channel, .video-uploader__name",
        "channel_link_selector": ".usernameWrap a, .channel-link, .videoblock__channel a, .video-uploader__name",
        "meta_selector": ".views, .video-views, .videoblock__views, .video-meta-item",
        "fallback_selectors": {
            "container": ["li.pcVideoListItem", ".video-item", "div.videoblock", "article.video-box"],
            "title": [".title", "a[title]", "[data-title]", "a.video-link", "h3"],
            "img": ["img[data-thumb]", "img[src]", "img[data-src]", "img[data-lazy]", "img[data-original]"],
            "link": ["a[href*='/view_video.php']", "a.video-link", ".videoblock__link", "a.thumb"],
            "channel_name": [".channel-name", ".video-uploader__name", ".usernameWrap a"],
            "channel_link": [".channel-link", ".video-uploader__name", ".usernameWrap a"],
            "time": [".duration", ".video-duration", "span.time"],
            "meta": [".views", ".video-views", "span.meta-item"],
        }
    },
    "xvideos": {
        "url": "https://www.xvideos.com",
        "search_path": "/?k={query}",
        "page_param": "p",
        "requires_js": False,
        "video_item_selector": "div.mozaique > div, .video-block, .thumb-block, article.video-item",
        "link_selector": ".thumb-under > a, .video-link, .thumb-block__header a, a[href*='/video/']",
        "title_selector": ".thumb-under > a, .video-title, .thumb-block__header a, h3",
        "img_selector": "img, img[data-src], .thumb img, img[data-original]",
        "time_selector": ".duration, .thumb-block__duration, .video-duration",
        "meta_selector": ".video-views, .views, .thumb-block__views",
        "channel_name_selector": ".video-uploader__name, .channel-name",
        "channel_link_selector": ".video-uploader__name, .channel-link",
        "fallback_selectors": {
            "container": ["div.mozaique > div", ".video-block", ".thumb-block", "article.video-item"],
            "title": ["a[title]", ".title", "p.title", "h3", ".thumb-under > a"],
            "img": ["img[data-src]", "img[src]", ".thumb img", "img[data-lazy]", "img[data-original]"],
            "link": ["a[href*='/video']", ".thumb-under > a", ".video-link", ".thumb-block__header a"],
            "channel_name": [".channel-name", ".video-uploader__name"],
            "channel_link": [".channel-link", ".video-uploader__name"],
            "time": [".duration", ".video-duration", "span.time"],
            "meta": [".views", ".video-views", "span.meta-item"],
        }
    },
    "xnxx": {
        "url": "https://www.xnxx.com",
        "search_path": "/search/{query}/",
        "page_param": "p",
        "requires_js": False,
        "video_item_selector": "div.mozaique > div.thumb-block, .video-block, article.video-item",
        "link_selector": ".thumb-under > a, .video-link, a[href*='/video/']",
        "title_selector": ".thumb-under > a, .video-title, h3",
        "img_selector": "img[data-src], .thumb img, img[src], img[data-original]",
        "time_selector": ".duration, .video-duration",
        "meta_selector": ".video-views, .views",
        "channel_name_selector": ".video-uploader__name, .channel-name",
        "channel_link_selector": ".video-uploader__name, .channel-link",
        "fallback_selectors": {
            "container": ["div.mozaique > div.thumb-block", ".video-block", "article.video-item"],
            "title": ["a[title]", ".title", "p.title", "h3", ".thumb-under > a"],
            "img": ["img[data-src]", "img[src]", ".thumb img", "img[data-lazy]", "img[data-original]"],
            "link": ["a[href*='/video']", ".thumb-under > a", ".video-link"],
            "channel_name": [".channel-name", ".video-uploader__name"],
            "channel_link": [".channel-link", ".video-uploader__name"],
            "time": [".duration", ".video-duration", "span.time"],
            "meta": [".views", ".video-views", "span.meta-item"],
        }
    },
    "youjizz": {
        "url": "https://www.youjizz.com",
        "search_path": "/search/{query}-{page}.html",
        "page_param": "", # Page is part of the path for this engine
        "requires_js": True,
        "video_item_selector": "div.video-thumb, article.video-item",
        "link_selector": "a.frame.video, a[href*='/videos/']",
        "title_selector": "div.video-title a, h3",
        "img_selector": "img.img-responsive.lazy, img[data-src]",
        "img_attribute": "data-original", # Specific attribute for this engine's images
        "time_selector": "span.time, .duration",
        "meta_selector": "span.views, .video-views",
        "channel_name_selector": "div.video-uploader__name, .channel-name",
        "channel_link_selector": "div.video-uploader__name, .channel-link",
        "fallback_selectors": {
            "container": ["div.video-thumb", "article.video-item", "div.video-block"],
            "title": ["a[title]", ".video-title a", "h3", "a.frame.video"],
            "img": ["img[data-src]", "img[src]", "img[data-lazy]", "img[data-original]"],
            "link": ["a[href*='/videos/']", "a.frame.video", ".video-link"],
            "channel_name": [".channel-name", "div.video-uploader__name"],
            "channel_link": [".channel-link", "div.video-uploader__name"],
            "time": [".duration", "span.time"],
            "meta": [".views", ".video-views", "span.meta-item"],
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
    proxy: str | None = None,
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
    delay_range: tuple[float, float],
    last_request_time: float | None = None,
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


def create_selenium_driver() -> webdriver.Chrome | None:
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


def extract_with_selenium(driver: webdriver.Chrome, url: str, cfg: dict) -> list:
    """Extract data using Selenium for JavaScript-heavy sites[2]."""
    try:
        driver.get(url)

        # Wait for video items to load
        wait = WebDriverWait(driver, 10)
        found_element = False
        # Iterate through primary and fallback selectors for video items
        selectors_to_try = cfg["video_item_selector"].split(',')
        if "fallback_selectors" in cfg and "container" in cfg["fallback_selectors"]:
            selectors_to_try.extend(cfg["fallback_selectors"]["container"])

        for selector in selectors_to_try:
            selector = selector.strip()
            if not selector: continue
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                found_element = True
                logger.debug(f"Selenium found element with selector: {selector}")
                break
            except TimeoutException:
                logger.debug(f"Selenium did not find element with selector: {selector}")
                continue

        if not found_element:
            logger.warning(f"Selenium could not find any video items with provided selectors for {url}")
            return []

        # Additional wait to ensure dynamic content loads
        time.sleep(2)

        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        logger.debug(f"Selenium parsed soup for {url}")
        return extract_video_items(soup, cfg)

    except (TimeoutException, WebDriverException) as e:
        logger.warning(f"Selenium extraction failed for {url}: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred during Selenium extraction for {url}: {e}")
        return []


@asynccontextmanager
async def aiohttp_session() -> AsyncGenerator[aiohttp.ClientSession | None, None]:
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
    semaphore: asyncio.Semaphore,
    max_attempts: int = 3,
) -> bool:
    """Async thumbnail download with enhanced error handling and retries."""
    if not ASYNC_AVAILABLE or not session:
        return False

    for attempt in range(max_attempts):
        async with semaphore:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        content_type = response.headers.get("content-type", "").lower()
                        if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                            logger.debug(f"Async download failed, invalid content type for {url}")
                            return False  # Fail fast on wrong content type

                        content = await response.read()
                        if not content or len(content) > 10 * 1024 * 1024:  # 10MB limit
                            logger.debug(f"Async download failed, invalid content size for {url}")
                            continue  # Retry on empty or too large content

                        with open(path, "wb") as f:
                            f.write(content)

                        if path.stat().st_size > 0:
                            return True
                        path.unlink(missing_ok=True)
                        logger.debug(f"Async download resulted in empty file for {url}")
                        continue  # Retry if file is empty

                    logger.debug(f"Async download failed, status {response.status} for {url} (attempt {attempt + 1})")

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.debug(f"Async download failed for {url} (attempt {attempt + 1}): {e}")
            except Exception as e:
                logger.error(f"Unexpected error during async download for {url}: {e}")
                return False  # Do not retry on unexpected errors

        if attempt < max_attempts - 1:
            await asyncio.sleep(1.5 ** attempt)  # Exponential backoff

    return False


def robust_download_sync(session: requests.Session, url: str, path: Path, max_attempts: int = 3) -> bool:
    """Synchronous fallback download with enhanced validation and retries[3]."""
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
                    return False  # Fail fast on wrong content type

                # Validate content length
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
                    logger.debug(f"Sync download failed, content too large for {url}")
                    return False # Fail fast on oversized content

                # Write file with validation
                with open(path, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)

                if path.stat().st_size > 0:
                    return True
                path.unlink(missing_ok=True)
                logger.debug(f"Sync download resulted in empty file for {url} (attempt {attempt + 1})")
                    # Continue to retry

        except requests.exceptions.RequestException as e:
            logger.debug(f"Download failed for {url} (attempt {attempt + 1}): {e}")
        except Exception as e:
            logger.error(f"Unexpected error during sync download for {url}: {e}")
            return False # Do not retry on unexpected errors

        if attempt < max_attempts - 1:
            time.sleep(1.5 ** attempt)  # Exponential backoff

    return False


def get_search_results(
    session: requests.Session,
    engine: str,
    query: str,
    limit: int,
    page: int,
    delay_range: tuple[float, float],
) -> list[dict]:
    """Enhanced scraping with comprehensive error handling[1][2][3]."""
    if engine not in ENGINE_MAP:
        logger.error(f"Unsupported engine: {engine}", extra={'engine': engine, 'query': query})
        return []

    cfg = ENGINE_MAP[engine]
    base_url = cfg["url"]
    results: list[dict] = []
    last_request_time = None
    driver = None

    # Create Selenium driver if needed for JavaScript content
    if cfg.get("requires_js", False) and SELENIUM_AVAILABLE:
        driver = create_selenium_driver()
        if not driver:
            logger.warning(f"JavaScript required for {engine} but Selenium unavailable")

    try:
        items_per_page = 30
        # Fetch up to 5 pages or until the limit is reached
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
            search_path_template = cfg["search_path"]
            url_params = {"query": quote_plus(query), "page": current_page}

            # Handle page number insertion based on template
            if "{page}" in search_path_template:
                search_path = search_path_template.format(**url_params)
            else:
                search_path = search_path_template.format(query=url_params["query"])
                # Append page number as query parameter if not in path and page_param is defined
                if current_page > 1 and cfg.get("page_param"):
                    separator = "&" if "?" in search_path else "?"
                    search_path += f"{separator}{cfg.get('page_param')}={current_page}"

            url = urljoin(base_url, search_path)

            logger.info(f"Fetching page {current_page}: {url}",
                       extra={'engine': engine, 'query': query})

            try:
                # Use Selenium for JavaScript sites, otherwise requests
                if driver and cfg.get("requires_js", False):
                    video_items = extract_with_selenium(driver, url, cfg)
                else:
                    # Rotate User-Agent and headers for each request
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
                    logger.warning(f"No video items found on page {current_page} for {engine}")
                    # If no items are found, it might be the end of results or a block.
                    # Consider breaking if this happens consistently for a few pages.
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
                        logger.debug(f"Failed to extract or validate video data: {e}")
                        continue

            except Exception as e:
                logger.error(f"Request failed for page {current_page} ({url}): {e}")
                continue

    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    logger.info(f"Successfully extracted {len(results)} videos for '{query}' from {engine}",
               extra={'engine': engine, 'query': query})
    return results[:limit]


def extract_video_items(soup: BeautifulSoup, cfg: dict) -> list:
    """Extract video items with comprehensive fallback logic."""
    video_items = []

    # Try primary selectors first
    primary_selectors = cfg.get("video_item_selector", "").split(",")
    for selector in primary_selectors:
        selector = selector.strip()
        if not selector: continue
        items = soup.select(selector)
        if items:
            video_items.extend(items)
            logger.debug(f"Found {len(items)} items using primary selector: {selector}")
            # If we found items, we can potentially stop or continue to gather more if needed
            # For now, let's collect all from primary selectors
            # break # Uncomment to stop after first successful primary selector

    # If no items found with primary selectors, try fallback selectors
    if not video_items and "fallback_selectors" in cfg and "container" in cfg["fallback_selectors"]:
        fallback_selectors = cfg["fallback_selectors"]["container"]
        for selector in fallback_selectors:
            selector = selector.strip()
            if not selector: continue
            items = soup.select(selector)
            if items:
                video_items.extend(items)
                logger.debug(f"Found {len(items)} items using fallback selector: {selector}")
                # Break if we found items using fallbacks to avoid redundant searches
                break

    if not video_items:
        logger.debug("No video items found using primary or fallback selectors.")

    return video_items


def extract_video_data_enhanced(item, cfg: dict, base_url: str) -> dict | None:
    """Enhanced video data extraction with comprehensive fallbacks[3]."""
    try:
        # --- Extract Title ---
        title = "Untitled"
        title_selectors = [cfg.get("title_selector", "")]
        if "fallback_selectors" in cfg and "title" in cfg["fallback_selectors"]:
            title_selectors.extend(cfg["fallback_selectors"]["title"])

        for selector in title_selectors:
            selector = selector.strip()
            if not selector: continue
            logger.debug(f"Attempting to select title with: {selector}")
            title_el = item.select_one(selector)
            if title_el:
                title_attr = cfg.get("title_attribute")
                if title_attr and title_el.has_attr(title_attr):
                    title = title_el.get(title_attr, "").strip()
                else:
                    title = title_el.get_text(strip=True)
                if title and title != "Untitled":
                    break # Found a valid title

        # --- Extract Link ---
        link = "#"
        link_selectors = [cfg.get("link_selector", "")]
        if "fallback_selectors" in cfg and "link" in cfg["fallback_selectors"]:
            link_selectors.extend(cfg["fallback_selectors"]["link"])

        for selector in link_selectors:
            selector = selector.strip()
            if not selector: continue
            logger.debug(f"Attempting to select link with: {selector}")
            link_el = item.select_one(selector)
            if link_el and link_el.has_attr("href"):
                href = link_el["href"]
                if href and href != "#":
                    link = urljoin(base_url, href)
                    break # Found a valid link

        # --- Extract Image URL ---
        img_url = None
        img_selectors = [cfg.get("img_selector", "")]
        img_attribute = cfg.get("img_attribute", "") # Specific attribute like data-original
        if "fallback_selectors" in cfg and "img" in cfg["fallback_selectors"]:
            img_selectors.extend(cfg["fallback_selectors"]["img"])

        for selector in img_selectors:
            selector = selector.strip()
            if not selector: continue
            logger.debug(f"Attempting to select image with: {selector}")
            img_el = item.select_one(selector)
            if img_el:
                # Try specific attribute first, then common ones
                attributes_to_try = []
                if img_attribute:
                    attributes_to_try.append(img_attribute)
                attributes_to_try.extend(["data-src", "src", "data-lazy", "data-original", "data-thumb"])

                for attr in attributes_to_try:
                    if img_el.has_attr(attr):
                        img_val = img_el[attr]
                        if img_val and not img_val.startswith("data:"): # Avoid data URIs for now
                            img_url = urljoin(base_url, img_val)
                            break # Found a valid image URL
                if img_url:
                    break # Found an image URL

        # --- Extract Metadata ---
        duration = extract_text_safe(item, cfg.get("time_selector", ""), "N/A")
        views = extract_text_safe(item, cfg.get("meta_selector", ""), "N/A")
        channel_name = extract_text_safe(item, cfg.get("channel_name_selector", ""), "N/A")

        channel_link = "#"
        channel_link_selector = cfg.get("channel_link_selector", "")
        if channel_link_selector:
            for selector in channel_link_selector.split(','):
                selector = selector.strip()
                if not selector: continue
                logger.debug(f"Attempting to select channel link with: {selector}")
                channel_link_el = item.select_one(selector)
                if channel_link_el and channel_link_el.has_attr("href"):
                    href = channel_link_el["href"]
                    if href and href != "#":
                        channel_link = urljoin(base_url, href)
                        break # Found a valid channel link

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
    """Safely extract text with comprehensive error handling and fallbacks."""
    if not selector:
        logger.debug(f"extract_text_safe received empty selector, returning default: {default}")
        return default

    # Split selectors by comma and try each one
    selectors = [s.strip() for s in selector.split(',')]
    for sel in selectors:
        if not sel: continue
        try:
            logger.debug(f"Attempting to extract text with selector: {sel}")
            el = element.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if text and text != "N/A": # Return first non-empty, non-default text
                    return text
        except Exception as e:
            logger.debug(f"Error with selector '{sel}': {e}")
            continue # Try next selector

    # If no text found with any selector, return default
    return default


def validate_video_data_enhanced(data: dict) -> bool:
    """Enhanced validation with comprehensive checks[3]."""
    if not isinstance(data, dict):
        return False

    # Required fields validation
    required_fields = ["title", "link"]
    for field in required_fields:
        if not data.get(field) or data[field] in ["", "Untitled", "#"]:
            logger.debug(f"Validation failed: Missing or invalid required field '{field}'")
            return False

    # URL validation
    try:
        parsed_link = urlparse(data["link"])
        if not parsed_link.scheme or not parsed_link.netloc:
            logger.debug(f"Validation failed: Invalid link URL '{data['link']}'")
            return False
    except Exception:
        logger.debug(f"Validation failed: Exception parsing link URL '{data['link']}'")
        return False

    # Title validation
    title = data.get("title", "")
    if len(title) < 3 or title.lower() in ["untitled", "n/a", "error"]:
        logger.debug(f"Validation failed: Invalid title '{title}'")
        return False

    # Image URL validation (optional, but good practice)
    img_url = data.get("img_url")
    if img_url:
        try:
            parsed_img_url = urlparse(img_url)
            if not parsed_img_url.scheme or not parsed_img_url.netloc:
                logger.debug(f"Validation failed: Invalid image URL '{img_url}'")
                return False
        except Exception:
            logger.debug(f"Validation failed: Exception parsing image URL '{img_url}'")
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
            display: flex; /* Use flex for centering placeholder */
            align-items: center;
            justify-content: center;
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
            width: 100%;
            height: 100%;
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
            <h1>{title}</h1>
            <p class="subtitle">Search results from {engine}</p>
            <div class="stats">
                <div class="stat">🎬 {count} videos</div>
                <div class="stat">🔍 {engine}</div>
                <div class="stat">⏰ {timestamp}</div>
            </div>
        </header>
        <main class="video-grid">"""

ENHANCED_HTML_TAIL = """        </main>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            const images = document.querySelectorAll('img[data-src]');
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        const placeholderContainer = img.parentElement; // The div containing the img
                        
                        // Add loading animation to the container
                        placeholderContainer.classList.add('loading-placeholder');
                        
                        img.src = img.dataset.src;
                        img.onload = () => {
                            img.removeAttribute('data-src');
                            placeholderContainer.classList.remove('loading-placeholder');
                        };
                        img.onerror = () => {
                            // Replace placeholder with error icon if image fails to load
                            placeholderContainer.innerHTML = '<div class="error-placeholder">❌</div>';
                        };
                        imageObserver.unobserve(img);
                    }
                });
            });

            images.forEach(img => {
                // Ensure the img element itself is observed, not just its parent
                imageObserver.observe(img);
            });
        });
    </script>
</body>
</html>"""


async def build_enhanced_html_async(
    results: Sequence[dict],
    query: str,
    engine: str,
    thumbs_dir: Path,
    session: requests.Session,
    workers: int,
) -> Path:
    """Build enhanced HTML with async thumbnail downloads."""
    ensure_dir(thumbs_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize query for filename and ensure uniqueness with UUID
    safe_query_filename = enhanced_slugify(query)[:50]
    filename = f"{engine}_{safe_query_filename}_{timestamp}_{uuid.uuid4().hex[:8]}.html"
    outfile = Path(filename)

    def get_thumb_path(img_url: str, title: str, idx: int) -> Path:
        """Generate a consistent, safe file path for a thumbnail."""
        # Extract extension from URL, default to .jpg if not found or invalid
        parsed_url = urlparse(img_url)
        _, ext = os.path.splitext(parsed_url.path)
        if not ext or ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            ext = ".jpg" # Default to jpg if extension is missing or unsupported

        safe_title = enhanced_slugify(title)[:50]
        # Ensure filename is unique and safe
        return thumbs_dir / f"{safe_title}_{idx}{ext}"

    def generate_placeholder_svg(icon: str) -> str:
        """Generate SVG placeholder for thumbnails."""
        # Using a dark background matching the card background
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
            <rect width="100%" height="100%" fill="#16213e"/>
            <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" 
                  font-family="sans-serif" font-size="2rem" fill="#666">{icon}</text>
        </svg>'''
        # Base64 encode the SVG for embedding in HTML
        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

    async def fetch_thumbnail_async_task(idx: int, video: dict) -> tuple[int, str]:
        """Download thumbnail async with caching and fallbacks."""
        img_url = video.get("img_url")
        if not img_url:
            return idx, generate_placeholder_svg("🎬") # Placeholder for missing image URL

        dest_path = get_thumb_path(img_url, video.get("title", "video"), idx)

        # Use cached version if it exists and is valid (non-empty)
        if dest_path.exists() and dest_path.stat().st_size > 0:
            return idx, str(dest_path).replace("\", "/") # Return path relative to script

        try:
            # Try async download first
            async with aiohttp_session() as async_session:
                if async_session:
                    semaphore = asyncio.Semaphore(workers) # Limit concurrent downloads
                    if await async_download_thumbnail(async_session, img_url, dest_path, semaphore):
                        return idx, str(dest_path).replace("\", "/")

            # Fallback to sync download if async fails or is unavailable
            if robust_download_sync(session, img_url, dest_path):
                return idx, str(dest_path).replace("\", "/")

        except Exception as e:
            logger.debug(f"Error during thumbnail fetch for {img_url}: {e}")

        # Return error placeholder if all download attempts fail
        return idx, generate_placeholder_svg("❌")

    def fetch_thumbnail_sync_task(idx: int, video: dict) -> tuple[int, str]:
        """Wrapper for threaded sync download with caching."""
        img_url = video.get("img_url")
        if not img_url:
            return idx, generate_placeholder_svg("🎬")

        dest_path = get_thumb_path(img_url, video.get("title", "video"), idx)

        # Use cached version if it exists and is valid
        if dest_path.exists() and dest_path.stat().st_size > 0:
            return idx, str(dest_path).replace("\", "/")

        if robust_download_sync(session, img_url, dest_path):
            return idx, str(dest_path).replace("\", "/")

        return idx, generate_placeholder_svg("❌")

    # Download thumbnails concurrently
    thumbnail_paths = [""] * len(results)

    if ASYNC_AVAILABLE and not args.no_async: # Use async if available and not disabled
        tasks = [fetch_thumbnail_async_task(i, video) for i, video in enumerate(results)]
        # Gather results, handling potential exceptions from tasks
        results_with_idx = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results_with_idx:
            if isinstance(result, tuple) and len(result) == 2:
                idx, path = result
                thumbnail_paths[idx] = path
            elif isinstance(result, Exception):
                logger.debug(f"Error gathering async thumbnail result: {result}")
                # Assign a placeholder if an exception occurred for a specific task
                # This requires knowing which task failed, which gather doesn't directly provide without more complex handling.
                # For simplicity, we'll rely on the task itself returning a placeholder on error.
            else:
                logger.debug(f"Unexpected result format from asyncio.gather: {result}")
    else:
        # Fallback to threaded downloads if async is not available or disabled
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, 20)) as executor:
            future_to_idx = {
                executor.submit(fetch_thumbnail_sync_task, i, video): i
                for i, video in enumerate(results)
            }

            # Use tqdm for progress bar during threaded downloads
            for future in tqdm(
                concurrent.futures.as_completed(future_to_idx),
                total=len(future_to_idx),
                desc=f"{NEON['MAGENTA']}Downloading Thumbnails{NEON['RESET']}",
                unit="files",
                ncols=100
            ):
                i = future_to_idx[future]
                try:
                    _, path = future.result()
                    thumbnail_paths[i] = path
                except Exception as e:
                    logger.debug(f"Error with threaded download for item {i}: {e}")
                    thumbnail_paths[i] = generate_placeholder_svg("❌") # Assign placeholder on error

    # Generate HTML
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(ENHANCED_HTML_HEAD.format(
            title=f"{html.escape(query)} - {engine.title()}", # Use title-cased engine name
            query=html.escape(query),
            engine=engine.title(),
            count=len(results),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        # Iterate through results and their corresponding thumbnail paths
        for video, thumbnail in zip(results, thumbnail_paths, strict=False): # strict=False to handle potential length mismatch gracefully
            # Build meta items for display
            meta_items = []
            if video.get("time", "N/A") != "N/A":
                meta_items.append(f'<span class="meta-item">⏱️ {html.escape(video["time"])}</span>')

            if video.get("channel_name", "N/A") != "N/A":
                channel_link = video.get("channel_link", "#")
                if channel_link != "#":
                    meta_items.append(f'<span class="meta-item"><a href="{html.escape(channel_link)}" target="_blank" rel="noopener noreferrer">👤 {html.escape(video["channel_name"])}</a></span>')
                else:
                    meta_items.append(f'<span class="meta-item">👤 {html.escape(video["channel_name"])}</span>')

            if video.get("meta", "N/A") != "N/A":
                meta_items.append(f'<span class="meta-item">👁️ {html.escape(video["meta"])}</span>')

            # Write video card HTML
            f.write(f'''
            <div class="video-card">
                <a href="{html.escape(video['link'])}" target="_blank" rel="noopener noreferrer">
                    <div class="thumbnail">
                        <img src="" data-src="{html.escape(thumbnail)}" alt="{html.escape(video['title'])}" loading="lazy">
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
                        {" ".join(meta_items)}
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
        epilog="""
Example usage:
  python3 video_search.py "cats in space"
  python3 video_search.py "ocean waves" -e pexels -l 50 -p 2 -o json
  python3 video_search.py "daily news" -e dailymotion --no-async --no-open
  python3 video_search.py "search term" -x http://user:pass@host:port
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

    # Check for async availability and user override
    global ASYNC_AVAILABLE
    if args.no_async:
        ASYNC_AVAILABLE = False
        logger.info("Async downloading disabled by user.")

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
                # Synchronous fallback for HTML generation
                async def sync_html_builder_wrapper():
                    return await build_enhanced_html_async(
                        results=results,
                        query=args.query,
                        engine=args.engine,
                        thumbs_dir=Path(THUMBNAILS_DIR),
                        session=session,
                        workers=args.workers,
                    )
                # Run the async function synchronously
                outfile = asyncio.run(sync_html_builder_wrapper())

            # Open the file in the browser if not disabled
            if not args.no_open and outfile.exists():
                try:
                    # Ensure absolute path for file:// URL
                    abs_outfile_path = os.path.abspath(outfile)
                    webbrowser.open(f"file://{abs_outfile_path}")
                    print(f"{NEON['CYAN']}HTML results saved to: {outfile}{NEON['RESET']}")
                except Exception as e:
                    print(f"{NEON['YELLOW']}Failed to open browser automatically: {e}{NEON['RESET']}")
                    print(f"{NEON['YELLOW']}Please open the file manually: {os.path.abspath(outfile)}{NEON['RESET']}")

    except Exception as e:
        logger.critical(f"An unhandled error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()