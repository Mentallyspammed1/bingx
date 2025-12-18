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
    # Provide a dummy tqdm if not available to avoid crashing
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
    f"%(message)s{NEON['RESET']}" # Query context added via logger.info(..., extra={'query': query})
)

class ContextFilter(logging.Filter):
    """Adds engine and query context to log records."""
    def filter(self, record):
        record.engine = getattr(record, 'engine', 'Wowxxx')
        record.query = getattr(record, 'query', '') # Default to empty string if not set
        return True

# Configure logging with stream and file handlers
log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    from logging.handlers import RotatingFileHandler
    log_file_path = Path("wowxxx_search.log")
    file_handler = RotatingFileHandler(
        log_file_path,
        maxBytes=5*1024*1024, # 5 MB
        backupCount=3,
        encoding="utf-8"
    )
    log_handlers.append(file_handler)
except (ImportError, PermissionError) as e:
    logging.getLogger(__name__).warning(f"Could not set up file logging: {e}")

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FMT,
    handlers=log_handlers
)
logger = logging.getLogger(__name__)
logger.addFilter(ContextFilter())

# Reduce verbosity of noisy libraries
for noisy in ("urllib3", "chardet", "requests", "aiohttp", "selenium"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# --- Constants and Configuration ---
THUMBNAILS_DIR = Path("downloaded_thumbnails")
VSEARCH_DIR = Path("wowxxx_results")
DEFAULT_ENGINE = "wowxxx"
DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_FORMAT = "html"
DEFAULT_TIMEOUT = 30 # Default timeout for requests
DEFAULT_DELAY = (1.5, 4.0) # Default delay range between requests
DEFAULT_MAX_RETRIES = 5 # Default max retries for requests
DEFAULT_WORKERS = 12 # Default concurrent workers for downloads

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
    """Generate realistic headers mimicking a browser, with variations."""
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
        "DNT": "1", # Do Not Track
        "Sec-GPC": "1", # Privacy related header
        "Referer": "https://www.google.com/", # Common referrer
        # Add common Sec-CH-UA headers (adjust based on common Chrome versions)
        "Sec-Ch-Ua": '"Not/A)Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
        "Sec-Ch-Ua-Mobile": "?0", # Assume desktop unless specified
        "Sec-Ch-Ua-Platform": '"Windows"', # Example platform, can be randomized if needed
    }
    return headers

# Default configuration for wow.xxx scraping
WOWXXX_CONFIG: dict[str, Any] = {
    "url": "https://www.wow.xxx",
    "search_path": "/popular/search/{query}/top-rated/", # Path pattern for search queries
    "page_param": None, # Parameter for page number if needed (e.g., ?page=N)
    "requires_js": True, # Whether the site requires JavaScript rendering
    # CSS selectors for different video elements
    "video_item_selector": "article.video-card, div.video-item, li.video-list-item",
    "link_selector": "a.video-card__link, a.video-item__link, a[href*='/video/']",
    "title_selector": "h3.video-card__title, h2.video-title, span.title-text",
    "title_attribute": "title", # Attribute to get title from if element text is insufficient
    "img_selector": "img.video-card__thumbnail, img.video-thumbnail, img[data-src], img[src]",
    "time_selector": "span.video-card__duration, span.duration, div.time", # Duration/time on video card
    "meta_selector": "span.video-card__views, span.views, div.meta-info", # Views or other metadata
    "channel_name_selector": "a.video-card__channel-name, span.channel-name, a[href*='/channel/']",
    "channel_link_selector": "a.video-card__channel-link, a.channel-link", # Link to the channel page
    # Fallback selectors if primary ones fail
    "fallback_selectors": {
        "title": ["a[title]", "h2", "div.title", "span.title", "div.video-title"],
        "img": ["img[data-src]", "img[src]", "video-preview", "img.lazy", "img.thumbnail"],
        "link": ["a[href*='/video/']", "a[href*='/viewkey=']", "a.item-link", "a.video-link"]
    },
    # Pagination configuration
    "pagination": {
        "enabled": True,
        "max_pages": 5, # Maximum pages to scrape per search
        "items_per_page": 30, # Assumed items per page for limit calculation
        "path_pattern": "/{page}/", # URL path pattern for subsequent pages
        "detect_end": True, # Try to detect end of results if no next page link
        "next_page_selector": "a.next-page, a[rel='next']" # Selector for the 'next page' link
    },
    # Thumbnail download configuration
    "thumbnail": {
        "min_size": 5000,  # Minimum acceptable thumbnail size in bytes
        "max_size": 5 * 1024 * 1024,  # Maximum thumbnail size (5 MB)
        "timeout": 20, # Timeout for individual thumbnail downloads
        "retries": 3 # Number of retries for failed thumbnail downloads
    }
}

