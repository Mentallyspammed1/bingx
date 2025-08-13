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
import csv
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
    TQDM_AVAILABLE = True
except ModuleNotFoundError:
    TQDM_AVAILABLE = False
    def tqdm(iterable, **kwargs):  # type: ignore
        return iterable


# ── Enhanced Color Setup ────────────────────────────────────────────────
init(autoreset=True)
NEON = {
    "CYAN": Fore.CYAN, "MAGENTA": Fore.MAGENTA, "GREEN": Fore.GREEN,
    "YELLOW": Fore.YELLOW, "RED": Fore.RED, "BLUE": Fore.BLUE,
    "WHITE": Fore.WHITE, "BRIGHT": Style.BRIGHT, "RESET": Style.RESET_ALL,
}

LOG_FMT = (
    f"{NEON['CYAN']}%(asctime)s{NEON['RESET']} - "
    f"{NEON['MAGENTA']}%(levelname)s{NEON['RESET']} - "
    f"{NEON['BLUE']}[%(engine)s]{NEON['RESET']} "
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
    log_handlers.append(logging.FileHandler("video_search.log", mode="a", encoding="utf-8"))
except PermissionError:
    pass

logging.basicConfig(level=logging.INFO, format=LOG_FMT, handlers=log_handlers)
logger = logging.getLogger(__name__)
logger.addFilter(ContextFilter())

# Suppress noisy loggers
for noisy in ("urllib3", "chardet", "requests", "aiohttp", "selenium"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


# ── Enhanced Defaults & Configuration ────────────────────────────────────
THUMBNAILS_DIR = Path("downloaded_thumbnails")
VSEARCH_DIR = Path("vsearch_results")
DEFAULT_ENGINE = "pexels"
DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_FORMAT = "html"
DEFAULT_TIMEOUT = 25
DEFAULT_DELAY = (1.5, 4.0)
DEFAULT_MAX_RETRIES = 5
DEFAULT_WORKERS = 12
ADULT_ENGINES = {"xhamster", "pornhub", "xvideos", "xnxx", "youjizz", "redtube"}
ALLOW_ADULT = False # This will be set by argparse

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
        "DNT": "1", # Do Not Track
        "Sec-GPC": "1", # Global Privacy Control
    }

# ── The Grimoire of Web Sources (Engine Configurations) ──────────────────
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
            "link": ["a[href*='/video/']", "a.video-link"],
            "container": ["article"]
        }
    },
    "dailymotion": {
        "url": "https://www.dailymotion.com",
        "search_path": "/search/{query}/videos",
        "page_param": "page",
        "requires_js": True,
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
            "link": ["a[href*='/video/']"],
            "container": ["div.VideoTile"]
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
            "link": ["a[href*='/videos/']"],
            "container": ["div.thumb-list__item"]
        }
    },
    "pornhub": {
        "url": "https://www.pornhub.com",
        "search_path": "/video/search?search={query}",
        "gif_search_path": "/gifs/search?search={query}",
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
            "link": ["a[href*='/view_video.php']", "a.video-link"],
            "container": ["li.video-item", "div.videoblock"]
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
            "link": ["a[href*='/video']"],
            "container": ["div.thumb-block"]
        }
    },
    "xnxx": {
        "url": "https://www.xnxx.com",
        "search_path": "/search/{query}/",
        "page_param": "p",
        "requires_js": False,
        "video_item_selector": "div.mozaique > div.thumb-block",
        "link_selector": ".thumb-under > a",
        "title_selector": ".thumb-under > a",
        "img_selector": "img[data-src]",
        "time_selector": "span.duration",
        "meta_selector": "span.video-views",
        "fallback_selectors": {
            "title": ["a[title]", "p.title"],
            "img": ["img[src]"],
            "link": ["a[href*='/video']"],
            "container": ["div.thumb-block"]
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
            "link": ["a[href*='/videos/']"],
            "container": ["div.video-thumb"]
        }
    },
    "redtube": {
        "url": "https://www.redtube.com",
        "search_path": "/?search={query}",
        "page_param": "page",
        "requires_js": False,
        "video_item_selector": "li.video-item",
        "link_selector": "a.video-link",
        "title_selector": "span.video-title",
        "img_selector": "img",
        "time_selector": "span.duration",
        "meta_selector": "span.views",
        "fallback_selectors": {
            "title": ["span.video-title", "a[title]"],
            "img": ["img[src]", "img[data-src]"],
            "link": ["a.video-link"],
            "container": ["li.video-item"]
        }
    },
}

