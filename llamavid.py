#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
video_search.py - Enhanced Video Search Tool (2025 Edition)

Overview:
- Modern Python 3.10+ features (type hints, pathlib, async/await)
- Dual download system: async primary with sync fallback for thumbnails
- Robust error handling and retries
- Progress tracking with tqdm (optional)
- HTML and JSON output options
- Optional Selenium/aiohttp integration for JS-heavy engines
- Adult-content gating via CLI flag
- Improved handling of HTML image sources for lazy loading and placeholders.

Usage remains compatible with your existing CLI surface.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
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

# Optional async libs
try:
    import aiohttp
    ASYNC_AVAILABLE = True
except Exception:
    ASYNC_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False

try:
    from tqdm import tqdm
except Exception:
    def tqdm(iterable, *_, **__):
        return iterable  # type: ignore

# ─── Configuration ─────────────────────────────────────────────────────────

# Initialize color output
colorama_init(autoreset=True)

# Directories
THUMBNAILS_DIR = Path("downloaded_thumbnails")
VSEARCH_DIR = Path("vsearch")

# Defaults
DEFAULT_ENGINE = "pexels"
DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_FORMAT = "html"
DEFAULT_TIMEOUT = 25
DEFAULT_DELAY = (1.5, 4.0)
DEFAULT_MAX_RETRIES = 5
DEFAULT_WORKERS = 12

# Neon palette for logs
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

# Adult engines gating (default: disabled)
ADULT_ENGINES = {"pornhub", "xhamster"}
ALLOW_ADULT = False  # Controlled by --allow-adult

# Realistic user agents
REALISTIC_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15; rv:122.0) "
    "Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# ─── Logging Setup ─────────────────────────────────────────────────────────
class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.engine = getattr(record, "engine", "unknown")
        record.query = getattr(record, "query", "unknown")
        return True

