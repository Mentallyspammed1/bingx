#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wowxxx_search.py - Enhanced Wow.xxx Video Search Tool

This script is a specialized version of the generic video search tool,
configured specifically for the wow.xxx platform. It is designed to be
robust, efficient, and respectful of web scraping best practices.

It includes:
- Advanced User-Agent rotation and realistic headers.
- Robust error handling and network retry mechanisms.
- Intelligent, human-like delays with jitter to avoid detection.
- Asynchronous thumbnail downloading for performance.
- A clean, modern HTML gallery output with lazy-loading.

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

# --- Import necessary components from the provided codebase ---
# We will adapt and reuse functions from vids_working.py and scrapevid.py
# that are essential for the core functionality.

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

# Detect Termux environment and disable Selenium if present, as chromedriver setup is complex
if 'TERMUX_VERSION' in os.environ:
    SELENIUM_AVAILABLE = False
    # Wizardly note: In the shadowed realms of Termux, Selenium spirits are hard to summon. 
    # Consider 'pkg install chromium' and manual chromedriver setup if you dare.

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ModuleNotFoundError:
    TQDM_AVAILABLE = False
    def tqdm(iterable, **kwargs):
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
    f"{NEON['BLUE']}[Wowxxx]{NEON['RESET']} "
    f"{NEON['GREEN']}%(message)s{NEON['RESET']}"
)

# Enhanced logging with context
class ContextFilter(logging.Filter):
    def filter(self, record):
        record.engine = getattr(record, 'engine', 'Wowxxx')
        record.query = getattr(record, 'query', 'unknown')
        return True

log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    log_handlers.append(logging.FileHandler("wowxxx_search.log", mode="a", encoding="utf-8"))
except PermissionError:
    pass

logging.basicConfig(level=logging.INFO, format=LOG_FMT, handlers=log_handlers)
logger = logging.getLogger(__name__)
logger.addFilter(ContextFilter())

for noisy in ("urllib3", "chardet", "requests", "aiohttp", "selenium"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# ── Wow.xxx Specific Configuration ────────────────────────────────────
THUMBNAILS_DIR = Path("downloaded_thumbnails")
VSEARCH_DIR = Path("wowxxx_results")
DEFAULT_ENGINE = "wowxxx"
DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_FORMAT = "html"
DEFAULT_TIMEOUT = 25
DEFAULT_DELAY = (1.5, 4.0)
DEFAULT_MAX_RETRIES = 5
DEFAULT_WORKERS = 12

REALISTIC_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.6; rv:129.0) Gecko/20100101 Firefox/129.0",
]

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

WOWXXX_CONFIG: Dict[str, Any] = {
    "url": "https://www.wow.xxx",
    "search_path": "/popular/search/{query}/", # Simplified search path
    "page_param": None,  # Paging is path-based: /<page>/
    "requires_js": True,
    "video_item_selector": "article.video-card",
    "link_selector": "a.video-card__link",
    "title_selector": "h3.video-card__title",
    "title_attribute": "title",
    "img_selector": "img.video-card__thumbnail",
    "time_selector": "span.video-card__duration",
    "meta_selector": "span.video-card__views",
    "channel_name_selector": "a.video-card__channel-name",
    "channel_link_selector": "a.video-card__channel-link",
    "fallback_selectors": {
        "title": ["a[title]", "h2", "div.title"],
        "img": ["img[data-src]", "img[src]", "video-preview", "img.lazy"],
        "link": ["a[href*='/video/']", "a[href*='/viewkey=']", "a.item-link"]
    }
}

# ── Arcane Utilities & Helpers (from vids_working.py) ───────────────────
def ensure_dir(path: Path) -> None:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise

def enhanced_slugify(text: str) -> str:
    if not text or not isinstance(text, str):
        return "untitled"
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"[^a-zA-Z0-9\s\-_.]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    text = text.strip("._-")
    text = text[:100] or "untitled"
    reserved_names = {"con", "prn", "aux", "nul", "com1", "com2"}
    if text.lower() in reserved_names:
        text = f"file_{text}"
    return text