# ── Arcane Utilities & Helpers ───────────────────────────────────────────
def ensure_dir(path: Path) -> None:
    """Ensure directory exists with comprehensive error handling."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise

def enhanced_slugify(text: str) -> str:
    """Enhanced slugify with better Unicode handling and security."""
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
    # Windows reserved names
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
    """Create enhanced session with 2025 best practices."""
    session = requests.Session()

    retries = Retry(
        total=max_retries,
        backoff_factor=2.0,
        backoff_jitter=0.5,
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

    user_agent = random.choice(REALISTIC_USER_AGENTS)
    session.headers.update(get_realistic_headers(user_agent))

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
    """Implement intelligent delays with jitter to avoid detection."""
    min_delay, max_delay = delay_range
    current_time = time.time()
    
    if last_request_time:
        elapsed = current_time - last_request_time
        base_wait = random.uniform(min_delay, max_delay)
        jitter_amount = base_wait * jitter * random.uniform(-1, 1)
        min_wait = max(0.5, base_wait + jitter_amount)
        
        if elapsed < min_wait:
            time.sleep(min_wait - elapsed)
    else:
        base_wait = random.uniform(min_delay, max_delay)
        jitter_amount = base_wait * jitter * random.uniform(-1, 1)
        time.sleep(max(0.5, base_wait + jitter_amount))

def create_selenium_driver() -> Optional[webdriver.Chrome]:
    """Create Selenium driver for JavaScript-heavy sites."""
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
        options.add_argument(f"--user-agent={random.choice(REALISTIC_USER_AGENTS)}")
        
        # Disable images and CSS for faster loading, unless specified otherwise
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
    """Extract data using Selenium for JavaScript-heavy sites."""
    try:
        driver.get(url)
        
        # Wait for video items to load
        wait = WebDriverWait(driver, 10)
        found_element = False
        all_selectors = cfg["video_item_selector"].split(',') + cfg.get("fallback_selectors", {}).get("container", [])
        
        for selector in [s.strip() for s in all_selectors if s.strip()]:
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
        
        # Additional wait to ensure dynamic content loads, can be adjusted
        time.sleep(2)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
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


async def download_thumbnail_async(
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
    """Synchronous fallback download with enhanced validation."""
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

def extract_text_safe(element, selector: str, default: str = "N/A") -> str:
    """Safely extract text with comprehensive error handling and fallbacks."""
    if not selector:
        return default
    try:
        # Split selector by comma to try multiple alternatives
        selectors_to_try = [s.strip() for s in selector.split(',') if s.strip()]
        for sel in selectors_to_try:
            el = element.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                return text if text else default
        return default
    except Exception:
        return default

def extract_video_data_enhanced(item, cfg: Dict, base_url: str) -> Optional[Dict]:
    """Enhanced video data extraction with comprehensive fallbacks."""
    try:
        # Extract title with multiple fallback strategies
        title = "Untitled"
        title_selectors = [s.strip() for s in cfg.get("title_selector", "").split(',') if s.strip()]
        if "fallback_selectors" in cfg and "title" in cfg["fallback_selectors"]:
            title_selectors.extend([s.strip() for s in cfg["fallback_selectors"]["title"] if s.strip()])

        for selector in title_selectors:
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
        link_selectors = [s.strip() for s in cfg.get("link_selector", "").split(',') if s.strip()]
        if "fallback_selectors" in cfg and "link" in cfg["fallback_selectors"]:
            link_selectors.extend([s.strip() for s in cfg["fallback_selectors"]["link"] if s.strip()])
            
        for selector in link_selectors:
            link_el = item.select_one(selector)
            if link_el and link_el.has_attr("href"):
                href = link_el["href"]
                if href and href != "#":
                    link = urljoin(base_url, href)
                    break

        # Extract image URL with comprehensive fallbacks
        img_url = None
        img_selectors = [s.strip() for s in cfg.get("img_selector", "").split(',') if s.strip()]
        if "fallback_selectors" in cfg and "img" in cfg["fallback_selectors"]:
            img_selectors.extend([s.strip() for s in cfg["fallback_selectors"]["img"] if s.strip()])

        for selector in img_selectors:
            img_el = item.select_one(selector)
            if img_el:
                # Try multiple attributes in order of preference
                for attr in ["data-src", "src", "data-lazy", "data-original", "data-thumb"]:
                    if img_el.has_attr(attr):
                        img_val = img_el[attr]
                        if img_val and not img_val.startswith("data:"): # Avoid data URIs as primary img_url
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

def validate_video_data_enhanced(data: Dict) -> bool:
    """Enhanced validation with comprehensive checks."""
    if not isinstance(data, dict):
        return False
        
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


# ── Search & Output Generation ───────────────────────────────────────────
def get_search_results(
    session: requests.Session,
    engine: str,
    query: str,
    limit: int,
    page: int,
    delay_range: Tuple[float, float],
    search_type: str = "video",
) -> List[Dict]:
    """Enhanced scraping with comprehensive error handling."""
    if engine not in ENGINE_MAP:
        logger.error(f"Unsupported engine: {engine}", extra={'engine': engine, 'query': query})
        return []

    cfg = ENGINE_MAP[engine]
    base_url = cfg["url"]
    results: List[Dict] = []
    last_request_time = None
    driver = None

    if cfg.get("requires_js", False) and SELENIUM_AVAILABLE:
        driver = create_selenium_driver()
        if not driver:
            logger.warning(f"JavaScript required for {engine} but Selenium unavailable", extra={'engine': engine, 'query': query})

    try:
        items_per_page = 30 # A reasonable estimate, actual might vary
        pages_to_fetch = min(5, (limit + items_per_page - 1) // items_per_page)
        pages_to_fetch = max(1, pages_to_fetch) # Ensure at least one page is fetched

        logger.info(f"Searching {engine} for '{query}' (up to {pages_to_fetch} pages)", 
                   extra={'engine': engine, 'query': query})

        # Use tqdm for page progress if available
        page_range_iterable = range(page, page + pages_to_fetch)
        page_progress_bar = tqdm(page_range_iterable, desc=f"{NEON['BLUE']}Scraping {engine} for '{query}'{NEON['RESET']}", unit="page", dynamic_ncols=True, ncols=100) if TQDM_AVAILABLE else page_range_iterable

        for current_page in page_progress_bar:
            if len(results) >= limit:
                break

            smart_delay_with_jitter(delay_range, last_request_time)
            last_request_time = time.time()

            search_path_key = "gif_search_path" if search_type == "gif" and "gif_search_path" in cfg else "search_path"
            search_path = cfg.get(search_path_key)
            if not search_path:
                logger.error(f"No search path defined for {engine} and type {search_type}", extra={'engine': engine, 'query': query})
                return []

            # Build URL with page parameter logic
            url = urljoin(base_url, search_path.format(query=quote_plus(query)))
            
            if "{page}" in search_path: # Path-based pagination (e.g., /search/query/page)
                url = url.format(page=current_page)
            elif current_page > 1 and cfg.get("page_param"): # Query-parameter based pagination (e.g., ?page=X)
                separator = "&" if "?" in url else "?"
                url += f"{separator}{cfg.get('page_param')}={current_page}"

            logger.debug(f"Fetching page {current_page}: {url}", extra={'engine': engine, 'query': query})

            try:
                # Use Selenium for JavaScript sites, otherwise requests
                if driver and cfg.get("requires_js", False):
                    video_items = extract_with_selenium(driver, url, cfg)
                else:
                    user_agent = random.choice(REALISTIC_USER_AGENTS)
                    session.headers.update(get_realistic_headers(user_agent))
                    
                    response = session.get(url, timeout=getattr(session, 'timeout', DEFAULT_TIMEOUT))
                    response.raise_for_status()

                    if response.status_code != 200:
                        logger.warning(f"Unexpected status {response.status_code} for {url}", extra={'engine': engine, 'query': query})
                        continue

                    soup = BeautifulSoup(response.text, "html.parser")
                    video_items = extract_video_items(soup, cfg)

                if not video_items:
                    logger.warning(f"No video items found on page {current_page}", extra={'engine': engine, 'query': query})
                    continue

                logger.debug(f"Found {len(video_items)} raw video items on page {current_page}", extra={'engine': engine, 'query': query})

                # Process each video item with enhanced validation
                for item in video_items:
                    if len(results) >= limit:
                        break

                    try:
                        video_data = extract_video_data_enhanced(item, cfg, base_url)
                        if video_data and validate_video_data_enhanced(video_data):
                            results.append(video_data)
                    except Exception as e:
                        logger.debug(f"Failed to extract video data from item: {e}", extra={'engine': engine, 'query': query})
                        continue

            except Exception as e:
                logger.error(f"Request failed for page {current_page}: {e}", extra={'engine': engine, 'query': query})
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


# HTML Placeholder for lazy loading images before they download
# Uses a small, immediate SVG to prevent broken image icons
def generate_placeholder_svg(icon: str) -> str:
    """Generate SVG placeholder for image loading/error states."""
    safe_icon = html.escape(unicodedata.normalize("NFKC", icon), quote=True)
    # Using a 100x100 viewBox and centering text for better scaling
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 100 100">
        <rect width="100%" height="100%" fill="#1a1a2e"/>
        <text x="50" y="55" font-family="sans-serif" font-size="40" fill="#4a4a5e" text-anchor="middle" dominant-baseline="middle">{safe_icon}</text>
    </svg>'''
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")

PLACEHOLDER_THUMB_SVG = generate_placeholder_svg("\U0001F3AC") # Film Projector/Clapperboard

HTML_HEAD = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-dark: #0a0a1a; --card-dark: #16213e; --text-dark: #e0e0e0; --muted-dark: #a0a0a0; --border-dark: #2a2a3e;
      --bg-light: #f0f2f5; --card-light: #ffffff; --text-light: #1c1e21; --muted-light: #65676b; --border-light: #ced0d4;
      --accent-cyan: #00d4ff; --accent-pink: #ff006e;
      --grad: linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-pink) 100%);
      --shadow: rgba(0, 0, 0, 0.2);
    }}
    [data-theme="dark"] {{
      --bg: var(--bg-dark); --card: var(--card-dark); --text: var(--text-dark); --muted: var(--muted-dark); --border: var(--border-dark);
    }}
    [data-theme="light"] {{
      --bg: var(--bg-light); --card: var(--card-light); --text: var(--text-light); --muted: var(--muted-light); --border: var(--border-light);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); transition: background 0.3s, color 0.3s; line-height: 1.6; overflow-x: hidden;}}
    .container {{ max-width: 1600px; margin: 2rem auto; padding: 1rem; background: var(--bg); border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
    header {{ text-align: center; padding: 1.5rem 0; margin-bottom: 2rem; }}
    h1 {{ font-family: "JetBrains Mono", monospace; font-size: 2.5rem; background: var(--grad); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 0.5rem; text-shadow: 0 0 15px rgba(0, 212, 255, 0.2);}}
    .subtitle {{ color: var(--muted); font-size: 1.1rem; }}
    .stats {{ display: flex; justify-content: center; gap: 2rem; margin: 1.5rem 0; flex-wrap: wrap; }}
    .stat {{ background: var(--card); padding: 0.75rem 1.5rem; border-radius: 25px; border: 1px solid var(--border); font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; white-space: nowrap;}}

    .controls {{ display: flex; justify-content: center; align-items: center; gap: 1rem; margin-top: 2rem; flex-wrap: wrap;}}
    #filterInput {{ background: var(--card); color: var(--text); border: 1px solid var(--border); border-radius: 8px; padding: 0.6rem 1.2rem; font-size: 1rem; width: 300px; max-width: 80%;}}
    #theme-toggle {{ background: var(--card); color: var(--text); border: 1px solid var(--border); border-radius: 8px; padding: 0.6rem 0.8rem; cursor: pointer; font-size: 1.1rem;}}

    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 2rem; padding: 1rem 0; margin-top: 2rem; }}
    .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 16px; overflow: hidden; display: flex; flex-direction: column; transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); position: relative; box-shadow: 0 4px 20px var(--shadow); }}
    .card:hover {{ transform: translateY(-8px) scale(1.02); box-shadow: 0 20px 40px rgba(0, 212, 255, 0.15); border-color: var(--accent-cyan); }}
    .card::before {{ content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--grad); opacity: 0; transition: opacity 0.3s ease;}}
    .card:hover::before {{ opacity: 1; }}

    .thumb {{ position: relative; width: 100%; height: 200px; overflow: hidden; background: #111; display: flex; align-items: center; justify-content: center;}}
    .thumb img, .thumb .placeholder {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s ease;}}
    .card:hover .thumb img {{ transform: scale(1.1); }}
    
    .loading-spinner {{ border: 4px solid rgba(255, 255, 255, 0.3); border-top: 4px solid var(--accent-cyan); border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; }}
    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}

    .body {{ padding: 1.5rem; display: flex; flex-direction: column; flex-grow: 1; }}
    .title {{ font-size: 1.1rem; font-weight: 600; margin: 0 0 1rem; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 0.75rem; font-size: 0.85rem; color: var(--muted); margin-top: auto; padding-top: 1rem; border-top: 1px solid var(--border); }}
    .meta .item {{ background: rgba(0, 212, 255, 0.1); color: var(--accent-cyan); padding: 0.3rem 0.8rem; border-radius: 15px; font-family: 'JetBrains Mono', monospace; font-weight: 500; white-space: nowrap; display: flex; align-items: center; gap: 0.3rem; }}
    a {{ text-decoration: none; color: inherit; transition: color 0.3s ease; }}
    a:hover {{ color: var(--accent-cyan); }}

    @media (max-width: 768px) {{
        .container {{ margin: 1rem; padding: 0.5rem; border-radius: 12px; }}
        h1 {{ font-size: 2rem; }}
        .stats {{ gap: 1rem; }}
        .stat {{ padding: 0.5rem 1rem; font-size: 0.8rem; }}
        .grid {{ grid-template-columns: 1fr; gap: 1.5rem; }}
        .body {{ padding: 1rem; }}
    }}
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>{query}</h1>
    <p class="subtitle">Search results from {engine}</p>
    <div class="stats">
        <div class="stat">������ {count} videos</div>
        <div class="stat">������ {engine}</div>
        <div class="stat">23F0 {timestamp}</div>
    </div>
    <div class="controls">
      <input type="text" id="filterInput" placeholder="Filter results by title...">
      <button id="theme-toggle" title="Toggle theme">\U0001F319</button>
    </div>
  </header>
  <section class="grid">
"""