def setup_logging(verbose: bool = False) -> logging.Logger:
    log_handlers: List[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    try:
        log_handlers.append(logging.FileHandler("video_search.log", mode="a"))
    except PermissionError:
        pass

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    fmt = (
        f"{NEON['CYAN']}%(asctime)s{NEON['RESET']} - "
        f"{NEON['MAGENTA']}%(levelname)s{NEON['RESET']} - "
        f"{NEON['GREEN']}%(engine)s{NEON['RESET']} - "
        f"{NEON['GREEN']}%(query)s{NEON['RESET']} - "
        f"{NEON['GREEN']}%(message)s{NEON['RESET']}"
    )
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO,
                        format=fmt, handlers=log_handlers)
    logger.addFilter(ContextFilter())

    # Suppress noisy loggers
    for noisy in ("urllib3", "chardet", "requests", "aiohttp", "selenium"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logger

logger = setup_logging()

# ─── Helper Functions ─────────────────────────────────────────────────────────
def enhanced_slugify(text: str) -> str:
    """Create filesystem-safe slugs from text."""
    if not text or not isinstance(text, str):
        return "untitled"

    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)        # strip dangerous chars
    text = re.sub(r"[^a-zA-Z0-9\s\-_.]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    text = text.strip("._-")

    text = text[:100] or "untitled"
    reserved_names = {
        "con", "prn", "aux", "nul", "com1", "com2", "com3", "com4", "com5",
        "com6", "com7", "com8", "com9", "lpt1", "lpt2", "lpt3", "lpt4",
        "lpt5", "lpt6", "lpt7", "lpt8", "lpt9"
    }
    if text.lower() in reserved_names:
        text = f"file_{text}"

    return text

def ensure_dir(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise

def get_realistic_headers(user_agent: str) -> Dict[str, str]:
    return {
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
    }

# A small pool of realistic headers (rotated for each request/session)
REALISTIC_HEADERS = get_realistic_headers(random.choice(REALISTIC_USER_AGENTS)) # type: ignore

def build_enhanced_session(
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    proxy: Optional[str] = None,
) -> requests.Session:
    """Create a robust HTTP session with retries and realistic headers."""
    session = requests.Session()

    # Retry strategy (handle 429 and common 5xx)
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
        # Fallback for older urllib3 versions
        retries = Retry(
            total=max_retries,
            backoff_factor=0.5,
            backoff_max=4.0,
            status_forcelist=(429, 500, 502, 503, 504),
            method_whitelist=frozenset({"GET", "HEAD", "OPTIONS"}), # type: ignore
            respect_retry_after_header=True,
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
            parsed = urlparse(proxy)
            if parsed.scheme and parsed.netloc:
                session.proxies.update({"http": proxy, "https": proxy})
                logger.info(f"Using proxy: {parsed.netloc}")
            else:
                logger.warning(f"Invalid proxy format: {proxy}")
        except Exception as e:
            logger.warning(f"Failed to set proxy {proxy}: {e}")

    # Attach timeout to session for convenient usage
    setattr(session, "_default_timeout", timeout)
    return session

def smart_delay_with_jitter(
    delay_range: Tuple[float, float],
    last_request_time: Optional[float] = None,
    jitter: float = 0.3
) -> None:
    """Implement intelligent delays with jitter."""
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

# ─── Thumbnail Handling ───────────────────────────────────────────────────
def generate_placeholder_svg(icon: str) -> str:
    """Generate SVG placeholder with proper UTF-8 encoding."""
    svg = (
        f'''<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 100 100">
        <rect width="100%" height="100%" fill="#16213e"/>
        <text x="50" y="55" text-anchor="middle" dominant-baseline="middle" font-family="sans-serif" font-size="40" fill="#666">{html.escape(icon)}</text>
    </svg>'''
    )
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")

def robust_download_sync(session: requests.Session, url: str, path: Path, max_attempts: int = 3) -> bool:
    """Synchronous fallback download with validation."""
    if not url or not urlparse(url).scheme:
        return False

    for attempt in range(max_attempts):
        try:
            session.headers.update({"User-Agent": random.choice(REALISTIC_USER_AGENTS)})
            with session.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()

                content_type = response.headers.get("content-type", "").lower()
                if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                    logger.debug(f"Sync download invalid content type for {url}")
                    return False

                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > 10 * 1024 * 1024:
                    logger.debug(f"Sync download too large for {url}")
                    return False

                with open(path, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)

                if path.stat().st_size == 0:
                    path.unlink(missing_ok=True)
                    logger.debug(f"Sync download produced empty file for {url}")
                    return False

                return True

        except Exception as e:
            logger.debug(f"Download failed for {url} (attempt {attempt + 1}): {e}")
            if attempt < max_attempts - 1:
                time.sleep(2 ** attempt)

    return False

async def async_download_thumbnail(
    session: "aiohttp.ClientSession",
    url: str,
    path: Path,
    semaphore: asyncio.Semaphore
) -> bool:
    """Async thumbnail download with enhanced error handling."""
    if not ASYNC_AVAILABLE or not session:
        return False

    async with semaphore:
        try:
            async with session.get(url, timeout=30) as response:
                if response.status != 200:
                    logger.debug(f"Async download failed, status {response.status} for {url}")
                    return False

                content_type = response.headers.get("content-type", "").lower()
                if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                    logger.debug(f"Async download failed, invalid content type for {url}")
                    return False

                content = await response.read()
                if len(content) == 0 or len(content) > 10 * 1024 * 1024:
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

def get_thumb_path(video: Dict[str, Any], idx: int, thumbs_dir: Path) -> Tuple[str, Path, str]:
    """Generate a unique, safe path for a thumbnail."""
    img_url = video.get("img_url")
    ext = os.path.splitext(urlparse(img_url or "").path)[1] or ".jpg"
    safe_title = enhanced_slugify(video.get("title", "video"))[:50]
    filename = f"{safe_title}_{idx}_{uuid.uuid4().hex[:4]}{ext}"
    dest_path = thumbs_dir / filename
    # Relative to the generated HTML file (which sits in VSEARCH_DIR)
    rel_path = f"../{THUMBNAILS_DIR.name}/{filename}".replace("\\", "/")
    return img_url, dest_path, rel_path

# ─── HTML Output ──────────────────────────────────────────────────────────
# Simple yet effective HTML head/tail; placeholders filled in at generation time
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
      --bg: #0a0a1a;
      --card: #16213e;
      --text: #ffffff;
      --muted: #a0a0a0;
      --border: #2a2a3e;
      --grad: linear-gradient(135deg, #00d4ff 0%, #ff006e 100%);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: 'Inter', system-ui, -apple-system; background: var(--bg); color: var(--text); }}
    .container {{ max-width: 1400px; margin: 2rem auto; padding: 1rem; }}
    header {{ text-align: center; padding: 1.5rem 0; }}
    h1 {{ font-family: "JetBrains Mono", monospace; font-size: 2rem; background: var(--grad); -webkit-background-clip: text; color: transparent; }}
    .subtitle {{ color: var(--muted); margin-bottom: 1rem; }}
    .stats {{ display: flex; justify-content: center; gap: 1.5rem; flex-wrap: wrap; }}
    .stat {{ background: rgba(22, 33, 62, 0.9); border: 1px solid var(--border); padding: 0.5rem 0.75rem; border-radius: 999px; font-family: monospace; }}
    .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.5rem; padding: 1rem 0; }
    .card { background: rgba(22, 33, 62, 0.95); border: 1px solid var(--border); border-radius: 14px; overflow: hidden; display: flex; flex-direction: column; transition: transform 0.2s ease-out, box-shadow 0.2s ease-out; }
    .card:hover { transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.3); }
    .thumb { position: relative; width: 100%; height: 180px; overflow: hidden; background: #111; }
    .thumb img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s ease; }
    .card:hover .thumb img { transform: scale(1.05); }
    .body { padding: 12px 14px 14px; display: flex; flex-direction: column; flex: 1; }
    .title { font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; line-height: 1.4; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
    .meta { display: flex; flex-wrap: wrap; gap: 0.5rem; font-size: 0.85rem; color: var(--muted); margin-top: auto; padding-top: 1rem; border-top: 1px solid var(--border); }
    .meta .item { background: rgba(0, 212, 255, 0.15); color: #00d4ff; padding: 0.25rem 0.6rem; border-radius: 12px; font-family: 'JetBrains Mono', monospace; font-weight: 500; white-space: nowrap; }
    .link { text-decoration: none; color: inherit; }
    .link:hover { color: #00d4ff; }
    .error-placeholder { background: var(--card); display: flex; align-items: center; justify-content: center; color: var(--muted); font-size: 2rem; width: 100%; height: 100%; }
  </style>
</head>
<body>
<div class="container">
  <header>
    <h1>{query} • {engine}</h1>
    <div class="subtitle">Showing {count} results</div>
    <div class="stats">
      <div class="stat">⏱ {timestamp}</div>
    </div>
  </header>
  <section class="grid">
"""

HTML_TAIL = """  </section>
</div>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        const images = document.querySelectorAll('img[data-src]');
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src; // Set the actual image source
                    img.removeAttribute('data-src'); // Remove data-src once loaded
                    img.onload = () => { /* Optional: add a class for smooth transition */ };
                    img.onerror = () => {
                        // On error, replace with a dedicated error placeholder
                        img.remove();
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'error-placeholder';
                        errorDiv.textContent = '❌';
                        img.parentElement.appendChild(errorDiv);
                    };
                    observer.unobserve(img); // Stop observing once loaded or failed
                }
            });
        });
        images.forEach(img => imageObserver.observe(img));
    });