def build_enhanced_session(
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    proxy: Optional[str] = None,
) -> requests.Session:
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
    adapter = HTTPAdapter(max_retries=retries, pool_connections=15, pool_maxsize=30)
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

@asynccontextmanager
async def aiohttp_session() -> AsyncGenerator[Optional[aiohttp.ClientSession], None]:
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

def robust_download_sync(session: requests.Session, url: str, path: Path, max_attempts: int = 3) -> bool:
    if not url or not urlparse(url).scheme:
        return False
    for attempt in range(max_attempts):
        try:
            session.headers.update(get_realistic_headers(random.choice(REALISTIC_USER_AGENTS)))
            with session.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                    logger.debug(f"Sync download failed, invalid content type for {url}")
                    return False
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > 10 * 1024 * 1024:
                    logger.debug(f"Sync download failed, invalid content size for {url}")
                    return False
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
                time.sleep(2 ** attempt)
    return False

def extract_video_items(soup: BeautifulSoup, cfg: Dict) -> List:
    video_items = []
    for selector in cfg["video_item_selector"].split(","):
        items = soup.select(selector.strip())
        if items:
            video_items.extend(items)
    return video_items

def extract_text_safe(element, selector: str, default: str = "N/A") -> str:
    if not selector:
        return default
    try:
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
    try:
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
        
        img_url = None
        img_selectors = [s.strip() for s in cfg.get("img_selector", "").split(',') if s.strip()]
        if "fallback_selectors" in cfg and "img" in cfg["fallback_selectors"]:
            img_selectors.extend([s.strip() for s in cfg["fallback_selectors"]["img"] if s.strip()])
        for selector in img_selectors:
            img_el = item.select_one(selector)
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
    if not isinstance(data, dict): return False
    required_fields = ["title", "link"]
    for field in required_fields:
        if not data.get(field) or data[field] in ["", "Untitled", "#"]: return False
    try:
        parsed_link = urlparse(data["link"])
        if not parsed_link.scheme or not parsed_link.netloc: return False
    except Exception: return False
    title = data.get("title", "")
    if len(title) < 3 or title.lower() in ["untitled", "n/a", "error"]: return False
    return True