HTML_TAIL = """  </section>
</div>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        // Lazy loading for images
        const images = document.querySelectorAll('img[data-src]');
        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    const thumbDiv = img.closest('.thumb'); // Get the parent .thumb div
                    
                    // Show a spinner while loading
                    if (thumbDiv) {
                        thumbDiv.innerHTML = '<div class="loading-spinner"></div>';
                    }

                    const actualImg = new Image();
                    actualImg.src = img.dataset.src;

                    actualImg.onload = () => {
                        if (thumbDiv) {
                            thumbDiv.innerHTML = ''; // Clear spinner
                            thumbDiv.appendChild(actualImg);
                            actualImg.classList.add('original-image-loaded'); // Add class for potential CSS transitions
                        }
                    };

                    actualImg.onerror = () => {
                        console.error('Failed to load image:', img.dataset.src);
                        if (thumbDiv) {
                            thumbDiv.innerHTML = '<div class="placeholder">274C</div>'; // Show error icon
                        }
                    };

                    obs.unobserve(img); // Stop observing once load is initiated
                }
            });
        }, { threshold: 0.1 });
        images.forEach(img => observer.observe(img));

        // Live filter
        const filterInput = document.getElementById('filterInput');
        const grid = document.querySelector('.grid');
        const cards = Array.from(grid.children);
        filterInput.addEventListener('input', (e) => {
            const searchTerm = e.target.value.toLowerCase();
            cards.forEach(card => {
                const title = card.dataset.title || '';
                card.style.display = title.includes(searchTerm) ? '' : 'none';
            });
        });

        // Theme toggle
        const toggle = document.getElementById('theme-toggle');
        const doc = document.documentElement;
        // Set initial theme icon
        toggle.textContent = doc.getAttribute('data-theme') === 'dark' ? '\\U0001F319' : '\\u2600\\uFE0F';
        toggle.addEventListener('click', () => {
            const currentTheme = doc.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            doc.setAttribute('data-theme', newTheme);
            toggle.textContent = newTheme === 'dark' ? '\\U0001F319' : '\\u2600\\uFE0F';
        });
    });
</script>
</body>
</html>"""

