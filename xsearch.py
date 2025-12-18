#!/usr/bin/env python3
"""
vsearch.py • 2025-10-01 (OMEGA-EDITION)

The definitive video search and scraper tool.
Features:
- State-of-the-art 2025 Selectors for major video platforms.
- Async/Await high-performance thumbnail downloading.
- Anti-detection headers and jitter-based delays.
- Responsive, Netflix-style HTML output gallery.
- Cross-platform compatibility (Windows/Linux/Termux).
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
import shutil
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from string import Template
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

# 3rd Party Imports
import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from requests.adapters import HTTPAdapter, Retry

# ── Optional Dependencies Check ──────────────────────────────────────────
try:
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs): return iterable

# ── Color & Logging Config ───────────────────────────────────────────────
init(autoreset=True)
NEON = {
    "CYAN": Fore.CYAN, "MAGENTA": Fore.MAGENTA, "GREEN": Fore.GREEN,
    "YELLOW": Fore.YELLOW, "RED": Fore.RED, "BLUE": Fore.BLUE,
    "WHITE": Fore.WHITE, "BRIGHT": Style.BRIGHT, "RESET": Style.RESET_ALL,
}

LOG_FMT = (
    f"{NEON['BLUE']}%(asctime)s{NEON['RESET']} - "
    f"{NEON['MAGENTA']}%(levelname)s{NEON['RESET']} - "
    f"{NEON['WHITE']}%(message)s{NEON['RESET']}"
)

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.engine = getattr(record, 'engine', 'unknown')
        record.query = getattr(record, 'query', 'unknown')
        return True

# Setup Logging
log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    log_file_path = Path.home() / "vsearch_debug.log"
    log_handlers.append(logging.FileHandler(log_file_path, mode="a", encoding="utf-8"))
except (PermissionError, OSError):
    pass

logging.basicConfig(level=logging.INFO, format=LOG_FMT, handlers=log_handlers)
logger = logging.getLogger(__name__)
logger.addFilter(ContextFilter())

# Suppress noisy libraries
for lib in ["urllib3", "chardet", "requests", "aiohttp", "selenium", "webdriver_manager"]:
    logging.getLogger(lib).setLevel(logging.WARNING)

# ── Configuration & Constants ────────────────────────────────────────────
# Directories (Cross-platform safe)
BASE_DIR = Path.home() / "vsearch_data"
THUMBNAILS_DIR = BASE_DIR / "thumbnails"
OUTPUT_DIR = BASE_DIR / "results"

# Defaults
DEFAULT_ENGINE = "pexels"
DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_FORMAT = "html"
DEFAULT_TIMEOUT = 20
DEFAULT_DELAY = (1.0, 3.0)
DEFAULT_MAX_RETRIES = 3
DEFAULT_WORKERS = 10
DEFAULT_CACHE_TTL = 7  # Days

# 2025 Realistic User Agents
REALISTIC_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
]

def get_realistic_headers(user_agent: str) -> dict[str, str]:
    """Generate high-fidelity browser headers."""
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
        "Sec-CH-UA": '"Chromium";v="130", "Google Chrome";v="130", "Not?A_Brand";v="99"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Windows"',
        "Cache-Control": "max-age=0",
    }

# ── The Grimoire: Engine Definitions ─────────────────────────────────────
# NOTE: Selectors updated for late 2024/2025 layouts.
ENGINE_MAP: dict[str, dict[str, Any]] = {
    "pexels": {
        "url": "https://www.pexels.com",
        "search_path": "/search/videos/{query}/",
        "page_param": "page",
        "requires_js": False,
        "video_item_selector": "article[data-testid='video-card'], article.hide-favorite-badge-container",
        "link_selector": "a[data-testid='video-card-link'], a[href*='/video/']",
        "title_selector": "img[data-testid='video-card-img'], .video-title",
        "title_attribute": "alt",
        "img_selector": "img[data-testid='video-card-img']",
        "channel_name_selector": "a[data-testid='video-card-user-avatar-link']",
        "fallback_selectors": {
            "title": ["img[alt]"],
            "img": ["img[src]"]
        }
    },
    "dailymotion": {
        "url": "https://www.dailymotion.com",
        "search_path": "/search/{query}/videos",
        "page_param": "page",
        "requires_js": True, # Highly dynamic
        "video_item_selector": "div[data-testid='video-card'], .video-item",
        "link_selector": "a[data-testid='card-link']",
        "title_selector": "div[data-testid='card-title']",
        "img_selector": "img[data-testid='card-thumbnail']",
        "time_selector": "span[data-testid='card-duration']",
        "channel_name_selector": "div[data-testid='card-owner-name']",
        "fallback_selectors": {
            "title": ["a[aria-label]"],
            "img": ["img[src]"]
        }
    },
    "xhamster": {
        "url": "https://xhamster.com",
        "search_path": "/search/{query}",
        "page_param": "page",
        "requires_js": True, # Often required for thumbnails
        "video_item_selector": "div[data-role='video-thumb'], div.thumb-list__item",
        "link_selector": "a.video-thumb__image-container",
        "title_selector": "div.video-thumb-info__name",
        "img_selector": "img.thumb-image-container__image",
        "time_selector": "div[data-role='video-duration'], .thumb-image-container__duration",
        "meta_selector": ".video-thumb-views",
        "fallback_selectors": {
            "title": ["a[title]", "img[alt]"],
            "img": ["img[src]", "img[data-src]"],
            "link": ["a[href*='/videos/']"]
        }
    },
    "pornhub": {
        "url": "https://www.pornhub.com",
        "search_path": "/video/search?search={query}",
        "page_param": "page",
        "requires_js": False,
        "video_item_selector": "li.pcVideoListItem, div.videoBox, .video-item",
        "link_selector": "a[href*='/view_video.php']",
        "title_selector": "span.title a, .title a, a[title]",
        "img_selector": "img.fadeUp, img[data-thumb_url], img[data-src]",
        "time_selector": "var.duration, .duration",
        "channel_name_selector": ".usernameWrap a",
        "meta_selector": ".views, .video-views",
        "fallback_selectors": {
            "title": ["img[alt]", "a.title"],
            "img": ["img[src]", "img[data-mediabook]"],
            "link": ["a.video-link"]
        }
    },
    "xvideos": {
        "url": "https://www.xvideos.com",
        "search_path": "/?k={query}",
        "page_param": "p",
        "requires_js": False,
        "video_item_selector": "div.frame-block, .thumb-block",
        "link_selector": ".thumb-under a, .title a",
        "title_selector": ".thumb-under a, .title a, p.title a",
        "img_selector": "img.thumb, img[data-src]",
        "time_selector": "span.duration",
        "meta_selector": ".video-views",
        "channel_name_selector": "span.name",
        "fallback_selectors": {
            "title": ["a[title]"],
            "img": ["img[src]"],
            "link": ["a[href*='/video']"]
        }
    },
    "xnxx": {
        "url": "https://www.xnxx.com",
        "search_path": "/search/{query}/{page}",
        "page_param": "", # Built into path
        "requires_js": False,
        "video_item_selector": "div.thumb-block, .mozaique > div",
        "link_selector": ".thumb-under a, .title a",
        "title_selector": ".thumb-under a, p.title a",
        "img_selector": "img.thumb, img[data-src]",
        "time_selector": "span.duration",
        "meta_selector": ".metadata",
        "fallback_selectors": {
            "title": ["a[title]"],
            "img": ["img[src]"],
            "link": ["a[href*='/video']"]
        }
    },
    "spankbang": {
        "url": "https://spankbang.com",
        "search_path": "/s/{query}/{page}/",
        "page_param": "",
        "requires_js": False,
        "video_item_selector": "div.video-item",
        "link_selector": "a.thumb",
        "title_selector": "img.thumb", 
        "title_attribute": "alt",
        "img_selector": "img.thumb",
        "time_selector": "span.l", # length
        "meta_selector": "span.v", # views
        "fallback_selectors": {
            "title": ["a.n"],
            "img": ["img[data-src]"],
            "link": ["a[href*='/video/']"]
        }
    },
    "youjizz": {
        "url": "https://www.youjizz.com",
        "search_path": "/search/{query}-{page}.html",
        "page_param": "",
        "requires_js": True,
        "video_item_selector": "div.video-thumb",
        "link_selector": "a.frame",
        "title_selector": "div.video-title",
        "img_selector": "img.lazy",
        "img_attribute": "data-original",
        "time_selector": "span.time",
        "meta_selector": "span.views",
        "fallback_selectors": {
            "title": ["a[title]"],
            "img": ["img[src]"],
            "link": ["a[href*='/videos/']"]
        }
    },
    "motherless": {
        "url": "https://www.motherless.com",
        "search_path": "/term/videos/{query}?page={page}",
        "page_param": "",
        "requires_js": False,
        "video_item_selector": "div.thumb-container",
        "link_selector": "a.img-container",
        "title_selector": "a.img-container img",
        "title_attribute": "alt",
        "img_selector": "a.img-container img",
        "time_selector": "span.duration",
        "meta_selector": "span.views",
        "fallback_selectors": {
            "title": ["div.caption"],
            "img": ["img[src]"],
            "link": ["a[href*='/video/']"]
        }
    }
}

# ── Core Logic ───────────────────────────────────────────────────────────

def ensure_dir(path: Path) -> None:
    """Robust directory creation."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        logger.error(f"{NEON['RED']}FATAL: Cannot create directory {path}: {e}{NEON['RESET']}")
        sys.exit(1)

