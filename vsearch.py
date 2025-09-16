#!/usr/bin/env python3
"""vsearch.py  •  2025-09-12 (PYRMETHUS-ENHANCED-V3)

Pyrmethus' supreme video search grimoire, forged in the Termux crucible.
Channels all realms: youjizz, spankbang, motherless, pornhub, xnxx, xhamster, and more.
Fixes: Added asynccontextmanager import, enhanced dependency checks, and vibrant UX.
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
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from string import Template
from typing import Any
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from requests.adapters import HTTPAdapter, Retry

try:
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False
    print(f"{Fore.YELLOW}⚠️ aiohttp not found; async downloads disabled. Install with: pip install aiohttp{Fore.RESET}")

try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print(f"{Fore.YELLOW}⚠️ selenium not found; JS-heavy sites may fail. Install with: pip install selenium{Fore.RESET}")

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable
    print(f"{Fore.YELLOW}⚠️ tqdm not found; progress bars disabled. Install with: pip install tqdm{Fore.RESET}")

# ── Pyrmethus' Colorama Enchantment ─────────────────────────────────────
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

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.engine = getattr(record, 'engine', 'unknown')
        record.query = getattr(record, 'query', 'unknown')
        return True

log_handlers = [logging.StreamHandler(sys.stdout)]
try:
    log_handlers.append(logging.FileHandler("video_search.log", mode="a", encoding="utf-8"))
except PermissionError:
    print(f"{NEON['YELLOW']}⚠️ Cannot create log file; check Termux permissions{Fore.RESET}")

logging.basicConfig(level=logging.INFO, format=LOG_FMT, handlers=log_handlers)
logger = logging.getLogger(__name__)
logger.addFilter(ContextFilter())

for noisy in ("urllib3", "chardet", "requests", "aiohttp", "selenium"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# ── Termux-Optimized Defaults ───────────────────────────────────────────
THUMBNAILS_DIR = Path.home() / "downloaded_thumbnails"
OUTPUT_DIR = Path.home() / "vsearch_results"
DEFAULT_ENGINE = "pexels"
DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_FORMAT = "html"
DEFAULT_TIMEOUT = 15
DEFAULT_DELAY = (1.5, 3.5)
DEFAULT_MAX_RETRIES = 5
DEFAULT_WORKERS = 8
DEFAULT_CACHE_TTL = 7

REALISTIC_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
]

def get_realistic_headers(user_agent: str) -> dict[str, str]:
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": random.choice(["en-US,en;q=0.9", "en-GB,en;q=0.9"]),
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }

# ── Engine Map ─────────────────────────────────────────────────────────
ENGINE_MAP: dict[str, dict[str, Any]] = {
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
            "title": ["a[title]", "h3", ".video-title"],
            "img": ["img[data-src]", "img[src]", "img[data-preview]"],
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
        "img_selector": "img[src], img[data-src], img[data-lazy], img[data-thumb]",
        "time_selector": "var.duration, .duration, .videoblock__duration",
        "channel_name_selector": ".usernameWrap a, .channel-name, .videoblock__channel",
        "channel_link_selector": ".usernameWrap a, .channel-link",
        "meta_selector": ".views, .video-views, .videoblock__views",
        "fallback_selectors": {
            "title": [".title", "a[title]", "[data-title]"],
            "img": ["img[data-thumb]", "img[src]", "img[data-src]"],
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
            "img": ["img[data-src]", "img[src]", "img[data-preview]"],
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
            "img": ["img[data-src]", "img[src]", "img[data-preview]"],
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
        "channel_name_selector": "a.channel-name",
        "channel_link_selector": "a.channel-name",
        "fallback_selectors": {
            "title": ["a[title]", ".video-title", "h3"],
            "img": ["img[data-original]", "img[src]", "img[data-src]"],
            "link": ["a[href*='/videos/']"]
        }
    },
    "motherless": {
        "url": "https://www.motherless.com",
        "search_path": "/term/videos/{query}?page={page}",
        "page_param": "",
        "requires_js": False,
        "video_item_selector": "div.thumb.video",
        "link_selector": "a[href*='/video']",
        "title_selector": ".thumb-caption a",
        "title_attribute": "title",
        "img_selector": "img.thumb-img",
        "img_attribute": "src",
        "time_selector": ".thumb-duration",
        "meta_selector": ".thumb-views",
        "channel_name_selector": ".thumb-member a",
        "channel_link_selector": ".thumb-member a",
        "fallback_selectors": {
            "title": ["a[title]", ".caption-title", "h3"],
            "img": ["img[src]", "img[data-src]"],
            "link": ["a[href*='/video/']"]
        }
    },
    "spankbang": {
        "url": "https://spankbang.com",
        "search_path": "/s/{query}/{page}/",
        "page_param": "",
        "requires_js": True,
        "video_item_selector": "div.video-item",
        "link_selector": "a.thumb",
        "title_selector": "h2.n",
        "img_selector": "img.thumb",
        "img_attribute": "data-src",
        "time_selector": "span.l",
        "meta_selector": "span.v",
        "channel_name_selector": "a.u",
        "channel_link_selector": "a.u",
        "fallback_selectors": {
            "title": ["h2.n", "a[title]", ".video-title"],
            "img": ["img[data-src]", "img[src]", "img[data-preview]"],
            "link": ["a[href*='/video/']", "a.thumb"]
        }
    }
}

# ── Helper Incantations ─────────────────────────────────────────────────
def ensure_dir(path: Path) -> None:
    """Summon a directory sanctum with wards against failure."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        logger.error(f"{NEON['RED']}Permission denied summoning {path}{NEON['RESET']}")
        raise
    except OSError as e:
        logger.error(f"{NEON['RED']}Failed to summon {path}: {e}{NEON['RESET']}")
        raise

