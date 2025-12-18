#!/usr/bin/env python3
"""wowxxx_search.py - Enhanced Wow.xxx Video Search Tool (Upgraded Version)
This script is a specialized version of the generic video search tool,
configured specifically for the wow.xxx platform. It includes numerous
improvements while maintaining backward compatibility.

Key Upgrades:
- Enhanced error recovery and retry mechanisms
- Improved JavaScript rendering detection
- Better thumbnail download management
- Advanced rate limiting with adaptive algorithms
- Enhanced configuration flexibility
- Improved logging and monitoring
- Better proxy support with automatic rotation
- Enhanced output formatting options

Usage:
  python3 wowxxx_search.py "your search query" [options]

Example:
  python3 wowxxx_search.py "your query" -l 50
  python3 wowxxx_search.py "your query" --output-format json
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import concurrent.futures
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

# --- Import optional components ---
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

# Detect Termux environment and disable Selenium if present
if 'TERMUX_VERSION' in os.environ:
    SELENIUM_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ModuleNotFoundError:
    TQDM_AVAILABLE = False
    def tqdm(iterable, **kwargs):
        return iterable

# --- Enhanced Configuration ---
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
    f"{NEON['BLUE']}[%(engine)s]{NEON['RESET']} "
    f"{NEON['GREEN']}%(message)s{NEON['RESET']}"
)

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.engine = getattr(record, 'engine', 'Wowxxx')
        record.query = getattr(record, 'query', 'unknown')
        return True

# Configure logging with file rotation
log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    from logging.handlers import RotatingFileHandler
    file_handler = RotatingFileHandler(
        "wowxxx_search.log",
        maxBytes=5*1024*1024,
        backupCount=3,
        encoding="utf-8"
    )
    log_handlers.append(file_handler)
except (ImportError, PermissionError):
    pass

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FMT,
    handlers=log_handlers
)
logger = logging.getLogger(__name__)
logger.addFilter(ContextFilter())

for noisy in ("urllib3", "chardet", "requests", "aiohttp", "selenium"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# --- Constants and Configuration ---
THUMBNAILS_DIR = Path("downloaded_thumbnails")
VSEARCH_DIR = Path("wowxxx_results")
DEFAULT_ENGINE = "wowxxx"
DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_FORMAT = "html"
DEFAULT_TIMEOUT = 30
DEFAULT_DELAY = (1.5, 4.0)
DEFAULT_MAX_RETRIES = 5
DEFAULT_WORKERS = 12

# Enhanced user agents with more variety
REALISTIC_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.6; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 OPR/101.0.0.0",
]

def get_realistic_headers(user_agent: str) -> dict[str, str]:
    """Generate realistic headers with additional security measures"""
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
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
        "Referer": "https://www.google.com/",
        "Sec-Ch-Ua": '"Not.A/Brand";v="8", "Chromium";v="127", "Google Chrome";v="127"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
    }
    return headers

# Enhanced configuration with more fallback options
WOWXXX_CONFIG: dict[str, Any] = {
    "url": "https://www.wow.xxx",
    "search_path": "/popular/search/{query}/top-rated/",
    "page_param": None,
    "requires_js": True,
    "video_item_selector": "article.video-card, div.video-item, li.video-list-item",
    "link_selector": "a.video-card__link, a.video-item__link, a[href*='/video/']",
    "title_selector": "h3.video-card__title, h2.video-title, span.title-text",
    "title_attribute": "title",
    "img_selector": "img.video-card__thumbnail, img.video-thumbnail, img[data-src], img[src]",
    "time_selector": "span.video-card__duration, span.duration, div.time",
    "meta_selector": "span.video-card__views, span.views, div.meta-info",
    "channel_name_selector": "a.video-card__channel-name, span.channel-name, a[href*='/channel/']",
    "channel_link_selector": "a.video-card__channel-link, a.channel-link",
    "fallback_selectors": {
        "title": ["a[title]", "h2", "div.title", "span.title", "div.video-title"],
        "img": ["img[data-src]", "img[src]", "video-preview", "img.lazy", "img.thumbnail"],
        "link": ["a[href*='/video/']", "a[href*='/viewkey=']", "a.item-link", "a.video-link"]
    },
    "pagination": {
        "enabled": True,
        "max_pages": 5,
        "items_per_page": 30,
        "path_pattern": "/{page}/",
        "detect_end": True,
        "next_page_selector": "a.next-page, a[rel='next']"
    },
    "thumbnail": {
        "min_size": 5000,  # Minimum acceptable thumbnail size in bytes
        "max_size": 5 * 1024 * 1024,  # Maximum thumbnail size
        "timeout": 20,
        "retries": 3
    }
}

# --- Enhanced Utility Functions ---
def ensure_dir(path: Path) -> None:
    """Ensure directory exists with improved error handling"""
    try:
        path.mkdir(parents=True, exist_ok=True)
        # Verify directory was actually created
        if not path.exists():
            raise OSError(f"Directory creation failed: {path}")
    except (PermissionError, OSError) as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise

def enhanced_slugify(text: str) -> str:
    """Improved slugify function with better character handling"""
    if not text or not isinstance(text, str):
        return "untitled"

    # Enhanced normalization and cleaning
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"[^\w\s\-_.]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "_", text.strip())
    text = text.strip("._-")

    # Ensure minimum length and handle empty strings
    if not text or len(text) < 3:
        text = "untitled"

    # Handle reserved names in Windows
    reserved_names = {"con", "prn", "aux", "nul", "com1", "com2", "com3", "com4", "lpt1", "lpt2"}
    if text.lower() in reserved_names:
        text = f"file_{text}"

    return text[:100]

def build_enhanced_session(
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    proxy: str | None = None,
    proxy_list: list[str] | None = None
) -> requests.Session:
    """Build an enhanced session with improved retry logic and proxy rotation"""
    session = requests.Session()

    # Enhanced retry strategy
    retries = Retry(
        total=max_retries,
        backoff_factor=2.0,
        backoff_jitter=0.5,
        status_forcelist=(408, 429, 500, 502, 503, 504, 520, 521, 522, 524),
        allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
        respect_retry_after_header=True,
        raise_on_redirect=False,
        raise_on_status=False
    )

    adapter = HTTPAdapter(
        max_retries=retries,
        pool_connections=20,
        pool_maxsize=50,
        pool_block=False
    )

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # User agent rotation
    user_agent = random.choice(REALISTIC_USER_AGENTS)
    session.headers.update(get_realistic_headers(user_agent))

    # Proxy handling
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

    # Proxy rotation if list provided
    if proxy_list:
        session.proxies = {}
        session.proxy_list = proxy_list
        session.current_proxy = 0

        def rotate_proxy():
            if session.current_proxy >= len(session.proxy_list):
                session.current_proxy = 0
            proxy = session.proxy_list[session.current_proxy]
            session.current_proxy += 1
            try:
                parsed_proxy = urlparse(proxy)
                if parsed_proxy.scheme and parsed_proxy.netloc:
                    session.proxies.update({"http": proxy, "https": proxy})
                    logger.debug(f"Rotated to proxy: {parsed_proxy.netloc}")
                else:
                    logger.warning(f"Invalid proxy in rotation list: {proxy}")
            except Exception as e:
                logger.warning(f"Failed to rotate to proxy {proxy}: {e}")

        # Add hook to rotate proxy on request failures
        session.hooks['response'].append(lambda r, *args, **kwargs: rotate_proxy() if r.status_code >= 400 else None)

    session.timeout = timeout
    return session

def smart_delay_with_jitter(
    delay_range: tuple[float, float],
    last_request_time: float | None = None,
    jitter: float = 0.3,
    adaptive: bool = True,
    request_history: list[float] | None = None
) -> None:
    """Enhanced delay function with adaptive rate limiting based on request history
    and improved jitter calculation for more human-like behavior.
    """
    min_delay, max_delay = delay_range
    current_time = time.time()

    # Initialize request history if not provided
    if request_history is None:
        request_history = []

    # Calculate average request rate if we have history
    if len(request_history) > 1:
        avg_interval = (current_time - request_history[0]) / len(request_history)
    else:
        avg_interval = (min_delay + max_delay) / 2

    if last_request_time:
        elapsed = current_time - last_request_time
        request_history.append(current_time)

        # Keep only the last 10 requests for history
        if len(request_history) > 10:
            request_history.pop(0)

        if adaptive:
            # Adaptive delay based on request history
            if avg_interval < min_delay:
                # If we're going too fast, increase the wait time
                adaptive_factor = min_delay / max(0.1, avg_interval)
                base_wait = random.uniform(min_delay, max_delay) * adaptive_factor
            else:
                # If we're going at a normal pace, use normal delay
                base_wait = random.uniform(min_delay, max_delay)

            # Add jitter with more sophisticated calculation
            jitter_amount = base_wait * jitter * random.gauss(0, 1)
            min_wait = max(0.5, base_wait + jitter_amount)

            if elapsed < min_wait:
                time.sleep(min_wait - elapsed)
        else:
            base_wait = random.uniform(min_delay, max_delay)
            jitter_amount = base_wait * jitter * random.uniform(-1, 1)
            time.sleep(max(0.5, base_wait + jitter_amount))
    else:
        base_wait = random.uniform(min_delay, max_delay)
        jitter_amount = base_wait * jitter * random.uniform(-1, 1)
        time.sleep(max(0.5, base_wait + jitter_amount))

@asynccontextmanager
async def aiohttp_session(
    timeout: int = 30,
    proxy: str | None = None,
    proxy_auth: tuple[str, str] | None = None
) -> AsyncGenerator[aiohttp.ClientSession | None, None]:
    """Enhanced aiohttp session with proxy support and better error handling"""
    if not ASYNC_AVAILABLE:
        yield None
        return

    try:
        # Configure timeout
        timeout_obj = aiohttp.ClientTimeout(total=timeout, connect=10)

        # Configure headers
        headers = get_realistic_headers(random.choice(REALISTIC_USER_AGENTS))

        # Configure proxy if provided
        connector = aiohttp.TCPConnector(limit=50, limit_per_host=10)
        if proxy:
            if proxy_auth:
                auth = aiohttp.BasicAuth(*proxy_auth)
                proxy_url = f"http://{proxy}"
                connector = aiohttp.TCPConnector(
                    limit=50,
                    limit_per_host=10,
                    ssl=False,
                    enable_cleanup_closed=True
                )
            else:
                proxy_url = proxy

            async with aiohttp.ClientSession(
                timeout=timeout_obj,
                headers=headers,
                connector=connector,
                trust_env=True
            ) as session:
                yield session
                return

        # Regular session without proxy
        async with aiohttp.ClientSession(
            timeout=timeout_obj,
            headers=headers,
            connector=connector
        ) as session:
            yield session
    except Exception as e:
        logger.error(f"Failed to create aiohttp session: {e}")
        yield None

async def download_thumbnail_async(
    session: aiohttp.ClientSession,
    url: str,
    path: Path,
    semaphore: asyncio.Semaphore,
    max_retries: int = 3,
    min_size: int = 5000,
    max_size: int = 5 * 1024 * 1024
) -> bool:
    """Enhanced thumbnail download with size validation and better error handling"""
    if not ASYNC_AVAILABLE or not session:
        return False

    # Validate URL before attempting download
    try:
        parsed_url = urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            logger.debug(f"Invalid URL format: {url}")
            return False
    except Exception as e:
        logger.debug(f"URL parsing failed for {url}: {e}")
        return False

    for attempt in range(max_retries):
        async with semaphore:
            try:
                async with session.get(url) as response:
                    if response.status != 200:
                        logger.debug(f"Async download failed, status {response.status} for {url} (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                        continue

                    content_type = response.headers.get("content-type", "").lower()
                    if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                        logger.debug(f"Async download failed, invalid content type for {url} (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                        continue

                    content = await response.read()
                    content_length = len(content)

                    if content_length == 0:
                        logger.debug(f"Async download failed, empty content for {url} (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                        continue

                    if content_length < min_size:
                        logger.debug(f"Async download failed, content too small ({content_length} bytes) for {url} (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                        continue

                    if content_length > max_size:
                        logger.debug(f"Async download failed, content too large ({content_length} bytes) for {url} (attempt {attempt + 1})")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                        continue

                    # Write to file with atomic operation
                    temp_path = path.with_suffix(path.suffix + ".tmp")
                    with open(temp_path, "wb") as f:
                        f.write(content)

                    # Verify file was written correctly
                    if temp_path.exists() and temp_path.stat().st_size == content_length:
                        temp_path.rename(path)
                        return True
                    temp_path.unlink(missing_ok=True)
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.debug(f"Async download failed for {url} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Unexpected error during async download for {url} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

    return False

def robust_download_sync(
    session: requests.Session,
    url: str,
    path: Path,
    max_attempts: int = 3,
    min_size: int = 5000,
    max_size: int = 5 * 1024 * 1024
) -> bool:
    """Enhanced synchronous download with better validation and error handling"""
    if not url or not urlparse(url).scheme:
        return False

    for attempt in range(max_attempts):
        try:
            # Update headers for each attempt
            session.headers.update(get_realistic_headers(random.choice(REALISTIC_USER_AGENTS)))

            with session.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()

                content_type = response.headers.get("content-type", "").lower()
                if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                    logger.debug(f"Sync download failed, invalid content type for {url} (attempt {attempt + 1})")
                    if attempt < max_attempts - 1:
                        time.sleep(2 ** attempt)
                    continue

                content_length = int(response.headers.get("content-length", 0))
                if content_length > max_size:
                    logger.debug(f"Sync download failed, content too large ({content_length} bytes) for {url} (attempt {attempt + 1})")
                    if attempt < max_attempts - 1:
                        time.sleep(2 ** attempt)
                    continue

                # Use temp file for atomic operation
                temp_path = path.with_suffix(path.suffix + ".tmp")
                bytes_written = 0

                with open(temp_path, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
                            bytes_written += len(chunk)

                # Verify download
                if bytes_written < min_size:
                    temp_path.unlink(missing_ok=True)
                    logger.debug(f"Sync download failed, content too small ({bytes_written} bytes) for {url} (attempt {attempt + 1})")
                    if attempt < max_attempts - 1:
                        time.sleep(2 ** attempt)
                    continue

                # Rename temp file to final path
                temp_path.rename(path)
                return True

        except Exception as e:
            logger.debug(f"Download failed for {url} (attempt {attempt + 1}): {e}")
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)

    return False

def extract_video_items(soup: BeautifulSoup, cfg: dict) -> list:
    """Enhanced video item extraction with better fallback handling"""
    video_items = []

    # Try primary selectors first
    for selector in cfg["video_item_selector"].split(","):
        items = soup.select(selector.strip())
        if items:
            video_items.extend(items)
            break  # Use first successful selector

    # If no items found with primary selectors, try fallback
    if not video_items:
        logger.debug("No video items found with primary selectors, trying fallbacks")
        fallback_selectors = [
            "div.video-item",
            "li.video-list-item",
            "article.video",
            "div.video-card",
            "div.video-thumbnail"
        ]
        for selector in fallback_selectors:
            items = soup.select(selector)
            if items:
                video_items.extend(items)
                logger.debug(f"Found {len(items)} items with fallback selector: {selector}")
                break

    return video_items

def extract_text_safe(element, selector: str, default: str = "N/A") -> str:
    """Enhanced text extraction with better fallback handling"""
    if not selector or not element:
        return default

    try:
        selectors_to_try = [s.strip() for s in selector.split(',') if s.strip()]

        for sel in selectors_to_try:
            elements = element.select(sel)
            if elements:
                for el in elements:
                    text = el.get_text(strip=True)
                    if text and text != "N/A":
                        return text

        # If no text found, try to get from attributes
        for sel in selectors_to_try:
            elements = element.select(sel)
            if elements:
                for el in elements:
                    for attr in ["title", "alt", "aria-label", "data-title"]:
                        if el.has_attr(attr):
                            text = el[attr].strip()
                            if text and text != "N/A":
                                return text

        return default
    except Exception as e:
        logger.debug(f"Error extracting text with selector '{selector}': {e}")
        return default

def extract_video_data_enhanced(item, cfg: dict, base_url: str) -> dict | None:
    """Enhanced video data extraction with better validation and fallback handling"""
    try:
        # Extract title with multiple fallback options
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

                # Clean up title
                title = ' '.join(title.split())
                if title and title.lower() not in ["untitled", "n/a", "error"]:
                    break

        # Extract link with validation
        link = "#"
        link_selectors = [s.strip() for s in cfg.get("link_selector", "").split(',') if s.strip()]
        if "fallback_selectors" in cfg and "link" in cfg["fallback_selectors"]:
            link_selectors.extend([s.strip() for s in cfg["fallback_selectors"]["link"] if s.strip()])

        for selector in link_selectors:
            link_el = item.select_one(selector)
            if link_el and link_el.has_attr("href"):
                href = link_el["href"]
                if href and href != "#":
                    # Clean up URL
                    href = href.split('?')[0].split('#')[0].strip()
                    link = urljoin(base_url, href)
                    break

        # Extract image URL with multiple fallback options
        img_url = None
        img_selectors = [s.strip() for s in cfg.get("img_selector", "").split(',') if s.strip()]
        if "fallback_selectors" in cfg and "img" in cfg["fallback_selectors"]:
            img_selectors.extend([s.strip() for s in cfg["fallback_selectors"]["img"] if s.strip()])

        for selector in img_selectors:
            img_el = item.select_one(selector)
            if img_el:
                for attr in ["data-src", "src", "data-lazy", "data-original", "data-thumb", "data-srcset"]:
                    if img_el.has_attr(attr):
                        img_val = img_el[attr].strip()
                        if img_val and not img_val.startswith("data:"):
                            # Handle srcset attribute
                            if attr == "data-srcset":
                                srcset = img_val.split()
                                if len(srcset) >= 2:
                                    img_url = urljoin(base_url, srcset[0])
                                else:
                                    img_url = urljoin(base_url, img_val)
                            else:
                                img_url = urljoin(base_url, img_val)
                            if img_url:
                                break
                if img_url:
                    break

        # Extract duration with fallback
        duration = extract_text_safe(item, cfg.get("time_selector", ""), "N/A")
        if duration == "N/A":
            # Try to extract from other possible locations
            duration = extract_text_safe(item, "span.duration, div.duration, time", "N/A")

        # Extract views/meta information
        views = extract_text_safe(item, cfg.get("meta_selector", ""), "N/A")
        if views == "N/A":
            views = extract_text_safe(item, "span.views, div.views, span.meta-info", "N/A")

        # Extract channel information
        channel_name = extract_text_safe(item, cfg.get("channel_name_selector", ""), "N/A")
        channel_link = "#"
        channel_link_selector = cfg.get("channel_link_selector", "")
        if channel_link_selector:
            channel_link_el = item.select_one(channel_link_selector)
            if channel_link_el and channel_link_el.has_attr("href"):
                href = channel_link_el["href"]
                if href and href != "#":
                    channel_link = urljoin(base_url, href.split('?')[0].split('#')[0].strip())

        # Additional metadata extraction
        additional_meta = {}
        for attr in ["data-id", "data-video-id", "data-duration", "data-views"]:
            if item.has_attr(attr):
                additional_meta[attr] = item[attr]

        # Extract video ID from URL if possible
        video_id = "N/A"
        if link and link != "#":
            parsed = urlparse(link)
            if parsed.path:
                parts = [p for p in parsed.path.split('/') if p]
                if parts:
                    video_id = parts[-1]

        return {
            "title": html.escape(title[:200]),
            "link": link,
            "img_url": img_url,
            "time": duration,
            "channel_name": channel_name,
            "channel_link": channel_link,
            "meta": views,
            "video_id": video_id,
            "extracted_at": datetime.now().isoformat(),
            "source_engine": cfg.get("url", base_url),
            "additional_meta": additional_meta
        }
    except Exception as e:
        logger.debug(f"Error extracting video data: {e}")
        return None

def validate_video_data_enhanced(data: dict) -> bool:
    """Enhanced validation with more comprehensive checks"""
    if not isinstance(data, dict):
        return False

    required_fields = ["title", "link"]
    for field in required_fields:
        if not data.get(field) or data[field] in ["", "Untitled", "#", "N/A"]:
            return False

    try:
        parsed_link = urlparse(data["link"])
        if not parsed_link.scheme or not parsed_link.netloc:
            return False
    except Exception:
        return False

    title = data.get("title", "")
    if len(title) < 3 or title.lower() in ["untitled", "n/a", "error"]:
        return False

    # Additional validation for video ID if present
    video_id = data.get("video_id", "")
    if video_id and video_id != "N/A":
        if len(video_id) < 3 or not re.match(r'^[a-zA-Z0-9_-]+$', video_id):
            return False

    return True

def generate_placeholder_svg(icon: str, width: int = 100, height: int = 100) -> str:
    """Enhanced placeholder SVG generation with customizable size"""
    safe_icon = html.escape(unicodedata.normalize("NFKC", icon), quote=True)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        <rect width="100%" height="100%" fill="#1a1a2e"/>
        <text x="50%" y="50%" font-family="sans-serif" font-size="{min(width, height) // 3}" fill="#4a4a5e"
              text-anchor="middle" dominant-baseline="middle">{safe_icon}</text>
    </svg>'''
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")

# Enhanced HTML templates with better structure and styling
HTML_HEAD = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <meta name="description" content="Video search results for {query} from wow.xxx"/>
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-dark: #0a0a1a;
      --card-dark: #16213e;
      --text-dark: #e0e0e0;
      --muted-dark: #a0a0a0;
      --border-dark: #2a2a3e;
      --accent-cyan: #00d4ff;
      --accent-pink: #ff006e;
      --grad: linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-pink) 100%);
      --shadow: rgba(0, 0, 0, 0.2);
      --transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
    }}
    [data-theme="dark"] {{
      --bg: var(--bg-dark);
      --card: var(--card-dark);
      --text: var(--text-dark);
      --muted: var(--muted-dark);
      --border: var(--border-dark);
    }}
    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}
    body {{
      margin: 0;
      font-family: 'Inter', sans-serif;
      background: var(--bg);
      color: var(--text);
      transition: background 0.3s, color 0.3s;
      line-height: 1.6;
      overflow-x: hidden;
      min-height: 100vh;
    }}
    .container {{
      max-width: 1600px;
      margin: 2rem auto;
      padding: 1rem;
      background: var(--bg);
      border-radius: 20px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }}
    header {{
      text-align: center;
      padding: 1.5rem 0;
      margin-bottom: 2rem;
      position: relative;
    }}
    h1 {{
      font-family: "JetBrains Mono", monospace;
      font-size: 2.5rem;
      background: var(--grad);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 0.5rem;
      text-shadow: 0 0 15px rgba(0, 212, 255, 0.2);
      line-height: 1.2;
    }}
    .subtitle {{
      color: var(--muted);
      font-size: 1.1rem;
      margin-bottom: 1rem;
    }}
    .stats {{
      display: flex;
      justify-content: center;
      gap: 2rem;
      margin: 1.5rem 0;
      flex-wrap: wrap;
    }}
    .stat {{
      background: var(--card);
      padding: 0.75rem 1.5rem;
      border-radius: 25px;
      border: 1px solid var(--border);
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.9rem;
      white-space: nowrap;
      box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 2rem;
      padding: 1rem 0;
      margin-top: 2rem;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 16px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: var(--transition);
      position: relative;
      box-shadow: 0 4px 20px var(--shadow);
      height: 100%;
    }}
    .card:hover {{
      transform: translateY(-8px) scale(1.02);
      box-shadow: 0 20px 40px rgba(0, 212, 255, 0.15);
      border-color: var(--accent-cyan);
    }}
    .card::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: var(--grad);
      opacity: 0;
      transition: opacity 0.3s ease;
    }}
    .card:hover::before {{
      opacity: 1;
    }}
    .thumb {{
      position: relative;
      width: 100%;
      height: 180px;
      overflow: hidden;
      background: #111;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .thumb img, .thumb .placeholder {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 0.3s ease;
    }}
    .card:hover .thumb img {{
      transform: scale(1.1);
    }}
    .loading-spinner {{
      border: 4px solid rgba(255, 255, 255, 0.3);
      border-top: 4px solid var(--accent-cyan);
      border-radius: 50%;
      width: 30px;
      height: 30px;
      animation: spin 1s linear infinite;
    }}
    @keyframes spin {{
      0% {{ transform: rotate(0deg); }}
      100% {{ transform: rotate(360deg); }}
    }}
    .body {{
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      flex-grow: 1;
      height: 100%;
    }}
    .title {{
      font-size: 1.1rem;
      font-weight: 600;
      margin: 0 0 1rem;
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
      min-height: 3rem;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 0.75rem;
      font-size: 0.85rem;
      color: var(--muted);
      margin-top: auto;
      padding-top: 1rem;
      border-top: 1px solid var(--border);
    }}
    .meta .item {{
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
    a {{
      text-decoration: none;
      color: inherit;
      transition: color 0.3s ease;
    }}
    a:hover {{
      color: var(--accent-cyan);
    }}
    .footer {{
      text-align: center;
      margin-top: 2rem;
      padding: 1rem;
      color: var(--muted);
      font-size: 0.9rem;
    }}
    @media (max-width: 768px) {{
      .container {{
        margin: 1rem;
        padding: 0.5rem;
        border-radius: 12px;
      }}
      h1 {{
        font-size: 2rem;
      }}
      .stats {{
        gap: 1rem;
      }}
      .stat {{
        padding: 0.5rem 1rem;
        font-size: 0.8rem;
      }}
      .grid {{
        grid-template-columns: 1fr;
        gap: 1.5rem;
      }}
      .body {{
        padding: 1rem;
      }}
    }}
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>{query}</h1>
    <p class="subtitle">Search results from wow.xxx</p>
    <div class="stats">
        <div class="stat">📹 {count} videos</div>
        <div class="stat">🔍 wow.xxx</div>
        <div class="stat">⏰ {timestamp}</div>
    </div>
  </header>
  <section class="grid">
"""