def generate_placeholder_svg(icon: str) -> str:
    safe_icon = html.escape(unicodedata.normalize("NFKC", icon), quote=True)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%" viewBox="0 0 100 100">
        <rect width="100%" height="100%" fill="#1a1a2e"/>
        <text x="50" y="55" font-family="sans-serif" font-size="40" fill="#4a4a5e" text-anchor="middle" dominant-baseline="middle">{safe_icon}</text>
    </svg>'''
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode("ascii")

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
      --accent-cyan: #00d4ff; --accent-pink: #ff006e;
      --grad: linear-gradient(135deg, var(--accent-cyan) 0%, var(--accent-pink) 100%);
      --shadow: rgba(0, 0, 0, 0.2);
    }}
    [data-theme="dark"] {{
      --bg: var(--bg-dark); --card: var(--card-dark); --text: var(--text-dark); --muted: var(--muted-dark); --border: var(--border-dark);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); transition: background 0.3s, color 0.3s; line-height: 1.6; overflow-x: hidden;}}
    .container {{ max-width: 1600px; margin: 2rem auto; padding: 1rem; background: var(--bg); border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }}
    header {{ text-align: center; padding: 1.5rem 0; margin-bottom: 2rem; }}
    h1 {{ font-family: "JetBrains Mono", monospace; font-size: 2.5rem; background: var(--grad); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 0.5rem; text-shadow: 0 0 15px rgba(0, 212, 255, 0.2);}}
    .subtitle {{ color: var(--muted); font-size: 1.1rem; }}
    .stats {{ display: flex; justify-content: center; gap: 2rem; margin: 1.5rem 0; flex-wrap: wrap; }}
    .stat {{ background: var(--card); padding: 0.75rem 1.5rem; border-radius: 25px; border: 1px solid var(--border); font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; white-space: nowrap;}}
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
</div>
<script>
    document.addEventListener('DOMContentLoaded', function() {
        const images = document.querySelectorAll('img[data-src]');
        const observer = new IntersectionObserver((entries, obs) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    const thumbDiv = img.closest('.thumb');
                    if (thumbDiv) {
                        thumbDiv.innerHTML = '<div class="loading-spinner"></div>';
                    }
                    const actualImg = new Image();
                    actualImg.src = img.dataset.src;
                    actualImg.onload = () => {
                        if (thumbDiv) {
                            thumbDiv.innerHTML = '';
                            thumbDiv.appendChild(actualImg);
                            actualImg.classList.add('original-image-loaded');
                        }
                    };
                    actualImg.onerror = () => {
                        console.error('Failed to load image:', img.dataset.src);
                        if (thumbDiv) {
                            thumbDiv.innerHTML = '<div class="placeholder">❌</div>';
                        }
                    };
                    obs.unobserve(img);
                }
            });
        }, { threshold: 0.1 });
        images.forEach(img => observer.observe(img));
    });
</script>
</body>
</html>
"""

async def build_enhanced_html_async(
    results: Sequence[Dict],
    query: str,
    engine: str,
    thumbs_dir: Path,
    session: requests.Session, # This is the requests.Session for sync fallback
    aio_session: Optional[aiohttp.ClientSession], # New: aiohttp session
    workers: int,
) -> Path:
    ensure_dir(thumbs_dir)
    ensure_dir(VSEARCH_DIR)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{engine}_{enhanced_slugify(query)}_{timestamp}_{uuid.uuid4().hex[:8]}.html"
    outfile = Path(VSEARCH_DIR) / filename
    
    def get_thumb_path(img_url: str, title: str, idx: int) -> Path:
        ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
        safe_title = enhanced_slugify(title)[:50]
        return thumbs_dir / f"{safe_title}_{idx}{ext}"

    async def fetch_thumbnail_async_task(idx: int, video: Dict, aio_session: Optional[aiohttp.ClientSession]) -> Tuple[int, str]:
        img_url = video.get("img_url")
        if not img_url: return idx, generate_placeholder_svg("📹")

        dest_path = get_thumb_path(img_url, video.get("title", "video"), idx)
        if dest_path.exists() and dest_path.stat().st_size > 0:
            return idx, str(dest_path).replace("\", "/")

        if aio_session:
            semaphore = asyncio.Semaphore(workers)
            if await download_thumbnail_async(aio_session, img_url, dest_path, semaphore):
                return idx, str(dest_path).replace("\", "/")
        
        if robust_download_sync(session, img_url, dest_path):
            return idx, str(dest_path).replace("\", "/")
        
        return idx, generate_placeholder_svg("❌")

    def fetch_thumbnail_sync_task(idx: int, video: Dict) -> Tuple[int, str]:
        img_url = video.get("img_url")
        if not img_url: return idx, generate_placeholder_svg("📹")
        dest_path = get_thumb_path(img_url, video.get("title", "video"), idx)
        if dest_path.exists() and dest_path.stat().st_size > 0:
            return idx, str(dest_path).replace("\\", "/")
        if robust_download_sync(session, img_url, dest_path):
            return idx, str(dest_path).replace("\\", "/")
        return idx, generate_placeholder_svg("❌")
        
    thumbnail_paths = [""] * len(results)
    
    if ASYNC_AVAILABLE:
        tasks = [fetch_thumbnail_async_task(i, video, aio_session) for i, video in enumerate(results)]
        results_with_idx = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results_with_idx:
            if isinstance(result, tuple) and len(result) == 2:
                idx, path = result
                thumbnail_paths[idx] = path
            else:
                logger.debug(f"Error gathering async thumbnail result: {result}")
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(workers, 20)) as executor:
            future_to_idx = {executor.submit(fetch_thumbnail_sync_task, i, video): i for i, video in enumerate(results)}
            progress_bar = tqdm(concurrent.futures.as_completed(future_to_idx), total=len(future_to_idx), desc=f"{NEON['MAGENTA']}Downloading Thumbnails{NEON['RESET']}", unit="files", ncols=100, disable=not TQDM_AVAILABLE)
            for future in progress_bar:
                i = future_to_idx[future]
                try:
                    _, path = future.result()
                    thumbnail_paths[i] = path
                except Exception as e:
                    logger.debug(f"Error with threaded download for item {i}: {e}")
                    thumbnail_paths[i] = generate_placeholder_svg("❌")
            progress_bar.close()

    with open(outfile, "w", encoding="utf-8") as f:
        f.write(HTML_HEAD.format(
            title=f"{html.escape(query)} - {engine}",
            query=html.escape(query),
            count=len(results),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        for video, thumbnail in zip(results, thumbnail_paths):
            meta_items = []
            if video.get("time", "N/A") != "N/A":
                meta_items.append(f'<div class="item">⏱️ {html.escape(video["time"])}</div>')
            if video.get("channel_name", "N/A") != "N/A":
                channel_link = video.get("channel_link", "#")
                if channel_link != "#":
                    meta_items.append(f'<div class="item"><a href="{html.escape(channel_link)}" target="_blank" rel="noopener noreferrer">👤 {html.escape(video["channel_name"])}</a></div>')
                else:
                    meta_items.append(f'<div class="item">👤 {html.escape(video["channel_name"])}</div>')
            if video.get("meta", "N/A") != "N/A":
                meta_items.append(f'<div class="item">👁️ {html.escape(video["meta"])}</div>')

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
                    <div class="meta">{" ".join(meta_items)}</div>
                </div>
            </div>
            ''')
        f.write(HTML_TAIL)

    logger.info(f"Enhanced HTML gallery saved to: {outfile}")
    return outfile