def cleanup_old_thumbnails(thumbs_dir: Path, ttl_days: int) -> None:
    """Banish expired thumbnails from the cache."""
    try:
        cutoff = datetime.now() - timedelta(days=ttl_days)
        for f in thumbs_dir.glob("*"):
            if f.is_file() and f.stat().st_mtime < cutoff.timestamp():
                f.unlink(missing_ok=True)
                logger.debug(f"{NEON['YELLOW']}Banished expired thumbnail: {f}{NEON['RESET']}")
    except Exception as e:
        logger.warning(f"{NEON['YELLOW']}Failed to clean thumbnails: {e}{NEON['RESET']}")

def enhanced_slugify(text: str) -> str:
    """Purify text into a safe slug, banishing Unicode demons."""
    if not text or not isinstance(text, str):
        return "untitled"
    text = html.unescape(text)
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "", text)
    text = re.sub(r"[^a-zA-Z0-9\s\-_.]", "", text)
    text = re.sub(r"\s+", "_", text.strip()).strip("._-")
    text = text[:100] or "untitled"
    reserved = {"con", "prn", "aux", "nul"} | {f"com{i}" for i in range(1,10)} | {f"lpt{i}" for i in range(1,10)}
    if text.lower() in reserved:
        text = f"file_{text}"
    return text