HTML_TAIL = """  </section>
  <footer class="footer">
    <p>Generated by Wow.xxx Search Tool | {timestamp}</p>
  </footer>
</div>
<script>
    document.addEventListener('DOMContentLoaded', function() {{
        const images = document.querySelectorAll('img[data-src]');
        const observer = new IntersectionObserver((entries, obs) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    const img = entry.target;
                    const thumbDiv = img.closest('.thumb');
                    if (thumbDiv) {{
                        thumbDiv.innerHTML = '<div class="loading-spinner"></div>';
                    }}
                    const actualImg = new Image();
                    actualImg.src = img.dataset.src;
                    actualImg.onload = () => {{
                        if (thumbDiv) {{
                            thumbDiv.innerHTML = '';
                            thumbDiv.appendChild(actualImg);
                            actualImg.classList.add('original-image-loaded');
                        }}
                    }};
                    actualImg.onerror = () => {{
                        console.error('Failed to load image:', img.dataset.src);
                        if (thumbDiv) {{
                            thumbDiv.innerHTML = '<div class="placeholder">❌</div>';
                        }}
                    }};
                    obs.unobserve(img);
                }}
            }});
        }}, {{ threshold: 0.1 }});
        images.forEach(img => observer.observe(img));
    }});
</script>
</body>
</html>
"""