def get_wowxxx_results(
    session: requests.Session,
    query: str,
    limit: int,
    page: int,
    delay_range: Tuple[float, float],
) -> List[Dict[str, Any]]:
    config = WOWXXX_CONFIG
    base_url = config["url"]
    results: List[Dict[str, Any]] = []
    last_request_time = None
    items_per_page = 30 
    pages_to_fetch = min(5, (limit + items_per_page - 1) // items_per_page)
    pages_to_fetch = max(1, pages_to_fetch)
    
    logger.info(f"Searching wow.xxx for '{query}' (up to {pages_to_fetch} pages)", extra={'engine': 'Wowxxx', 'query': query})
    page_range_iterable = range(page, page + pages_to_fetch)
    page_progress_bar = tqdm(page_range_iterable, desc=f"{NEON['BLUE']}Scraping wow.xxx for '{query}'{NEON['RESET']}", unit="page", dynamic_ncols=True, ncols=100, disable=not TQDM_AVAILABLE)
    
    driver = None
    if config.get("requires_js") and SELENIUM_AVAILABLE:
        try:
            options = ChromeOptions()
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument(f"--user-agent={random.choice(REALISTIC_USER_AGENTS)}")
            driver = webdriver.Chrome(options=options)
        except Exception as e:
            logger.error(f"Failed to initialize Selenium driver: {e}")
            driver = None

    try:
        for current_page in page_progress_bar:
            if len(results) >= limit: break
            smart_delay_with_jitter(delay_range, last_request_time)
            last_request_time = time.time()
            
            search_path = config["search_path"].format(query=quote_plus(query))
            url = urljoin(base_url, search_path)
            if current_page > 1:
                url += f"{current_page}/"
            
            logger.debug(f"Fetching page {current_page}: {url}", extra={'engine': 'Wowxxx', 'query': query})

            if driver:
                try:
                    driver.get(url)
                    wait = WebDriverWait(driver, 10)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, config["video_item_selector"])))
                    soup = BeautifulSoup(driver.page_source, "html.parser")
                except (TimeoutException, WebDriverException) as e:
                    logger.warning(f"Selenium extraction failed for {url}: {e}")
                    soup = BeautifulSoup("", "html.parser")
            else:
                try:
                    user_agent = random.choice(REALISTIC_USER_AGENTS)
                    session.headers.update(get_realistic_headers(user_agent))
                    response = session.get(url, timeout=getattr(session, 'timeout', DEFAULT_TIMEOUT))
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, "html.parser")
                except requests.exceptions.RequestException as e:
                    logger.error(f"Request failed for page {current_page}: {e}", extra={'engine': 'Wowxxx', 'query': query})
                    # Enhanced handling: If 404, perhaps no more pages or invalid query
                    if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 404:
                        logger.info(f"No more pages available after page {current_page - 1}")
                        break
                    continue
            
            video_items = extract_video_items(soup, config)
            if not video_items:
                logger.warning(f"No video items found on page {current_page}", extra={'engine': 'Wowxxx', 'query': query})
                continue

            for item in video_items:
                if len(results) >= limit: break
                video_data = extract_video_data_enhanced(item, config, base_url)
                if video_data and validate_video_data_enhanced(video_data):
                    results.append(video_data)
        
    finally:
        if driver:
            driver.quit()
    
    page_progress_bar.close()
    logger.info(f"Successfully extracted {len(results)} videos", extra={'engine': 'Wowxxx', 'query': query})
    return results[:limit]