def build_enhanced_session(
    timeout: int = DEFAULT_TIMEOUT,
    max_retries: int = DEFAULT_MAX_RETRIES,
    proxies: list[str] | None = None,
) -> requests.Session:
    """Forge a session with retry wards and proxy cycles."""
    session = requests.Session()
    retries = Retry(
        total=max_retries,
        backoff_factor=1.5,
        backoff_jitter=0.3,
        status_forcelist=(429, 500, 502, 503, 504),
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=10, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    user_agent = random.choice(REALISTIC_USER_AGENTS)
    session.headers.update(get_realistic_headers(user_agent))
    if proxies:
        valid_proxies = [p for p in proxies if urlparse(p).scheme in ("http", "https")]
        if valid_proxies:
            proxy = random.choice(valid_proxies)
            session.proxies = {"http": proxy, "https": proxy}
            logger.info(f"{NEON['BLUE']}🪄 Cycling through proxy veil: {urlparse(proxy).netloc}{NEON['RESET']}")
    session.timeout = timeout
    return session

def smart_delay_with_jitter(
    delay_range: tuple[float, float],
    last_request_time: float | None = None,
) -> None:
    """Invoke a delay with jitter to evade watchful guardians."""
    min_delay, max_delay = delay_range
    current_time = time.time()
    base_wait = random.uniform(min_delay, max_delay)
    jitter = base_wait * 0.2 * random.uniform(-1, 1)
    wait_time = max(0.5, base_wait + jitter)
    if last_request_time and (elapsed := current_time - last_request_time) < wait_time:
        time.sleep(wait_time - elapsed)
    else:
        time.sleep(wait_time)

def create_selenium_driver() -> webdriver.Chrome | None:
    """Summon a Selenium phantom for JS-enchanted realms."""
    if not SELENIUM_AVAILABLE:
        logger.warning(f"{NEON['YELLOW']}⚠️ Selenium not available; JS realms may falter.{NEON['RESET']}")
        return None
    try:
        options = ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"--user-agent={random.choice(REALISTIC_USER_AGENTS)}")
        options.add_experimental_option("prefs", {"profile.managed_default_content_settings.images": 2})
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(15)
        return driver
    except Exception as e:
        logger.warning(f"{NEON['YELLOW']}Failed to summon Selenium phantom: {e}{NEON['RESET']}")
        return None

def extract_with_selenium(driver: webdriver.Chrome, url: str, cfg: dict) -> list:
    """Pierce JS veils with Selenium to extract items."""
    try:
        driver.get(url)
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, cfg["video_item_selector"].split(",")[0]))
        )
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        return extract_video_items(soup, cfg)
    except TimeoutException:
        logger.warning(f"{NEON['YELLOW']}Selenium timeout for {url}{NEON['RESET']}")
        return []
    except Exception as e:
        logger.error(f"{NEON['RED']}Selenium extraction failed for {url}: {e}{NEON['RESET']}")
        return []

@asynccontextmanager
async def aiohttp_session() -> AsyncGenerator[aiohttp.ClientSession | None, None]:
    """Conjure an async session for thumbnail summons."""
    if not ASYNC_AVAILABLE:
        yield None
        return
    timeout = aiohttp.ClientTimeout(total=15, connect=5)
    headers = get_realistic_headers(random.choice(REALISTIC_USER_AGENTS))
    try:
        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=aiohttp.TCPConnector(limit=15, limit_per_host=5)
        ) as session:
            yield session
    except Exception as e:
        logger.error(f"{NEON['RED']}Failed to conjure aiohttp session: {e}{NEON['RESET']}")
        yield None

async def async_download_thumbnail(
    session: aiohttp.ClientSession,
    url: str,
    path: Path,
    semaphore: asyncio.Semaphore,
    max_attempts: int = DEFAULT_MAX_RETRIES,
) -> bool:
    """Async summon thumbnail with retry wards."""
    for attempt in range(max_attempts):
        async with semaphore:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        content_type = response.headers.get("content-type", "").lower()
                        if "image/" not in content_type:
                            logger.debug(f"{NEON['YELLOW']}Invalid content type for {url}{NEON['RESET']}")
                            return False
                        content = await response.read()
                        if len(content) < 1024 or len(content) > 5 * 1024 * 1024:
                            logger.debug(f"{NEON['YELLOW']}Invalid size for {url}{NEON['RESET']}")
                            return False
                        path.write_bytes(content)
                        return path.stat().st_size > 0
                    logger.debug(f"{NEON['YELLOW']}Failed (status {response.status}) for {url}{NEON['RESET']}")
            except Exception as e:
                logger.debug(f"{NEON['YELLOW']}Async summon failed (attempt {attempt+1}): {e}{NEON['RESET']}")
        if attempt < max_attempts - 1:
            await asyncio.sleep(1.5 ** attempt + random.uniform(0, 0.3))
    path.unlink(missing_ok=True)
    return False