def enhanced_slugify(text: str) -> str:
    """Sanitize filenames to be OS-safe."""
    if not text: return "untitled"
    text = html.unescape(text)
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', text)
    text = re.sub(r'\s+', '_', text.strip())
    text = text[:60] # Cap length
    return text or "untitled"

def smart_sleep(delay_range: tuple[float, float]) -> None:
    """Jitter sleep to reduce bot detection signatures."""
    base = random.uniform(*delay_range)
    jitter = base * random.uniform(-0.2, 0.2)
    time.sleep(max(0.5, base + jitter))

def build_enhanced_session(proxies: list[str] | None = None) -> requests.Session:
    """Create a requests session tuned for scraping."""
    session = requests.Session()
    
    # Retry Strategy
    retries = Retry(
        total=DEFAULT_MAX_RETRIES,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504, 520, 522],
        allowed_methods=["GET", "POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Headers & Proxy
    session.headers.update(get_realistic_headers(random.choice(REALISTIC_USER_AGENTS)))
    
    if proxies:
        proxy = random.choice(proxies)
        logger.info(f"{NEON['MAGENTA']}🌐 Routing via proxy: {urlparse(proxy).netloc}{NEON['RESET']}")
        session.proxies = {"http": proxy, "https": proxy}
        
    return session

def create_selenium_driver() -> webdriver.Chrome | None:
    """Instantiate a headless Chrome driver if available."""
    if not SELENIUM_AVAILABLE:
        return None
    
    try:
        options = ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"--user-agent={random.choice(REALISTIC_USER_AGENTS)}")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Try to locate chromedriver in path or use Selenium Manager (default in newer Selenium)
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(15)
        return driver
    except Exception as e:
        logger.warning(f"{NEON['YELLOW']}⚠️ Selenium Init Failed: {e}{NEON['RESET']}")
        return None