# ── Main Execution Orchestration ─────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="wow.xxx Video Searcher based on web scraping.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""\
Example usage:
  python3 wowxxx_search.py "teen girl"
  python3 wowxxx_search.py "milf" -l 50
  python3 wowxxx_search.py "anal" --output-format json
"""
    )
    parser.add_argument("query", type=str, help="The search query for videos.")
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
        choices=["html", "json", "csv"],
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

    global ASYNC_AVAILABLE
    if args.no_async:
        ASYNC_AVAILABLE = False
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    def signal_handler(sig, frame):
        print(f"\n{NEON['YELLOW']}* Ctrl+C detected. Exiting gracefully...{NEON['RESET']}")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        session = build_enhanced_session(proxy=args.proxy)
        
        print(f"{NEON['CYAN']}{Style.BRIGHT}Starting search for '{args.query}' on wow.xxx...")

        results = get_wowxxx_results(
            session=session,
            query=args.query,
            limit=args.limit,
            page=args.page,
            delay_range=DEFAULT_DELAY,
        )
        
        if not results:
            print(f"{NEON['RED']}No videos found for '{args.query}'. Try refining your query or checking network.{NEON['RESET']}")
            sys.exit(1)
        
        print(f"{NEON['GREEN']}Found {len(results)} videos.{NEON['RESET']}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug_query = enhanced_slugify(args.query)
        ensure_dir(VSEARCH_DIR)

        if args.output_format == "json":
            filename = f"wowxxx_{slug_query}_{timestamp}.json"
            outfile = Path(VSEARCH_DIR) / filename
            with open(outfile, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            print(f"{NEON['CYAN']}JSON results saved to: {outfile}{NEON['RESET']}")
        elif args.output_format == "csv":
            filename = f"wowxxx_{slug_query}_{timestamp}.csv"
            outfile = Path(VSEARCH_DIR) / filename
            if results:
                fieldnames = results[0].keys()
                with open(outfile, "w", encoding="utf-8", newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(results)
            print(f"{NEON['CYAN']}CSV results saved to: {outfile}{NEON['RESET']}")
        else:
            if ASYNC_AVAILABLE and not args.no_async:
                async def run_async_html_build():
                    async with aiohttp_session() as aio_session:
                        if aio_session is None:
                            logger.warning("Failed to create aiohttp session, falling back to sync thumbnail download.")
                            # Fallback to sync path if async session fails
                            return await build_enhanced_html_async(
                                results=results,
                                query=args.query,
                                engine='wowxxx',
                                thumbs_dir=Path(THUMBNAILS_DIR),
                                session=session,
                                aio_session=None, # Explicitly pass None
                                workers=args.workers,
                            )
                        else:
                            return await build_enhanced_html_async(
                                results=results,
                                query=args.query,
                                engine='wowxxx',
                                thumbs_dir=Path(THUMBNAILS_DIR),
                                session=session,
                                aio_session=aio_session,
                                workers=args.workers,
                            )
                outfile = asyncio.run(run_async_html_build())
            else:
                # This path is for when ASYNC_AVAILABLE is False or --no-async is true.
                # In this case, we don't need an aiohttp session.
                outfile = asyncio.run(
                    build_enhanced_html_async(
                        results=results,
                        query=args.query,
                        engine='wowxxx',
                        thumbs_dir=Path(THUMBNAILS_DIR),
                        session=session,
                        aio_session=None, # Explicitly pass None for aio_session
                        workers=args.workers,
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