def robust_download_sync(session: requests.Session, url: str, path: Path, max_attempts: int = DEFAULT_MAX_RETRIES) -> bool:
    """Synchronous fallback summon with validation."""
    for attempt in range(max_attempts):
        try:
            session.headers.update(get_realistic_headers(random.choice(REALISTIC_USER_AGENTS)))
            with session.get(url, stream=True, timeout=10) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").lower()
                if "image/" not in content_type:
                    logger.debug(f"{NEON['YELLOW']}Invalid content type for {url}{NEON['RESET']}")
                    return False
                content_length = response.headers.get("content-length")
                if content_length and (int(content_length) < 1024 or int(content_length) > 5 * 1024 * 1024):
                    logger.debug(f"{NEON['YELLOW']}Invalid size for {url}{NEON['RESET']}")
                    return False
                with open(path, "wb") as f:
                    for chunk in response.iter_content(8192):
                        f.write(chunk)
                if path.stat().st_size > 1024:
                    return True
                path.unlink(missing_ok=True)
            logger.debug(f"{NEON['YELLOW']}Failed (attempt {attempt+1}) for {url}{NEON['RESET']}")
        except Exception as e:
            logger.debug(f"{NEON['YELLOW']}Sync summon failed (attempt {attempt+1}): {e}{NEON['RESET']}")
        time.sleep(1.5 ** attempt + random.uniform(0, 0.3))
    return False

def get_search_results(
    session: requests.Session,
    engine: str,
    query: str,
    limit: int,
    page: int,
    delay_range: tuple[float, float],
) -> list[dict]:
    """Scrape realms for video essences with enhanced wards."""
    if engine not in ENGINE_MAP:
        logger.error(f"{NEON['RED']}Unknown realm: {engine}{NEON['RESET']}", extra={'engine': engine, 'query': query})
        return []
    cfg = ENGINE_MAP[engine]
    base_url = cfg["url"]
    results: list[dict] = []
    last_request_time = None
    driver = None
    if cfg.get("requires_js", False) and SELENIUM_AVAILABLE:
        driver = create_selenium_driver()
    try:
        items_per_page = 40
        pages_to_fetch = min(5, (limit + items_per_page - 1) // items_per_page)
        logger.info(f"{NEON['CYAN']}🪄 Channeling search in {engine} for '{query}' (up to {pages_to_fetch} veils)...{NEON['RESET']}", extra={'engine': engine, 'query': query})
        for current_page in range(page, page + pages_to_fetch):
            if len(results) >= limit:
                break
            smart_delay_with_jitter(delay_range, last_request_time)
            last_request_time = time.time()
            search_path = cfg["search_path"].format(query=quote_plus(query), page=current_page) if "{page}" in cfg["search_path"] else cfg["search_path"].format(query=quote_plus(query))
            url = urljoin(base_url, search_path)
            if current_page > 1 and "{page}" not in cfg["search_path"] and cfg.get("page_param"):
                separator = "&" if "?" in url else "?"
                url += f"{separator}{cfg['page_param']}={current_page}"
            logger.info(f"{NEON['BLUE']}🔍 Piercing veil {current_page}: {url}{NEON['RESET']}", extra={'engine': engine, 'query': query})
            try:
                if driver and cfg.get("requires_js", False):
                    video_items = extract_with_selenium(driver, url, cfg)
                else:
                    session.headers.update(get_realistic_headers(random.choice(REALISTIC_USER_AGENTS)))
                    response = session.get(url)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, "html.parser")
                    video_items = extract_video_items(soup, cfg)
                if not video_items:
                    continue
                for item in video_items:
                    if len(results) >= limit:
                        break
                    video_data = extract_video_data_enhanced(item, cfg, base_url)
                    if video_data and validate_video_data_enhanced(video_data):
                        results.append(video_data)
            except Exception as e:
                logger.error(f"{NEON['RED']}Veil {current_page} resisted: {e}{NEON['RESET']}", extra={'engine': engine, 'query': query})
    finally:
        if driver:
            driver.quit()
    logger.info(f"{NEON['GREEN']}🚀 Extracted {len(results)} essences from the void.{NEON['RESET']}", extra={'engine': engine, 'query': query})
    return results[:limit]