# ── Extraction Logic ─────────────────────────────────────────────────────

def extract_with_selenium(driver: webdriver.Chrome, url: str, cfg: dict) -> list:
    """Fetch JS-rendered content."""
    try:
        driver.get(url)
        # Wait for the main container
        wait = WebDriverWait(driver, 8)
        selector = cfg["video_item_selector"].split(",")[0]
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
        except TimeoutException:
            logger.debug(f"Selenium wait timed out for {selector}")
        
        # Scroll down slightly to trigger lazy loads
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
        time.sleep(1)
        
        soup = BeautifulSoup(driver.page_source, "html.parser")
        return extract_video_items(soup, cfg)
    except Exception as e:
        logger.error(f"Selenium scrape error: {e}")
        return []

def extract_video_items(soup: BeautifulSoup, cfg: dict) -> list:
    """Extract raw HTML elements based on config."""
    items = []
    selectors = [s.strip() for s in cfg["video_item_selector"].split(",")]
    for selector in selectors:
        found = soup.select(selector)
        if found:
            items.extend(found)
            break # Prioritize primary selector
    return items

def safe_extract_text(element: Any, selector: str) -> str:
    """Safely extract text from a child element."""
    if not selector: return "N/A"
    try:
        el = element.select_one(selector)
        return el.get_text(strip=True) if el else "N/A"
    except:
        return "N/A"

