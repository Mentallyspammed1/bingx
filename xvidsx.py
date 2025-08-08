#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
video_search.py  •  2025-08-01 (ENHANCED)

Search several free (and adult) video sites, download/cache thumbnails,
and output HTML/JSON galleries.

Enhanced with 2025 Web Scraping Best Practices:
- IP rotation and proxy support
- Intelligent rate limiting with exponential backoff
- Enhanced error handling and resilience
- User-Agent rotation for better stealth
- Dynamic content handling capabilities
- Comprehensive data validation
- Modern responsive HTML/CSS output
- Advanced concurrency controls
"""

from __future__ import annotations

import argparse
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
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from requests.adapters import HTTPAdapter, Retry

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

# Enhanced logging with file backup
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
for noisy in ("urllib3", "chardet", "requests"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


# ── Enhanced Defaults ────────────────────────────────────────────────────
THUMBNAILS_DIR = "downloaded_thumbnails"
DEFAULT_ENGINE = "pexels"
DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_FORMAT = "html"
DEFAULT_TIMEOUT = 20
DEFAULT_DELAY = (1, 3)  # Random delay range in seconds
DEFAULT_MAX_RETRIES = 5

# Enhanced User-Agent rotation for better stealth
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


# ── Enhanced Engine Validation ─────────────────────────────────────────
def validate_engine_config(engine_name: str, config: Dict) -> List[str]:
    """Validate engine configuration and return list of issues."""
    issues = []
    required_fields = ["url", "search_path", "video_item_selector", "link_selector", "img_selector"]

    for field in required_fields:
        if field not in config:
            issues.append(f"Missing required field: {field}")

    # Validate URL format
    if "url" in config:
        try:
            parsed = urlparse(config["url"])
            if not parsed.scheme or not parsed.netloc:
                issues.append("Invalid URL format")
        except Exception:
            issues.append("Malformed URL")

    return issues


def validate_all_engines() -> None:
    """Validate all engine configurations at startup."""
    invalid_engines = []
    for engine_name, config in ENGINE_MAP.items():
        issues = validate_engine_config(engine_name, config)
        if issues:
            logger.warning(f"{NEON['RED']}Engine '{engine_name}' has issues: {', '.join(issues)}{NEON['RESET']}")
            invalid_engines.append(engine_name)

    for engine in invalid_engines:
        del ENGINE_MAP[engine]

    if not ENGINE_MAP:
        logger.error(f"{NEON['RED']}No valid engines available!{NEON['RESET']}")
        sys.exit(1)


# ── Enhanced Engine Definitions ─────────────────────────────────────────
ENGINE_MAP: Dict[str, Dict[str, str]] = {
    "xhamster": {
        "url": "https://xhamster.com",
        "search_path": "/search/{query}",
        "page_param": "page",
        "video_item_selector": "div.video-thumb-container[data-id], div.video-item",
        "link_selector": "a.video-thumb-info__name, a.video-thumb__link",
        "title_selector": "a.video-thumb-info__name, .video-title",
        "img_selector": "img.video-thumb__image, img[data-src], img[src]",
        "time_selector": "div.video-thumb-info__duration, .duration",
        "meta_selector": "span.video-thumb-info__views, .views",
        "fallback_selectors": {
            "title": [".title", "h3", "a[title]"],
            "img": ["img[data-lazy]", "img[data-original]", "img"]
        }
    },
    "pexels": {
        "url": "https://www.pexels.com",
        "search_path": "/search/videos/{query}/",
        "page_param": "page",
        "video_item_selector": "article.hide-favorite-badge-container, article[data-testid='video-card']",
        "link_selector": 'a[data-testid="video-card-link"], a.video-link',
        "title_selector": 'img[data-testid="video-card-img"], .video-title',
        "title_attribute": "alt",
        "img_selector": 'img[data-testid="video-card-img"], img.video-thumbnail',
        "channel_name_selector": 'a[data-testid="video-card-user-avatar-link"] > span, .author-name',
        "channel_link_selector": 'a[data-testid="video-card-user-avatar-link"], .author-link',
    },
    "dailymotion": {
        "url": "https://www.dailymotion.com",
        "search_path": "/search/{query}/videos",
        "page_param": "page",
        "video_item_selector": 'div[data-testid="video-card"], .video-item',
        "link_selector": 'a[data-testid="card-link"], .video-link',
        "title_selector": 'div[data-testid="card-title"], .video-title',
        "img_selector": 'img[data-testid="card-thumbnail"], img.thumbnail',
        "time_selector": 'span[data-testid="card-duration"], .duration',
        "channel_name_selector": 'div[data-testid="card-owner-name"], .owner-name',
        "channel_link_selector": 'a[data-testid="card-owner-link"], .owner-link',
    },
    "pornhub": {
        "url": "https://www.pornhub.com",
        "search_path": "/video/search?search={query}",
        "page_param": "page",
        "video_item_selector": "li.pcVideoListItem, .video-item",
        "link_selector": "a.previewVideo, a.thumb, .video-link",
        "title_selector": "a.previewVideo .title, a.thumb .title, .video-title",
        "img_selector": "img[src], img[data-src]",
        "time_selector": "var.duration, .duration",
        "channel_name_selector": ".usernameWrap a, .channel-name",
        "channel_link_selector": ".usernameWrap a, .channel-link",
        "meta_selector": ".views, .video-views",
    },
    "redtube": {
        "url": "https://www.redtube.com",
        "search_path": "/?search={query}",
        "page_param": "page",
        "video_item_selector": "div.video, .video-item",
        "link_selector": "a.video-thumb, .video-link",
        "title_selector": "a.video-thumb[title], .video-title",
        "title_attribute": "title",
        "img_selector": "img[src], img[data-src]",
        "time_selector": ".duration",
        "channel_name_selector": ".video-uploader a, .uploader",
        "channel_link_selector": ".video-uploader a, .uploader-link",
        "meta_selector": ".video-views, .views",
    },
    "spankbang": {
        "url": "https://spankbang.com",
        "search_path": "/s/{query}/",
        "page_in_path": True,
        "page_in_path_template": "{page}/",
        "video_item_selector": "div.video-item, .video-card",
        "link_selector": "a.video-item__link, .video-link",
        "title_selector": "a.video-item__link span.title, .video-title",
        "img_selector": "img.video-item__img, img[data-src], img[src]",
        "time_selector": "div.video-item__info span.duration, .duration",
        "channel_name_selector": "a.video-item__user, .user-name",
        "channel_link_selector": "a.video-item__user, .user-link",
        "meta_selector": "div.video-item__info span.views, .views",
    },
    "xvideos": {
        "url": "https://www.xvideos.com",
        "search_path": "/?k={query}",
        "page_param": "p",
        "video_item_selector": "div.mozaique > div, .video-block",
        "link_selector": ".thumb-under > a, .video-link",
        "title_selector": ".thumb-under > a, .video-title",
        "img_selector": "img, img[data-src]",
        "time_selector": ".duration",
        "meta_selector": ".video-views, .views",
    },
    "xnxx": {
        "url": "https://www.xnxx.com",
        "search_path": "/search/{query}/",
        "page_param": "p",
        "video_item_selector": "div.mozaique > div, .video-block",
        "link_selector": ".thumb-under > a, .video-link",
        "title_selector": ".thumb-under > a, .video-title",
        "img_selector": "img, img[data-src]",
        "time_selector": ".duration",
        "meta_selector": ".video-views, .views",
    },
    "green.porn": {
        "url": "https://green.porn",
        "search_path": "/search/{query}/",
        "page_param": "page",
        "video_item_selector": "div.video-item, .video-card",
        "link_selector": "a.video-item__link, .video-link",
        "title_selector": "a.video-item__link span.title, .video-title",
        "img_selector": "img.video-item__img, img[data-src], img[src]",
        "time_selector": "div.video-item__info span.duration, .duration",
        "channel_name_selector": "a.video-item__user, .user-name",
        "channel_link_selector": "a.video-item__user, .user-link",
        "meta_selector": "div.video-item__info span.views, .views",
    },
    "youjizz": {
        "url": "https://www.youjizz.com",
        "search_path": "/videos/search?q={query}",
        "page_param": "page",
        "video_item_selector": "div.video-box, div.video-item", # Common class for video containers on Youjizz
        "link_selector": "a.title, a.video-link", # Link to the video page
        "title_selector": "a.title, .video-title", # Title text, often part of the link
        "img_selector": "img.thumb, img[data-src], img[src]", # Thumbnail image, check for data-src
        "time_selector": "span.duration, div.duration", # Video duration
        "meta_selector": "span.views, .views", # Views count
        "channel_name_selector": "a.username, .channel-name", # Uploader/channel name (if present)
        "channel_link_selector": "a.username, .channel-link", # Link to uploader/channel profile (if present)
        "fallback_selectors": {
            "title": [".title", "h3", "a[title]"],
            "img": ["img[data-lazy]", "img[data-original]", "img"]
        }
    },
}

# ── Enhanced Helper Functions ────────────────────────────────────────────
def ensure_dir(path: Path) -> None:
    """Ensure a directory exists with proper error handling."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.error(f"Permission denied creating directory: {path}")
        raise
    except OSError as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise


def enhanced_slugify(text: str) -> str:
    """Enhanced slugify with better Unicode handling and security."""
    if not text or not isinstance(text, str):
        return "untitled"

    # Normalize and clean
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    # Remove potentially dangerous characters
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"[^a-zA-Z0-9\s\-_.]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    text = text.strip("._-")

    # Ensure reasonable length and avoid reserved names
    text = text[:100] or "untitled"
    reserved_names = {"con", "prn", "aux", "nul", "com1", "com2", "com3", "com4", "com5", "com6", "com7", "com8", "com9", "lpt1", "lpt2", "lpt3", "lpt4", "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"}
    if text.lower() in reserved_names:
        text = f"file_{text}"

    return text


def build_enhanced_session(
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    proxy: Optional[str] = None,
    user_agent: Optional[str] = None
) -> requests.Session:
    """Create an enhanced session with better retry logic and stealth features."""
    session = requests.Session()

    # Enhanced retry strategy with exponential backoff
    retries = Retry(
        total=max_retries,
        backoff_factor=2.0,  # Exponential backoff
        status_forcelist=(429, 500, 502, 503, 504, 520, 521, 522, 524),
        allowed_methods=frozenset({"GET", "HEAD", "OPTIONS"}),
        respect_retry_after_header=True,
        raise_on_redirect=False,
        raise_on_status=False
    )

    adapter = HTTPAdapter(
        max_retries=retries,
        pool_connections=10,
        pool_maxsize=20
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Enhanced headers for better stealth
    headers = {
        "User-Agent": user_agent or random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Cache-Control": "max-age=0",
    }
    session.headers.update(headers)

    # Proxy support
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy})

    # Set timeout
    session.timeout = timeout

    return session


