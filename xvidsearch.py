#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
video_search.py - Enhanced Video Search Tool (2025 Edition)

This script serves as a powerful conduit for discovering video content across
various web platforms, leveraging modern Python features and robust web scraping
techniques. It's designed for the Termux environment, offering flexibility in
output formats and download strategies.

Core Features:
- Modern Python 3.10+ constructs (type hints, pathlib, async/await).
- Dual download system: async primary with sync fallback for thumbnails.
- Robust error handling, retries, and intelligent delays with jitter.
- Progress tracking via tqdm (optional, install with: pip install tqdm).
- HTML gallery, JSON, and CSV output options.
- Optional Selenium/aiohttp integration for JavaScript-heavy engines.
- Adult-content gating via CLI flag (--allow-adult).
- Enhanced handling of HTML image sources for lazy loading and placeholders.

Usage:
  python3 video_search.py "your search query" [options]

Example:
  python3 video_search.py "cats in space"
  python3 video_search.py "ocean waves" -e pexels -l 50 -o json
  python3 video_search.py "daily news" -e dailymotion --no-async --no-open
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
from colorama import Fore, Style, init as colorama_init
from requests.adapters import HTTPAdapter, Retry

# --- Optional Dependencies ---
# For async operations:
# pkg install python-aiohttp
try:
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

# For JavaScript-heavy sites (requires ChromeDriver):
# pkg install python-selenium
# pkg install chromium
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

# For progress bars:
# pip install tqdm
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    def tqdm(iterable, *_, **__):
        return iterable

# ─── Pyrmethus's Configuration & Constants ─────────────────────────────────

# Initialize the terminal's chromatic essence
colorama_init(autoreset=True)

# Define the directories where artifacts shall be stored
THUMBNAILS_DIR = Path("downloaded_thumbnails")
VSEARCH_DIR = Path("vsearch")

# Default parameters for the search incantations
DEFAULT_ENGINE = "pexels"
DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_FORMAT = "html"
DEFAULT_TIMEOUT = 25
DEFAULT_DELAY = (1.5, 4.0)  # Range for request delays with jitter
DEFAULT_MAX_RETRIES = 5
DEFAULT_WORKERS = 12  # Concurrency for thumbnail downloads

# A palette of vibrant colors for the terminal's tapestry
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

# Gating mechanism for adult content engines
ADULT_ENGINES = {"pornhub", "xhamster", "redtube"}
ALLOW_ADULT = False  # Controlled by the --allow-adult CLI flag

# A collection of realistic User-Agent strings to mimic diverse browsers
REALISTIC_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
]

# A curated set of realistic headers, rotated for each request/session
REALISTIC_HEADERS = {
    "User-Agent": random.choice(REALISTIC_USER_AGENTS),
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
}