def extract_video_data_enhanced(item: Any, cfg: dict, base_url: str) -> dict | None:
    """Parse a single video element into a standardized dictionary."""
    try:
        # Title
        title = "Untitled"
        title_selectors = [cfg.get("title_selector")] + cfg.get("fallback_selectors", {}).get("title", [])
        for sel in filter(None, title_selectors):
            el = item.select_one(sel)
            if el:
                attr = cfg.get("title_attribute")
                if attr and el.has_attr(attr):
                    title = el[attr]
                else:
                    title = el.get_text(strip=True)
                if title: break
        
        # Link
        link = "#"
        link_selectors = [cfg.get("link_selector")] + cfg.get("fallback_selectors", {}).get("link", [])
        for sel in filter(None, link_selectors):
            el = item.select_one(sel)
            if el and el.has_attr("href"):
                link = urljoin(base_url, el["href"])
                break
        
        # Image
        img_url = None
        img_selectors = [cfg.get("img_selector")] + cfg.get("fallback_selectors", {}).get("img", [])
        for sel in filter(None, img_selectors):
            el = item.select_one(sel)
            if el:
                # Priority: specific attribute -> data-src -> src
                attrs = [cfg.get("img_attribute"), "data-src", "data-original", "data-lazy", "src"]
                for attr in filter(None, attrs):
                    if el.has_attr(attr):
                        val = el[attr]
                        if val and not val.startswith("data:"):
                            img_url = urljoin(base_url, val)
                            break
                if img_url: break
        
        # Metadata
        duration = safe_extract_text(item, cfg.get("time_selector", ""))
        views = safe_extract_text(item, cfg.get("meta_selector", ""))
        channel = safe_extract_text(item, cfg.get("channel_name_selector", ""))
        
        # Validation
        if link == "#" or not img_url:
            return None

        return {
            "title": html.escape(title),
            "link": link,
            "img_url": img_url,
            "time": duration,
            "meta": views,
            "channel": channel,
            "engine": urlparse(base_url).netloc
        }
    except Exception as e:
        logger.debug(f"Extraction failed item: {e}")
        return None

# ── Search & Scrape Loop ─────────────────────────────────────────────────