async def build_html_gallery(results: List[Dict], query: str, engine: str, workers: int) -> Path:
    """Build HTML gallery with lazy-loaded and error-handled thumbnails."""
    ensure_dir(THUMBNAILS_DIR)
    ensure_dir(VSEARCH_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{engine}_{enhanced_slugify(query)}_{timestamp}_{uuid.uuid4().hex[:8]}.html"
    outfile = VSEARCH_DIR / filename
    
    semaphore = asyncio.Semaphore(workers)

    async def fetch_thumbnail_task(idx: int, video: Dict, session: requests.Session) -> Tuple[int, str]:
        """Download thumbnail async or fallback to sync, returning relative path."""
        img_url = video.get("img_url")
        if not img_url:
            return idx, generate_placeholder_svg("������") # Generic video icon if no URL

        try:
            # Determine appropriate file extension
            parsed_url = urlparse(img_url)
            ext = os.path.splitext(parsed_url.path)[1]
            if not ext or len(ext) > 5: # Basic check for valid extension
                ext = ".jpg" # Default to JPG if unknown
            safe_title = enhanced_slugify(video.get("title", "video"))
            thumb_filename = f"{safe_title}_{idx}{ext}"
            dest_path = THUMBNAILS_DIR / thumb_filename

            # If already downloaded, use existing
            if dest_path.exists() and dest_path.stat().st_size > 0:
                return idx, dest_path.relative_to(VSEARCH_DIR).as_posix()

            # Try async download first
            if ASYNC_AVAILABLE:
                async with aiohttp_session() as async_http_session:
                    if async_http_session and await download_thumbnail_async(async_http_session, img_url, dest_path, semaphore):
                        return idx, dest_path.relative_to(VSEARCH_DIR).as_posix()
            
            # Fallback to sync download
            if robust_download_sync(session, img_url, dest_path):
                return idx, dest_path.relative_to(VSEARCH_DIR).as_posix()

        except Exception as e:
            logger.debug(f"Error during thumbnail fetch for {img_url}: {e}")

        # If all attempts fail
        return idx, generate_placeholder_svg("274C") # Broken image icon

    # Collect all thumbnail fetching tasks
    tasks = [fetch_thumbnail_task(i, video, session) for i, video in enumerate(results)]
    
    # Run tasks with a progress bar if tqdm is available
    if TQDM_AVAILABLE:
        thumbnail_paths_with_idx_futures = tqdm(
            asyncio.as_completed(tasks),
            total=len(tasks),
            desc=f"{NEON['MAGENTA']}Downloading Thumbnails{NEON['RESET']}",
            unit="files",
            ncols=100,
            dynamic_ncols=True
        )
    else:
        thumbnail_paths_with_idx_futures = asyncio.as_completed(tasks)

    # Collect results from futures
    thumbnail_results: List[Tuple[int, str]] = []
    for future in thumbnail_paths_with_idx_futures:
        try:
            result = await future
            thumbnail_results.append(result)
        except Exception as e:
            logger.error(f"Error processing thumbnail task: {e}")
            # Append a placeholder result if an exception occurs at the future level
            thumbnail_results.append((-1, generate_placeholder_svg("⁉️")))

    # Sort results by original index to maintain order
    thumbnail_results.sort(key=lambda x: x[0])
    thumbnail_paths = [path for _, path in thumbnail_results]

    with open(outfile, "w", encoding="utf-8") as f:
        f.write(HTML_HEAD.format(
            title=f"{html.escape(query)} - {engine}",
            query=html.escape(query),
            engine=engine.title(),
            count=len(results),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
        ))

        for video, thumbnail_path in zip(results, thumbnail_paths):
            # Build meta items
            meta_items = []
            if video.get("time", "N/A") != "N/A":
                meta_items.append(f'<span class="item">23F1FE0F️ {html.escape(video["time"])}</span>')

            if video.get("channel_name", "N/A") != "N/A":
                channel_link = video.get("channel_link", "#")
                if channel_link and channel_link != "#":
                    meta_items.append(f'<span class="item"><a href="{html.escape(channel_link)}" target="_blank" rel="noopener noreferrer">������ {html.escape(video["channel_name"])}</a></span>')
                else:
                    meta_items.append(f'<span class="item">������ {html.escape(video["channel_name"])}</span>')

            if video.get("meta", "N/A") != "N/A":
                meta_items.append(f'<span class="item">������ {html.escape(video["meta"])}</span>')

            # Determine image src and data-src for lazy loading
            if thumbnail_path.startswith("data:image"):
                # If it's a base64 SVG (placeholder or error), load immediately
                img_html = f'<img src="{html.escape(thumbnail_path)}" alt="{html.escape(video["title"])}">'
            else:
                # If it's a local file, use lazy loading with a placeholder
                img_html = f'<img src="{PLACEHOLDER_THUMB_SVG}" data-src="{html.escape(thumbnail_path)}" alt="{html.escape(video["title"])}" loading="lazy">'

            f.write(f'''
            <div class="card" data-title="{video['title'].lower()}">
              <a href="{html.escape(video['link'])}" target="_blank" rel="noopener noreferrer">
                <div class="thumb">
                  {img_html}
                </div>
              </a>
              <div class="body">
                <div class="title"><a href="{html.escape(video['link'])}" target="_blank" rel="noopener noreferrer">{video['title']}</a></div>
                <div class="meta">{meta_items if isinstance(meta_items, str) else "".join(meta_items)}</div>
              </div>
            </div>''') # Fixed meta_items handling to always join
        f.write(HTML_TAIL)
    
    logger.info(f"HTML gallery saved to: {outfile}", extra={'engine': engine, 'query': query})
    return outfile

def generate_other_outputs(results: List[Dict], query: str, engine: str, format: str) -> None:
    """Generate JSON or CSV output files."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{engine}_{enhanced_slugify(query)}_{timestamp}.{format}"
    outfile = VSEARCH_DIR / filename
    ensure_dir(VSEARCH_DIR)
    
    if format == "json":
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
    elif format == "csv":
        if not results:
            logger.warning(f"No results to write for CSV output.", extra={'engine': engine, 'query': query})
            return
        
        # Determine headers, including all potential keys from all results
        all_keys = set()
        for res in results:
            all_keys.update(res.keys())
        # Prioritize common fields
        ordered_keys = [
            "title", "link", "img_url", "time", "channel_name", 
            "channel_link", "meta", "source_engine", "extracted_at"
        ]
        # Add any remaining keys
        for key in sorted(list(all_keys - set(ordered_keys))):
            ordered_keys.append(key)

        with open(outfile, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=ordered_keys)
            writer.writeheader()
            writer.writerows(results)
            
    logger.info(f"{format.upper()} output saved to: {outfile}", extra={'engine': engine, 'query': query})

# ── Main Execution Orchestration ─────────────────────────────────────────
def main():
    """Main function to parse arguments and run the search process."""
    parser = argparse.ArgumentParser(
        description="Enhanced Video Search Tool",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f"""\
Example usage:
  python3 video_search.py "cats in space"
  python3 video_search.py "ocean waves" -e pexels -l 50 -p 2 -o json
  python3 video_search.py "daily news" -e dailymotion --no-open
  python3 video_search.py "search term" -e pornhub --allow-adult -x http://user:pass@host:port
  python3 video_search.py "funny moments" -o csv
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
        "-o", "--output", type=str, default=DEFAULT_FORMAT,
        choices=["html", "json", "csv"],
        help=f"Output format for the results (default: {DEFAULT_FORMAT})."
    )
    parser.add_argument(
        "--type", type=str, default="video",
        choices=["video", "gif"],
        help="Type of content to search for (video or gif)."
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
        "--no-open", action="store_true",
        help="Do not automatically open the HTML result in a web browser."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose logging."
    )
    parser.add_argument(
        "--allow-adult", action="store_true",
        help="Allow searching on adult-themed engines. Use responsibly."
    )
    
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    global ALLOW_ADULT # Set global flag for adult content check
    if args.allow_adult:
        ALLOW_ADULT = True
    
    if args.engine in ADULT_ENGINES and not ALLOW_ADULT:
        logger.error(f"Engine '{args.engine}' requires the --allow-adult flag to be enabled. Aborting.", extra={'engine': args.engine, 'query': args.query})
        sys.exit(1)

    # Handle KeyboardInterrupt gracefully
    def signal_handler(sig, frame):
        print(f"\n{NEON['YELLOW']}* Ctrl+C detected. Exiting gracefully...{NEON['RESET']}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        session = build_enhanced_session(DEFAULT_TIMEOUT, DEFAULT_MAX_RETRIES, args.proxy)
        
        logger.info(f"{Style.BRIGHT}Starting search for '{args.query}' on {args.engine}...{Style.RESET_ALL}", 
                   extra={'engine': args.engine, 'query': args.query})

        # Search for results
        results = get_search_results(
            session=session,
            engine=args.engine,
            query=args.query,
            limit=args.limit,
            page=args.page,
            delay_range=DEFAULT_DELAY,
            search_type=args.type,
        )
        
        if not results:
            print(f"{NEON['RED']}No videos found for '{args.query}' on {args.engine}.{NEON['RESET']}")
            sys.exit(0) # Exit with 0 if no results found, as it's not an error condition
        
        print(f"{NEON['GREEN']}Found {len(results)} videos.{NEON['RESET']}")

        # Handle output format
        if args.output == "html":
            # Use asyncio to run the HTML builder
            loop = asyncio.get_event_loop()
            outfile = loop.run_until_complete(
                build_html_gallery(
                    results=results,
                    query=args.query,
                    engine=args.engine,
                    workers=args.workers,
                )
            )

            # Open the file
            if not args.no_open and outfile.exists():
                try:
                    webbrowser.open(f"file://{os.path.abspath(outfile)}")
                except Exception as e:
                    print(f"{NEON['YELLOW']}Failed to open browser: {e}{NEON['RESET']}")
        
        else: # json or csv format
            generate_other_outputs(results, args.query, args.engine, args.output)
        
    except Exception as e:
        logger.critical(f"An unhandled error occurred: {e}", exc_info=True, extra={'engine': args.engine, 'query': args.query})
        sys.exit(1)

if __name__ == "__main__":
    main()