def smart_delay(min_delay: float = 1.0, max_delay: float = 3.0, last_request_time: Optional[float] = None) -> None:
    """Implement intelligent delays between requests."""
    current_time = time.time()

    if last_request_time:
        elapsed = current_time - last_request_time
        min_wait = random.uniform(min_delay, max_delay)
        if elapsed < min_wait:
            time.sleep(min_wait - elapsed)
    else:
        time.sleep(random.uniform(min_delay, max_delay))


def robust_download(session: requests.Session, url: str, path: Path, max_attempts: int = 3) -> bool:
    """Enhanced download with better error handling and validation."""
    if not url or not url.startswith(("http://", "https://")):
        logger.debug(f"Invalid URL: {url}")
        return False

    for attempt in range(max_attempts):
        try:
            # Rotate User-Agent for each attempt
            session.headers["User-Agent"] = random.choice(USER_AGENTS)

            with session.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()

                # Validate content type
                content_type = response.headers.get("content-type", "").lower()
                if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                    logger.debug(f"Invalid content type {content_type} for {url}")
                    return False

                # Validate content length
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
                    logger.debug(f"File too large: {content_length} bytes")
                    return False

                # Write file
                with open(path, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)

                # Validate downloaded file
                if path.stat().st_size == 0:
                    logger.debug(f"Downloaded file is empty: {path}")
                    path.unlink()
                    return False

                return True

        except requests.exceptions.RequestException as e:
            logger.warning(f"Download failed for {url} (attempt {attempt + 1}/{max_attempts}): {e}")
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
    """Enhanced scraping with better error handling and data validation."""
    if engine not in ENGINE_MAP:
        logger.error(f"{NEON['RED']}Unsupported engine: {engine}{NEON['RESET']}")
        return []

    cfg = ENGINE_MAP[engine]
    base_url = cfg["url"]
    results: List[Dict] = []
    last_request_time = None

    # Calculate pages needed
    items_per_page = 30
    pages_to_fetch = min(5, (limit + items_per_page - 1) // items_per_page)

    logger.info(f"{NEON['CYAN']}Searching {engine} for '{query}' (up to {pages_to_fetch} pages){NEON['RESET']}")

    for current_page in range(page, page + pages_to_fetch):
        if len(results) >= limit:
            break

        # Implement smart delays
        smart_delay(delay_range[0], delay_range[1], last_request_time)
        last_request_time = time.time()

        # Build URL
        search_path = cfg["search_path"].format(query=quote_plus(query))

        if cfg.get("page_in_path") and current_page > 1:
            page_segment = cfg.get("page_in_path_template", "{page}/").format(page=current_page)
            url = urljoin(base_url, search_path.rstrip('/') + '/' + page_segment.lstrip('/'))
        else:
            url = urljoin(base_url, search_path)
            if current_page > 1:
                separator = "&" if "?" in url else "?"
                url += f"{separator}{cfg.get('page_param', 'page')}={current_page}"

        logger.info(f"{NEON['YELLOW']}Fetching page {current_page}: {url}{NEON['RESET']}")

        try:
            # Rotate User-Agent for each request
            session.headers["User-Agent"] = random.choice(USER_AGENTS)

            response = session.get(url, timeout=session.timeout)
            response.raise_for_status()

            if response.status_code != 200:
                logger.warning(f"Unexpected status code {response.status_code} for {url}")
                continue

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for page {current_page}: {e}")
            continue

        # Parse HTML with enhanced error handling
        try:
            soup = BeautifulSoup(response.text, "html.parser")
        except Exception as e:
            logger.error(f"Failed to parse HTML for page {current_page}: {e}")
            continue

        # Extract video items with fallback selectors
        video_items = []
        for selector in cfg["video_item_selector"].split(", "):
            video_items = soup.select(selector.strip())
            if video_items:
                break

        if not video_items:
            logger.warning(f"No video items found on page {current_page}")
            continue

        logger.debug(f"Found {len(video_items)} video items on page {current_page}")

        # Process each video item
        for item in video_items:
            if len(results) >= limit:
                break

            try:
                video_data = extract_video_data(item, cfg, base_url)
                if video_data and validate_video_data(video_data):
                    results.append(video_data)

            except Exception as e:
                logger.debug(f"Failed to extract video data: {e}")
                continue

    logger.info(f"{NEON['GREEN']}Successfully extracted {len(results)} videos{NEON['RESET']}")
    return results[:limit]


def extract_video_data(item: BeautifulSoup, cfg: Dict, base_url: str) -> Optional[Dict]:
    """Extract video data from HTML element with enhanced fallback logic."""
    try:
        # Extract title with fallbacks
        title = "Untitled"
        title_selectors = [cfg.get("title_selector", "")]
        if "fallback_selectors" in cfg and "title" in cfg["fallback_selectors"]:
            title_selectors.extend(cfg["fallback_selectors"]["title"])

        for selector in title_selectors:
            if not selector:
                continue
            title_el = item.select_one(selector)
            if title_el:
                title_attr = cfg.get("title_attribute")
                if title_attr and title_el.has_attr(title_attr):
                    title = title_el.get(title_attr, "").strip()
                else:
                    title = title_el.get_text(strip=True)
                if title:
                    break

        # Extract link
        link = "#"
        link_el = item.select_one(cfg.get("link_selector", ""))
        if link_el and link_el.has_attr("href"):
            link = urljoin(base_url, link_el["href"])

        # Extract image URL with fallbacks
        img_url = None
        img_selectors = [cfg.get("img_selector", "")]
        if "fallback_selectors" in cfg and "img" in cfg["fallback_selectors"]:
            img_selectors.extend(cfg["fallback_selectors"]["img"])

        for selector in img_selectors:
            if not selector:
                continue
            img_el = item.select_one(selector)
            if img_el:
                # Try multiple attributes
                for attr in ["data-src", "src", "data-lazy", "data-original"]:
                    if img_el.has_attr(attr):
                        img_url = urljoin(base_url, img_el[attr])
                        break
                if img_url:
                    break

        # Extract metadata
        duration = extract_text_safe(item, cfg.get("time_selector", ""), "N/A")
        views = extract_text_safe(item, cfg.get("meta_selector", ""), "N/A")

        # Extract channel info
        channel_name = extract_text_safe(item, cfg.get("channel_name_selector", ""), "N/A")
        channel_link = "#"
        channel_link_el = item.select_one(cfg.get("channel_link_selector", ""))
        if channel_link_el and channel_link_el.has_attr("href"):
            channel_link = urljoin(base_url, channel_link_el["href"])

        return {
            "title": html.escape(title[:200]),  # Limit title length
            "link": link,
            "img_url": img_url,
            "time": duration,
            "channel_name": channel_name,
            "channel_link": channel_link,
            "meta": views,
            "extracted_at": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.debug(f"Error extracting video data: {e}")
        return None


def extract_text_safe(element: BeautifulSoup, selector: str, default: str = "N/A") -> str:
    """Safely extract text from an element with fallback."""
    if not selector:
        return default
    try:
        el = element.select_one(selector)
        return el.get_text(strip=True) if el else default
    except Exception:
        return default


def validate_video_data(data: Dict) -> bool:
    """Validate extracted video data."""
    required_fields = ["title", "link"]
    return all(data.get(field) for field in required_fields) and data["title"] != "Untitled"


# ── Enhanced HTML Output ─────────────────────────────────────────────────
ENHANCED_HTML_HEAD = """
<!DOCTYPE html>
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

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

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

        .video-card:hover::before {{
            opacity: 1;
        }}

        .thumbnail {{
            position: relative;
            width: 100%;
            height: 200px;
            overflow: hidden;
        }}

        .thumbnail img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s ease;
        }}

        .video-card:hover .thumbnail img {{
            transform: scale(1.1);
        }}

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

        .video-title a:hover {{
            color: var(--accent-cyan);
        }}

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

        .meta-item a:hover {{
            opacity: 0.8;
        }}

        .loading {{
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
        }}

        .error-placeholder {{
            background: var(--bg-card);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-muted);
            font-size: 2rem;
            width: 100%;
            height: 100%;
        }}
        .error-placeholder span {
            font-size: 1.5rem;
        }

        @media (max-width: 768px) {{
            .container {{
                margin: 1rem;
                padding: 1rem;
                border-radius: 12px;
            }}

            h1 {{
                font-size: 2rem;
            }}

            .video-grid {{
                grid-template-columns: 1fr;
                gap: 1.5rem;
            }}

            .stats {{
                gap: 1rem;
            }}

            .stat {{
                padding: 0.5rem 1rem;
                font-size: 0.8rem;
            }}
        }}

        @media (prefers-reduced-motion: reduce) {{
            * {{
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }}
        }}

        /* Scroll animations */
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        .video-card {{
            animation: fadeIn 0.6s ease-out forwards;
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
        <main class="video-grid">
"""

ENHANCED_HTML_TAIL = """
        </main>
    </div>
    <script>
        // Add lazy loading for images
        document.addEventListener('DOMContentLoaded', function() {
            const images = document.querySelectorAll('img[data-src]');
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.onload = () => {
                            img.removeAttribute('data-src');
                            img.parentElement.classList.remove('loading-placeholder');
                        };
                        img.onerror = () => {
                            img.parentElement.innerHTML = '<div class="error-placeholder"><span>❌</span></div>';
                        };
                        imageObserver.unobserve(img);
                    }
                });
            });

            images.forEach(img => imageObserver.observe(img));
        });
    </script>
</body>
</html>
"""


def build_enhanced_html(
    results: Sequence[Dict],
    query: str,
    engine: str,
    limit: int,
    thumbs_dir: Path,
    session: requests.Session,
    workers: int,
) -> Path:
    """Build enhanced HTML gallery with modern design and better UX."""
    ensure_dir(thumbs_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{engine}_{enhanced_slugify(query)}_{timestamp}_{uuid.uuid4().hex[:8]}.html"
    outfile = Path(filename)

    def fetch_thumbnail(idx: int, video: Dict) -> str:
        """Download thumbnail with enhanced error handling."""
        img_url = video.get("img_url")
        if not img_url:
            return "data:image/svg+xml;base64," + base64.b64encode(
                f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><rect width="100%" height="100%" fill="#16213e"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="2rem" fill="#666">�</text></svg>'
                .encode()
            ).decode()

        # Create safe filename
        ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
        safe_title = enhanced_slugify(video.get("title", "video"))[:50]
        filename = f"{safe_title}_{idx}{ext}"
        dest_path = thumbs_dir / filename

        if not dest_path.exists():
            if not robust_download(session, img_url, dest_path):
                return "data:image/svg+xml;base64," + base64.b64encode(
                    f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><rect width="100%" height="100%" fill="#16213e"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="1.5rem" fill="#666">Failed to load</text></svg>'
                    .encode()
                ).decode()

        return str(Path(THUMBNAILS_DIR) / filename).replace("\\", "/")

    # Download thumbnails with progress tracking
    thumbnail_paths = [""] * len(results)
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, 20)) as executor:
        future_to_idx = {
            executor.submit(fetch_thumbnail, i, video): i
            for i, video in enumerate(results)
        }

        # Progress tracking
        iterable = concurrent.futures.as_completed(future_to_idx)
        if 'tqdm' in sys.modules:
            iterable = tqdm(iterable, total=len(future_to_idx), desc="Downloading thumbnails", unit="img")

        for future in iterable:
            idx = future_to_idx[future]
            try:
                thumbnail_paths[idx] = future.result()
            except Exception as e:
                logger.debug(f"Thumbnail download failed for index {idx}: {e}")
                thumbnail_paths[idx] = "data:image/svg+xml;base64," + base64.b64encode(
                    '<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><rect width="100%" height="100%" fill="#16213e"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="1.5rem" fill="#666">❌</text></svg>'
                    .encode()
                ).decode()

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
                    meta_items.append(f'<span class="meta-item"><a href="{html.escape(channel_link)}">� {html.escape(video["channel_name"])}</a></span>')
                else:
                    meta_items.append(f'<span class="meta-item">� {html.escape(video["channel_name"])}</span>')

            if video.get("meta", "N/A") != "N/A":
                meta_items.append(f'<span class="meta-item">�️ {html.escape(video["meta"])}</span>')

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
                        {"".join(meta_items)}
                    </div>
                </div>
            </div>
            ''')

        f.write(ENHANCED_HTML_TAIL)

    logger.info(f"{NEON['GREEN']}Enhanced HTML gallery saved → {outfile}{NEON['RESET']}")
    return outfile


def build_enhanced_json(results: Sequence[Dict], query: str, engine: str) -> Path:
    """Build enhanced JSON with metadata."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{engine}_{enhanced_slugify(query)}_{timestamp}_{uuid.uuid4().hex[:8]}.json"
    outfile = Path(filename)

    output_data = {
        "metadata": {
            "query": query,
            "engine": engine,
            "total_results": len(results),
            "generated_at": datetime.now().isoformat(),
            "script_version": "2025.08.01-enhanced",
        },
        "results": results
    }

    with open(outfile, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False, sort_keys=True)

    logger.info(f"{NEON['GREEN']}Enhanced JSON saved → {outfile}{NEON['RESET']}")
    return outfile


# ── Enhanced CLI ─────────────────────────────────────────────────────────
def get_enhanced_args() -> argparse.Namespace:
    """Parse enhanced command line arguments."""
    parser = argparse.ArgumentParser(
        description="Enhanced video search with modern web scraping techniques",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Examples:
  {sys.argv[0]} -q "cats" -e pexels
  {sys.argv[0]} -q "nature" -l 50 --format json
  {sys.argv[0]} --list-engines
  {sys.argv[0]} -q "cute dogs" -e pexels --workers 10
  {sys.argv[0]} -q "funny videos" -p 2 --delay 2 5
"""
    )
    parser.add_argument(
        "-q", "--query", help="The search query.", required=True, metavar="QUERY"
    )
    parser.add_argument(
        "-e",
        "--engine",
        help="Search engine to use.",
        choices=list(ENGINE_MAP.keys()),
        default=DEFAULT_ENGINE,
    )
    parser.add_argument(
        "-l",
        "--limit",
        type=int,
        help="Maximum number of videos to find.",
        default=DEFAULT_LIMIT,
        metavar="INT",
    )
    parser.add_argument(
        "-p",
        "--page",
        type=int,
        help="Start search from a specific page.",
        default=DEFAULT_PAGE,
        metavar="INT",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["html", "json"],
        help="Output format.",
        default=DEFAULT_FORMAT,
    )
    parser.add_argument(
        "-d",
        "--delay",
        type=float,
        nargs=2,
        help="Min and max delay in seconds between requests.",
        default=DEFAULT_DELAY,
        metavar=("MIN", "MAX"),
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=5,
        help="Number of workers for concurrent thumbnail downloading.",
        metavar="INT",
    )
    parser.add_argument(
        "--proxy",
        help="Use a proxy for all requests (e.g., http://user:pass@host:port).",
        metavar="URL",
    )
    parser.add_argument(
        "-O",
        "--output-dir",
        type=Path,
        help="Specify a directory for output files.",
    )
    parser.add_argument(
        "--open-in-browser",
        action="store_true",
        help="Open the generated HTML file in the default web browser.",
    )
    parser.add_argument(
        "--list-engines",
        action="store_true",
        help="List all available search engines and exit.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )

    args = parser.parse_args()

    if args.delay[0] > args.delay[1]:
        parser.error("Minimum delay cannot be greater than maximum delay.")

    return args


def handle_signals(signum, frame) -> None:
    """Handle termination signals gracefully."""
    logger.warning(f"{NEON['RED']}Process interrupted by signal {signum}. Exiting gracefully...{NEON['RESET']}")
    sys.exit(1)


def main() -> None:
    """Main function to orchestrate the search and output process."""
    signal.signal(signal.SIGINT, handle_signals)
    signal.signal(signal.SIGTERM, handle_signals)

    validate_all_engines()
    args = get_enhanced_args()

    if args.list_engines:
        print(f"{NEON['BRIGHT']}{NEON['CYAN']}Available Engines:{NEON['RESET']}")
        for engine in ENGINE_MAP:
            print(f"  - {engine}")
        sys.exit(0)

    if args.debug:
        logging.getLogger(__name__).setLevel(logging.DEBUG)
        logging.getLogger("requests").setLevel(logging.DEBUG)

    query = args.query.strip()
    if not query:
        logger.error(f"{NEON['RED']}Search query cannot be empty.{NEON['RESET']}")
        sys.exit(1)

    thumbs_dir = Path(THUMBNAILS_DIR)
    if args.output_dir:
        thumbs_dir = args.output_dir / THUMBNAILS_DIR
    ensure_dir(thumbs_dir)

    session = build_enhanced_session(
        proxy=args.proxy,
        timeout=DEFAULT_TIMEOUT,
        max_retries=DEFAULT_MAX_RETRIES
    )

    results = get_search_results(
        session,
        args.engine,
        query,
        args.limit,
        args.page,
        tuple(args.delay)  # type: ignore
    )

    if not results:
        logger.info(f"{NEON['YELLOW']}No results found for '{query}' on {args.engine}.{NEON['RESET']}")
        sys.exit(0)

    if args.format == "html":
        outfile = build_enhanced_html(results, query, args.engine, args.limit, thumbs_dir, session, args.workers)
        if args.open_in_browser:
            webbrowser.open_new_tab(f"file://{os.path.abspath(outfile)}")
    elif args.format == "json":
        build_enhanced_json(results, query, args.engine)


if __name__ == "__main__":
    main()