def get_search_results(
    session: requests.Session, 
    engine: str, 
    query: str, 
    limit: int, 
    page_start: int
) -> list[dict]:
    """Main orchestration function for scraping."""
    if engine not in ENGINE_MAP:
        logger.error(f"Invalid Engine: {engine}")
        return []
    
    cfg = ENGINE_MAP[engine]
    results = []
    driver = None
    
    # Init Selenium if needed
    if cfg.get("requires_js") and SELENIUM_AVAILABLE:
        driver = create_selenium_driver()
        if not driver:
            logger.warning("Falling back to Requests (Selenium init failed)")
    
    try:
        items_per_page_est = 30
        pages = (limit // items_per_page_est) + 1
        
        for page in range(page_start, page_start + pages):
            if len(results) >= limit:
                break
            
            # Construct URL
            path_tmpl = cfg["search_path"]
            if "{page}" in path_tmpl:
                path = path_tmpl.format(query=quote_plus(query), page=page)
            else:
                path = path_tmpl.format(query=quote_plus(query))
            
            url = urljoin(cfg["url"], path)
            if "{page}" not in path_tmpl and cfg.get("page_param") and page > 1:
                sep = "&" if "?" in url else "?"
                url += f"{sep}{cfg['page_param']}={page}"
            
            logger.info(f"{NEON['CYAN']}🔍 Scraping {engine} - Page {page}: {url}{NEON['RESET']}")
            
            raw_items = []
            try:
                if driver:
                    raw_items = extract_with_selenium(driver, url, cfg)
                else:
                    resp = session.get(url, timeout=DEFAULT_TIMEOUT)
                    if resp.status_code != 200:
                        logger.warning(f"HTTP {resp.status_code} for {url}")
                        continue
                    soup = BeautifulSoup(resp.text, "html.parser")
                    raw_items = extract_video_items(soup, cfg)
                
                if not raw_items:
                    logger.warning(f"{NEON['YELLOW']}No items found on page {page}. Stopping.{NEON['RESET']}")
                    break
                
                for item in raw_items:
                    if len(results) >= limit: break
                    data = extract_video_data_enhanced(item, cfg, cfg["url"])
                    if data: results.append(data)
                
                smart_sleep(DEFAULT_DELAY)
                
            except Exception as e:
                logger.error(f"Page {page} failed: {e}")
                continue
                
    finally:
        if driver:
            driver.quit()
            
    return results[:limit]

# ── Async Thumbnail Downloading ──────────────────────────────────────────

@asynccontextmanager
async def get_aiohttp_session():
    timeout = aiohttp.ClientTimeout(total=30)
    connector = aiohttp.TCPConnector(limit=20, ssl=False) # Optimized connector
    async with aiohttp.ClientSession(connector=connector, timeout=timeout, headers=get_realistic_headers(REALISTIC_USER_AGENTS[0])) as session:
        yield session

async def download_one_thumb(session, url: str, path: Path) -> bool:
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                content = await resp.read()
                if len(content) > 0:
                    with open(path, 'wb') as f:
                        f.write(content)
                    return True
    except Exception:
        return False
    return False

def sync_download_fallback(url: str, path: Path, session: requests.Session) -> bool:
    try:
        r = session.get(url, timeout=10, stream=True)
        if r.status_code == 200:
            with open(path, 'wb') as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            return True
    except:
        return False
    return False

async def process_thumbnails(results: list[dict], session_sync: requests.Session) -> list[str]:
    ensure_dir(THUMBNAILS_DIR)
    paths = []
    
    # Prepare tasks
    tasks = []
    if ASYNC_AVAILABLE:
        async with get_aiohttp_session() as aio_session:
            for idx, vid in enumerate(results):
                ext = os.path.splitext(urlparse(vid['img_url']).path)[1] or ".jpg"
                if len(ext) > 5: ext = ".jpg"
                fname = f"{enhanced_slugify(vid['title'])}_{idx}{ext}"
                fpath = THUMBNAILS_DIR / fname
                vid['_local_path'] = fpath
                
                if not fpath.exists():
                    tasks.append(download_one_thumb(aio_session, vid['img_url'], fpath))
                else:
                    tasks.append(asyncio.sleep(0)) # No-op
            
            # Execute Async
            if tasks:
                logger.info(f"{NEON['MAGENTA']}⬇️ Downloading {len(tasks)} thumbnails async...{NEON['RESET']}")
                for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), unit="img"):
                    await f
    
    # Fallback / Path Collection
    for vid in results:
        fpath = vid.get('_local_path')
        if fpath and fpath.exists() and fpath.stat().st_size > 0:
            # Make path relative for HTML
            try:
                rel = fpath.relative_to(OUTPUT_DIR)
                paths.append(str(rel))
            except ValueError:
                # If absolute path needed (e.g. separate drives), utilize file:// logic in template
                # For Termux/Local, relative from output dir is best if possible.
                # Here we copy/link or just use absolute path.
                paths.append(f"file://{fpath.absolute()}")
        else:
            # Sync Retry
            if fpath:
                if sync_download_fallback(vid['img_url'], fpath, session_sync):
                     paths.append(f"file://{fpath.absolute()}")
                else:
                    paths.append(vid['img_url']) # Failover to remote URL
            else:
                paths.append(vid['img_url'])

    return paths