# --- Enhanced Utility Functions ---
def ensure_dir(path: Path) -> None:
    """Ensure a directory exists, creating it if necessary with error handling."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        # Verify directory was actually created and is accessible
        if not path.is_dir():
            raise OSError(f"Path exists but is not a directory: {path}")
        # Test write access
        test_file = path / f".write_test_{uuid.uuid4().hex[:8]}"
        with open(test_file, "w") as f:
            f.write("test")
        test_file.unlink() # Clean up test file
    except (PermissionError, OSError) as e:
        logger.error(f"Failed to create or access directory {path}: {e}", exc_info=True)
        # Re-raise to signal failure to the caller
        raise

def enhanced_slugify(text: str) -> str:
    """Improved slugify function for creating safe filenames.
    Handles Unicode, removes invalid characters, trims whitespace,
    and avoids reserved names.
    """
    if not text or not isinstance(text, str):
        return "untitled"

    # Normalize Unicode characters (e.g., accented chars to base chars)
    text = unicodedata.normalize("NFKD", text)
    # Encode to ASCII ignoring errors, effectively removing non-ASCII chars
    text = text.encode("ascii", "ignore").decode("ascii")
    # Remove characters invalid for filenames across OSes
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    # Replace sequences of whitespace/hyphens/dots with a single underscore
    text = re.sub(r"[_\-.\s]+", "_", text.strip(), flags=re.UNICODE)
    # Remove leading/trailing underscores/dots/hyphens
    text = text.strip("._-")

    # Ensure minimum length and handle empty strings after cleaning
    if not text or len(text) < 3:
        text = "untitled"

    # Handle reserved names in Windows (case-insensitive)
    reserved_names = {"con", "prn", "aux", "nul", "com1", "com2", "com3", "com4", "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"}
    if text.lower() in reserved_names:
        text = f"file_{text}"

    # Truncate to a reasonable length to avoid excessively long filenames
    return text[:100]

def build_enhanced_session(
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    proxy: str | None = None,
    proxy_list: list[str] | None = None
) -> requests.Session:
    """Builds a requests.Session object with enhanced configurations:
    - Robust retry strategy (status codes, backoff).
    - Realistic User-Agent rotation.
    - Proxy support (single proxy or rotation from a list).
    - Configurable timeout.
    """
    session = requests.Session()

    # Enhanced retry strategy for robustness against transient network issues
    retries = Retry(
        total=max_retries,
        backoff_factor=2.0, # Exponential backoff
        backoff_jitter=0.5, # Add jitter to backoff times
        # Consider more server errors as retryable
        status_forcelist=(408, 429, 500, 502, 503, 504, 520, 521, 522, 524, 530),
        allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}), # Only retry idempotent methods
        respect_retry_after_header=True, # Respect server's Retry-After header
        raise_on_redirect=False, # Don't raise on redirects, handle them manually if needed
        raise_on_status=False # Don't raise on non-2xx status, allow response handling
    )

    # Mount the adapter to both http and https protocols
    adapter = HTTPAdapter(
        max_retries=retries,
        pool_connections=20, # Increase pool size for potentially many downloads
        pool_maxsize=50,
        pool_block=False # Non-blocking pool
    )

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set a realistic User-Agent and store list for potential rotation
    user_agent = random.choice(REALISTIC_USER_AGENTS)
    session.headers.update(get_realistic_headers(user_agent))
    session.user_agent_list = REALISTIC_USER_AGENTS # Store list for potential rotation per request if needed

    # --- Proxy Handling ---
    if proxy:
        try:
            parsed_proxy = urlparse(proxy)
            if parsed_proxy.scheme and parsed_proxy.netloc:
                session.proxies.update({"http": proxy, "https": proxy})
                logger.info(f"Using proxy: {parsed_proxy.netloc}")
            else:
                logger.warning(f"Invalid proxy format provided: {proxy}. Skipping.")
        except Exception as e:
            logger.warning(f"Failed to parse or set proxy '{proxy}': {e}")

    # --- Proxy Rotation ---
    if proxy_list:
        session.proxies = {} # Clear single proxy if list is provided
        session.proxy_list = [p for p in proxy_list if p and urlparse(p).scheme in ['http', 'https'] and urlparse(p).netloc] # Filter invalid proxies
        session.current_proxy_index = 0

        if not session.proxy_list:
            logger.warning("Proxy list provided, but it's empty or contains only invalid proxies. Proceeding without proxy rotation.")
        else:
            logger.info(f"Configured for proxy rotation with {len(session.proxy_list)} valid proxies.")

            def rotate_proxy_on_failure(response, *args, **kwargs):
                """Callback function to rotate proxy upon receiving an error status code."""
                # Rotate on client/server errors (4xx or 5xx)
                if response.status_code >= 400:
                    current_index = session.current_proxy_index
                    next_index = (current_index + 1) % len(session.proxy_list)
                    proxy_to_try = session.proxy_list[next_index]
                    try:
                        parsed_proxy = urlparse(proxy_to_try)
                        session.proxies.update({"http": proxy_to_try, "https": proxy_to_try})
                        logger.debug(f"Proxy rotation triggered. Switched to proxy: {parsed_proxy.netloc}")
                        session.current_proxy_index = next_index
                    except Exception as e:
                        logger.warning(f"Failed to rotate to proxy '{proxy_to_try}': {e}")

            # Register the callback hook
            session.hooks['response'].append(rotate_proxy_on_failure)

    session.timeout = timeout # Set the default timeout for all requests
    return session

def smart_delay_with_jitter(
    delay_range: tuple[float, float],
    last_request_time: float | None = None,
    jitter: float = 0.3,
    adaptive: bool = True,
    request_history: list[float] | None = None,
    target_engine: str = "Unknown",
    query: str = ""
) -> None:
    """Implements a delay with jitter, potentially adapting based on request history.
    Designed to mimic human browsing behavior and avoid detection.

    Args:
        delay_range: Tuple (min_delay, max_delay) in seconds.
        last_request_time: Timestamp of the last request.
        jitter: Factor for randomizing the delay (0.0 to 1.0).
        adaptive: If True, adjusts delay based on recent request intervals.
        request_history: List of timestamps of recent requests.
        target_engine: Name of the target service for logging context.
        query: The search query for logging context.
    """
    min_delay, max_delay = delay_range
    current_time = time.time()

    # Initialize request history if not provided or if it's empty
    if request_history is None:
        request_history = []

    # Calculate average interval between requests if history is available
    if len(request_history) >= 2:
        # Average interval over the last few requests
        avg_interval = (current_time - request_history[0]) / (len(request_history) -1)
    else:
        # Default average if history is too short
        avg_interval = (min_delay + max_delay) / 2

    # Ensure request_history list doesn't grow indefinitely
    if len(request_history) > 10:
        request_history.pop(0)

    # Add current time to history for the next call
    request_history.append(current_time)

    # Calculate base delay
    if adaptive and len(request_history) >= 2:
        # If requests are happening faster than min_delay, increase base wait time
        if avg_interval < min_delay:
            # Scale factor to push interval closer to min_delay
            scale_factor = min_delay / max(0.1, avg_interval)
            base_wait = random.uniform(min_delay, max_delay) * scale_factor
            logger.debug(f"Adaptive delay: avg_interval ({avg_interval:.2f}s) < min_delay ({min_delay:.2f}s). Scaling wait.", extra={'engine': target_engine, 'query': query})
        else:
            # Normal delay if intervals are reasonable
            base_wait = random.uniform(min_delay, max_delay)
    else:
        # Non-adaptive or insufficient history: use random delay within range
        base_wait = random.uniform(min_delay, max_delay)

    # Apply jitter: Gaussian jitter tends to feel more natural than uniform
    jitter_amount = base_wait * jitter * random.gauss(0, 1) # Use gauss for bell curve jitter
    calculated_delay = max(0.5, base_wait + jitter_amount) # Ensure minimum delay of 0.5s

    if last_request_time:
        time_since_last = current_time - last_request_time
        if time_since_last < calculated_delay:
            sleep_time = calculated_delay - time_since_last
            logger.debug(f"Waiting {sleep_time:.2f}s (total delay {calculated_delay:.2f}s)", extra={'engine': target_engine, 'query': query})
            time.sleep(sleep_time)
        # else: Request was already slower than needed, no extra sleep required.
    else:
        # Initial delay before the first request
        logger.debug(f"Initial wait {calculated_delay:.2f}s", extra={'engine': target_engine, 'query': query})
        time.sleep(calculated_delay)

@asynccontextmanager
async def aiohttp_session_context(
    timeout: int = 30,
    proxy: str | None = None,
    proxy_auth: tuple[str, str] | None = None
) -> AsyncGenerator[aiohttp.ClientSession | None, None]:
    """Provides an enhanced aiohttp.ClientSession using a context manager.
    Includes realistic headers, proxy support, and configurable timeouts.
    Yields the session or None if creation fails or aiohttp is unavailable.
    """
    if not ASYNC_AVAILABLE:
        logger.debug("aiohttp is not installed. Cannot create async session.")
        yield None
        return

    session = None
    try:
        # Configure timeout object for aiohttp
        timeout_obj = aiohttp.ClientTimeout(total=timeout, connect=10) # 10s connect timeout

        # Generate realistic headers
        headers = get_realistic_headers(random.choice(REALISTIC_USER_AGENTS))

        # Configure connector with limits and proxy settings
        connector_kwargs = {
            'limit': 50, # Total connection limit
            'limit_per_host': 10, # Limit per host
            'ssl': False, # Disable SSL verification if needed, but generally keep True
            'enable_cleanup_closed': True # Cleanup closed connections
        }
        if proxy:
            proxy_url = proxy
            # Basic Auth for proxy is handled via the proxy URL format itself or explicitly if needed
            connector_kwargs['proxy'] = proxy_url
            # If proxy_auth is a tuple like ('user', 'pass'), it should be embedded in the proxy URL string

        connector = aiohttp.TCPConnector(**connector_kwargs)

        session = aiohttp.ClientSession(
            timeout=timeout_obj,
            headers=headers,
            connector=connector,
            trust_env=True # Respect environment variables like HTTP_PROXY
        )
        yield session
    except Exception as e:
        logger.error(f"Failed to create aiohttp session: {e}", exc_info=True)
        yield None # Yield None on failure
    finally:
        # Ensure the session is closed if it was successfully created
        if session and not session.closed:
            try:
                await session.close()
            except Exception as e:
                logger.warning(f"Error closing aiohttp session: {e}")

async def download_thumbnail_async(
    session: aiohttp.ClientSession,
    url: str,
    path: Path,
    semaphore: asyncio.Semaphore,
    max_retries: int = WOWXXX_CONFIG["thumbnail"]["retries"],
    min_size: int = WOWXXX_CONFIG["thumbnail"]["min_size"],
    max_size: int = WOWXXX_CONFIG["thumbnail"]["max_size"],
    thumb_timeout: int = WOWXXX_CONFIG["thumbnail"]["timeout"],
    engine: str = "Wowxxx",
    query: str = ""
) -> bool:
    """Downloads a thumbnail asynchronously using aiohttp, with retries, size validation,
    and atomic saving using temporary files. Returns True on success, False otherwise.
    """
    if not ASYNC_AVAILABLE or not session:
        logger.debug("aiohttp session unavailable or not provided.")
        return False

    # Basic URL validation
    try:
        parsed_url = urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            logger.debug(f"Invalid thumbnail URL format: {url}")
            return False
    except Exception as e:
        logger.debug(f"URL parsing failed for thumbnail '{url}': {e}")
        return False

    # Define temporary file path for atomic write
    temp_path = path.with_suffix(path.suffix + ".tmp")

    for attempt in range(max_retries):
        try:
            # Acquire semaphore before making the request
            async with semaphore:
                logger.debug(f"Attempting async download: {url} (Attempt {attempt + 1}/{max_retries})", extra={'engine': engine, 'query': query})
                # Use a specific timeout for the thumbnail download request
                async with session.get(url, timeout=thumb_timeout) as response:
                    # Check status code first
                    if response.status != 200:
                        logger.debug(f"Thumbnail download failed: HTTP {response.status} for {url}", extra={'engine': engine, 'query': query})
                        # Don't retry on codes like 404, 403 etc., unless they are transient (e.g., 5xx)
                        if response.status >= 500 and attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt) # Exponential backoff
                        continue # Try next attempt or next proxy/request

                    # Check content type to ensure it's an image
                    content_type = response.headers.get("content-type", "").lower()
                    if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                        logger.debug(f"Thumbnail download failed: Invalid content type '{content_type}' for {url}", extra={'engine': engine, 'query': query})
                        continue # Skip this URL

                    # Read content (use read() for smaller files, might need streaming for very large ones)
                    content = await response.read()
                    content_length = len(content)

                    # Validate content size
                    if content_length == 0:
                        logger.debug(f"Thumbnail download failed: Received empty content for {url}", extra={'engine': engine, 'query': query})
                        continue
                    if content_length < min_size:
                        logger.debug(f"Thumbnail download failed: Content too small ({content_length} bytes) for {url}", extra={'engine': engine, 'query': query})
                        continue
                    if content_length > max_size:
                        logger.debug(f"Thumbnail download failed: Content too large ({content_length} bytes) for {url}", extra={'engine': engine, 'query': query})
                        continue

                    # Write to temp file and then rename for atomicity
                    try:
                        with open(temp_path, "wb") as f:
                            f.write(content)

                        # Verify file integrity (size matches) before renaming
                        if temp_path.stat().st_size == content_length:
                            temp_path.rename(path) # Atomic rename
                            logger.debug(f"Thumbnail downloaded successfully: {path.name}")
                            return True
                        temp_path.unlink(missing_ok=True) # Clean up corrupted temp file
                        logger.debug(f"Thumbnail download failed: Size mismatch after writing {path.name}", extra={'engine': engine, 'query': query})
                    except OSError as e:
                        logger.debug(f"Failed to write thumbnail to {temp_path}: {e}", extra={'engine': engine, 'query': query})
                        temp_path.unlink(missing_ok=True) # Ensure temp file is removed on error
                        if attempt < max_retries - 1: await asyncio.sleep(2 ** attempt) # Backoff

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.debug(f"Network error during async download for {url} (Attempt {attempt + 1}): {e}", extra={'engine': engine, 'query': query})
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt) # Exponential backoff
        except Exception as e:
            logger.error(f"Unexpected error during async thumbnail download for {url} (Attempt {attempt + 1}): {e}", exc_info=True, extra={'engine': engine, 'query': query})
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt) # Backoff

    # If all retries failed, clean up potential temporary file and return False
    temp_path.unlink(missing_ok=True)
    logger.debug(f"All retries failed for thumbnail download: {url}", extra={'engine': engine, 'query': query})
    return False

def robust_download_sync(
    session: requests.Session,
    url: str,
    path: Path,
    max_attempts: int = WOWXXX_CONFIG["thumbnail"]["retries"],
    min_size: int = WOWXXX_CONFIG["thumbnail"]["min_size"],
    max_size: int = WOWXXX_CONFIG["thumbnail"]["max_size"],
    thumb_timeout: int = WOWXXX_CONFIG["thumbnail"]["timeout"],
    engine: str = "Wowxxx",
    query: str = ""
) -> bool:
    """Downloads a file synchronously using requests session, with retries,
    size validation, and atomic saving. Returns True on success, False otherwise.
    """
    if not url or not urlparse(url).scheme:
        logger.debug(f"Invalid URL for sync download: {url}")
        return False

    # Define temporary file path
    temp_path = path.with_suffix(path.suffix + ".tmp")

    for attempt in range(max_attempts):
        try:
            # Update headers for each attempt to rotate User-Agent if needed
            session.headers.update(get_realistic_headers(random.choice(session.user_agent_list)))

            logger.debug(f"Attempting sync download: {url} (Attempt {attempt + 1}/{max_attempts})", extra={'engine': engine, 'query': query})
            with session.get(url, stream=True, timeout=thumb_timeout) as response:
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                # Check content type
                content_type = response.headers.get("content-type", "").lower()
                if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                    logger.debug(f"Sync download failed: Invalid content type '{content_type}' for {url}", extra={'engine': engine, 'query': query})
                    continue # Try next attempt

                # Check content length from headers if available
                content_length_str = response.headers.get("content-length")
                content_length = 0
                if content_length_str:
                    try:
                        content_length = int(content_length_str)
                        if content_length > max_size:
                            logger.debug(f"Sync download failed: Content too large ({content_length} bytes) for {url}", extra={'engine': engine, 'query': query})
                            continue # Skip if content length indicates it's too large
                    except ValueError:
                        logger.debug(f"Could not parse content-length header: {content_length_str}")

                bytes_written = 0
                try:
                    with open(temp_path, "wb") as fh:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk: # filter out keep-alive chunks
                                fh.write(chunk)
                                bytes_written += len(chunk)
                                # If content_length was known, check progress against max_size
                                if content_length > 0 and bytes_written > max_size:
                                    logger.debug(f"Sync download failed: Exceeded max size ({max_size} bytes) while downloading {url}", extra={'engine': engine, 'query': query})
                                    break # Stop downloading if max size exceeded

                    # Check if download was successful based on size validation
                    if content_length > 0 and bytes_written != content_length:
                         # If header provided length and it doesn't match bytes written
                        logger.debug(f"Sync download failed: Size mismatch ({bytes_written}/{content_length} bytes) for {url}", extra={'engine': engine, 'query': query})
                        temp_path.unlink(missing_ok=True)
                        continue

                    if bytes_written < min_size:
                        logger.debug(f"Sync download failed: Content too small ({bytes_written} bytes) for {url}", extra={'engine': engine, 'query': query})
                        temp_path.unlink(missing_ok=True)
                        continue

                    # Atomic rename upon successful download and validation
                    temp_path.rename(path)
                    logger.debug(f"Thumbnail downloaded successfully: {path.name}")
                    return True

                except OSError as e:
                    logger.debug(f"Failed to write thumbnail to {temp_path}: {e}", extra={'engine': engine, 'query': query})
                    temp_path.unlink(missing_ok=True) # Ensure temp file is removed on error
                    if attempt < max_attempts - 1:
                        time.sleep(2 ** attempt) # Exponential backoff

        except requests.exceptions.RequestException as e:
            logger.debug(f"Network error during sync download for {url} (Attempt {attempt + 1}): {e}", extra={'engine': engine, 'query': query})
            if attempt < max_attempts - 1:
                # Apply backoff for network errors
                time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Unexpected error during sync thumbnail download for {url} (Attempt {attempt + 1}): {e}", exc_info=True, extra={'engine': engine, 'query': query})
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt) # Backoff

    # Cleanup failed download attempt
    temp_path.unlink(missing_ok=True)
    logger.debug(f"All retries failed for sync thumbnail download: {url}", extra={'engine': engine, 'query': query})
    return False

def extract_video_items(soup: BeautifulSoup, cfg: dict) -> list:
    """Extracts potential video item elements from the parsed HTML soup
    using primary and fallback CSS selectors.
    """
    video_items = []
    primary_selectors = [s.strip() for s in cfg.get("video_item_selector", "").split(',') if s.strip()]

    # Try primary selectors first
    for selector in primary_selectors:
        try:
            items = soup.select(selector)
            if items:
                video_items.extend(items)
                logger.debug(f"Found {len(items)} video items using selector: '{selector}'")
                break # Stop once items are found using the first successful selector
        except Exception as e:
            logger.debug(f"Error using selector '{selector}': {e}")

    # If primary selectors yielded no results, try fallback selectors
    if not video_items:
        logger.debug("No video items found with primary selectors, trying fallbacks...")
        fallback_selectors = [
            "div.video-item", "li.video-list-item", "article.video",
            "div.video-card", "div.video-thumbnail"
        ]
        for selector in fallback_selectors:
            try:
                items = soup.select(selector)
                if items:
                    video_items.extend(items)
                    logger.debug(f"Found {len(items)} video items using fallback selector: '{selector}'")
                    break # Use the first successful fallback selector
            except Exception as e:
                logger.debug(f"Error using fallback selector '{selector}': {e}")

    if not video_items:
        logger.warning("Could not find any video items using primary or fallback selectors.")
        # Optionally log a snippet of the HTML for debugging
        # logger.debug(f"HTML snippet:\n{soup.prettify()[:1000]}")

    return video_items

def extract_text_safe(element, selector: str, default: str = "N/A") -> str:
    """Safely extracts text content from an element using a CSS selector.
    Tries multiple selectors and falls back to attributes if needed.
    Returns 'default' value if no text is found or an error occurs.
    """
    if not selector or not element:
        return default

    selectors_to_try = [s.strip() for s in selector.split(',') if s.strip()]

    # First, try extracting text content from the element itself
    for sel in selectors_to_try:
        try:
            found_elements = element.select(sel)
            if found_elements:
                for el in found_elements:
                    text = el.get_text(strip=True)
                    # Return the first non-empty, non-"N/A" text found
                    if text and text.lower() != "n/a":
                        return text
        except Exception as e:
            logger.debug(f"Error selecting text with '{sel}': {e}")
            continue # Try next selector

    # If text content failed, try extracting from common attributes (title, alt, etc.)
    for sel in selectors_to_try:
        try:
            found_elements = element.select(sel)
            if found_elements:
                for el in found_elements:
                    # Check common attributes that might hold the desired text
                    for attr in ["title", "alt", "aria-label", "data-title"]:
                        if el.has_attr(attr):
                            text = el.get(attr, "").strip()
                            if text and text.lower() != "n/a":
                                return text
        except Exception as e:
            logger.debug(f"Error selecting attribute with '{sel}': {e}")
            continue # Try next selector

    # Return default value if nothing was found
    return default

def extract_video_data_enhanced(item, cfg: dict, base_url: str) -> dict | None:
    """Extracts detailed information for a single video item based on configuration.
    Includes robust handling for missing data and uses fallback mechanisms.
    """
    video_info = {}
    try:
        # --- Extract Title ---
        title = "Untitled"
        title_selectors = [s.strip() for s in cfg.get("title_selector", "").split(',') if s.strip()]
        # Add fallback selectors if defined
        if "fallback_selectors" in cfg and "title" in cfg["fallback_selectors"]:
            title_selectors.extend([s.strip() for s in cfg["fallback_selectors"]["title"] if s.strip()])

        for selector in title_selectors:
            title_el = item.select_one(selector)
            if title_el:
                title_attr = cfg.get("title_attribute")
                # Prefer attribute if specified and exists
                if title_attr and title_el.has_attr(title_attr):
                    title = title_el.get(title_attr, "").strip()
                else: # Otherwise, get text content
                    title = title_el.get_text(strip=True)

                # Clean title: remove extra whitespace and check if valid
                title = ' '.join(title.split())
                if title and title.lower() not in ["untitled", "n/a", "error", ""]:
                    break # Found a valid title

        video_info["title"] = html.escape(title[:200]) # Escape and limit length

        # --- Extract Link ---
        link = "#"
        link_selectors = [s.strip() for s in cfg.get("link_selector", "").split(',') if s.strip()]
        if "fallback_selectors" in cfg and "link" in cfg["fallback_selectors"]:
            link_selectors.extend([s.strip() for s in cfg["fallback_selectors"]["link"] if s.strip()])

        for selector in link_selectors:
            link_el = item.select_one(selector)
            if link_el and link_el.has_attr("href"):
                href = link_el["href"].strip()
                # Basic cleaning of URL: remove fragments and query params
                if href and href != "#":
                    cleaned_href = urlparse(href)._replace(query="", fragment="").geturl()
                    link = urljoin(base_url, cleaned_href) # Ensure absolute URL
                    break # Found a valid link

        video_info["link"] = link

        # --- Extract Image URL ---
        img_url = None
        img_selectors = [s.strip() for s in cfg.get("img_selector", "").split(',') if s.strip()]
        if "fallback_selectors" in cfg and "img" in cfg["fallback_selectors"]:
            img_selectors.extend([s.strip() for s in cfg["fallback_selectors"]["img"] if s.strip()])

        for selector in img_selectors:
            img_el = item.select_one(selector)
            if img_el:
                # Check various attributes for image source (src, data-src, etc.)
                for attr in ["data-src", "src", "data-lazy", "data-original", "data-thumb", "data-srcset"]:
                    if img_el.has_attr(attr):
                        img_val = img_el.get(attr, "").strip()
                        if img_val and not img_val.startswith("data:"): # Ignore data URIs for now
                            # Handle srcset for responsive images
                            if attr == "data-srcset":
                                sources = img_val.split(',')
                                if sources:
                                    # Take the first URL (usually the smallest size)
                                    first_source = sources[0].strip().split(' ')[0]
                                    img_url = urljoin(base_url, first_source)
                            else:
                                img_url = urljoin(base_url, img_val) # Ensure absolute URL

                            if img_url: # Found a valid image URL
                                break
                if img_url: # Stop searching selectors once an image is found
                    break

        video_info["img_url"] = img_url

        # --- Extract Duration ---
        duration = extract_text_safe(item, cfg.get("time_selector", ""), "N/A")
        # Add secondary selectors if primary fails
        if duration == "N/A":
            duration = extract_text_safe(item, "span.duration, div.duration, time", "N/A")
        video_info["time"] = duration

        # --- Extract Views/Meta ---
        views = extract_text_safe(item, cfg.get("meta_selector", ""), "N/A")
        if views == "N/A":
            views = extract_text_safe(item, "span.views, div.views, span.meta-info", "N/A")
        video_info["meta"] = views

        # --- Extract Channel Info ---
        channel_name = extract_text_safe(item, cfg.get("channel_name_selector", ""), "N/A")
        video_info["channel_name"] = channel_name

        channel_link = "#"
        channel_link_selector = cfg.get("channel_link_selector")
        if channel_link_selector:
            channel_link_el = item.select_one(channel_link_selector)
            if channel_link_el and channel_link_el.has_attr("href"):
                href = channel_link_el["href"].strip()
                if href and href != "#":
                    cleaned_href = urlparse(href)._replace(query="", fragment="").geturl()
                    channel_link = urljoin(base_url, cleaned_href)
        video_info["channel_link"] = channel_link

        # --- Extract Video ID (if possible from URL structure) ---
        video_id = "N/A"
        if link != "#":
            parsed_link = urlparse(link)
            path_parts = [part for part in parsed_link.path.split('/') if part]
            if path_parts:
                # Assume last part of path is video ID, adjust if site structure differs
                video_id = path_parts[-1]
                # Simple validation: alphanumeric, underscore, hyphen
                if not re.match(r'^[a-zA-Z0-9_-]+$', video_id):
                    video_id = "N/A" # Reset if format is unexpected
        video_info["video_id"] = video_id

        # --- Extract other data attributes ---
        additional_meta = {}
        for attr in ["data-id", "data-video-id", "data-duration", "data-views", "data-title"]:
            if item.has_attr(attr):
                additional_meta[attr] = item[attr]
        video_info["additional_meta"] = additional_meta

        # --- Add metadata ---
        video_info["extracted_at"] = datetime.now().isoformat()
        video_info["source_engine"] = cfg.get("url", base_url) # Store base URL as source

        return video_info

    except Exception as e:
        # Log error during extraction of a single item
        logger.warning(f"Failed to extract data for an item: {e}", exc_info=True)
        # Return partially extracted data or None if critical fields are missing
        if "title" not in video_info or video_info.get("title") in ["Untitled", "N/A", ""] or \
           "link" not in video_info or video_info.get("link") == "#":
            return None # Indicate failure if essential fields are missing
        return video_info # Return partial data if some fields failed but core info exists

def validate_video_data_enhanced(data: dict, item_index: int = -1) -> bool:
    """Performs enhanced validation on the extracted video data dictionary.
    Returns True if the data is considered valid, False otherwise.
    Logs reasons for validation failure.
    """
    if not isinstance(data, dict):
        logger.debug(f"Item {item_index}: Validation failed - Data is not a dictionary.")
        return False

    # Check required fields and basic validity
    required_fields = ["title", "link"]
    for field in required_fields:
        value = data.get(field)
        if not value or value in ["Untitled", "#", "N/A", ""]:
            logger.debug(f"Item {item_index}: Validation failed - Missing or invalid required field: '{field}'. Value: '{value}'")
            return False

    # Validate the link format
    try:
        parsed_link = urlparse(data["link"])
        if not parsed_link.scheme or not parsed_link.netloc:
            logger.debug(f"Item {item_index}: Validation failed - Invalid link URL format: {data['link']}")
            return False
    except Exception as e:
        logger.debug(f"Item {item_index}: Validation failed - Error parsing link URL '{data['link']}': {e}")
        return False

    # Validate title length and content
    title = data.get("title", "")
    if len(title) < 3 or title.lower() in ["untitled", "n/a", "error", ""]:
        logger.debug(f"Item {item_index}: Validation failed - Invalid title: '{title}'")
        return False

    # Validate video ID format if present
    video_id = data.get("video_id", "N/A")
    if video_id != "N/A":
        # Basic check: must be alphanumeric with optional underscores/hyphens, length > 2
        if len(video_id) < 3 or not re.match(r'^[a-zA-Z0-9_-]+$', video_id):
            logger.debug(f"Item {item_index}: Validation failed - Invalid video ID format: '{video_id}'")
            return False

    # If all checks pass
    logger.debug(f"Item {item_index}: Data validated successfully.")
    return True

def generate_placeholder_svg(icon: str, width: int = 100, height: int = 100) -> str:
    """Generates a simple placeholder SVG as a data URI string."""
    safe_icon = html.escape(unicodedata.normalize("NFKC", icon), quote=True)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
        <rect width="100%" height="100%" fill="#1a1a2e"/>
        <text x="50%" y="50%" font-family="sans-serif" font-size="{min(width, height) // 3}" fill="#4a4a5e"
              text-anchor="middle" dominant-baseline="middle">{safe_icon}</text>
    </svg>'''
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")

# --- HTML Output Generation ---
# Enhanced HTML template with modern design and lazy loading script
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
      height: 180px; /* Fixed height for thumbnails */
      overflow: hidden;
      background: var(--bg-dark); /* Fallback background */
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .thumb img {{
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      object-fit: cover; /* Cover the area, cropping if necessary */
      transition: transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94); /* Smooth zoom on hover */
    }}
    .card:hover .thumb img {{
      transform: scale(1.08);
    }}
    .loading-spinner {{
      border: 4px solid rgba(255, 255, 255, 0.3);
      border-top: 4px solid var(--accent-cyan);
      border-radius: 50%;
      width: 30px;
      height: 30px;
      animation: spin 1s linear infinite;
      position: absolute; /* Center the spinner */
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
    }}
    @keyframes spin {{
      0% {{ transform: translate(-50%, -50%) rotate(0deg); }}
      100% {{ transform: translate(-50%, -50%) rotate(360deg); }}
    }}
    .placeholder {{ /* Style for placeholder icon */
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 2rem;
        color: var(--muted);
    }}
    .body {{
      padding: 1.5rem;
      display: flex;
      flex-direction: column;
      flex-grow: 1; /* Allow body to grow to fill card height */
    }}
    .title {{
      font-size: 1.1rem;
      font-weight: 600;
      margin-bottom: 1rem;
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2; /* Limit title to 2 lines */
      -webkit-box-orient: vertical;
      overflow: hidden;
      min-height: 3rem; /* Ensure consistent height for title box */
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap; /* Allow meta items to wrap */
      gap: 0.75rem;
      font-size: 0.85rem;
      color: var(--muted);
      margin-top: auto; /* Push meta info to the bottom */
      padding-top: 1rem;
      border-top: 1px solid var(--border);
    }}
    .meta .item {{
      background: rgba(0, 212, 255, 0.1); /* Subtle background */
      color: var(--accent-cyan);
      padding: 0.3rem 0.8rem;
      border-radius: 15px; /* Pill shape */
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
    /* Responsive adjustments */
    @media (max-width: 768px) {{
      .container {{
        margin: 1rem;
        padding: 0.5rem;
        border-radius: 12px;
      }}
      header {{
        margin-bottom: 1.5rem;
      }}
      h1 {{
        font-size: 2rem;
      }}
      .stats {{
        flex-direction: column; /* Stack stats vertically */
        gap: 0.75rem;
      }}
      .stat {{
        padding: 0.5rem 1rem;
        font-size: 0.8rem;
      }}
      .grid {{
        grid-template-columns: 1fr; /* Single column layout */
        gap: 1.5rem;
      }}
      .body {{
        padding: 1rem;
      }}
      .title {{
        font-size: 1rem;
      }}
      .meta {{
        justify-content: center; /* Center meta items */
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
<!-- Lazy loading script -->
<script>
    document.addEventListener('DOMContentLoaded', function() {{
        const lazyImages = document.querySelectorAll('img[data-src]');
        const observer = new IntersectionObserver((entries, obs) => {{
            entries.forEach(entry => {{
                if (entry.isIntersecting) {{
                    const imgElement = entry.target;
                    const thumbContainer = imgElement.closest('.thumb');

                    // Show loading spinner while image loads
                    if (thumbContainer) {{
                        const spinner = document.createElement('div');
                        spinner.className = 'loading-spinner';
                        thumbContainer.appendChild(spinner);
                    }}

                    const actualImage = new Image();
                    actualImage.src = imgElement.dataset.src; // Set the source from data-src

                    actualImage.onload = () => {{
                        if (thumbContainer) {{
                            thumbContainer.innerHTML = ''; // Clear spinner
                            thumbContainer.appendChild(actualImage); // Add the loaded image
                            actualImage.classList.add('loaded'); // Add class for potential styling
                        }}
                        observer.unobserve(imgElement); // Stop observing once loaded
                    }};

                    actualImage.onerror = () => {{
                        console.error('Failed to load image:', imgElement.dataset.src);
                        if (thumbContainer) {{
                            thumbContainer.innerHTML = '<div class="placeholder">❌</div>'; // Show error placeholder
                        }}
                        observer.unobserve(imgElement); // Stop observing on error
                    }};
                }}
            }});
        }}, {{ threshold: 0.1 }}); // Trigger when 10% of the image is visible

        lazyImages.forEach(img => observer.observe(img));
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
) -> Path | None:
    """Generates an enhanced HTML gallery page from the search results.
    Downloads thumbnails concurrently (async or threaded) and embeds them.
    Returns the path to the generated HTML file or None on failure.
    """
    output_directory = output_dir or VSEARCH_DIR
    try:
        ensure_dir(output_directory)
        ensure_dir(thumbs_dir) # Ensure thumbnail directory exists
    except Exception as e:
        logger.error(f"Failed to prepare output directories: {e}")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Create a safer filename using slugify
    safe_query_slug = enhanced_slugify(query)
    filename = f"{engine}_{safe_query_slug}_{timestamp}_{uuid.uuid4().hex[:8]}.html"
    outfile = Path(output_directory) / filename

    def get_thumb_path(img_url: str, title: str, idx: int) -> Path:
        """Generates a safe local path for a thumbnail based on URL and title."""
        if not img_url:
            # Use a generic placeholder if no URL provided
            return thumbs_dir / f"placeholder_{idx}.svg"

        try:
            # Extract extension from URL, default to .jpg if missing or invalid
            parsed_url = urlparse(img_url)
            _, ext = os.path.splitext(parsed_url.path)
            if not ext or ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']:
                ext = ".jpg"

            safe_title = enhanced_slugify(title)[:50] # Use part of title for filename
            # Combine elements for a unique and descriptive thumbnail name
            return thumbs_dir / f"{safe_title}_{idx}{ext}"
        except Exception as e:
            logger.debug(f"Error generating thumbnail path for '{img_url}': {e}")
            # Fallback to a generic name if path generation fails
            return thumbs_dir / f"thumbnail_{idx}.jpg"

    # --- Thumbnail Fetching Tasks ---
    async def fetch_thumbnail_async_task(idx: int, video: dict) -> tuple[int, str]:
        """Async task to download a single thumbnail."""
        img_url = video.get("img_url")
        title = video.get("title", f"video_{idx}")
        destination_path = get_thumb_path(img_url, title, idx)

        # 1. Check if thumbnail already exists and is valid
        if destination_path.exists():
            try:
                if destination_path.stat().st_size >= WOWXXX_CONFIG["thumbnail"]["min_size"]:
                    logger.debug(f"Thumbnail exists: {destination_path.name}")
                    return idx, str(destination_path).replace("\\", "/") # Return relative path
            except Exception as e:
                logger.debug(f"Error checking existing thumbnail {destination_path}: {e}")

        # 2. Attempt download using async session if available
        if ASYNC_AVAILABLE:
            async with aiohttp_session_context() as async_session: # Get session from context manager
                if async_session:
                    # Create a semaphore for concurrency control within async downloads
                    # Use a reasonable limit, adjust based on workers count and system capability
                    thumb_semaphore = asyncio.Semaphore(max(1, workers // 2))
                    success = await download_thumbnail_async(
                        async_session, img_url, destination_path, thumb_semaphore,
                        engine=engine, query=query
                    )
                    if success: return idx, str(destination_path).replace("\\", "/")

        # 3. Fallback to synchronous download using the main requests session
        # Use threads for sync download to avoid blocking the async event loop
        loop = asyncio.get_running_loop()
        success = await loop.run_in_executor(
            None, # Uses default ThreadPoolExecutor
            robust_download_sync,
            session, img_url, destination_path, engine=engine, query=query
        )
        if success: return idx, str(destination_path).replace("\\", "/")

        # 4. If all downloads fail, return a placeholder SVG data URI
        return idx, generate_placeholder_svg("📹", width=150, height=100) # Use a slightly larger placeholder


    # --- Execute Thumbnail Downloads Concurrently ---
    thumbnail_paths = [""] * len(results) # Pre-allocate list for results

    # Prefer async execution if available and not disabled by args
    use_async_downloads = ASYNC_AVAILABLE and not getattr(args, 'no_async', False)

    if use_async_downloads:
        try:
            logger.info(f"Starting async thumbnail downloads using up to {workers} workers...")
            tasks = [fetch_thumbnail_async_task(i, video) for i, video in enumerate(results)]
            # Use gather to run tasks concurrently
            download_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results, handling potential exceptions from gather
            for result in download_results:
                if isinstance(result, tuple) and len(result) == 2:
                    idx, path = result
                    thumbnail_paths[idx] = path
                elif isinstance(result, Exception):
                    logger.error(f"An exception occurred during thumbnail download: {result}", exc_info=result)
                else: # Handle unexpected result types or None paths
                    logger.warning(f"Received unexpected result during async download: {result}")

        except Exception as e:
            logger.error(f"Failed to run async thumbnail downloads: {e}", exc_info=True)
            # Fallback to synchronous download if the async gathering fails critically
            use_async_downloads = False # Force sync download path

    # If async was disabled or failed, use ThreadPoolExecutor for sync downloads
    if not use_async_downloads:
        logger.info(f"Starting synchronous thumbnail downloads using ThreadPoolExecutor (workers={workers})...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, 20)) as executor: # Limit threads to avoid resource exhaustion
            # Create futures for each download task
            future_to_idx = {executor.submit(lambda i, v: (i, robust_download_sync(session, v.get('img_url'), get_thumb_path(v.get('img_url'), v.get('title', f'video_{i}'), i), engine=engine, query=query)) # Simplified lambda for sync task
                                            , i, video): i for i, video in enumerate(results)}
            progress_bar = tqdm(
                concurrent.futures.as_completed(future_to_idx),
                total=len(future_to_idx),
                desc=f"{NEON['MAGENTA']}Downloading Thumbnails{NEON['RESET']}",
                unit="files",
                ncols=100,
                disable=not TQDM_AVAILABLE # Disable progress bar if tqdm is not installed
            )
            for future in progress_bar:
                i = future_to_idx[future] # Get original index
                try:
                    idx, path_str = future.result() # Get result tuple (index, path_str)
                    thumbnail_paths[idx] = path_str
                except Exception as e:
                    logger.error(f"Error getting result for sync download task {i}: {e}", exc_info=True)
                    thumbnail_paths[i] = generate_placeholder_svg("❌", width=150, height=100) # Placeholder on error

    # --- Generate HTML Content ---
    try:
        logger.info(f"Generating HTML output file: {outfile}")
        with open(outfile, "w", encoding="utf-8") as f:
            # Write HTML Head
            f.write(HTML_HEAD.format(
                title=f"{html.escape(query)} - {engine} Results",
                query=html.escape(query),
                count=len(results),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
            ))

            # Write HTML for each video card
            for i, video in enumerate(results):
                # Prepare metadata items for display
                meta_items = []
                if video.get("time", "N/A") != "N/A":
                    meta_items.append(f'<div class="item">⏱️ {html.escape(video["time"])}</div>')

                if video.get("channel_name", "N/A") != "N/A":
                    channel_link = video.get("channel_link", "#")
                    channel_display = html.escape(video["channel_name"])
                    if channel_link != "#":
                        meta_items.append(f'<div class="item">👤 <a href="{html.escape(channel_link)}" target="_blank" rel="noopener noreferrer">{channel_display}</a></div>')
                    else:
                        meta_items.append(f'<div class="item">👤 {channel_display}</div>')

                if video.get("meta", "N/A") != "N/A":
                    meta_items.append(f'<div class="item">👁️ {html.escape(video["meta"])}</div>')

                if video.get("video_id", "N/A") != "N/A":
                    meta_items.append(f'<div class="item">🆔 {html.escape(video["video_id"])}</div>')

                # Construct the video card HTML
                f.write(f'''
                <div class="card">
                    <a href="{html.escape(video['link'])}" target="_blank" rel="noopener noreferrer">
                        <div class="thumb">
                            <!-- Use data-src for lazy loading -->
                            <img src="" data-src="{html.escape(thumbnail_paths[i])}" alt="{html.escape(video['title'])}" loading="lazy">
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

            # Write HTML Tail (includes closing tags and script)
            f.write(HTML_TAIL.format(timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        logger.info(f"HTML gallery saved to: {outfile}")

        # Optionally open the generated file in the default web browser
        if open_browser and outfile.exists():
            try:
                abs_path = os.path.abspath(outfile)
                webbrowser.open(f"file://{abs_path}")
                logger.debug(f"Opened HTML file in browser: {abs_path}")
            except Exception as e:
                logger.warning(f"Failed to open browser automatically: {e}")

        return outfile # Return the path of the generated file

    except OSError as e:
        logger.error(f"Failed to write HTML output to {outfile}: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during HTML generation: {e}", exc_info=True)
        return None


def get_wowxxx_results(
    session: requests.Session,
    query: str,
    limit: int,
    page: int,
    delay_range: tuple[float, float],
    config: dict[str, Any] = WOWXXX_CONFIG,
    use_selenium: bool | None = None, # If None, derive from config
    verbose: bool = False # Pass verbose flag for detailed logging
) -> list[dict[str, Any]]:
    """Fetches video search results from wow.xxx, handling pagination, JS rendering,
    and potential errors. Returns a list of video data dictionaries.
    """
    base_url = config.get("url", "https://www.wow.xxx")
    results: list[dict[str, Any]] = []
    last_request_time: float | None = None
    request_history: list[float] = [] # For adaptive delay calculation

    # --- Configuration for Pagination ---
    pagination_config = config.get("pagination", {})
    max_pages_to_scrape = pagination_config.get("max_pages", 5)
    items_per_page = pagination_config.get("items_per_page", 30)
    detect_end_of_results = pagination_config.get("detect_end", False)
    next_page_selector = pagination_config.get("next_page_selector", "")

    # Calculate the maximum number of pages to fetch based on limit and items_per_page
    # Ensure we fetch at least 1 page, and not more than max_pages_to_scrape
    pages_to_fetch = max(1, min(max_pages_to_scrape, (limit + items_per_page - 1) // items_per_page))

    logger.info(
        f"Starting search for '{query}' on {base_url}. Fetching up to {pages_to_fetch} pages.",
        extra={'engine': 'Wowxxx', 'query': query}
    )

    # --- Selenium Setup ---
    driver = None
    current_use_selenium = use_selenium if use_selenium is not None else config.get("requires_js", False)

    if current_use_selenium and SELENIUM_AVAILABLE:
        logger.info("JavaScript rendering detected or forced. Initializing Selenium WebDriver...")
        try:
            chrome_options = ChromeOptions()
            # Headless mode for running without a visible browser window
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox") # Bypass OS security model, required for Docker/rootless
            chrome_options.add_argument("--disable-dev-shm-usage") # Overcome limited resource problems
            chrome_options.add_argument(f"--user-agent={random.choice(session.user_agent_list)}") # Use realistic UA
            # Stealth enhancements to avoid Selenium detection
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer") # Often needed with headless
            chrome_options.add_argument("--window-size=1200,800") # Set initial window size

            # Initialize the WebDriver
            driver = webdriver.Chrome(options=chrome_options)
            logger.info("Selenium WebDriver initialized successfully.")

            # Further stealth: Modify navigator.webdriver flag via CDP
            try:
                driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => false
                        });
                    """
                })
                logger.debug("Applied navigator.webdriver stealth script.")
            except Exception as e:
                logger.warning(f"Failed to apply navigator.webdriver stealth: {e}")

        except WebDriverException as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {e}. Disabling Selenium.", exc_info=True)
            current_use_selenium = False # Disable Selenium if initialization fails
        except Exception as e: # Catch any other unexpected errors during setup
            logger.error(f"Unexpected error during Selenium setup: {e}. Disabling Selenium.", exc_info=True)
            current_use_selenium = False

    # --- Main Scraping Loop ---
    current_page_num = page
    has_more_pages = True

    while has_more_pages and len(results) < limit:
        # Apply adaptive delay before making the request
        smart_delay_with_jitter(
            delay_range, last_request_time,
            target_engine="Wowxxx", query=query,
            request_history=request_history, adaptive=True # Enable adaptive delay
        )
        last_request_time = time.time() # Record time of this request

        # Construct the URL for the current page
        try:
            search_query_encoded = quote_plus(query)
            # Construct base search URL
            search_path = config.get("search_path", "/search/{query}/").format(query=search_query_encoded)
            current_url = urljoin(base_url, search_path)

            # Append page number if not the first page and pagination is configured
            if current_page_num > 1 and config.get("pagination", {}).get("enabled", False):
                page_pattern = config["pagination"].get("path_pattern", "/page/{page}/")
                page_url_part = page_pattern.format(page=current_page_num)
                current_url += page_url_part # Append page info
                logger.debug(f"Constructed URL for page {current_page_num}: {current_url}")

            logger.info(f"Fetching page {current_page_num}: {current_url}", extra={'engine': 'Wowxxx', 'query': query})

            soup = None # Initialize soup to None for this iteration
            page_content_error = False

            # --- Fetch page content ---
            if driver and current_use_selenium:
                # Use Selenium to render the page
                try:
                    driver.get(current_url)
                    # Wait for essential elements to load - adjust timeout as needed
                    wait = WebDriverWait(driver, 20) # Max 20 seconds wait
                    # Wait for at least one video item container to be present
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config["video_item_selector"])))

                    # Optional: Scroll down to trigger lazy loading if necessary
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    # Give lazy loaded content a moment to load after scrolling
                    time.sleep(random.uniform(1.0, 2.5))

                    # Get page source after rendering and wait
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, "html.parser")
                    logger.debug(f"Page {current_page_num} loaded via Selenium.")

                except (TimeoutException, WebDriverException) as e:
                    logger.error(f"Selenium failed to load page {current_page_num} ({current_url}): {e}. Trying without JS.", exc_info=True)
                    page_content_error = True
                    # Disable Selenium for subsequent requests if it failed
                    current_use_selenium = False
                    if driver: driver.quit() # Quit potentially stuck driver
                    driver = None
                except Exception as e: # Catch other unexpected errors
                    logger.error(f"Unexpected error with Selenium on page {current_page_num}: {e}. Trying without JS.", exc_info=True)
                    page_content_error = True
                    current_use_selenium = False
                    if driver: driver.quit()
                    driver = None

            else: # Use requests if Selenium is disabled or unavailable
                try:
                    # Ensure session headers are up-to-date (UA might change)
                    session.headers.update(get_realistic_headers(random.choice(session.user_agent_list)))
                    # Send request using the enhanced session
                    response = session.get(current_url) # Timeout is set on session

                    # Check for rate limiting or other common issues
                    if response.status_code == 429: # Too Many Requests
                        logger.warning(f"Rate limited by server (HTTP 429) on page {current_page_num}. Increasing delays.")
                        # Adjust delay range adaptively
                        min_d, max_d = delay_range
                        delay_range = (min_d * 1.8, max_d * 1.8) # Increase delay significantly
                        # Add extra wait time before retrying this page
                        time.sleep(random.uniform(5, 10))
                        continue # Retry the same page with increased delay

                    response.raise_for_status() # Raise HTTPError for other bad statuses (4xx, 5xx)

                    # Check if the page indicates no results found
                    if "no results found" in response.text.lower() or "not found" in response.text.lower():
                        logger.info(f"Server indicated no results found for query '{query}' on page {current_page_num}.")
                        has_more_pages = False # Stop searching
                        break

                    # Parse HTML content
                    soup = BeautifulSoup(response.text, "html.parser")
                    logger.debug(f"Page {current_page_num} loaded successfully via requests.")

                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 404:
                        logger.info(f"Page {current_page_num} not found (HTTP 404). Assuming end of results.")
                        has_more_pages = False
                        break
                    if e.response.status_code == 403:
                        logger.error(f"Access forbidden (HTTP 403) on page {current_page_num}. Possible IP block or CAPTCHA. Stopping search.")
                        has_more_pages = False
                        break
                    # Handle other HTTP errors
                    logger.error(f"HTTP error fetching page {current_page_num}: {e}", exc_info=True)
                    page_content_error = True

                except requests.exceptions.RequestException as e:
                    logger.error(f"Network request failed for page {current_page_num} ({current_url}): {e}", exc_info=True)
                    page_content_error = True
                except Exception as e: # Catch other unexpected errors
                    logger.error(f"Unexpected error fetching page {current_page_num}: {e}", exc_info=True)
                    page_content_error = True

            # If page content fetching failed (either Selenium or Requests)
            if page_content_error or soup is None:
                logger.warning(f"Failed to retrieve or parse content for page {current_page_num}. Skipping.")
                # Decide whether to stop or try next page depending on error type
                if not has_more_pages: break # If already marked no more pages, stop
                # Continue to next page iteration, maybe the next page works
                current_page_num += 1
                continue

            # --- Extract Video Items ---
            video_items = extract_video_items(soup, config)

            if not video_items:
                logger.warning(f"No video items found on page {current_page_num} using available selectors.")
                # Check if we should stop based on configuration
                if detect_end_of_results:
                    logger.info("Detected end of results based on missing items.")
                    has_more_pages = False
                    break

                # If pagination is enabled, check for a 'next page' link
                if next_page_selector and config.get("pagination", {}).get("enabled", False):
                    next_page_link = soup.select_one(next_page_selector)
                    if not next_page_link:
                        logger.info(f"No 'next page' link found on page {current_page_num}. Stopping pagination.")
                        has_more_pages = False
                        break
                # If no specific detection or next page selector, assume we might continue if limit not reached
                # Continue loop, but don't add results this round.
            else:
                logger.info(f"Found {len(video_items)} potential video items on page {current_page_num}.")
                # --- Process Each Video Item ---
                for idx, item in enumerate(video_items):
                    if len(results) >= limit: # Stop if we reached the desired limit
                        break

                    # Extract data for the video item
                    video_data = extract_video_data_enhanced(item, config, base_url)

                    # Validate the extracted data
                    if video_data and validate_video_data_enhanced(video_data, item_index=len(results)):
                        results.append(video_data)
                    # Log validation failure if data was extracted but invalid
                    elif video_data:
                         logger.debug(f"Item {len(results)} failed validation (data: {str(video_data)[:100]}...)", extra={'engine': 'Wowxxx', 'query': query})


                # --- Check for End of Pagination ---
                # Check if we should stop based on next page selector after processing items
                if next_page_selector and config.get("pagination", {}).get("enabled", False):
                    next_page_link = soup.select_one(next_page_selector)
                    if not next_page_link:
                        logger.info(f"No 'next page' link found after processing page {current_page_num}. Stopping pagination.")
                        has_more_pages = False
                        # Break the loop if no more pages can be found
                        break
                elif not video_items and detect_end_of_results: # Also check if no items were found and detection is on
                    logger.info(f"No items found on page {current_page_num} and end detection is enabled. Stopping.")
                    has_more_pages = False
                    break


            # Move to the next page number for the next iteration
            current_page_num += 1

        except Exception as e: # Catch-all for unexpected errors in the loop
            logger.error(f"Critical error processing page {current_page_num}: {e}", exc_info=True)
            has_more_pages = False # Stop loop on critical error
            break

    # --- Cleanup ---
    if driver:
        try:
            logger.info("Closing Selenium WebDriver.")
            driver.quit()
        except Exception as e:
            logger.warning(f"Error quitting Selenium driver: {e}")

    # Log final summary
    actual_limit = len(results)
    logger.info(f"Search finished. Found {actual_limit} valid video results (requested limit: {limit}).", extra={'engine': 'Wowxxx', 'query': query})
    return results[:limit] # Return results up to the requested limit