</script>
</body>
</html>"""

# ─── Engine Configurations (subset) ─────────────────
ENGINE_MAP: Dict[str, Dict[str, Any]] = {
    # Pexels
    "pexels": {
        "url": "https://www.pexels.com",
        "search_path": "/search/videos/{query}/",
        "page_param": "page",
        "requires_js": False,
        "video_item_selector": "article[data-testid='video-card']",
        "link_selector": 'a[data-testid="video-card-link"], a.video-link',
        "title_selector": 'img[data-testid="video-card-img"]',
        "title_attribute": "alt",
        "img_selector": 'img[data-testid="video-card-img"], img.video-thumbnail',
        "time_selector": "",
        "meta_selector": "",
        "channel_name_selector": "",
        "channel_link_selector": "",
        "fallback_selectors": {
            "title": ["img[alt]", ".video-title", "h3", "a[title]"],
            "img": ["img[data-src]", "img[src]", "img[data-lazy]"],
            "link": ["a[href*='/video/']", "a.video-link"]
        }
    },

    # Dailymotion
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

    # Xhamster (adult content – gated)
    "xhamster": {
        "url": "https://xhamster.com",
        "search_path": "/search/{query}",
        "page_param": "page",
        "requires_js": True,
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

    # PornHub (adult content – gated)
    "pornhub": {
        "url": "https://www.pornhub.com",
        "search_path": "/video/search?search={query}",
        "page_param": "page",
        "requires_js": False,
        "video_item_selector": "li.pcVideoListItem, .video-item, div.videoblock",
        "link_selector": "a.previewVideo, a.thumb, .video-link, .videoblock__link",
        "title_selector": "span.title, .title",
        "img_selector": "img[src], img[data-src]",
        "time_selector": "",
        "meta_selector": "",
        "channel_name_selector": "",
        "channel_link_selector": "",
        "fallback_selectors": {
            "title": ["span.title", "a[title]", ".video-title"],
            "img": ["img[data-src]", "img[src]", "img[data-original]"],
            "link": ["a[href*='/video/']"]
        }
    }
}

# ─── Helper: extracters and parsers (common for engines) ─────────────────
def extract_text_safe(element, selector: str, default: str = "N/A") -> str:
    if not selector:
        return default
    try:
        el = element.select_one(selector)
        if el:
            text = el.get_text(strip=True)
            return text if text else default
        return default
    except Exception:
        return default

def extract_video_items(soup: BeautifulSoup, cfg: Dict[str, Any]) -> List:
    video_items: List[Any] = []
    for selector in cfg.get("video_item_selector", "").split(","):
        sel = selector.strip()
        if not sel:
            continue
        video_items = soup.select(sel)
        if video_items:
            break
    if not video_items and "fallback_selectors" in cfg:
        for selector in cfg["fallback_selectors"].get("container", []):
            video_items = soup.select(selector)
            if video_items:
                break
    return video_items

def extract_video_data_enhanced(item, cfg: Dict[str, Any], base_url: str) -> Optional[Dict[str, Any]]:
    try:
        title = "Untitled"

        # Title extraction
        title_el = None
        if "title_selector" in cfg and cfg["title_selector"]:
            sel = cfg["title_selector"]
            title_el = item.select_one(sel)
        # Fallbacks
        if not title_el and "fallback_selectors" in cfg:
            for tsel in cfg["fallback_selectors"].get("title", []) or []:
                if not tsel:
                    continue
                title_el = item.select_one(tsel)
                if title_el:
                    break
        if title_el:
            if cfg.get("title_attribute") and title_el.has_attr(cfg["title_attribute"]):
                title = title_el.get(cfg["title_attribute"], "").strip() or title
            else:
                title = title_el.get_text(strip=True) or title

        link = "#"
        link_el = None
        if "link_selector" in cfg and cfg["link_selector"]:
            link_el = item.select_one(cfg["link_selector"])
        if not link_el and "fallback_selectors" in cfg:
            for lsel in cfg["fallback_selectors"].get("link", []) or []:
                if not lsel:
                    continue
                link_el = item.select_one(lsel)
                if link_el:
                    break
        if link_el and link_el.has_attr("href"):
            href = link_el["href"]
            if href and href != "#":
                link = urljoin(base_url, href)

        img_url = None
        if "img_selector" in cfg and cfg["img_selector"]:
            img_el = item.select_one(cfg["img_selector"])
            if img_el:
                for attr in ["data-src", "src", "data-lazy", "data-original", "data-thumb"]:
                    if img_el.has_attr(attr):
                        img_val = img_el[attr]
                        if img_val and not img_val.startswith("data:"):
                            img_url = urljoin(base_url, img_val)
                            break
        if not img_url and "fallback_selectors" in cfg:
            for isel in cfg["fallback_selectors"].get("img", []) or []:
                if not isel:
                    continue
                img_el = item.select_one(isel)
                if img_el:
                    for attr in ["data-src", "src", "data-lazy", "data-original", "data-thumb"]:
                        if img_el.has_attr(attr):
                            img_val = img_el[attr]
                            if img_val and not img_val.startswith("data:"):
                                img_url = urljoin(base_url, img_val)
                                break
                    if img_url:
                        break

        duration = extract_text_safe(item, cfg.get("time_selector", ""), "N/A")
        views = extract_text_safe(item, cfg.get("meta_selector", ""), "N/A")
        channel_name = extract_text_safe(item, cfg.get("channel_name_selector", ""), "N/A")
        channel_link = "#"
        channel_link_selector = cfg.get("channel_link_selector", "")
        if channel_link_selector:
            ch_el = item.select_one(channel_link_selector)
            if ch_el and ch_el.has_attr("href"):
                href = ch_el["href"]
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

def extract_with_selenium(driver, url: str, cfg: Dict[str, Any]) -> List[Any]:
    """Extract using Selenium when JavaScript rendering is needed."""
    try:
        driver.get(url)
        time.sleep(2)  # simple wait; can be enhanced with WebDriverWait
        from bs4 import BeautifulSoup as _BS4
        soup = _BS4(driver.page_source, "html.parser")
        return extract_video_items(soup, cfg)
    except Exception as e:
        logger.warning(f"Selenium extraction failed for {url}: {e}")
        return []

@asynccontextmanager
async def aiohttp_session() -> AsyncGenerator[Any, None]:
    if not ASYNC_AVAILABLE:
        yield None
        return
    timeout = aiohttp.ClientTimeout(total=30, connect=10)
    headers = REALISTIC_HEADERS
    try:
        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=aiohttp.TCPConnector(limit=50, limit_per_host=10),
        ) as session:
            yield session
    except Exception as e:
        logger.error(f"Failed to create aiohttp session: {e}")
        yield None

# ─── HTML Output: Enhanced gallery with deduplicated thumbnails ─────────────────
async def build_enhanced_html_async(
    results: Sequence[Dict[str, Any]],
    query: str,
    engine: str,
    thumbs_dir: Path,
    session: requests.Session,
    workers: int,
) -> Path:
    """
    Build an HTML gallery asynchronously with deduplicated thumbnails.

    Primary thumbnail download uses async path (aiohttp) when available,
    with a robust fallback to synchronous downloads.
    """
    ensure_dir(thumbs_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ensure_dir(Path(VSEARCH_DIR))
    filename = f"{engine}_{enhanced_slugify(query)}_{timestamp}_{uuid.uuid4().hex[:8]}.html"
    outfile = Path(VSEARCH_DIR) / filename

    # Deduplication map for thumbnails
    thumb_map: Dict[str, str] = {}

    # Semaphore to control concurrency
    semaphore = asyncio.Semaphore(max(1, workers))

    async def fetch_thumbnail_async_task(
        idx: int, video: Dict[str, Any]
    ) -> Tuple[int, str]:
        img_url = video.get("img_url")
        if not img_url:
            return idx, generate_placeholder_svg("������") # Neutral video icon placeholder

        if img_url in thumb_map:
            return idx, thumb_map[img_url]

        img_ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
        safe_title = enhanced_slugify(video.get("title", "video"))[:50]
        filename = f"{safe_title}_{idx}{img_ext}"
        dest_path = thumbs_dir / filename
        rel_path = f"../{THUMBNAILS_DIR.name}/{filename}".replace("\\", "/")

        try:
            os.makedirs(thumbs_dir, exist_ok=True)

            if dest_path.exists() and dest_path.stat().st_size > 0:
                thumb_map[img_url] = rel_path
                return idx, rel_path

            # Try async first
            if ASYNC_AVAILABLE:
                async with aiohttp_session() as async_session:
                    if async_session:
                        success = await async_download_thumbnail(async_session, img_url, dest_path, semaphore)
                        if success:
                            thumb_map[img_url] = rel_path
                            return idx, rel_path
            # Fallback to sync
            if robust_download_sync(session, img_url, dest_path):
                thumb_map[img_url] = rel_path
                return idx, rel_path
        except Exception as e:
            logger.debug(f"Error during thumbnail fetch for {img_url}: {e}")

        # If all attempts fail, return an error placeholder
        placeholder = generate_placeholder_svg("❌") # Explicit error icon
        thumb_map[img_url] = placeholder
        return idx, placeholder

    # Launch thumbnail downloads
    thumbnail_tasks = [
        fetch_thumbnail_async_task(i, video) for i, video in enumerate(results)
    ]
    results_thumbs = await asyncio.gather(*thumbnail_tasks, return_exceptions=True)

    # Build HTML document
    with open(outfile, "w", encoding="utf-8") as f:
        f.write(
            HTML_HEAD.format(
                title=f"{html.escape(query)} - {engine}",
                query=html.escape(query),
                engine=engine.title(),
                count=len(results),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            )
        )

        for video, thumb_result in zip(results, results_thumbs):
            thumbnail: str
            if isinstance(thumb_result, tuple) and len(thumb_result) == 2:
                # Successfully retrieved thumbnail path or placeholder
                thumbnail = thumb_result[1]
            else:
                # Error during thumbnail task execution, use generic error placeholder
                thumbnail = generate_placeholder_svg("❌")

            meta_items: List[str] = []
            if video.get("time", "N/A") and video["time"] != "N/A":
                meta_items.append(f'<span class="item">⏱️ {html.escape(video["time"])}</span>')
            if video.get("channel_name", "N/A") != "N/A":
                channel_link = video.get("channel_link", "#")
                if channel_link and channel_link != "#":
                    meta_items.append(
                        f'<span class="item"><a href="{html.escape(channel_link)}" target="_blank" rel="noopener noreferrer">������ {html.escape(video["channel_name"])}</a></span>'
                    )
                else:
                    meta_items.append(f'<span class="item">������ {html.escape(video["channel_name"])}</span>')
            if video.get("meta", "N/A") != "N/A":
                meta_items.append(f'<span class="item">������ {html.escape(str(video["meta"]))}</span>')

            # --- Improved Image Tag Generation ---
            if thumbnail.startswith("data:image"):
                # If it's an SVG placeholder (either for success/no-image or error), use it directly
                img_html = f'<img src="{html.escape(thumbnail)}" alt="{html.escape(video.get("title",""))}" loading="lazy">'
            else:
                # If it's a file path to a downloaded thumbnail, use a neutral SVG placeholder in src
                # and the actual path in data-src for lazy loading.
                neutral_lazy_load_placeholder = generate_placeholder_svg("������")
                img_html = f'<img src="{neutral_lazy_load_placeholder}" data-src="{html.escape(thumbnail)}" alt="{html.escape(video.get("title",""))}" loading="lazy">'
            # --- End Improved Image Tag Generation ---

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

        f.write(HTML_TAIL)

    logger.info(f"Enhanced HTML gallery saved to: {outfile}")
    return outfile

# ─── Main Functionality ───────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Enhanced video search with web scraping.",
        epilog=(
            "Example usage:\n"
            '  python3 video_search.py "cats in space"\n'
            "  python3 video_search.py \"ocean waves\" -e pexels -l 50 -p 2 -o json\n"
            "  python3 video_search.py \"daily news\" -e dailymotion --no-async --no-open"
        )
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
        "--no-async", action="store_true",
        help="Disable async downloading and use synchronous mode for thumbnails."
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
        help="Allow adult content engines (adult content gating is enabled by default)."
    )
    args = parser.parse_args()

    global ALLOW_ADULT
    if args.allow_adult:
        ALLOW_ADULT = True

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Setup signal handler for graceful exit
    def signal_handler(sig, frame):
        print(f"\n{NEON['YELLOW']}* Ctrl+C detected. Exiting gracefully...{NEON['RESET']}")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        session = build_enhanced_session(proxy=args.proxy)

        print(f"{NEON['CYAN']}{Style.BRIGHT}Starting search for '{args.query}' on {args.engine}...{NEON['RESET']}")
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
            sys.exit(1)

        print(f"{NEON['GREEN']}Found {len(results)} videos.{NEON['RESET']}")
        if args.output_format == "json":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{args.engine}_{enhanced_slugify(args.query)}_{timestamp}.json"
            outfile = Path(filename)
            with open(outfile, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            print(f"{NEON['CYAN']}JSON results saved to: {outfile}{NEON['RESET']}")
        else:
            # Build HTML gallery (async thumbnail handling)
            outfile: Path
            if ASYNC_AVAILABLE and not getattr(args, "no_async", False):
                # Use asyncio.run for clean event loop handling
                outfile = asyncio.run(
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
                # Fallback: run with a small event loop to reuse the async function, but disable true async
                outfile = asyncio.run(
                    build_enhanced_html_async(
                        results=results,
                        query=args.query,
                        engine=args.engine,
                        thumbs_dir=Path(THUMBNAILS_DIR),
                        session=session,
                        workers=1, # Force 1 worker for "no-async"
                    )
                )

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