# ── Output Generation ────────────────────────────────────────────────────

HTML_TEMPLATE = Template("""
<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$query - VSearch</title>
    <style>
        :root { --bg: #141414; --card: #1f1f1f; --text: #fff; --accent: #e50914; }
        body { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 20px; }
        .header { text-align: center; margin-bottom: 30px; padding: 20px; border-bottom: 1px solid #333; }
        .header h1 { margin: 0; color: var(--accent); text-transform: uppercase; letter-spacing: 2px; }
        .stats { color: #888; font-size: 0.9rem; margin-top: 10px; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }
        
        .card { background: var(--card); border-radius: 4px; overflow: hidden; transition: transform 0.3s, box-shadow 0.3s; position: relative; }
        .card:hover { transform: scale(1.03); box-shadow: 0 10px 20px rgba(0,0,0,0.5); z-index: 2; }
        
        .thumb-container { position: relative; padding-top: 56.25%; /* 16:9 aspect */ background: #000; overflow: hidden; }
        .thumb-container img { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; transition: opacity 0.3s; }
        .play-icon { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 3rem; opacity: 0; transition: opacity 0.3s; text-shadow: 0 2px 5px rgba(0,0,0,0.5); }
        .card:hover .play-icon { opacity: 1; }
        
        .info { padding: 15px; }
        .title { margin: 0 0 10px 0; font-size: 1rem; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .title a { color: var(--text); text-decoration: none; }
        .meta { display: flex; justify-content: space-between; font-size: 0.8rem; color: #aaa; }
        .tag { background: #333; padding: 2px 6px; border-radius: 2px; }
        
        .copy-btn {
            position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.7); 
            color: white; border: none; padding: 5px 10px; cursor: pointer; 
            opacity: 0; transition: opacity 0.2s; border-radius: 4px; font-size: 0.8rem;
        }
        .card:hover .copy-btn { opacity: 1; }
        .copy-btn:active { background: var(--accent); }

        /* Lazy loading blur effect */
        img.lazy { filter: blur(10px); }
        img.loaded { filter: blur(0); }
    </style>
</head>
<body>
    <div class="header">
        <h1>$engine Search</h1>
        <div class="stats">Query: "$query" • Results: $count • Generated: $date</div>
    </div>
    <div class="grid">
        $cards
    </div>
    <script>
        // Lazy Loading
        document.addEventListener("DOMContentLoaded", function() {
            const imageObserver = new IntersectionObserver((entries, imgObserver) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        const lazyImage = entry.target;
                        lazyImage.src = lazyImage.dataset.src;
                        lazyImage.onload = () => lazyImage.classList.add('loaded');
                        lazyImage.classList.remove("lazy");
                        imgObserver.unobserve(lazyImage);
                    }
                });
            });
            document.querySelectorAll('img[data-src]').forEach((v) => imageObserver.observe(v));
        });

        // Copy to Clipboard
        function copyLink(url) {
            navigator.clipboard.writeText(url).then(() => {
                alert("Link copied!");
            });
        }
    </script>
</body>
</html>
""")