# --- Argument Parsing ---
def parse_arguments():
    """Parses command-line arguments for the script."""
    parser = argparse.ArgumentParser(
        description="Wow.xxx Video Search Tool - Enhanced Scraper.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  python wowxxx_search.py "teen girl"
  python wowxxx_search.py "milf" -l 50 --output-format json
  python wowxxx_search.py "anal" -v --output-dir my_results
  python wowxxx_search.py "stepmom" --config custom_selectors.json --no-js
  python wowxxx_search.py "search term" --proxy http://localhost:8080
  python wowxxx_search.py "proxy rotation" --proxy-list proxies.txt

Dependencies: requests, beautifulsoup4, colorama. Optional: aiohttp, selenium, tqdm.
Install optional dependencies: pip install aiohttp selenium tqdm
"""
    )

    parser.add_argument(
        "query",
        type=str,
        help="The search query for videos (enclose in quotes if spaces are present)."
    )

    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"Maximum number of video results to retrieve (default: {DEFAULT_LIMIT})."
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
        help="Single proxy server to use for all requests (e.g., http://user:pass@host:port)."
    )

    parser.add_argument(
        "--proxy-list",
        type=str,
        help="Path to a file containing a list of proxies (one per line) for rotation."
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
        help="Disable asynchronous thumbnail downloading and use a thread pool instead (useful if asyncio/aiohttp cause issues)."
    )

    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not automatically open the generated HTML report in the web browser."
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level) to show more details."
    )

    parser.add_argument(
        "--no-js",
        action="store_true",
        help="Force disabling JavaScript rendering via Selenium, even if 'requires_js' is true in config."
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=None, # Default handled later, None means use VSEARCH_DIR
        help="Custom directory to save output files (HTML, JSON, CSV, thumbnails). Defaults to './wowxxx_results'."
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to a custom JSON configuration file to override default selectors and settings."
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode: perform a search for a few results, check basic functionality, but don't save outputs."
    )

    return parser.parse_args()

def load_custom_config(config_file: str) -> dict[str, Any]:
    """Loads custom configuration from a JSON file and merges it with defaults."""
    if not config_file:
        return WOWXXX_CONFIG # Return defaults if no file specified

    config_path = Path(config_file)
    if not config_path.is_file():
        logger.error(f"Custom configuration file not found: {config_file}")
        return WOWXXX_CONFIG # Return defaults if file is missing

    try:
        with open(config_path, encoding='utf-8') as f:
            custom_data = json.load(f)

        # Deep merge custom config into default config
        merged_config = WOWXXX_CONFIG.copy() # Start with defaults

        def merge_dicts(target, source):
            """Recursively merges source dict into target dict."""
            for key, value in source.items():
                if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                    merge_dicts(target[key], value) # Recurse for nested dictionaries
                else:
                    target[key] = value # Overwrite or add new key/value
            return target

        merged_config = merge_dicts(merged_config, custom_data)

        logger.info(f"Successfully loaded and merged custom configuration from {config_file}")
        return merged_config
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse custom config file {config_file}: {e}. Using default configuration.", exc_info=True)
        return WOWXXX_CONFIG
    except Exception as e:
        logger.error(f"Failed to load custom configuration from {config_file}: {e}. Using default configuration.", exc_info=True)
        return WOWXXX_CONFIG

def load_proxy_list(proxy_list_file: str) -> list[str]:
    """Loads a list of proxies from a file, skipping comments and invalid lines."""
    proxies = []
    if not proxy_list_file:
        return proxies # Return empty list if no file specified

    proxy_path = Path(proxy_list_file)
    if not proxy_path.is_file():
        logger.warning(f"Proxy list file not found: {proxy_list_file}. Proceeding without proxy list.")
        return proxies

    try:
        with open(proxy_path, encoding='utf-8') as f:
            for line in f:
                proxy = line.strip()
                # Skip empty lines, comments, and lines that don't look like valid proxy URLs
                if proxy and not proxy.startswith('#') and urlparse(proxy).scheme in ['http', 'https']:
                    proxies.append(proxy)
        if proxies:
            logger.info(f"Loaded {len(proxies)} proxies from {proxy_list_file}")
        else:
            logger.warning(f"No valid proxies found in {proxy_list_file}.")
    except OSError as e:
        logger.error(f"Failed to read proxy list file {proxy_list_file}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred loading proxy list {proxy_list_file}: {e}", exc_info=True)

    return proxies

# --- Main Execution Block ---
def main():
    """Main function to orchestrate the search, download, and output process."""
    args = parse_arguments()

    # Set logging level
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled.")

    # Load configuration: merge defaults with custom file if provided
    config = load_custom_config(args.config)

    # Load proxy list if provided
    proxy_list = load_proxy_list(args.proxy_list)

    # --- Graceful Exit Handling ---
    global shutdown_flag
    shutdown_flag = False
    def signal_handler(sig, frame):
        """Handles SIGINT (Ctrl+C) for graceful shutdown."""
        global shutdown_flag
        shutdown_flag = True
        print(f"\n{NEON['YELLOW']}* Detected Ctrl+C. Initiating graceful shutdown...{NEON['RESET']}")
    signal.signal(signal.SIGINT, signal_handler)

    session = None # Initialize session to None
    try:
        # Build the requests session with proxy settings
        session = build_enhanced_session(
            proxy=args.proxy,
            proxy_list=proxy_list if proxy_list else None
        )

        # Determine whether to use Selenium based on config, args, and availability
        should_use_selenium = not args.no_js and config.get("requires_js", False) and SELENIUM_AVAILABLE
        if not SELENIUM_AVAILABLE and config.get("requires_js", False):
             logger.warning("Site requires JavaScript, but Selenium is not installed or failed to load. Results might be incomplete or missing.")

        print(f"{NEON['CYAN']}{Style.BRIGHT}Starting search for '{args.query}' on wow.xxx...")

        # --- Test Mode ---
        if args.test:
            print(f"{NEON['YELLOW']}Running in TEST MODE. Checking search functionality only.{NEON['RESET']}")
            test_results = get_wowxxx_results(
                session=session, query=args.query, limit=5, page=args.page,
                delay_range=DEFAULT_DELAY, config=config,
                use_selenium=should_use_selenium, verbose=args.verbose
            )
            if test_results:
                print(f"{NEON['GREEN']}TEST SUCCESS: Found {len(test_results)} videos.{NEON['RESET']}")
                print(f"{NEON['CYAN']}First result title: {test_results[0].get('title', 'N/A')}")
            else:
                print(f"{NEON['RED']}TEST FAILED: No videos found or an error occurred during search.{NEON['RESET']}")
                print(f"{NEON['YELLOW']}Consider checking selectors, network connection, or enabling verbose logging (-v).{NEON['RESET']}")
            if session and not session.closed: session.close()
            sys.exit(0) # Exit after test run

        # --- Perform Actual Search ---
        results = get_wowxxx_results(
            session=session, query=args.query, limit=args.limit, page=args.page,
            delay_range=DEFAULT_DELAY, config=config,
            use_selenium=should_use_selenium, verbose=args.verbose
        )

        # Handle case where no results were found
        if not results:
            print(f"{NEON['RED']}No video results found matching '{args.query}'.{NEON['RESET']}")
            print(f"{NEON['YELLOW']}Try refining your search query or check the website structure if issues persist.{NEON['RESET']}")
            if session and not session.closed: session.close()
            sys.exit(1) # Exit with error code if no results found

        print(f"{NEON['GREEN']}Successfully found {len(results)} video results.{NEON['RESET']}")

        # --- Handle Output ---
        output_directory = Path(args.output_dir) if args.output_dir else VSEARCH_DIR
        output_format = args.output_format

        # Prepare filename components
        timestamp_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_slug = enhanced_slugify(args.query)
        base_filename = f"{config.get('url', DEFAULT_ENGINE).split('//')[1]}_{query_slug}_{timestamp_suffix}"

        output_path = None # Store path of generated file

        if output_format == "json":
            filename = f"{base_filename}.json"
            output_path = Path(output_directory) / filename
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(results, f, ensure_ascii=False, indent=4)
                print(f"{NEON['CYAN']}JSON results saved to: {output_path}{NEON['RESET']}")
            except OSError as e:
                print(f"{NEON['RED']}Error saving JSON file to {output_path}: {e}{NEON['RESET']}")
                sys.exit(1)

        elif output_format == "csv":
            filename = f"{base_filename}.csv"
            output_path = Path(output_directory) / filename
            try:
                if results: # Ensure there are results before writing CSV
                    # Use keys from the first result as headers, assuming consistency
                    fieldnames = results[0].keys()
                    with open(output_path, "w", encoding="utf-8", newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        writer.writerows(results)
                print(f"{NEON['CYAN']}CSV results saved to: {output_path}{NEON['RESET']}")
            except OSError as e:
                print(f"{NEON['RED']}Error saving CSV file to {output_path}: {e}{NEON['RESET']}")
                sys.exit(1)
            except Exception as e: # Catch potential issues with DictWriter or data structure
                 print(f"{NEON['RED']}Error processing data for CSV output: {e}{NEON['RESET']}")
                 sys.exit(1)


        else: # Default to HTML output
            print(f"{NEON['CYAN']}Generating HTML report...{NEON['RESET']}")
            # Check if async capabilities are available for HTML generation
            if ASYNC_AVAILABLE:
                try:
                    # Use asyncio.run to execute the async HTML builder function
                    generated_file_path = asyncio.run(
                        build_enhanced_html_async(
                            results=results, query=args.query, engine=config.get('url', DEFAULT_ENGINE).split('//')[1],
                            thumbs_dir=THUMBNAILS_DIR, session=session, workers=args.workers,
                            output_dir=output_directory, open_browser=not args.no_open
                        )
                    )
                    if not generated_file_path:
                        raise RuntimeError("HTML generation failed internally.")
                    output_path = generated_file_path
                    # Success message is printed inside build_enhanced_html_async
                except RuntimeError as e: # Catch errors from build_enhanced_html_async
                    print(f"{NEON['RED']}Failed to generate HTML output: {e}{NEON['RESET']}")
                    if session and not session.closed: session.close()
                    sys.exit(1)
                except Exception as e: # Catch unexpected errors during async execution
                    print(f"{NEON['RED']}An unexpected error occurred during HTML generation: {e}{NEON['RESET']}")
                    if session and not session.closed: session.close()
                    sys.exit(1)
            else: # aiohttp not available, HTML cannot be generated
                # This else block correctly handles the case where HTML is requested but aiohttp is missing.
                print(f"{NEON['RED']}HTML output requires the 'aiohttp' library, which is not installed.{NEON['RESET']}")
                # Clean up session and exit if HTML is requested but impossible
                if session and not session.closed: session.close()
                sys.exit(1)

    except KeyboardInterrupt:
        print(f"\n{NEON['YELLOW']}Operation interrupted by user.{NEON['RESET']}")
        if session and not session.closed: session.close()
        sys.exit(0) # Exit cleanly on interrupt
    except Exception as e:
        # Catch any unexpected critical errors
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"{NEON['RED']}A critical error occurred: {e}{NEON['RESET']}")
        if session and not session.closed: session.close()
        sys.exit(1)
    finally:
        # Ensure session is closed in all exit scenarios
        if session and not session.closed:
            try:
                session.close()
            except Exception as e:
                logger.warning(f"Error closing requests session in finally block: {e}")

        # Check shutdown flag state after all operations
        if shutdown_flag:
            print(f"{NEON['YELLOW']}Exiting gracefully due to interruption.{NEON['RESET']}")
            # Exit code 130 is standard for termination via Ctrl+C
            sys.exit(130)

# --- Script Entry Point ---
if __name__ == "__main__":
    # The main() function handles all logic, including conditional async execution.
    # Simply call main() here.
    try:
        main()
    except KeyboardInterrupt:
        # Fallback catch for interrupt if not handled perfectly within main()
        print(f"\n{NEON['YELLOW']}Operation interrupted by user (caught in __main__).{NEON['RESET']}")
        sys.exit(0)
    except Exception as e:
        # Catch any unexpected errors during the execution initiated by main()
        logger.critical(f"Unhandled exception during script execution: {e}", exc_info=True)
        print(f"{NEON['RED']}An unhandled exception occurred: {e}{NEON['RESET']}")
        sys.exit(1)