def extract_video_items(soup: BeautifulSoup, cfg: dict) -> list:
    """Extract item vessels with fallback divinations."""
    video_items = []
    for selector in cfg["video_item_selector"].split(", "):
        video_items = soup.select(selector.strip())
        if video_items:
            break
    if not video_items and "fallback_selectors" in cfg:
        for selector in cfg["fallback_selectors"].get("container", []):
            video_items = soup.select(selector)
            if video_items:
                break
    return video_items

def extract_video_data_enhanced(item, cfg: dict, base_url: str) -> dict | None:
    """Divine video data with layered fallbacks."""
    try:
        title_selectors = [cfg.get("title_selector", "")] + cfg["fallback_selectors"].get("title", [])
        title = "Untitled"
        for selector in title_selectors:
            title_el = item.select_one(selector)
            if title_el:
                attr = cfg.get("title_attribute")
                title = title_el.get(attr, "").strip() if attr else title_el.get_text(strip=True)
                if title:
                    break
        link_selectors = [cfg.get("link_selector", "")] + cfg["fallback_selectors"].get("link", [])
        link = "#"
        for selector in link_selectors:
            link_el = item.select_one(selector)
            if link_el and link_el.has_attr("href"):
                link = urljoin(base_url, link_el["href"])
                if link != "#":
                    break
        img_selectors = [cfg.get("img_selector", "")] + cfg["fallback_selectors"].get("img", [])
        img_url = None
        for selector in img_selectors:
            img_el = item.select_one(selector)
            if img_el:
                for attr in ["data-src", "src", "data-lazy", "data-original", "data-thumb", cfg.get("img_attribute", "")]:
                    if attr and img_el.has_attr(attr):
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
        if cfg.get("channel_link_selector"):
            channel_el = item.select_one(cfg["channel_link_selector"])
            if channel_el and channel_el.has_attr("href"):
                channel_link = urljoin(base_url, channel_el["href"])
        return {
            "title": html.escape(title[:200]),
            "link": link,
            "img_url": img_url,
            "time": duration,
            "channel_name": channel_name,
            "channel_link": channel_link,
            "meta": views,
            "extracted_at": datetime.now().isoformat(),
            "source_engine": base_url,
        }
    except Exception as e:
        logger.debug(f"{NEON['YELLOW']}Data divination failed: {e}{NEON['RESET']}")
        return None

def extract_text_safe(element, selector: str, default: str = "N/A") -> str:
    """Safely divine text from elements."""
    if not selector:
        return default
    try:
        el = element.select_one(selector)
        return el.get_text(strip=True) if el else default
    except Exception:
        return default

def validate_video_data_enhanced(data: dict) -> bool:
    """Validate data essence with strict wards."""
    if not data or not all(key in data for key in ["title", "link"]):
        return False
    if data["title"] in ["", "Untitled"] or data["link"] == "#":
        return False
    parsed = urlparse(data["link"])
    if not parsed.scheme or not parsed.netloc:
        return False
    if len(data["title"]) < 3:
        return False
    return True