def generate_html(results: list[dict], thumbnails: list[str], engine: str, query: str):
    cards = []
    for vid, thumb in zip(results, thumbnails):
        # Fallback image if local thumb failed
        if not thumb: thumb = vid['img_url']
        
        card = f"""
        <div class="card">
            <div class="thumb-container">
                <a href="{vid['link']}" target="_blank">
                    <img class="lazy" data-src="{thumb}" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" alt="{vid['title']}">
                    <div class="play-icon">▶</div>
                </a>
                <button class="copy-btn" onclick="copyLink('{vid['link']}')">📋 Copy</button>
            </div>
            <div class="info">
                <h3 class="title"><a href="{vid['link']}" target="_blank">{vid['title']}</a></h3>
                <div class="meta">
                    <span class="tag">{vid['time']}</span>
                    <span>{vid.get('channel', 'Unknown')}</span>
                    <span>{vid.get('meta', '')}</span>
                </div>
            </div>
        </div>
        """
        cards.append(card)
    
    ensure_dir(OUTPUT_DIR)
    filename = OUTPUT_DIR / f"{engine}_{enhanced_slugify(query)}.html"
    
    html_content = HTML_TEMPLATE.substitute(
        engine=engine.title(),
        query=query,
        count=len(results),
        date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        cards="\n".join(cards)
    )
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    return filename

# ── Main Ritual ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ultimate Video Search Tool 2025")
    parser.add_argument("query", help="Search terms")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=ENGINE_MAP.keys(), help="Search engine")
    parser.add_argument("-l", "--limit", type=int, default=DEFAULT_LIMIT, help="Max results")
    parser.add_argument("-p", "--page", type=int, default=DEFAULT_PAGE, help="Start page")
    parser.add_argument("--no-async", action="store_true", help="Disable async downloads")
    parser.add_argument("--no-open", action="store_true", help="Don't open browser after completion")
    parser.add_argument("-x", "--proxy", help="Proxy string (http://user:pass@ip:port)")
    
    args = parser.parse_args()
    
    print(f"{NEON['CYAN']}{Style.BRIGHT}>>> VSEARCH 2025: {args.engine.upper()} SEARCH INITIATED <<<{NEON['RESET']}")
    print(f"{NEON['WHITE']}Target: {args.query} | Limit: {args.limit}{NEON['RESET']}")

    # Setup Session
    proxies = [args.proxy] if args.proxy else None
    session = build_enhanced_session(proxies)

    # 1. Scrape Video Data
    results = get_search_results(session, args.engine, args.query, args.limit, args.page)

    if not results:
        print(f"{NEON['RED']}No results found. Try a different query or engine.{NEON['RESET']}")
        sys.exit(0)

    print(f"{NEON['GREEN']}Found {len(results)} videos. Processing assets...{NEON['RESET']}")

    # 2. Download Thumbnails (Async/Sync hybrid)
    # Only run asyncio loop if async is available and requested
    thumbnails = []
    if ASYNC_AVAILABLE and not args.no_async:
        try:
            if os.name == 'nt':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            thumbnails = asyncio.run(process_thumbnails(results, session))
        except Exception as e:
            logger.error(f"Async loop failed: {e}. Falling back to remote URLs.")
            thumbnails = [r['img_url'] for r in results]
    else:
        # Sync download logic could be placed here, currently just uses remote URLs if async off
        thumbnails = [r['img_url'] for r in results]

    # 3. Generate Report
    outfile = generate_html(results, thumbnails, args.engine, args.query)
    
    print(f"{NEON['CYAN']}✔ Done! Output saved to:{NEON['RESET']} {outfile}")
    
    if not args.no_open:
        try:
            import webbrowser
            webbrowser.open(f"file://{outfile.resolve()}")
        except Exception:
            print("Could not open browser automatically.")

if __name__ == "__main__":
    main()