async def build_enhanced_html_async(
    results: Sequence[dict],
    query: str,
    engine: str,
    thumbs_dir: Path,
    session: requests.Session,
    workers: int,
    output_dir: Path | None = None,
    open_browser: bool = True
) -> Path:
    """Enhanced HTML builder with better error handling and output options"""
    ensure_dir(thumbs_dir)
    output_dir = output_dir or VSEARCH_DIR
    ensure_dir(output_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{engine}_{enhanced_slugify(query)}_{timestamp}_{uuid.uuid4().hex[:8]}.html"
    outfile = Path(output_dir) / filename

    def get_thumb_path(img_url: str, title: str, idx: int) -> Path:
        """Generate thumbnail path with better filename handling"""
        if not img_url:
            return thumbs_dir / f"placeholder_{idx}.svg"

        try:
            parsed = urlparse(img_url)
            ext = os.path.splitext(parsed.path)[1] or ".jpg"
            if not ext.startswith('.'):
                ext = ".jpg"

            safe_title = enhanced_slugify(title)[:50]
            return thumbs_dir / f"{safe_title}_{idx}{ext}"
        except Exception:
            return thumbs_dir / f"thumbnail_{idx}.jpg"

    async def fetch_thumbnail_async_task(idx: int, video: dict) -> tuple[int, str]:
        """Enhanced thumbnail fetch task with better error handling"""
        img_url = video.get("img_url")
        if not img_url:
            return idx, generate_placeholder_svg("📹")

        dest_path = get_thumb_path(img_url, video.get("title", "video"), idx)

        # Check if thumbnail already exists
        if dest_path.exists():
            try:
                if dest_path.stat().st_size > WOWXXX_CONFIG["thumbnail"]["min_size"]:
                    return idx, str(dest_path).replace("\\", "/")
            except Exception as e:
                logger.debug(f"Error checking existing thumbnail {dest_path}: {e}")

        # Try async download first
        if ASYNC_AVAILABLE:
            async with aiohttp_session() as async_session:
                if async_session:
                    semaphore = asyncio.Semaphore(workers)
                    success = await download_thumbnail_async(
                        async_session,
                        img_url,
                        dest_path,
                        semaphore,
                        max_retries=WOWXXX_CONFIG["thumbnail"]["retries"],
                        min_size=WOWXXX_CONFIG["thumbnail"]["min_size"],
                        max_size=WOWXXX_CONFIG["thumbnail"]["max_size"]
                    )
                    if success:
                        return idx, str(dest_path).replace("\\", "/")

        # Fall back to sync download
        success = robust_download_sync(
            session,
            img_url,
            dest_path,
            max_attempts=WOWXXX_CONFIG["thumbnail"]["retries"],
            min_size=WOWXXX_CONFIG["thumbnail"]["min_size"],
            max_size=WOWXXX_CONFIG["thumbnail"]["max_size"]
        )

        if success:
            return idx, str(dest_path).replace("\\", "/")

        # If all else fails, return placeholder
        return idx, generate_placeholder_svg("❌")

    def fetch_thumbnail_sync_task(idx: int, video: dict) -> tuple[int, str]:
        """Synchronous thumbnail fetch task"""
        img_url = video.get("img_url")
        if not img_url:
            return idx, generate_placeholder_svg("📹")

        dest_path = get_thumb_path(img_url, video.get("title", "video"), idx)

        # Check if thumbnail already exists
        if dest_path.exists():
            try:
                if dest_path.stat().st_size > WOWXXX_CONFIG["thumbnail"]["min_size"]:
                    return idx, str(dest_path).replace("\\", "/")
            except Exception as e:
                logger.debug(f"Error checking existing thumbnail {dest_path}: {e}")

        # Try sync download
        success = robust_download_sync(
            session,
            img_url,
            dest_path,
            max_attempts=WOWXXX_CONFIG["thumbnail"]["retries"],
            min_size=WOWXXX_CONFIG["thumbnail"]["min_size"],
            max_size=WOWXXX_CONFIG["thumbnail"]["max_size"]
        )

        if success:
            return idx, str(dest_path).replace("\\", "/")

        return idx, generate_placeholder_svg("❌")

    # Initialize thumbnail paths
    thumbnail_paths = [""] * len(results)

    # Use async if available and not disabled
    if ASYNC_AVAILABLE:
        try:
            tasks = [fetch_thumbnail_async_task(i, video) for i, video in enumerate(results)]
            results_with_idx = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results_with_idx:
                if isinstance(result, tuple) and len(result) == 2:
                    idx, path = result
                    thumbnail_paths[idx] = path
                else:
                    logger.debug(f"Error gathering async thumbnail result: {result}")
        except Exception as e:
            logger.error(f"Error in async thumbnail processing: {e}")
            # Fall back to synchronous processing
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, 20)) as executor:
                future_to_idx = {executor.submit(fetch_thumbnail_sync_task, i, video): i for i, video in enumerate(results)}
                progress_bar = tqdm(
                    concurrent.futures.as_completed(future_to_idx),
                    total=len(future_to_idx),
                    desc=f"{NEON['MAGENTA']}Downloading Thumbnails{NEON['RESET']}",
                    unit="files",
                    ncols=100,
                    disable=not TQDM_AVAILABLE
                )
                for future in progress_bar:
                    i = future_to_idx[future]
                    try:
                        _, path = future.result()
                        thumbnail_paths[i] = path
                    except Exception as e:
                        logger.debug(f"Error with threaded download for item {i}: {e}")
                        thumbnail_paths[i] = generate_placeholder_svg("❌")
    else:
        # Use thread pool for synchronous processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, 20)) as executor:
            future_to_idx = {executor.submit(fetch_thumbnail_sync_task, i, video): i for i, video in enumerate(results)}
            progress_bar = tqdm(
                concurrent.futures.as_completed(future_to_idx),
                total=len(future_to_idx),
                desc=f"{NEON['MAGENTA']}Downloading Thumbnails{NEON['RESET']}",
                unit="files",
                ncols=100,
                disable=not TQDM_AVAILABLE
            )
            for future in progress_bar:
                i = future_to_idx[future]
                try:
                    _, path = future.result()
                    thumbnail_paths[i] = path
                except Exception as e:
                    logger.debug(f"Error with threaded download for item {i}: {e}")
                    thumbnail_paths[i] = generate_placeholder_svg("❌")

    # Generate HTML content
    try:
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(HTML_HEAD.format(
                title=f"{html.escape(query)} - {engine}",
                query=html.escape(query),
                count=len(results),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
            ))

            for video, thumbnail in zip(results, thumbnail_paths, strict=False):
                meta_items = []

                # Add duration if available
                if video.get("time", "N/A") != "N/A":
                    meta_items.append(f'<div class="item">⏱️ {html.escape(video["time"])}</div>')

                # Add channel information if available
                if video.get("channel_name", "N/A") != "N/A":
                    channel_link = video.get("channel_link", "#")
                    if channel_link != "#":
                        meta_items.append(f'<div class="item"><a href="{html.escape(channel_link)}" target="_blank" rel="noopener noreferrer">👤 {html.escape(video["channel_name"])}</a></div>')
                    else:
                        meta_items.append(f'<div class="item">👤 {html.escape(video["channel_name"])}</div>')

                # Add views/meta information if available
                if video.get("meta", "N/A") != "N/A":
                    meta_items.append(f'<div class="item">👁️ {html.escape(video["meta"])}</div>')

                # Add video ID if available
                if video.get("video_id", "N/A") != "N/A":
                    meta_items.append(f'<div class="item">🆔 {html.escape(video["video_id"])}</div>')

                # Write video card
                f.write(f'''
                <div class="card">
                    <a href="{html.escape(video['link'])}" target="_blank" rel="noopener noreferrer">
                        <div class="thumb">
                            <img src="" data-src="{html.escape(thumbnail)}" alt="{html.escape(video['title'])}" loading="lazy">
                        </div>
                    </a>
                    <div class="body">
                        <h3 class="title">
                            <a href="{html.escape(video['link'])}" target="_blank" rel="noopener noreferrer">
                                {html.escape(video['title'])}
                            </a>
                        </h3>
                        <div class="meta">
                            {" ".join(meta_items)}
                        </div>
                    </div>
                </div>
                ''')

            f.write(HTML_TAIL.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    except Exception as e:
        logger.error(f"Failed to write HTML output: {e}")
        raise

    logger.info(f"Enhanced HTML gallery saved to: {outfile}")

    # Optionally open in browser
    if open_browser and outfile.exists():
        try:
            webbrowser.open(f"file://{os.path.abspath(outfile)}")
        except Exception as e:
            logger.warning(f"Failed to open browser: {e}")

    return outfile

def get_wowxxx_results(
    session: requests.Session,
    query: str,
    limit: int,
    page: int,
    delay_range: tuple[float, float],
    config: dict[str, Any] = WOWXXX_CONFIG,
    use_selenium: bool | None = None
) -> list[dict[str, Any]]:
    """Enhanced results fetching with better pagination and error handling"""
    base_url = config["url"]
    results: list[dict[str, Any]] = []
    last_request_time = None
    request_history = []

    # Get pagination configuration
    pagination_config = config.get("pagination", {})
    max_pages = pagination_config.get("max_pages", 5)
    items_per_page = pagination_config.get("items_per_page", 30)
    detect_end = pagination_config.get("detect_end", False)
    next_page_selector = pagination_config.get("next_page_selector", "")

    pages_to_fetch = min(max_pages, (limit + items_per_page - 1) // items_per_page)
    pages_to_fetch = max(1, pages_to_fetch)

    logger.info(
        f"Searching wow.xxx for '{query}' (up to {pages_to_fetch} pages)",
        extra={'engine': 'Wowxxx', 'query': query}
    )

    # Determine if we should use Selenium
    if use_selenium is None:
        use_selenium = config.get("requires_js", False) and SELENIUM_AVAILABLE

    driver = None
    if use_selenium and SELENIUM_AVAILABLE:
        try:
            options = ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"--user-agent={random.choice(REALISTIC_USER_AGENTS)}")
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)

            # Additional options for better stealth
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--disable-default-apps")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")

            # Set window size
            options.add_argument("--window-size=1200,800")

            # Initialize driver
            driver = webdriver.Chrome(options=options)

            # Additional stealth measures
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false
                    })
                """
            })

            logger.info("Selenium driver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium driver: {e}")
            driver = None
            use_selenium = False

    current_page = page
    has_next_page = True

    while has_next_page and len(results) < limit and current_page <= pages_to_fetch:
        smart_delay_with_jitter(delay_range, last_request_time, adaptive=True, request_history=request_history)
        last_request_time = time.time()

        search_path = config["search_path"].format(query=quote_plus(query))
        url = urljoin(base_url, search_path)

        if current_page > 1:
            page_pattern = pagination_config.get("path_pattern", "/{page}/")
            url += page_pattern.format(page=current_page)

        logger.debug(f"Fetching page {current_page}: {url}", extra={'engine': 'Wowxxx', 'query': query})

        try:
            if driver and use_selenium:
                try:
                    driver.get(url)

                    # Wait for dynamic content to load
                    wait = WebDriverWait(driver, 20)

                    # First wait for the main content
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config["video_item_selector"])))

                    # Then wait for potential lazy-loaded elements
                    time.sleep(random.uniform(1.0, 3.0))

                    # Scroll to trigger lazy loading
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(random.uniform(0.5, 1.5))

                    soup = BeautifulSoup(driver.page_source, "html.parser")
                except (TimeoutException, WebDriverException) as e:
                    logger.warning(f"Selenium extraction failed for {url}: {e}")
                    soup = BeautifulSoup("", "html.parser")
            else:
                try:
                    user_agent = random.choice(REALISTIC_USER_AGENTS)
                    session.headers.update(get_realistic_headers(user_agent))

                    # Add random delay to headers
                    session.headers["X-Request-Delay"] = str(random.uniform(0.1, 1.0))

                    response = session.get(url, timeout=getattr(session, 'timeout', DEFAULT_TIMEOUT))
                    response.raise_for_status()

                    # Check if page indicates no results
                    if "no results" in response.text.lower() or "not found" in response.text.lower():
                        logger.info("No results found for the query")
                        has_next_page = False
                        break

                    soup = BeautifulSoup(response.text, "html.parser")
                except requests.exceptions.RequestException as e:
                    logger.error(f"Request failed for page {current_page}: {e}", extra={'engine': 'Wowxxx', 'query': query})

                    # Enhanced handling for different status codes
                    if isinstance(e, requests.exceptions.HTTPError):
                        if e.response.status_code == 404:
                            logger.info(f"No more pages available after page {current_page - 1}")
                            has_next_page = False
                            break
                        if e.response.status_code == 429:
                            # Too many requests - increase delay
                            delay_range = (delay_range[0] * 1.5, delay_range[1] * 1.5)
                            logger.warning(f"Rate limited. Increasing delays to {delay_range}")
                            time.sleep(random.uniform(5, 10))
                            continue
                        if e.response.status_code == 403:
                            logger.error("Access forbidden. Check your IP or user agent.")
                            has_next_page = False
                            break
                    continue

            video_items = extract_video_items(soup, config)

            if not video_items:
                logger.warning(f"No video items found on page {current_page}", extra={'engine': 'Wowxxx', 'query': query})

                # Check if we should detect end of results
                if detect_end:
                    logger.info(f"Detected end of results at page {current_page}")
                    has_next_page = False
                    break

                # Check for next page link if selector is provided
                if next_page_selector:
                    next_page_link = soup.select_one(next_page_selector)
                    if not next_page_link:
                        logger.info(f"No next page link found at page {current_page}")
                        has_next_page = False
                        break
                continue

            # Process each video item
            for item in video_items:
                if len(results) >= limit:
                    break

                video_data = extract_video_data_enhanced(item, config, base_url)
                if video_data and validate_video_data_enhanced(video_data):
                    results.append(video_data)

            # Check for next page
            if next_page_selector:
                next_page_link = soup.select_one(next_page_selector)
                if not next_page_link:
                    logger.info(f"No next page link found at page {current_page}")
                    has_next_page = False
                    break

            current_page += 1

        except Exception as e:
            logger.error(f"Unexpected error processing page {current_page}: {e}")
            has_next_page = False

    # Clean up Selenium if used
    if driver:
        try:
            driver.quit()
        except Exception as e:
            logger.warning(f"Error quitting Selenium driver: {e}")

    logger.info(f"Successfully extracted {len(results)} videos", extra={'engine': 'Wowxxx', 'query': query})
    return results[:limit]

# --- Main Execution with Enhanced Argument Handling ---
def parse_arguments():
    """Enhanced argument parsing with better help and validation"""
    parser = argparse.ArgumentParser(
        description="wow.xxx Video Searcher based on web scraping (Enhanced Version).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Example usage:
  python3 wowxxx_search.py "teen girl"
  python3 wowxxx_search.py "milf" -l 50
  python3 wowxxx_search.py "anal" --output-format json
  python3 wowxxx_search.py "search query" --output-dir custom_folder
"""
    )

    parser.add_argument(
        "query",
        type=str,
        help="The search query for videos (enclose in quotes if it contains spaces)."
    )

    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum number of video results to return (default: {DEFAULT_LIMIT})."
    )

    parser.add_argument(
        "-p", "--page",
        type=int,
        default=DEFAULT_PAGE,
        help=f"Starting page number for the search (default: {DEFAULT_PAGE})."
    )

    parser.add_argument(
        "-o", "--output-format",
        type=str,
        default=DEFAULT_FORMAT,
        choices=["html", "json", "csv"],
        help=f"Output format for the results (default: {DEFAULT_FORMAT})."
    )

    parser.add_argument(
        "-x", "--proxy",
        type=str,
        help="Proxy to use for requests (e.g., http://user:pass@host:port)."
    )

    parser.add_argument(
        "--proxy-list",
        type=str,
        help="File containing list of proxies to rotate through (one per line)."
    )

    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of concurrent workers for thumbnail downloads (default: {DEFAULT_WORKERS})."
    )

    parser.add_argument(
        "--no-async",
        action="store_true",
        help="Disable async downloading and use a thread pool for thumbnails."
    )

    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not automatically open the HTML result in a web browser."
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging."
    )

    parser.add_argument(
        "--no-js",
        action="store_true",
        help="Force disable JavaScript rendering even if Selenium is available."
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        help="Custom output directory for results (default: wowxxx_results)."
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Custom configuration file to override default selectors."
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode - only check if the search works without saving results."
    )

    return parser.parse_args()