# ── Enhanced HTML Grimoire ──────────────────────────────────────────────
ENHANCED_HTML_HEAD = Template("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$title</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@500&display=swap" rel="stylesheet">
    <style>
        :root {
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
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            overflow-x: hidden;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 2rem;
            background: var(--bg-secondary);
            border-radius: 20px;
            margin-top: 2rem;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        }
        .header {
            text-align: center;
            margin-bottom: 3rem;
            position: relative;
        }
        .header::before {
            content: '';
            position: absolute;
            top: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 100px;
            height: 4px;
            background: var(--gradient);
            border-radius: 2px;
        }
        h1 {
            font-family: 'JetBrains Mono', monospace;
            font-size: 2.5rem;
            font-weight: 700;
            background: var(--gradient);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
            text-shadow: 0 0 20px var(--shadow);
        }
        .subtitle {
            color: var(--text-secondary);
            font-size: 1.1rem;
        }
        .stats {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin: 1.5rem 0;
            flex-wrap: wrap;
        }
        .stat {
            background: var(--bg-card);
            padding: 0.75rem 1.5rem;
            border-radius: 25px;
            border: 1px solid var(--border);
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
        }
        .video-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 2rem;
            margin-top: 2rem;
        }
        .video-card {
            background: var(--bg-card);
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--border);
            transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            position: relative;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            display: flex;
            flex-direction: column;
        }
        .video-card:hover {
            transform: translateY(-8px) scale(1.02);
            box-shadow: 0 20px 40px var(--shadow);
            border-color: var(--accent-cyan);
        }
        .video-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: var(--gradient);
            opacity: 0;
            transition: opacity 0.3s;
        }
        .video-card:hover::before { opacity: 1; }
        .thumbnail {
            position: relative;
            width: 100%;
            height: 200px;
            overflow: hidden;
            background: var(--bg-primary);
        }
        .thumbnail img {
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.3s;
        }
        .video-card:hover .thumbnail img { transform: scale(1.1); }
        .play-overlay {
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
            transition: all 0.3s;
            cursor: pointer;
        }
        .video-card:hover .play-overlay {
            opacity: 1;
            transform: translate(-50%, -50%) scale(1.1);
        }
        .play-overlay::before {
            content: '▶';
            color: white;
            font-size: 1.2rem;
            margin-left: 3px;
        }
        .video-info {
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }
        .video-title {
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 1rem;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .video-title a {
            color: inherit;
            text-decoration: none;
            transition: color 0.3s;
        }
        .video-title a:hover { color: var(--accent-cyan); }
        .video-meta {
            display: flex;
            flex-wrap: wrap;
            gap: 0.75rem;
            margin-top: auto;
            padding-top: 1rem;
            border-top: 1px solid var(--border);
            font-size: 0.85rem;
        }
        .meta-item {
            background: rgba(0, 212, 255, 0.1);
            color: var(--accent-cyan);
            padding: 0.3rem 0.8rem;
            border-radius: 15px;
            font-family: 'JetBrains Mono', monospace;
            white-space: nowrap;
        }
        .loading-placeholder {
            background: linear-gradient(90deg, var(--bg-card) 25%, rgba(255,255,255,0.05) 50%, var(--bg-card) 75%);
            background-size: 200% 100%;
            animation: loading 1.5s infinite;
        }
        @keyframes loading {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
        }
        @media (max-width: 768px) {
            .container { padding: 1rem; }
            .video-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>$query</h1>
            <p class="subtitle">Essences from $engine</p>
            <div class="stats">
                <div class="stat">🎬 $count videos</div>
                <div class="stat">🔍 $engine</div>
                <div class="stat">⏰ $timestamp</div>
            </div>
        </header>
        <main class="video-grid">
""")

ENHANCED_HTML_TAIL = """        </main>
    </div>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const obs = new IntersectionObserver(entries => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.onload = () => img.removeAttribute('data-src');
                        obs.unobserve(img);
                    }
                });
            });
            document.querySelectorAll('img[data-src]').forEach(img => obs.observe(img));
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
    no_thumbs: bool = False,
    cache_ttl: int = DEFAULT_CACHE_TTL,
) -> Path:
    """Weave an HTML gallery with async thumbnail summons."""
    ensure_dir(OUTPUT_DIR)
    ensure_dir(thumbs_dir)
    cleanup_old_thumbnails(thumbs_dir, cache_ttl)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{engine}_{enhanced_slugify(query)}_{timestamp}.html"
    outfile = OUTPUT_DIR / filename

    def get_thumb_path(img_url: str, title: str, idx: int) -> Path:
        ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
        safe_title = enhanced_slugify(title)[:50]
        return thumbs_dir / f"{safe_title}_{idx}{ext}"

    def generate_placeholder_svg(icon: str) -> str:
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%"><rect width="100%" height="100%" fill="#16213e"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="2rem" fill="#666">{icon}</text></svg>'
        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

    async def fetch_thumbnail_async_task(idx: int, video: dict) -> tuple[int, str]:
        img_url = video.get("img_url")
        if no_thumbs or not img_url:
            return idx, generate_placeholder_svg("🎬")
        path = get_thumb_path(img_url, video.get("title", "untitled"), idx)
        if path.exists() and path.stat().st_size > 1024:
            rel_path = os.path.relpath(path, outfile.parent).replace("\\", "/")
            return idx, rel_path
        async with aiohttp_session() as async_session:
            if async_session:
                semaphore = asyncio.Semaphore(workers)
                if await async_download_thumbnail(async_session, img_url, path, semaphore):
                    rel_path = os.path.relpath(path, outfile.parent).replace("\\", "/")
                    return idx, rel_path
        if robust_download_sync(session, img_url, path):
            rel_path = os.path.relpath(path, outfile.parent).replace("\\", "/")
            return idx, rel_path
        return idx, generate_placeholder_svg("❌")

    thumbnail_paths = [""] * len(results)
    if ASYNC_AVAILABLE and not no_thumbs:
        tasks = [fetch_thumbnail_async_task(i, video) for i, video in enumerate(results)]
        progress = tqdm(tasks, desc=f"{NEON['MAGENTA']}🪄 Summoning Thumbnails{NEON['RESET']}", total=len(tasks))
        for result in await asyncio.gather(*tasks, return_exceptions=True):
            progress.update(1)
            if isinstance(result, tuple):
                idx, path = result
                thumbnail_paths[idx] = path
        progress.close()
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(robust_download_sync, session, video.get("img_url"), get_thumb_path(video.get("img_url", ""), video.get("title", ""), i)): i
                for i, video in enumerate(results) if not no_thumbs and video.get("img_url")
            }
            progress = tqdm(futures, desc=f"{NEON['MAGENTA']}🪄 Summoning Thumbnails{NEON['RESET']}", total=len(futures))
            for future in concurrent.futures.as_completed(futures):
                i = futures[future]
                progress.update(1)
                try:
                    if future.result():
                        path = get_thumb_path(results[i]["img_url"], results[i]["title"], i)
                        rel_path = os.path.relpath(path, outfile.parent).replace("\\", "/")
                        thumbnail_paths[i] = rel_path
                    else:
                        thumbnail_paths[i] = generate_placeholder_svg("❌")
                except Exception:
                    thumbnail_paths[i] = generate_placeholder_svg("❌")
            progress.close()

    with open(outfile, "w", encoding="utf-8") as f:
        f.write(ENHANCED_HTML_HEAD.substitute(
            title=f"{html.escape(query)} - {engine}",
            query=html.escape(query),
            engine=engine.title(),
            count=len(results),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
        ))
        for video, thumb in zip(results, thumbnail_paths, strict=False):
            meta_items = []
            if video["time"] != "N/A":
                meta_items.append(f'<span class="meta-item">⏱️ {html.escape(video["time"])}</span>')
            if video["channel_name"] != "N/A":
                ch_link = html.escape(video["channel_link"]) if video["channel_link"] != "#" else "#"
                meta_items.append(f'<span class="meta-item"><a href="{ch_link}" target="_blank" rel="noopener noreferrer">👤 {html.escape(video["channel_name"])}</a></span>')
            if video["meta"] != "N/A":
                meta_items.append(f'<span class="meta-item">👁️ {html.escape(video["meta"])}</span>')
            f.write(f'''
            <div class="video-card">
                <a href="{html.escape(video['link'])}" target="_blank" rel="noopener noreferrer">
                    <div class="thumbnail">
                        <img data-src="{html.escape(thumb)}" alt="{html.escape(video['title'])}" loading="lazy">
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
    logger.info(f"{NEON['CYAN']}📜 HTML grimoire woven at: {outfile}{NEON['RESET']}")
    return outfile

# ── Main Ritual ─────────────────────────────────────────────────────────
def list_engines():
    """Display available realms in a table."""
    print(f"{NEON['CYAN']}🪄 Available Realms:{NEON['RESET']}")
    print(f"{NEON['BLUE']}{'Engine':<15} {'URL':<40} {'JS Required':<12}{NEON['RESET']}")
    print(f"{NEON['BLUE']}{'-'*15} {'-'*40} {'-'*12}{NEON['RESET']}")
    for engine, cfg in sorted(ENGINE_MAP.items()):
        js_color = NEON['RED'] if cfg.get('requires_js', False) else NEON['GREEN']
        print(f"{NEON['GREEN']}{engine:<15} {cfg['url']:<40} {js_color}{cfg.get('requires_js', False)!s:<12}{NEON['RESET']}")

def main():
    parser = argparse.ArgumentParser(
        description="Pyrmethus' supreme video search grimoire.",
        epilog="Summon examples: python vsearch.py 'cats' -e spankbang -l 50",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("query", help="The essence to seek.")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=list(ENGINE_MAP), help="Realm to pierce.")
    parser.add_argument("-l", "--limit", type=int, default=DEFAULT_LIMIT, help="Max essences.")
    parser.add_argument("-p", "--page", type=int, default=DEFAULT_PAGE, help="Starting veil.")
    parser.add_argument("-o", "--output-format", default=DEFAULT_FORMAT, choices=["html", "json"], help="Output form.")
    parser.add_argument("-x", "--proxy", help="Proxy veils (comma-separated).")
    parser.add_argument("-w", "--workers", type=int, default=DEFAULT_WORKERS, help="Concurrent spirits.")
    parser.add_argument("--cache-ttl", type=int, default=DEFAULT_CACHE_TTL, help="Thumbnail cache TTL (days).")
    parser.add_argument("--no-async", action="store_true", help="Banish async, use threads.")
    parser.add_argument("--no-thumbs", action="store_true", help="Skip thumbnail summons.")
    parser.add_argument("--no-open", action="store_true", help="Do not unveil in browser.")
    parser.add_argument("-v", "--verbose", action="store_true", help="Reveal deeper logs.")
    parser.add_argument("--list-engines", action="store_true", help="List available realms.")
    args = parser.parse_args()

    if args.list_engines:
        list_engines()
        sys.exit(0)

    if args.verbose:
        logger.setLevel(logging.DEBUG)
    global ASYNC_AVAILABLE
    if args.no_async:
        ASYNC_AVAILABLE = False

    def signal_handler(sig, frame):
        print(f"\n{NEON['YELLOW']}🪄 Ctrl+C detected. Dissolving ritual...{NEON['RESET']}")
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    proxies = [p.strip() for p in args.proxy.split(",")] if args.proxy else None
    session = build_enhanced_session(proxies=proxies)

    sanitized_query = enhanced_slugify(args.query)
    print(f"{NEON['CYAN']}{NEON['BRIGHT']}🪄 Igniting search for '{args.query}' in {args.engine}...{NEON['RESET']}")

    results = get_search_results(session, args.engine, args.query, args.limit, args.page, DEFAULT_DELAY)

    if not results:
        print(f"{NEON['RED']}No essences found in '{args.query}' realm of {args.engine}.{NEON['RESET']}")
        sys.exit(1)

    print(f"{NEON['GREEN']}🚀 Summoned {len(results)} video essences.{NEON['RESET']}")

    if args.output_format == "json":
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{args.engine}_{sanitized_query}_{timestamp}.json"
        outfile = OUTPUT_DIR / filename
        ensure_dir(outfile.parent)
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        print(f"{NEON['CYAN']}📜 JSON scroll etched at: {outfile}{NEON['RESET']}")
    else:
        import webbrowser
        outfile = asyncio.run(build_enhanced_html_async(
            results, args.query, args.engine, THUMBNAILS_DIR, session, args.workers, args.no_thumbs, args.cache_ttl
        ))
        if not args.no_open:
            webbrowser.open(f"file://{outfile.absolute()}")

if __name__ == "__main__":
    main()