# ─── Logging Rituals ───────────────────────────────────────────────────────
class ContextFilter(logging.Filter):
    """A filter to add context (engine, query) to log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        record.engine = getattr(record, "engine", "unknown")
        record.query = getattr(record, "query", "unknown")
        return True

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configures the logging system for clear and informative output."""
    log_handlers: List[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    try:
        # Attempt to log to a file as well, for persistent records
        log_file_path = Path("video_search.log")
        log_handlers.append(logging.FileHandler(log_file_path, mode="a", encoding="utf-8"))
    except PermissionError:
        logger.warning("Permission denied: Could not write to log file.")
    except Exception as e:
        logger.warning(f"Failed to set up log file handler: {e}")

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Define the mystical format for log messages
    log_format = (
        f"{NEON['CYAN']}%(asctime)s{NEON['RESET']} - "
        f"{NEON['MAGENTA']}%(levelname)s{NEON['RESET']} - "
        f"{NEON['GREEN']}%(engine)s{NEON['RESET']} - "
        f"{NEON['GREEN']}%(query)s{NEON['RESET']} - "
        f"{NEON['WHITE']}%(message)s{NEON['RESET']}"
    )
    formatter = logging.Formatter(log_format)

    for handler in log_handlers:
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.addFilter(ContextFilter())

    # Silence overly verbose libraries
    for noisy_logger_name in ("urllib3", "chardet", "requests", "aiohttp", "selenium"):
        logging.getLogger(noisy_logger_name).setLevel(logging.WARNING)

    return logger

logger = setup_logging()

# ─── Arcane Utilities & Helpers ──────────────────────────────────────────

def enhanced_slugify(text: str) -> str:
    """
    Forge a filesystem-safe slug from a given text string.
    This ensures compatibility across different operating systems and avoids
    issues with special characters.
    """
    if not text or not isinstance(text, str):
        return "untitled"

    # Normalize text to decompose characters and remove accents
    text = unicodedata.normalize("NFKD", text)
    # Encode to ASCII, ignoring errors, then decode back to ASCII
    text = text.encode("ascii", "ignore").decode("ascii")

    # Remove characters that are problematic in filenames
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    # Allow alphanumeric, spaces, hyphens, underscores, and periods
    text = re.sub(r"[^a-zA-Z0-9\s\-_.]", "", text)
    # Replace whitespace sequences with a single underscore
    text = re.sub(r"\s+", "_", text.strip())
    # Remove leading/trailing underscores, periods, or hyphens
    text = text.strip("._-")

    # Truncate to a reasonable length to prevent overly long filenames
    text = text[:100] or "untitled"

    # Prevent usage of reserved filenames (common in Windows)
    reserved_names = {
        "con", "prn", "aux", "nul", "com1", "com2", "com3", "com4", "com5",
        "com6", "com7", "com8", "com9", "lpt1", "lpt2", "lpt3", "lpt4",
        "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"
    }
    if text.lower() in reserved_names:
        text = f"file_{text}"

    return text

def ensure_dir(path: Path) -> None:
    """Create a directory if it does not already exist, with error handling."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured directory exists: {path}")
    except OSError as e:
        logger.error(f"Failed to create directory {path}: {e}")
        # Re-raise to halt execution if directory creation is critical
        raise

def get_realistic_headers(user_agent: Optional[str] = None) -> Dict[str, str]:
    """Generates a dictionary of realistic HTTP headers."""
    ua = user_agent or random.choice(REALISTIC_USER_AGENTS)
    return {
        "User-Agent": ua,
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
    }

def build_enhanced_session(
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    proxy: Optional[str] = None,
) -> requests.Session:
    """
    Forge a robust HTTP session. This session is equipped with retry mechanisms,
    realistic headers, and optional proxy support, ensuring stable connections.
    """
    session = requests.Session()

    # Define a resilient retry strategy for network requests
    try:
        retries = Retry(
            total=max_retries,
            backoff_factor=0.5,
            backoff_max=4.0,
            status_forcelist=(429, 500, 502, 503, 504, 520, 521, 522, 524),
            allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
            respect_retry_after_header=True,
        )
    except TypeError:
        # Fallback for older urllib3 versions that might not support 'allowed_methods'
        retries = Retry(
            total=max_retries,
            backoff_factor=0.5,
            backoff_max=4.0,
            status_forcelist=(429, 500, 502, 503, 504),
            method_whitelist=frozenset({"GET", "HEAD", "OPTIONS"}), # type: ignore
            respect_retry_after_header=True,
        )

    # Mount the adapter to handle HTTP and HTTPS protocols
    adapter = HTTPAdapter(
        max_retries=retries,
        pool_connections=15,
        pool_maxsize=30
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set realistic headers for the session
    session.headers.update(get_realistic_headers())

    # Configure proxy if provided
    if proxy:
        try:
            parsed = urlparse(proxy)
            if parsed.scheme and parsed.netloc:
                session.proxies.update({"http": proxy, "https": proxy})
                logger.info(f"Using proxy: {NEON['YELLOW']}{parsed.netloc}{NEON['RESET']}")
            else:
                logger.warning(f"Invalid proxy format provided: {proxy}")
        except Exception as e:
            logger.warning(f"Failed to configure proxy '{proxy}': {e}")

    # Store the default timeout on the session object for easy access
    setattr(session, "_default_timeout", timeout)
    return session

def smart_delay_with_jitter(
    delay_range: Tuple[float, float],
    last_request_time: Optional[float] = None,
    jitter_factor: float = 0.3
) -> None:
    """
    Implement intelligent delays between requests, incorporating jitter
    to mimic human behavior and avoid detection.
    """
    min_delay, max_delay = delay_range
    current_time = time.time()

    if last_request_time:
        elapsed = current_time - last_request_time
        # Calculate a base wait time within the specified range
        base_wait = random.uniform(min_delay, max_delay)
        # Introduce jitter: a random variation around the base wait time
        jitter_amount = base_wait * jitter_factor * random.uniform(-1, 1)
        # Ensure a minimum wait time to avoid overly rapid requests
        min_wait = max(0.5, base_wait + jitter_amount)

        if elapsed < min_wait:
            sleep_duration = min_wait - elapsed
            logger.debug(f"Waiting {sleep_duration:.2f}s to avoid rapid requests.")
            time.sleep(sleep_duration)
    else:
        # First request, just apply a random delay
        base_wait = random.uniform(min_delay, max_delay)
        jitter_amount = base_wait * jitter_factor * random.uniform(-1, 1)
        sleep_duration = max(0.5, base_wait + jitter_amount)
        logger.debug(f"Initial delay of {sleep_duration:.2f}s.")
        time.sleep(sleep_duration)

# ─── Thumbnail Manifestation (Download & Placeholders) ─────────────────────

def generate_placeholder_svg(icon: str) -> str:
    """
    Generate an SVG placeholder with proper UTF-8 encoding for embedding.
    This is crucial for handling potentially problematic characters in icons.
    """
    try:
        # Ensure the icon character is safely normalized and encoded
        safe_icon = unicodedata.normalize("NFKC", icon)
        safe_icon = html.escape(safe_icon, quote=True)  # Escape for safe embedding in SVG

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 100 100">
            <rect width="100%" height="100%" fill="#16213e"/>
            <text x="50" y="55" text-anchor="middle" dominant-baseline="middle" font-family="sans-serif" font-size="40" fill="#666">{safe_icon}</text>
        </svg>'''
        # Encode the final SVG string to Base64 for the data URI
        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")
    except Exception as e:
        logger.error(f"Error generating SVG placeholder for icon '{icon}': {e}")
        # Return a minimal, safe placeholder in case of failure
        return "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIHZpZXdCb3g9IjAgMCAxMDAgMTAwIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMTYyMTNlIi8+PHRleHQgeD0iNTAiIHk9IjU1IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiBmb250LWZhbWlseT0ic2Fucy1zZXJpZiIgZm9udC1zaXplPSI0MCIgZmlsbD0iIzY2NiI+Pz88L3RleHQ+PC9zdmc+"

def robust_download_sync(session: requests.Session, url: str, path: Path, max_attempts: int = 3) -> bool:
    """
    Synchronous fallback for downloading thumbnails. Includes validation
    and retry logic for resilience.
    """
    if not url or not urlparse(url).scheme:
        logger.debug(f"Skipping sync download: Invalid URL '{url}'")
        return False

    for attempt in range(max_attempts):
        try:
            # Rotate User-Agent for each attempt to appear more diverse
            session.headers.update({"User-Agent": random.choice(REALISTIC_USER_AGENTS)})
            
            with session.get(url, stream=True, timeout=session._default_timeout) as response:
                response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

                content_type = response.headers.get("content-type", "").lower()
                # Check if the content type is likely an image or a generic binary stream
                if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                    logger.debug(f"Sync download skipped for {url}: Unsupported content type '{content_type}'")
                    return False

                # Prevent downloading excessively large files
                content_length_str = response.headers.get("content-length")
                if content_length_str and int(content_length_str) > 10 * 1024 * 1024: # 10MB limit
                    logger.debug(f"Sync download skipped for {url}: File size exceeds limit ({content_length_str} bytes)")
                    return False

                # Write the content to the destination path
                with open(path, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)

                # Final check: ensure the file is not empty
                if path.stat().st_size == 0:
                    path.unlink(missing_ok=True) # Clean up empty file
                    logger.debug(f"Sync download resulted in an empty file for {url}")
                    return False

                logger.debug(f"Successfully downloaded thumbnail (sync): {path.name}")
                return True

        except requests.exceptions.RequestException as e:
            logger.debug(f"Sync download failed for {url} (attempt {attempt + 1}/{max_attempts}): {e}")
            if attempt < max_attempts - 1:
                # Exponential backoff for retries
                time.sleep(2 ** attempt)
        except Exception as e:
            logger.error(f"Unexpected error during sync download for {url}: {e}")
            return False # Fail on unexpected errors

    return False # Return False if all attempts failed

async def async_download_thumbnail(
    session: Optional["aiohttp.ClientSession"],
    url: str,
    path: Path,
    semaphore: asyncio.Semaphore
) -> bool:
    """
    Asynchronous download of thumbnails using aiohttp.
    Utilizes a semaphore to control concurrency.
    """
    if not ASYNC_AVAILABLE or not session:
        logger.debug("Async download skipped: aiohttp not available or session missing.")
        return False

    if not url or not urlparse(url).scheme:
        logger.debug(f"Skipping async download: Invalid URL '{url}'")
        return False

    async with semaphore: # Acquire a permit from the semaphore
        try:
            async with session.get(url, timeout=30) as response: # Use a reasonable timeout
                if response.status != 200:
                    logger.debug(f"Async download failed for {url}: Status {response.status}")
                    return False

                content_type = response.headers.get("content-type", "").lower()
                if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                    logger.debug(f"Async download failed for {url}: Unsupported content type '{content_type}'")
                    return False

                content = await response.read()
                # Check content size to prevent issues with empty or excessively large files
                if not content or len(content) > 10 * 1024 * 1024: # 10MB limit
                    logger.debug(f"Async download failed for {url}: Invalid content size ({len(content)} bytes)")
                    return False

                # Write the downloaded content to the file
                with open(path, "wb") as f:
                    f.write(content)

                logger.debug(f"Successfully downloaded thumbnail (async): {path.name}")
                return True

        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.debug(f"Async download failed for {url}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during async download for {url}: {e}")
            return False

# ─── HTML Gallery Generation (Pyrmethus's Masterpiece) ─────────────────────

# Define the structure of the HTML output, using placeholders for dynamic content
HTML_HEAD = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0a0a1a; /* Deep space background */
      --card: #16213e; /* Nebula card background */
      --text: #ffffff; /* Starlight text */
      --muted: #a0a0a0; /* Faint starlight */
      --border: #2a2a3e; /* Cosmic dust border */
      --grad: linear-gradient(135deg, #00d4ff 0%, #ff006e 100%); /* Aurora gradient */
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: 'Inter', system-ui, -apple-system; background: var(--bg); color: var(--text); }}
    .container {{ max-width: 1400px; margin: 2rem auto; padding: 1rem; }}
    header {{ text-align: center; padding: 1.5rem 0; }}
    h1 {{ font-family: "JetBrains Mono", monospace; font-size: 2.5rem; background: var(--grad); -webkit-background-clip: text; color: transparent; margin-bottom: 0.5rem; }}
    .subtitle {{ color: var(--muted); font-size: 1.1rem; }}
    .stats {{ display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; margin-top: 1rem; }}
    .stat {{ background: rgba(22, 33, 62, 0.9); border: 1px solid var(--border); padding: 0.5rem 0.75rem; border-radius: 999px; font-family: monospace; font-size: 0.9rem; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem; padding: 1rem 0; }}
    .card {{ background: rgba(22, 33, 62, 0.95); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; display: flex; flex-direction: column; transition: transform 0.2s ease-out, box-shadow 0.2s ease-out; }}
    .card:hover {{ transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.3); }}
    .thumb {{ position: relative; width: 100%; height: 180px; overflow: hidden; background: #111; display: flex; align-items: center; justify-content: center; }}
    .thumb img {{ width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s ease; }}
    .card:hover .thumb img {{ transform: scale(1.05); }}
    .body {{ padding: 12px 14px 14px; display: flex; flex-direction: column; flex: 1; }}
    .title {{ font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; line-height: 1.4; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 0.5rem; font-size: 0.85rem; color: var(--muted); margin-top: auto; padding-top: 1rem; border-top: 1px solid var(--border); }}
    .meta .item {{ background: rgba(0, 212, 255, 0.15); color: #00d4ff; padding: 0.25rem 0.6rem; border-radius: 12px; font-family: 'JetBrains Mono', monospace; font-weight: 500; white-space: nowrap; }}
    .link {{ text-decoration: none; color: inherit; transition: color 0.2s ease; }}
    .link:hover {{ color: #00d4ff; }}
    .error-placeholder {{ background: var(--card); display: flex; align-items: center; justify-content: center; color: var(--muted); font-size: 2rem; width: 100%; height: 100%; }}
    .loading-placeholder {{ font-size: 1.5rem; color: var(--muted); }}
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>{query} • {engine}</h1>
    <div class="subtitle">Displaying {count} results from the digital ether</div>
    <div class="stats">
      <div class="stat">⏱ {timestamp}</div>
    </div>
  </header>
  <section class="grid">
"""

HTML_TAIL = """  </section>
</div>
<script>
    // Observer for lazy loading images
    document.addEventListener('DOMContentLoaded', function() {
        const images = document.querySelectorAll('img[data-src]');
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src; // Load the actual image
                    img.removeAttribute('data-src'); // Clean up attribute
                    
                    // Handle image loading errors
                    img.onerror = () => {
                        console.error('Failed to load image:', img.dataset.src);
                        // Replace with a dedicated error placeholder SVG
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'error-placeholder';
                        errorDiv.textContent = '❌'; // Simple error icon
                        img.parentElement.replaceChild(errorDiv, img);
                    };
                    
                    // Optional: Add a class for smooth transition after loading
                    img.onload = () => {
                        img.classList.add('loaded');
                    };
                    
                    observer.unobserve(img); // Stop observing once loaded or failed
                }
            });
        }, { threshold: 0.1 }); // Trigger when 10% of the image is visible

        images.forEach(img => imageObserver.observe(img));
    });
</script>
</body>
</html>"""

# ─── Engine Definitions (The Grimoire of Web Sources) ──────────────────────
# This dictionary holds the configurations for each supported search engine.
# Each entry specifies selectors and parameters needed to scrape video data.
ENGINE_MAP: Dict[str, Dict[str, Any]] = {
    # Pexels: A source for free stock photos and videos.
    "pexels": {
        "url": "https://www.pexels.com",
        "search_path": "/search/videos/{query}/",
        "page_param": "page",
        "requires_js": False, # Does not require JavaScript rendering
        "video_item_selector": "article[data-testid='video-card']",
        "link_selector": 'a[data-testid="video-card-link"], a.video-link',
        "title_selector": 'img[data-testid="video-card-img"]',
        "title_attribute": "alt", # Title is often in the 'alt' attribute of the image
        "img_selector": 'img[data-testid="video-card-img"], img.video-thumbnail',
        "time_selector": "", # Pexels doesn't prominently display duration in card view
        "meta_selector": "", # Pexels doesn't prominently display views in card view
        "channel_name_selector": "", # Pexels doesn't prominently display channel name in card view
        "channel_link_selector": "",
        # Fallback selectors for robustness if primary ones fail
        "fallback_selectors": {
            "title": ["img[alt]", ".video-title", "h3", "a[title]"],
            "img": ["img[data-src]", "img[src]", "img[data-lazy]"],
            "link": ["a[href*='/video/']", "a.video-link"]
        }
    },

    # Dailymotion: A popular video-sharing platform.
    "dailymotion": {
        "url": "https://www.dailymotion.com",
        "search_path": "/search/{query}/videos",
        "page_param": "page",
        "requires_js": False,
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

    # Xhamster: Adult content platform (requires --allow-adult flag).
    "xhamster": {
        "url": "https://xhamster.com",
        "search_path": "/search/{query}",
        "page_param": "page",
        "requires_js": True, # Often requires JS for dynamic loading
        "video_item_selector": "div.thumb-list__item.video-thumb",
        "link_selector": "a.video-thumb__image-container[data-role='thumb-link']",
        "title_selector": "a.video-thumb-info__name[data-role='thumb-link']",
        "img_selector": "img.thumb-image-container__image[data-role='thumb-preview-img']",
        "time_selector": "",
        "meta_selector": "",
        "channel_name_selector": "",
        "channel_link_selector": "",
        "fallback_selectors": {
            "title": ["a[title]"],
            "img": ["img[data-src]", "img[src]"],
            "link": ["a[href*='/videos/']"]
        }
    },

    # PornHub: Another adult content platform (requires --allow-adult flag).
    "pornhub": {
        "url": "https://www.pornhub.com",
        "search_path": "/video/search?search={query}",
        "page_param": "page",
        "requires_js": False, # Generally scrapes well without JS
        "video_item_selector": "li.pcVideoListItem, .video-item, div.videoblock",
        "link_selector": "a.previewVideo, a.thumb, .video-link, .videoblock__link",
        "title_selector": "span.title, .title",
        "img_selector": "img[src], img[data-src]", # Handles both static and lazy-loaded images
        "time_selector": "",
        "meta_selector": "",
        "channel_name_selector": "",
        "channel_link_selector": "",
        "fallback_selectors": {
            "title": ["span.title", "a[title]", ".video-title"],
            "img": ["img[data-src]", "img[src]", "img[data-original]"],
            "link": ["a[href*='/video/']"]
        }
    },

    # Redtube: Adult content platform (requires --allow-adult flag).
    "redtube": {
        "url": "https://www.redtube.com",
        "search_path": "/?search={query}",
        "page_param": "page",
        "requires_js": False, # Generally scrapes well without JS
        "video_item_selector": "li.video-item, div.video-block",
        "link_selector": "a.video-link, .video-thumb",
        "title_selector": "span.video-title, .title",
        "img_selector": "img[data-src], img[src]",
        "time_selector": "span.duration",
        "meta_selector": "span.views",
        "channel_name_selector": "span.channel",
        "channel_link_selector": "a.channel-link",
        "fallback_selectors": {
            "title": ["span.video-title", "a[title]", ".title"],
            "img": ["img[data-src]", "img[src]", "img[data-thumb]"],
            "link": ["a[href*='/video/']"]
        }
    }
}

# ─── Data Extraction Incantations ──────────────────────────────────────────

def extract_text_safe(element: BeautifulSoup, selector: str, default: str = "N/A") -> str:
    """Safely extract text from a BeautifulSoup element using a CSS selector."""
    if not selector:
        return default
    try:
        el = element.select_one(selector)
        if el:
            text = el.get_text(strip=True)
            # Return the text if it's not empty, otherwise use the default
            return text if text else default
        return default
    except Exception as e:
        logger.debug(f"Error extracting text with selector '{selector}': {e}")
        return default

def extract_video_items(soup: BeautifulSoup, cfg: Dict[str, Any]) -> List[BeautifulSoup]:
    """
    Extracts individual video item elements from the parsed HTML soup,
    using primary selectors and falling back to alternatives if necessary.
    """
    video_items: List[BeautifulSoup] = []
    # Try primary selectors first
    for selector in cfg.get("video_item_selector", "").split(","):
        sel = selector.strip()
        if not sel: continue
        found_items = soup.select(sel)
        if found_items:
            video_items = found_items
            logger.debug(f"Found video items using primary selector: '{sel}'")
            break # Stop once items are found

    # If no items found, try fallback selectors (e.g., for containers)
    if not video_items and "fallback_selectors" in cfg:
        for selector in cfg["fallback_selectors"].get("container", []) or []:
            sel = selector.strip()
            if not sel: continue
            found_items = soup.select(sel)
            if found_items:
                video_items = found_items
                logger.debug(f"Found video items using fallback container selector: '{sel}'")
                break
    
    if not video_items:
         logger.debug("No video items found using any selectors.")

    return video_items

def extract_video_data_enhanced(item: BeautifulSoup, cfg: Dict[str, Any], base_url: str) -> Optional[Dict[str, Any]]:
    """
    Extracts detailed information (title, link, image URL, etc.) for a single
    video item using the provided engine configuration.
    """
    try:
        title = "Untitled Video"

        # --- Title Extraction ---
        title_el = None
        title_selectors = [cfg.get("title_selector")] + cfg.get("fallback_selectors", {}).get("title", [])
        for sel in title_selectors:
            if sel:
                title_el = item.select_one(sel)
                if title_el:
                    break
        
        if title_el:
            if cfg.get("title_attribute") and title_el.has_attr(cfg["title_attribute"]):
                title = title_el.get(cfg["title_attribute"], "").strip() or title
            else:
                title = title_el.get_text(strip=True) or title
        
        title = html.escape(title[:200]) # Escape HTML and truncate

        # --- Link Extraction ---
        link = "#" # Default to a non-functional link
        link_el = None
        link_selectors = [cfg.get("link_selector")] + cfg.get("fallback_selectors", {}).get("link", [])
        for sel in link_selectors:
            if sel:
                link_el = item.select_one(sel)
                if link_el and link_el.has_attr("href"):
                    href = link_el["href"]
                    if href and href != "#":
                        link = urljoin(base_url, href) # Resolve relative URLs
                        break

        # --- Image URL Extraction ---
        img_url = None
        img_selectors = [cfg.get("img_selector")] + cfg.get("fallback_selectors", {}).get("img", [])
        for sel in img_selectors:
            if sel:
                img_el = item.select_one(sel)
                if img_el:
                    # Prioritize common attributes for image sources
                    for attr in ["data-src", "src", "data-lazy", "data-original", "data-thumb"]:
                        if img_el.has_attr(attr):
                            img_val = img_el[attr]
                            # Ensure it's a valid URL and not a data URI itself
                            if img_val and not img_val.startswith("data:"):
                                img_url = urljoin(base_url, img_val)
                                break
                    if img_url:
                        break

        # --- Metadata Extraction (Duration, Channel, Views) ---
        duration = extract_text_safe(item, cfg.get("time_selector", ""), "N/A")
        views = extract_text_safe(item, cfg.get("meta_selector", ""), "N/A")
        channel_name = extract_text_safe(item, cfg.get("channel_name_selector", ""), "N/A")
        
        channel_link = "#"
        channel_link_selector = cfg.get("channel_link_selector")
        if channel_link_selector:
            ch_el = item.select_one(channel_link_selector)
            if ch_el and ch_el.has_attr("href"):
                href = ch_el["href"]
                if href and href != "#":
                    channel_link = urljoin(base_url, href)

        # Construct the data dictionary for the video
        return {
            "title": title,
            "link": link,
            "img_url": img_url,
            "time": duration,
            "channel_name": channel_name,
            "channel_link": channel_link,
            "meta": views, # Generic field for views or other metadata
            "extracted_at": datetime.now().isoformat(),
            "source_engine": cfg.get("url", base_url), # Record the source domain
        }
    except Exception as e:
        logger.debug(f"Failed to extract data for a video item: {e}")
        return None # Return None if extraction fails for an item

def extract_with_selenium(driver: webdriver.Remote, url: str, cfg: Dict[str, Any]) -> List[BeautifulSoup]:
    """
    Utilizes Selenium WebDriver to render JavaScript-heavy pages and extract content.
    This is a fallback for engines that rely heavily on dynamic content loading.
    """
    if not SELENIUM_AVAILABLE:
        logger.warning("Selenium is not available. Cannot process JavaScript-heavy pages.")
        return []
        
    try:
        logger.debug(f"Attempting extraction with Selenium for URL: {url}")
        driver.get(url)
        # A brief pause to allow dynamic content to load. Consider using WebDriverWait for more robustness.
        time.sleep(3) 
        
        # Use BeautifulSoup to parse the rendered page source
        soup = BeautifulSoup(driver.page_source, "html.parser")
        return extract_video_items(soup, cfg)
        
    except Exception as e:
        logger.warning(f"Selenium extraction failed for {url}: {e}")
        return []

@asynccontextmanager
async def aiohttp_session() -> AsyncGenerator[Optional["aiohttp.ClientSession"], None]:
    """
    Provides an asynchronous HTTP client session using aiohttp,
    managing its lifecycle and configuration.
    """
    if not ASYNC_AVAILABLE:
        yield None # Yield None if aiohttp is not installed
        return
        
    # Configure session parameters for resilience and performance
    timeout = aiohttp.ClientTimeout(total=30, connect=10) # Total timeout and connection timeout
    connector = aiohttp.TCPConnector(limit=50, limit_per_host=10) # Connection pooling limits
    
    try:
        # Create the session with realistic headers
        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=REALISTIC_HEADERS, # Use pre-defined realistic headers
            connector=connector,
        ) as session:
            yield session # Provide the session to the context
    except Exception as e:
        logger.error(f"Failed to create aiohttp session: {e}")
        yield None # Yield None on failure

async def build_enhanced_html_async(
    results: Sequence[Dict[str, Any]],
    query: str,
    engine: str,
    thumbs_dir: Path,
    sync_session: requests.Session, # Use the synchronous session for fallback downloads
    workers: int,
) -> Path:
    """
    Constructs an enhanced HTML gallery asynchronously. It handles thumbnail
    downloads (prioritizing async) and embeds them into a visually appealing
    page structure.
    """
    ensure_dir(thumbs_dir) # Ensure the thumbnail directory exists
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ensure_dir(Path(VSEARCH_DIR)) # Ensure the output directory exists
    
    # Create a unique filename for the HTML output
    filename = f"{engine}_{enhanced_slugify(query)}_{timestamp}_{uuid.uuid4().hex[:8]}.html"
    outfile = Path(VSEARCH_DIR) / filename

    # Map to store downloaded thumbnail paths, preventing redundant downloads
    thumb_map: Dict[str, str] = {}
    # Semaphore to limit concurrent thumbnail downloads, preventing overload
    semaphore = asyncio.Semaphore(max(1, workers))

    async def fetch_thumbnail_task(
        idx: int, video: Dict[str, Any]
    ) -> Tuple[int, str]:
        """Task to fetch a single thumbnail, returning its index and path/placeholder."""
        img_url = video.get("img_url")
        
        # Use a placeholder if no image URL is available
        if not img_url:
            return idx, generate_placeholder_svg("📹") # Video camera icon

        # If thumbnail already processed, return the cached path
        if img_url in thumb_map:
            return idx, thumb_map[img_url]

        # Determine a safe filename for the thumbnail
        img_ext = os.path.splitext(urlparse(img_url).path) or ".jpg"
        safe_title = enhanced_slugify(video.get("title", "video"))[:50]
        thumb_filename = f"{safe_title}_{idx}{img_ext}"
        dest_path = thumbs_dir / thumb_filename
        # Relative path for HTML embedding
        rel_path = f"../{THUMBNAILS_DIR.name}/{thumb_filename}".replace("\\", "/")

        try:
            # Check if thumbnail already exists and is valid
            if dest_path.exists() and dest_path.stat().st_size > 0:
                thumb_map[img_url] = rel_path
                logger.debug(f"Using existing thumbnail: {dest_path.name}")
                return idx, rel_path

            # Attempt download using async aiohttp first
            if ASYNC_AVAILABLE:
                async with aiohttp_session() as async_session:
                    if async_session:
                        success = await async_download_thumbnail(async_session, img_url, dest_path, semaphore)
                        if success:
                            thumb_map[img_url] = rel_path
                            return idx, rel_path
            
            # Fallback to synchronous download if async failed or is unavailable
            if robust_download_sync(sync_session, img_url, dest_path):
                thumb_map[img_url] = rel_path
                return idx, rel_path

        except Exception as e:
            logger.debug(f"Error during thumbnail fetch for {img_url}: {e}")

        # If all download attempts fail, use an error placeholder
        error_placeholder = generate_placeholder_svg("❌") # Cross mark icon
        thumb_map[img_url] = error_placeholder
        return idx, error_placeholder

    # Create and gather all thumbnail fetching tasks
    thumbnail_tasks = [
        fetch_thumbnail_task(i, video) for i, video in enumerate(results)
    ]
    # Execute tasks concurrently, collecting results or exceptions
    results_with_thumbs = await asyncio.gather(*thumbnail_tasks, return_exceptions=True)

    # --- Construct the HTML Document ---
    try:
        with open(outfile, "w", encoding="utf-8") as f:
            # Write the HTML head section
            f.write(
                HTML_HEAD.format(
                    title=f"{html.escape(query)} - {engine.title()}",
                    query=html.escape(query),
                    engine=engine.title(),
                    count=len(results),
                    timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
            )

            # Iterate through results and write card HTML for each video
            for video, thumb_result in zip(results, results_with_thumbs):
                thumbnail_path: str
                if isinstance(thumb_result, tuple) and len(thumb_result) == 2:
                    # Successfully processed thumbnail (path or placeholder)
                    thumbnail_path = thumb_result
                else:
                    # Task failed, use a generic error placeholder
                    thumbnail_path = generate_placeholder_svg("❓") # Question mark icon

                # Prepare metadata items for display
                meta_items: List[str] = []
                if video.get("time", "N/A") and video["time"] != "N/A":
                    meta_items.append(f'<span class="item">⏱️ {html.escape(video["time"])}</span>')
                if video.get("channel_name", "N/A") != "N/A":
                    channel_link = video.get("channel_link", "#")
                    if channel_link and channel_link != "#":
                        meta_items.append(
                            f'<span class="item"><a href="{html.escape(channel_link)}" target="_blank" rel="noopener noreferrer">👤 {html.escape(video["channel_name"])}</a></span>'
                        )
                    else:
                        meta_items.append(f'<span class="item">👤 {html.escape(video["channel_name"])}</span>')
                if video.get("meta", "N/A") != "N/A":
                    meta_items.append(f'<span class="item">📊 {html.escape(str(video["meta"]))}</span>')

                # --- Image Tag Generation for Lazy Loading ---
                img_html: str
                if thumbnail_path.startswith("data:image"):
                    # If it's an SVG placeholder (error or no-image), use it directly
                    img_html = f'<img src="{html.escape(thumbnail_path)}" alt="{html.escape(video.get("title",""))}">'
                else:
                    # For actual file paths, use a neutral placeholder in `src`
                    # and the real path in `data-src` for lazy loading.
                    loading_placeholder = generate_placeholder_svg("🎬") # Clapperboard icon
                    img_html = f'<img src="{loading_placeholder}" data-src="{html.escape(thumbnail_path)}" alt="{html.escape(video.get("title",""))}" loading="lazy">'
                # --- End Image Tag Generation ---

                # Write the HTML for the video card
                f.write(f'''
            <div class="card">
              <a class="link" href="{html.escape(video["link"])}" target="_blank" rel="noopener noreferrer">
                <div class="thumb">{img_html}</div>
              </a>
              <div class="body">
                <div class="title">
                  <a class="link" href="{html.escape(video["link"])}" target="_blank" rel="noopener noreferrer">{html.escape(video["title"])}</a>
                </div>
                <div class="meta">{''.join(meta_items)}</div>
              </div>
            </div>
            ''')

            # Write the HTML tail section
            f.write(HTML_TAIL)

        logger.info(f"{NEON['GREEN']}Enhanced HTML gallery saved to:{NEON['RESET']} {NEON['YELLOW']}{outfile}{NEON['RESET']}")
        return outfile
        
    except IOError as e:
        logger.error(f"Failed to write HTML file {outfile}: {e}")
        raise # Re-raise to indicate failure

def generate_json_output(results: Sequence[Dict[str, Any]], query: str, engine: str) -> Path:
    """Generates a JSON file from the search results."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{engine}_{enhanced_slugify(query)}_{timestamp}.json"
    outfile = Path(filename)
    try:
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        logger.info(f"{NEON['GREEN']}JSON output saved to:{NEON['RESET']} {NEON['YELLOW']}{outfile}{NEON['RESET']}")
        return outfile
    except IOError as e:
        logger.error(f"Failed to write JSON file {outfile}: {e}")
        raise

def generate_csv_output(results: Sequence[Dict[str, Any]], query: str, engine: str) -> Path:
    """Generates a CSV file from the search results."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{engine}_{enhanced_slugify(query)}_{timestamp}.csv"
    outfile = Path(filename)
    try:
        with open(outfile, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=results.keys())
            writer.writeheader()
            writer.writerows(results)
        logger.info(f"{NEON['GREEN']}CSV output saved to:{NEON['RESET']} {NEON['YELLOW']}{outfile}{NEON['RESET']}")
        return outfile
    except IOError as e:
        logger.error(f"Failed to write CSV file {outfile}: {e}")
        raise

# ─── The Grand Search Ritual ───────────────────────────────────────────────

def get_search_results(
    session: requests.Session,
    engine: str,
    query: str,
    limit: int,
    page: int,
    delay_range: Tuple[float, float],
    search_type: str = "video",
) -> List[Dict[str, Any]]:
    """
    Performs the web search for video results using the specified engine.
    Handles pagination, delays, and potential JavaScript rendering needs.
    """
    if engine not in ENGINE_MAP:
        logger.error(f"Engine '{engine}' is not supported.")
        return []

    config = ENGINE_MAP[engine]
    base_url = config["url"]
    
    # Check if adult content is allowed for the chosen engine
    if engine in ADULT_ENGINES and not ALLOW_ADULT:
        logger.error(
            f"Accessing adult engine '{engine}' requires the --allow-adult flag. "
            f"Please re-run with the flag enabled if you wish to proceed."
        )
        return []

    # Construct the search URL
    search_path = config["search_path"].format(query=quote_plus(query))
    if config.get("page_param"):
        search_url = urljoin(base_url, f"{search_path}?{config['page_param']}={page}")
    else:
        search_url = urljoin(base_url, search_path)

    logger.info(f"Initiating search on {NEON['YELLOW']}{base_url}{NEON['RESET']} for '{query}' (Page {page})...")

    # Prepare for scraping
    soup: Optional[BeautifulSoup] = None
    last_request_time = None
    
    # Handle JavaScript rendering requirement
    if config.get("requires_js") and SELENIUM_AVAILABLE:
        try:
            # Configure Selenium WebDriver
            chrome_options = ChromeOptions()
            chrome_options.add_argument("--headless") # Run in background
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument(f"user-agent={REALISTIC_HEADERS['User-Agent']}")
            
            # Initialize WebDriver (ensure chromedriver is in PATH or specify executable_path)
            driver = webdriver.Chrome(options=chrome_options)
            
            # Extract items using Selenium
            video_items = extract_with_selenium(driver, search_url, config)
            driver.quit() # Close the browser instance
            
            if not video_items:
                logger.warning(f"No video items extracted via Selenium for {search_url}.")
                return []

            # Extract data from the found items
            extracted_data = [
                extract_video_data_enhanced(item, config, base_url)
                for item in video_items
            ]
            # Filter out any None results (failed extractions)
            return [data for data in extracted_data if data][:limit]

        except Exception as e:
            logger.error(f"Selenium execution failed: {e}")
            return []
            
    # Proceed with standard HTTP request if JS is not required or Selenium is unavailable
    elif not config.get("requires_js") or not SELENIUM_AVAILABLE:
        try:
            # Apply smart delay before the request
            smart_delay_with_jitter(delay_range, last_request_time)
            
            # Make the HTTP GET request
            logger.debug(f"Fetching URL: {search_url}")
            response = session.get(search_url, timeout=session._default_timeout)
            last_request_time = time.time() # Record time of last request
            
            response.raise_for_status() # Check for HTTP errors
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract video items from the parsed HTML
            video_items = extract_video_items(soup, config)
            if not video_items:
                logger.warning(f"No video items found using selectors for {search_url}.")
                return []

            # Extract detailed data for each video item
            extracted_data = [
                extract_video_data_enhanced(item, config, base_url)
                for item in video_items
            ]
            # Filter out None results (failed extractions) and limit the results
            return [data for data in extracted_data if data][:limit]

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request failed for {search_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"An error occurred during scraping: {e}")
            return []
    else:
        logger.error("JavaScript rendering is required, but Selenium is not available.")
        return []


# ─── Main Execution Orchestration ──────────────────────────────────────────
def main():
    """The main function to parse arguments and orchestrate the search process."""
    parser = argparse.ArgumentParser(
        description="Pyrmethus's Video Search: A mystical tool for discovering web videos.",
        epilog=(
            "Example invocations:\n"
            f"  {NEON['GREEN']}python3 {sys.argv} \"cats in space\"{NEON['RESET']}\n"
            f"  {NEON['GREEN']}python3 {sys.argv} \"ocean waves\" -e pexels -l 50 -o json{NEON['RESET']}\n"
            f"  {NEON['GREEN']}python3 {sys.argv} \"daily news\" -e dailymotion --no-async --no-open{NEON['RESET']}\n"
            f"  {NEON['YELLOW']}python3 {sys.argv} \"anime clips\" -e xhamster --allow-adult{NEON['RESET']}"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter # Preserve formatting in epilog
    )
    parser.add_argument("query", type=str, help="The search query for videos.")
    parser.add_argument(
        "-e", "--engine", type=str, default=DEFAULT_ENGINE,
        choices=list(ENGINE_MAP.keys()),
        help=f"The search engine to consult (default: {DEFAULT_ENGINE})."
    )
    parser.add_argument(
        "-l", "--limit", type=int, default=DEFAULT_LIMIT,
        help=f"Maximum number of video results to retrieve (default: {DEFAULT_LIMIT})."
    )
    parser.add_argument(
        "-p", "--page", type=int, default=DEFAULT_PAGE,
        help=f"Starting page number for the search (default: {DEFAULT_PAGE})."
    )
    parser.add_argument(
        "-o", "--output-format", type=str, default=DEFAULT_FORMAT,
        choices=["html", "json", "csv"],
        help=f"Format for the output results (default: {DEFAULT_FORMAT})."
    )
    parser.add_argument(
        "--type", type=str, default="video",
        choices=["video", "gif"],
        help="Type of content to search for (video or gif)."
    )
    parser.add_argument(
        "-x", "--proxy", type=str,
        help="Proxy server to use for network requests (e.g., http://user:pass@host:port)."
    )
    parser.add_argument(
        "-w", "--workers", type=int, default=DEFAULT_WORKERS,
        help=f"Number of concurrent workers for thumbnail downloads (default: {DEFAULT_WORKERS})."
    )
    parser.add_argument(
        "--no-async", action="store_true",
        help="Disable asynchronous thumbnail downloading and force synchronous mode."
    )
    parser.add_argument(
        "--no-open", action="store_true",
        help="Prevent the HTML result from opening automatically in a web browser."
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable verbose logging for detailed debugging."
    )
    parser.add_argument(
        "--allow-adult", action="store_true",
        help="Permit the use of adult content search engines. Use responsibly."
    )
    args = parser.parse_args()

    # Update global flag if --allow-adult is used
    global ALLOW_ADULT
    if args.allow_adult:
        ALLOW_ADULT = True

    # Adjust logging level if verbose mode is enabled
    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Register a signal handler for graceful termination (Ctrl+C)
    def signal_handler(sig, frame):
        print(f"\n{NEON['YELLOW']}* Interruption detected. Halting operations gracefully...{NEON['RESET']}")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Forge the primary HTTP session
        ether_session = build_enhanced_session(proxy=args.proxy)

        print(f"{NEON['CYAN']}{Style.BRIGHT}Pyrmethus awakens! Channeling search for '{args.query}' via {args.engine}...{NEON['RESET']}")
        
        # Fetch the search results
        results = get_search_results(
            session=ether_session,
            engine=args.engine,
            query=args.query,
            limit=args.limit,
            page=args.page,
            delay_range=DEFAULT_DELAY,
            search_type=args.type,
        )

        # Process the results based on the requested output format
        if not results:
            print(f"{NEON['RED']}Alas, no videos were found for '{args.query}' on {args.engine}.{NEON['RESET']}")
            sys.exit(1)

        print(f"{NEON['GREEN']}Successfully conjured {len(results)} video artifacts.{NEON['RESET']}")

        if args.output_format == "json":
            generate_json_output(results, args.query, args.engine)
        elif args.output_format == "csv":
            generate_csv_output(results, args.query, args.engine)
        else:
            # Generate and save the HTML gallery
            output_file: Path
            if ASYNC_AVAILABLE and not args.no_async:
                # Use asyncio to run the asynchronous HTML builder
                output_file = asyncio.run(
                    build_enhanced_html_async(
                        results=results,
                        query=args.query,
                        engine=args.engine,
                        thumbs_dir=Path(THUMBNAILS_DIR),
                        sync_session=ether_session, # Pass the sync session for fallback
                        workers=args.workers,
                    )
                )
            else:
                # If async is disabled or unavailable, run with a single worker
                logger.info("Running HTML generation in synchronous mode (or async unavailable).")
                output_file = asyncio.run(
                    build_enhanced_html_async(
                        results=results,
                        query=args.query,
                        engine=args.engine,
                        thumbs_dir=Path(THUMBNAILS_DIR),
                        sync_session=ether_session,
                        workers=1, # Force single worker for non-async behavior
                    )
                )

            # Optionally open the generated HTML file in the default browser
            if not args.no_open and output_file.exists():
                try:
                    # Ensure the path is absolute for the webbrowser module
                    abs_path = os.path.abspath(output_file)
                    webbrowser.open(f"file://{abs_path}")
                    logger.info(f"Opening gallery in your browser: {abs_path}")
                except Exception as e:
                    print(f"{NEON['YELLOW']}Could not automatically open the browser: {e}{NEON['RESET']}")

    except Exception as e:
        # Catch any unexpected errors during the main execution
        logger.critical(f"An unforeseen critical error occurred: {e}", exc_info=True)
        sys.exit(1)

# --- Entry Point of the Spell ---
if __name__ == "__main__":
    main()