def load_custom_config(config_file: str) -> dict[str, Any]:
    """Load custom configuration from JSON file"""
    try:
        with open(config_file, encoding='utf-8') as f:
            custom_config = json.load(f)

        # Merge with default config
        merged_config = WOWXXX_CONFIG.copy()
        merged_config.update(custom_config)

        logger.info(f"Loaded custom configuration from {config_file}")
        return merged_config
    except Exception as e:
        logger.error(f"Failed to load custom config {config_file}: {e}")
        return WOWXXX_CONFIG

def load_proxy_list(proxy_list_file: str) -> list[str]:
    """Load list of proxies from file"""
    proxies = []
    try:
        with open(proxy_list_file, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    proxies.append(line)
        logger.info(f"Loaded {len(proxies)} proxies from {proxy_list_file}")
        return proxies
    except Exception as e:
        logger.error(f"Failed to load proxy list {proxy_list_file}: {e}")
        return []

def main():
    """Enhanced main function with better error handling and workflow"""
    args = parse_arguments()

    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)

    # Load custom config if provided
    config = WOWXXX_CONFIG
    if args.config:
        config = load_custom_config(args.config)

    # Load proxy list if provided
    proxy_list = []
    if args.proxy_list:
        proxy_list = load_proxy_list(args.proxy_list)

    # Set up signal handler for graceful exit
    def signal_handler(sig, frame):
        print(f"\n{NEON['YELLOW']}* Ctrl+C detected. Exiting gracefully...{NEON['RESET']}")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Build session with proxy rotation if list provided
        session = build_enhanced_session(
            proxy=args.proxy,
            proxy_list=proxy_list if proxy_list else None
        )

        # Determine if we should use Selenium
        use_selenium = not args.no_js and config.get("requires_js", False) and SELENIUM_AVAILABLE

        print(f"{NEON['CYAN']}{Style.BRIGHT}Starting search for '{args.query}' on wow.xxx...")

        if args.test:
            print(f"{NEON['YELLOW']}Running in test mode - checking search functionality only{NEON['RESET']}")
            test_results = get_wowxxx_results(
                session=session,
                query=args.query,
                limit=5,  # Just check first few results
                page=args.page,
                delay_range=DEFAULT_DELAY,
                config=config,
                use_selenium=use_selenium
            )

            if test_results:
                print(f"{NEON['GREEN']}Test successful! Found {len(test_results)} videos.{NEON['RESET']}")
                print(f"{NEON['CYAN']}First result: {test_results[0]['title']}{NEON['RESET']}")
            else:
                print(f"{NEON['RED']}Test failed. No videos found for '{args.query}'.{NEON['RESET']}")
                print(f"{NEON['YELLOW']}Try refining your query or checking network.{NEON['RESET']}")
            return

        # Perform the actual search
        results = get_wowxxx_results(
            session=session,
            query=args.query,
            limit=args.limit,
            page=args.page,
            delay_range=DEFAULT_DELAY,
            config=config,
            use_selenium=use_selenium
        )

        if not results:
            print(f"{NEON['RED']}No videos found for '{args.query}'.{NEON['RESET']}")
            print(f"{NEON['YELLOW']}Try refining your query or checking network.{NEON['RESET']}")
            sys.exit(1)

        print(f"{NEON['GREEN']}Found {len(results)} videos.{NEON['RESET']}")

        # Handle different output formats
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug_query = enhanced_slugify(args.query)

        output_dir = Path(args.output_dir) if args.output_dir else VSEARCH_DIR
        ensure_dir(output_dir)

        if args.output_format == "json":
            filename = f"wowxxx_{slug_query}_{timestamp}.json"
            outfile = Path(output_dir) / filename
            try:
                with open(outfile, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=4)
                print(f"{NEON['CYAN']}JSON results saved to: {outfile}{NEON['RESET']}")
            except Exception as e:
                print(f"{NEON['RED']}Failed to save JSON results: {e}{NEON['RESET']}")
                sys.exit(1)

        elif args.output_format == "csv":
            filename = f"wowxxx_{slug_query}_{timestamp}.csv"
            outfile = Path(output_dir) / filename
            try:
                if results:
                    fieldnames = results[0].keys()
                    with open(outfile, "w", encoding="utf-8", newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(results)
                print(f"{NEON['CYAN']}CSV results saved to: {outfile}{NEON['RESET']}")
            except Exception as e:
                print(f"{NEON['RED']}Failed to save CSV results: {e}{NEON['RESET']}")
                sys.exit(1)

        else:  # HTML output
            try:
                if ASYNC_AVAILABLE and not args.no_async:
                    loop = asyncio.get_event_loop()
                    outfile = loop.run_until_complete(
                        build_enhanced_html_async(
                            results=results,
                            query=args.query,
                            engine='wowxxx',
                            thumbs_dir=Path(THUMBNAILS_DIR),
                            session=session,
                            workers=args.workers,
                            output_dir=output_dir,
                            open_browser=not args.no_open
                        )
                    )
                else:
                    async def sync_wrapper():
                        return await build_enhanced_html_async(
                            results=results,
                            query=args.query,
                            engine='wowxxx',
                            thumbs_dir=Path(THUMBNAILS_DIR),
                            session=session,
                            workers=args.workers,
                            output_dir=output_dir,
                            open_browser=not args.no_open
                        )

                    outfile = asyncio.run(sync_wrapper())

                if not outfile or not outfile.exists():
                    print(f"{NEON['RED']}Failed to generate HTML output{NEON['RESET']}")
                    sys.exit(1)

            except Exception as e:
                print(f"{NEON['RED']}Failed to generate HTML output: {e}{NEON['RESET']}")
                sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n{NEON['YELLOW']}Operation cancelled by user.{NEON['RESET']}")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"An unhandled error occurred: {e}", exc_info=True)
        print(f"{NEON['RED']}An error occurred: {e}{NEON['RESET']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
