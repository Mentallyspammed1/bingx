#!/usr/bin/env python3
"""
video_search.py • ULTIMATE EDITION V4 • 2025-12-12

Upgraded unified video search + scraping + gallery generator.

Key upgrades vs V3:
- Safer CLI defaults + better headless flag behavior
- Structured dataclasses for results + robust normalization
- Better engine config handling (page building, referer, per_page)
- Improved parsing resiliency (multi-selector fallback, link/img/title inference)
- Async thumbnail downloader hardened (content-type checks, atomic writes, retries)
- Better referer injection rules (engine base url, item link fallback)
- Optional JSON export + no-thumb mode + output path controls
- Graceful Selenium handling (optional wait selector, scroll loop)
- More robust logging + predictable exit codes

Notes:
- Scraping sites may block, change markup, or disallow automation. Use responsibly and legally.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import concurrent.futures
import dataclasses
import html
import json
import logging
import os
import random
import re
import sys
import time
import unicodedata
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter, Retry

# --- Optional Dependencies (Graceful Degradation) ---
try:
    from colorama import Fore, Style, init as colorama_init

    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

    class Fore:
        CYAN = MAGENTA = GREEN = YELLOW = RED = BLUE = WHITE = RESET = ""

    class Style:
        BRIGHT = RESET_ALL = ""

    def colorama_init(autoreset: bool = True) -> None:
        return


try:
    import aiohttp

    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False
    aiohttp = None  # type: ignore

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
    webdriver = None  # type: ignore

try:
    from tqdm import tqdm
except ImportError:

    def tqdm(iterable, **kwargs):
        return iterable


# ── Logging & UI Setup ───────────────────────────────────────────────────
colorama_init(autoreset=True)

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

logger = logging.getLogger("video_search")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(LOG_FMT, datefmt="%H:%M:%S"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Suppress noisy library logs
for lib in ["urllib3", "chardet", "requests", "aiohttp", "selenium", "webdriver_manager"]:
    logging.getLogger(lib).setLevel(logging.WARNING)

# ── Configuration & Constants ────────────────────────────────────────────
DEFAULT_ENGINE = "pexels"
DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_TIMEOUT = 20
DEFAULT_WORKERS = 12

DEFAULT_THUMBS_DIR = Path("downloaded_thumbnails")
DEFAULT_OUTPUT_DIR = Path("vsearch_results")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
]


def get_headers(referer: Optional[str] = None) -> dict[str, str]:
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    if referer:
        headers["Referer"] = referer
    return headers


# ── Engine Definitions ───────────────────────────────────────────────────
ENGINE_MAP: dict[str, dict[str, Any]] = {
    # --- Mainstream ---
    "pexels": {
        "url": "https://www.pexels.com",
        "search_path": "/search/videos/{query}/",
        "page_param": "page",
        "requires_js": False,
        "per_page": 24,
        "video_item_selector": "article.hide-favorite-badge-container, article[data-testid='video-card']",
        "link_selector": 'a[data-testid="video-card-link"], a.video-link',
        "title_selector": 'img[data-testid="video-card-img"], .video-title',
        "title_attribute": "alt",
        "img_selector": 'img[data-testid="video-card-img"], img.video-thumbnail',
        "channel_name_selector": 'a[data-testid="video-card-user-avatar-link"] > span, .author-name',
        "channel_link_selector": 'a[data-testid="video-card-user-avatar-link"]',
    },
    "dailymotion": {
        "url": "https://www.dailymotion.com",
        "search_path": "/search/{query}/videos",
        "page_param": "page",
        "requires_js": True,
        "per_page": 20,
        "video_item_selector": 'div[data-testid="video-card"], .video-item',
        "link_selector": 'a[data-testid="card-link"], .video-link',
        "title_selector": 'div[data-testid="card-title"], .video-title',
        "img_selector": 'img[data-testid="card-thumbnail"], img.thumbnail',
        "time_selector": 'span[data-testid="card-duration"], .duration',
        "channel_name_selector": 'div[data-testid="card-owner-name"], .owner-name',
        "channel_link_selector": 'a[data-testid="card-owner-link"]',
        "selenium_wait_selector": 'div[data-testid="video-card"], .video-item',
    },
    # --- Adult ---
    "pornhub": {
        "url": "https://www.pornhub.com",
        "search_path": "/video/search?search={query}",
        "page_param": "page",
        "requires_js": False,
        "per_page": 30,
        "video_item_selector": "li.pcVideoListItem, div.videoblock",
        "link_selector": "a.previewVideo, a.linkVideoThumb",
        "title_selector": "a.previewVideo .title, span.title a",
        "title_attribute": "title",
        "img_selector": "img",
        "img_attribute": "data-src",
        "time_selector": "var.duration",
        "channel_name_selector": ".usernameWrap a",
        "meta_selector": ".views, .video-views",
        "fallback_selectors": {
            "title": [".title", "a[title]"],
            "img": ["img[data-medium-thumb]", "img[data-thumb_url]", "img[src]"],
        },
    },
    "xnxx": {
        "url": "https://www.xnxx.com",
        "search_path": "/search/{query}/",
        "page_param": "p",
        "requires_js": False,
        "per_page": 40,
        "video_item_selector": "div.thumb-block, .mozaique > div",
        "link_selector": "div.thumb-under a",
        "title_selector": "div.thumb-under a",
        "title_attribute": "title",
        "img_selector": "div.thumb img",
        "img_attribute": "data-src",
        "time_selector": "span.duration",
        "fallback_selectors": {"img": ["img[src]"]},
    },
    "xvideos": {
        "url": "https://www.xvideos.com",
        "search_path": "/?k={query}",
        "page_param": "p",
        "requires_js": False,
        "per_page": 40,
        "video_item_selector": "div.thumb-block, .mozaique > div",
        "link_selector": ".thumb-under a, p.title a",
        "title_selector": ".thumb-under a, p.title a",
        "title_attribute": "title",
        "img_selector": "div.thumb img",
        "img_attribute": "data-src",
        "time_selector": "span.duration",
        "fallback_selectors": {"img": ["img[src]"]},
    },
    "xhamster": {
        "url": "https://xhamster.com",
        "search_path": "/search/{query}",
        "page_param": "page",
        "requires_js": True,
        "per_page": 30,
        "video_item_selector": "div.video-thumb",
        "link_selector": "a.video-thumb__image-container",
        "title_selector": "a.video-thumb-info__name",
        "img_selector": "img.thumb-image-container__image",
        "time_selector": "div.thumb-image-container__duration",
        "channel_name_selector": "a.video-uploader__name",
        "selenium_wait_selector": "div.video-thumb",
    },
    "youjizz": {
        "url": "https://www.youjizz.com",
        "search_path": "/search/{query}-{page}.html",
        "page_param": "",
        "requires_js": True,
        "per_page": 30,
        "video_item_selector": "div.video-thumb",
        "link_selector": "a.frame",
        "title_selector": ".video-title",
        "img_selector": "img.lazy",
        "img_attribute": "data-original",
        "time_selector": "span.time",
        "meta_selector": "span.views",
        "selenium_wait_selector": "div.video-thumb",
    },
    "spankbang": {
        "url": "https://spankbang.com",
        "search_path": "/s/{query}/{page}/",
        "page_param": "",
        "requires_js": True,
        "per_page": 30,
        "video_item_selector": "div.video-item",
        "link_selector": "a.thumb",
        "title_selector": "a.n",
        "img_selector": "img.cover",
        "img_attribute": "data-src",
        "time_selector": "span.l",
        "selenium_wait_selector": "div.video-item",
    },
    "eporner": {
        "url": "https://www.eporner.com",
        "search_path": "/search/{query}/{page}",
        "page_param": "",
        "requires_js": False,
        "per_page": 30,
        "video_item_selector": "div.video-box",
        "link_selector": "a.video-link",
        "title_selector": "a.video-link",
        "img_selector": "img.lazy",
        "img_attribute": "data-src",
        "time_selector": "span.duration",
    },
    "hqporner": {
        "url": "https://hqporner.com",
        "search_path": "/?q={query}",
        "page_param": "p",
        "requires_js": False,
        "per_page": 30,
        "video_item_selector": "div.video-block",
        "link_selector": "a.link",
        "title_selector": "h4.title",
        "img_selector": "img",
        "img_attribute": "src",
        "time_selector": "span.duration",
    },
    "youporn": {
        "url": "https://www.youporn.com",
        "search_path": "/search/?query={query}&page={page}",
        "page_param": "page",
        "requires_js": False,
        "per_page": 30,
        "video_item_selector": "div.video-box",
        "link_selector": "a[href*='/watch/']",
        "title_selector": "div.video-box-title",
        "img_selector": "img.thumb-image",
        "img_attribute": "data-src",
        "time_selector": "div.video-duration",
    },
    "redtube": {
        "url": "https://www.redtube.com",
        "search_path": "/?search={query}",
        "page_param": "page",
        "requires_js": False,
        "per_page": 30,
        "video_item_selector": "li.video_item",
        "link_selector": "a.video_link",
        "title_selector": "span.video_title",
        "img_selector": "img.video_thumb",
        "img_attribute": "data-src",
        "time_selector": "span.duration",
    },
    "thumbzilla": {
        "url": "https://www.thumbzilla.com",
        "search_path": "/video/search?q={query}&page={page}",
        "page_param": "page",
        "requires_js": False,
        "per_page": 30,
        "video_item_selector": "div.js-item",
        "link_selector": "a.js-thumb",
        "title_selector": "span.title",
        "img_selector": "img",
        "img_attribute": "data-src",
        "time_selector": "span.duration",
        "fallback_selectors": {"img": ["img[data-thumb-url]", "img[src]"]},
    },
    "tube8": {
        "url": "https://www.tube8.com",
        "search_path": "/searches.html?q={query}&page={page}",
        "page_param": "page",
        "requires_js": False,
        "per_page": 30,
        "video_item_selector": "div.video_box",
        "link_selector": "a",
        "title_selector": "div.video_title",
        "img_selector": "img",
        "img_attribute": "data-src",
        "time_selector": "span.video_duration",
    },
    "motherless": {
        "url": "https://www.motherless.com",
        "search_path": "/term/videos/{query}?page={page}",
        "page_param": "",
        "requires_js": False,
        "per_page": 28,
        "video_item_selector": "div.thumb",
        "link_selector": "a.img-container",
        "title_selector": ".caption-title",
        "img_selector": "img.static",
        "img_attribute": "src",
        "time_selector": ".thumb-duration",
    },
    "rule34video": {
        "url": "https://rule34video.com",
        "search_path": "/search/?q={query}",
        "page_param": "page",
        "requires_js": False,
        "per_page": 24,
        "video_item_selector": "div.item",
        "link_selector": "a.img",
        "title_selector": "a.title",
        "img_selector": "img.thumb",
        "img_attribute": "data-src",
        "time_selector": "div.duration",
        "fallback_selectors": {"img": ["img[src]"]},
    },
    "hentaihaven": {
        "url": "https://hentaihaven.xxx",
        "search_path": "/?s={query}",
        "page_param": "paged",
        "requires_js": False,
        "per_page": 20,
        "video_item_selector": "div.c-tabs-item__content",
        "link_selector": "a",
        "title_selector": "div.c-tabs-item__title",
        "img_selector": "img",
        "img_attribute": "src",
    },
    "ehentai": {
        "url": "https://e-hentai.org",
        "search_path": "/?f_search={query}",
        "page_param": "page",
        "requires_js": False,
        "per_page": 25,
        "video_item_selector": "div.itg.gld > div, div.gallery-item",
        "link_selector": "a",
        "title_selector": "div.glink",
        "img_selector": "img",
        "img_attribute": "src",
    },
}


# ── Data Model ───────────────────────────────────────────────────────────
@dataclasses.dataclass(slots=True)
class VideoResult:
    title: str
    link: str
    img_url: Optional[str] = None
    time: str = "N/A"
    channel: str = "N/A"
    channel_link: str = "#"
    views: str = "N/A"
    engine: str = ""

    # Output-only
    local_thumb: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        d = dataclasses.asdict(self)
        return d


# ── Helper Functions ─────────────────────────────────────────────────────
def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def sanitize_filename(text: str) -> str:
    if not text:
        return "untitled"
    text = html.unescape(text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)[:80]


def smart_delay(delay_range: tuple[float, float]) -> None:
    time.sleep(random.uniform(*delay_range))


def build_session(proxies: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT) -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    s.mount("http://", HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=50))
    s.mount("https://", HTTPAdapter(max_retries=retries, pool_connections=50, pool_maxsize=50))
    s.headers.update(get_headers())
    if proxies:
        s.proxies.update({"http": proxies, "https": proxies})
    # Optional: store timeout to reuse
    s.request_timeout = timeout  # type: ignore[attr-defined]
    return s


def normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def first_select(element, selectors: str):
    """Try comma-separated selectors; return first matching element."""
    if not element or not selectors:
        return None
    for sel in selectors.split(","):
        sel = sel.strip()
        if not sel:
            continue
        found = element.select_one(sel)
        if found:
            return found
    return None


def extract_text(element, selector: Optional[str]) -> str:
    if not element or not selector:
        return "N/A"
    try:
        el = first_select(element, selector)
        if not el:
            return "N/A"
        txt = normalize_whitespace(el.get_text(" ", strip=True))
        return txt if txt else "N/A"
    except Exception:
        return "N/A"


def extract_attr(element, selector: Optional[str], attr: str) -> Optional[str]:
    if not element or not selector:
        return None
    try:
        el = first_select(element, selector)
        if not el:
            return None
        v = el.get(attr)
        return v if v else None
    except Exception:
        return None


def looks_like_url(u: str) -> bool:
    try:
        p = urlparse(u)
        return bool(p.scheme and p.netloc)
    except Exception:
        return False


def process_item(item, cfg: dict[str, Any], base_url: str) -> Optional[VideoResult]:
    try:
        # --- Title ---
        title = "Untitled"
        t_el = first_select(item, cfg.get("title_selector", ""))
        if t_el:
            t_attr = cfg.get("title_attribute")
            if t_attr:
                title = (t_el.get(t_attr) or "").strip() or normalize_whitespace(t_el.get_text(" ", strip=True))
            else:
                title = normalize_whitespace(t_el.get_text(" ", strip=True)) or "Untitled"

        # Title fallback selectors
        if (not title or title == "Untitled") and cfg.get("fallback_selectors", {}).get("title"):
            for sel in cfg["fallback_selectors"]["title"]:
                el = first_select(item, sel)
                if not el:
                    continue
                title = (el.get("title") or "").strip() or normalize_whitespace(el.get_text(" ", strip=True))
                if title:
                    break
        title = title or "Untitled"

        # --- Link ---
        link = "#"
        l_el = first_select(item, cfg.get("link_selector", ""))
        if l_el and l_el.get("href"):
            link = urljoin(base_url, l_el.get("href"))

        # --- Image ---
        img_url: Optional[str] = None
        i_el = first_select(item, cfg.get("img_selector", ""))
        if i_el:
            attrs_to_try = [
                cfg.get("img_attribute"),
                "data-src",
                "data-original",
                "data-thumb",
                "data-poster",
                "data-lazy-src",
                "src",
            ]
            for attr in [a for a in attrs_to_try if a]:
                val = i_el.get(attr)
                if not val:
                    continue
                val = val.strip()
                if not val or val.startswith("data:"):
                    continue
                if "spacer" in val.lower() or "blank" in val.lower():
                    continue
                img_url = urljoin(base_url, val)
                break

        # Image fallbacks
        if not img_url and cfg.get("fallback_selectors", {}).get("img"):
            for sel in cfg["fallback_selectors"]["img"]:
                el = first_select(item, sel)
                if not el:
                    continue
                val = (el.get("data-src") or el.get("data-original") or el.get("src") or "").strip()
                if val and not val.startswith("data:"):
                    img_url = urljoin(base_url, val)
                    break

        # Minimal validity: require a real link and some title
        if not link or link == "#":
            return None
        if not title or title == "Untitled":
            # still allow, but it’s often noise; keep strict like V3
            return None

        channel_link = extract_attr(item, cfg.get("channel_link_selector"), "href")
        channel_link = urljoin(base_url, channel_link) if channel_link else "#"

        vr = VideoResult(
            title=html.escape(title),
            link=link,
            img_url=img_url,
            time=extract_text(item, cfg.get("time_selector")),
            channel=extract_text(item, cfg.get("channel_name_selector")),
            channel_link=channel_link,
            views=extract_text(item, cfg.get("meta_selector")),
            engine=base_url,
        )
        return vr
    except Exception as e:
        logger.debug(f"Parsing error: {e}")
        return None


def build_search_url(cfg: dict[str, Any], query: str, page: int) -> str:
    q = quote_plus(query)
    path = cfg["search_path"].replace("{query}", q).replace("{page}", str(page))

    # If path didn't include {page}, apply page_param when page > 1
    if "{page}" not in cfg["search_path"] and page > 1 and cfg.get("page_param"):
        sep = "&" if "?" in path else "?"
        path += f"{sep}{cfg['page_param']}={page}"

    return urljoin(cfg["url"], path)


def create_selenium_driver(headless: bool = True) -> Optional["webdriver.Chrome"]:
    if not SELENIUM_AVAILABLE:
        return None
    try:
        opts = ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_experimental_option(
            "prefs",
            {
                "profile.managed_default_content_settings.images": 2,
                "profile.managed_default_content_settings.stylesheets": 2,
                "profile.default_content_setting_values.notifications": 2,
            },
        )
        service = ChromeService()
        driver = webdriver.Chrome(service=service, options=opts)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        logger.warning(f"Selenium initialization failed: {e}")
        return None


def selenium_get_html(driver, cfg: dict[str, Any], url: str) -> str:
    wait_sel = cfg.get("selenium_wait_selector") or cfg.get("video_item_selector", "").split(",")[0].strip()
    driver.get(url)
    if wait_sel:
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_sel)))

    # Scroll a couple times to trigger lazy-loading
    for _ in range(3):
        driver.execute_script("window.scrollBy(0, document.body.scrollHeight/3);")
        time.sleep(0.8)
    return driver.page_source


def search_engine(
    session: requests.Session,
    engine_name: str,
    query: str,
    limit: int,
    page: int,
    driver=None,
) -> list[VideoResult]:
    cfg = ENGINE_MAP[engine_name]
    results: list[VideoResult] = []

    per_page = int(cfg.get("per_page", 20))
    pages_to_fetch = max(1, (limit + per_page - 1) // per_page)

    for current_page in range(page, page + pages_to_fetch):
        if len(results) >= limit:
            break

        url = build_search_url(cfg, query, current_page)
        logger.info(f"Scanning {engine_name} page {current_page}: {url}")

        try:
            if cfg.get("requires_js") and driver:
                html_content = selenium_get_html(driver, cfg, url)
            else:
                resp = session.get(url, timeout=getattr(session, "request_timeout", DEFAULT_TIMEOUT))
                if resp.status_code != 200:
                    logger.warning(f"Failed to fetch {url} ({resp.status_code})")
                    continue
                html_content = resp.text

            soup = BeautifulSoup(html_content, "html.parser")

            items = []
            for sel in cfg["video_item_selector"].split(","):
                sel = sel.strip()
                if not sel:
                    continue
                found = soup.select(sel)
                if found:
                    items = found
                    break

            if not items:
                logger.warning(f"No items found on {url}. Stopping for this engine.")
                break

            for item in items:
                if len(results) >= limit:
                    break
                vr = process_item(item, cfg, cfg["url"])
                if vr:
                    results.append(vr)

            smart_delay((1.2, 2.4))
        except (TimeoutException, WebDriverException) as e:
            logger.warning(f"Selenium error on {url}: {e}")
            break
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            break

    return results[:limit]


# ── Thumbnail Downloader ─────────────────────────────────────────────────
def get_svg_placeholder() -> str:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 180" width="320" height="180">
<rect width="100%" height="100%" fill="#1f2937"/>
<path fill="#374151" d="M140 70l60 30-60 30z"/>
</svg>"""
    return f"data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}"


def atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_suffix(path.suffix + ".part")
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)


@asynccontextmanager
async def get_aio_session(limit: int = 30):
    if not ASYNC_AVAILABLE:
        raise RuntimeError("aiohttp not installed")
    timeout = aiohttp.ClientTimeout(total=35)
    connector = aiohttp.TCPConnector(limit=limit, ssl=False)
    async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
        yield session


async def download_thumb_async(
    session,
    url: str,
    path: Path,
    sem: asyncio.Semaphore,
    referer: str,
    retries: int = 2,
) -> bool:
    if not url:
        return False
    headers = get_headers(referer=referer)

    async with sem:
        for attempt in range(retries + 1):
            try:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        await asyncio.sleep(0.4 * (attempt + 1))
                        continue
                    ctype = (resp.headers.get("Content-Type") or "").lower()
                    data = await resp.read()
                    # Some sites return HTML for blocked hotlinks; reject tiny/html responses.
                    if "text/html" in ctype or (len(data) < 512 and data.startswith(b"<")):
                        return False
                    atomic_write(path, data)
                    return True
            except Exception:
                await asyncio.sleep(0.4 * (attempt + 1))
    return False


def download_thumb_sync(session: requests.Session, url: str, path: Path, referer: str, retries: int = 2) -> bool:
    if not url:
        return False
    for attempt in range(retries + 1):
        try:
            headers = get_headers(referer=referer)
            resp = session.get(url, headers=headers, timeout=12)
            if resp.status_code != 200:
                time.sleep(0.4 * (attempt + 1))
                continue
            ctype = (resp.headers.get("Content-Type") or "").lower()
            data = resp.content
            if "text/html" in ctype or (len(data) < 512 and data.startswith(b"<")):
                return False
            atomic_write(path, data)
            return True
        except Exception:
            time.sleep(0.4 * (attempt + 1))
    return False


# ── HTML Generation ──────────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Search: {query} ({engine})</title>
  <style>
    :root {{ --bg:#0f172a; --card:#1e293b; --text:#f8fafc; --accent:#38bdf8; --border:#334155; }}
    html.light {{ --bg:#f1f5f9; --card:#ffffff; --text:#0f172a; --accent:#0284c7; --border:#e2e8f0; }}
    body {{ font-family: system-ui, sans-serif; background:var(--bg); color:var(--text); margin:0; padding:20px; transition:.3s; }}

    .header {{ max-width:1400px; margin:0 auto 30px; display:flex; flex-direction:column; align-items:center; gap:18px; padding-bottom:18px; border-bottom:1px solid var(--border); }}
    .header h1 {{ margin:0; font-size:2rem; background:linear-gradient(45deg,var(--accent),#8b5cf6); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
    .sub {{ font-size:.9rem; color:#94a3b8; margin-top:6px; text-align:center; }}

    .controls {{ display:flex; gap:12px; width:100%; max-width:760px; }}
    input {{ flex:1; padding:12px; border-radius:8px; border:1px solid var(--border); background:var(--card); color:var(--text); outline:none; }}
    input:focus {{ border-color:var(--accent); }}
    button {{ padding:10px 16px; border-radius:8px; border:none; background:var(--accent); color:white; cursor:pointer; font-weight:700; }}
    button:hover {{ opacity:.92; }}

    .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:22px; max-width:1600px; margin:0 auto; }}
    .card {{ background:var(--card); border-radius:12px; overflow:hidden; transition:.2s; border:1px solid var(--border); display:flex; flex-direction:column; }}
    .card:hover {{ transform:translateY(-4px); border-color:var(--accent); box-shadow:0 10px 18px rgba(0,0,0,.25); }}

    .thumb-wrap {{ position:relative; padding-top:56.25%; background:#000; display:block; }}
    .thumb {{ position:absolute; top:0; left:0; width:100%; height:100%; object-fit:cover; opacity:0; transition:opacity .25s; }}
    .thumb.loaded {{ opacity:1; }}

    .duration-badge {{ position:absolute; bottom:8px; right:8px; background:rgba(0,0,0,.8); color:#fff; padding:2px 6px; border-radius:4px; font-size:.75rem; font-weight:800; }}
    .play-overlay {{ position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); width:50px; height:50px; background:rgba(0,0,0,.6); border-radius:999px; display:flex; align-items:center; justify-content:center; opacity:0; transition:.2s; pointer-events:none; }}
    .card:hover .play-overlay {{ opacity:1; }}
    .play-overlay::after {{ content:'▶'; color:#fff; font-size:20px; margin-left:2px; }}

    .info {{ padding:14px 14px 12px; flex:1; display:flex; flex-direction:column; }}
    .title {{ margin:0 0 10px; font-size:1rem; line-height:1.35; flex:1; }}
    .title a {{ color:var(--text); text-decoration:none; }}
    .title a:hover {{ color:var(--accent); }}

    .meta {{ font-size:.8rem; color:#94a3b8; display:flex; justify-content:space-between; align-items:center; margin-top:auto; padding-top:10px; border-top:1px solid var(--border); gap:10px; }}
    .leftmeta {{ display:flex; flex-direction:column; gap:4px; min-width:0; }}
    .copy-btn {{ background:transparent; color:var(--accent); border:1px solid var(--border); padding:5px 8px; border-radius:6px; font-size:.75rem; cursor:pointer; white-space:nowrap; }}
    .copy-btn:hover {{ background:rgba(56,189,248,.10); }}
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1>{query}</h1>
      <div class="sub">{engine} • {count} results • {date}</div>
    </div>
    <div class="controls">
      <input type="text" id="search" placeholder="Filter by title..." onkeyup="filterGrid()">
      <button onclick="document.documentElement.classList.toggle('light')">Theme</button>
    </div>
  </div>

  <div class="grid" id="grid">
    {cards}
  </div>

  <script>
    const observer = new IntersectionObserver((entries) => {{
      entries.forEach(entry => {{
        if (entry.isIntersecting) {{
          const img = entry.target;
          img.src = img.dataset.src;
          img.onload = () => img.classList.add('loaded');
          observer.unobserve(img);
        }}
      }});
    }}, {{ rootMargin: "120px" }});
    document.querySelectorAll('img[data-src]').forEach(img => observer.observe(img));

    function filterGrid() {{
      const term = document.getElementById('search').value.toLowerCase();
      document.querySelectorAll('.card').forEach(card => {{
        const text = card.querySelector('.title').textContent.toLowerCase();
        card.style.display = text.includes(term) ? 'flex' : 'none';
      }});
    }}

    async function copyLink(url) {{
      try {{
        await navigator.clipboard.writeText(url);
      }} catch (e) {{
        prompt("Copy link:", url);
      }}
    }}
  </script>
</body>
</html>
"""


async def build_gallery(
    results: list[VideoResult],
    query: str,
    engine: str,
    workers: int,
    output_dir: Path,
    thumbs_dir: Path,
    download_thumbs: bool = True,
) -> Path:
    ensure_dir(output_dir)
    ensure_dir(thumbs_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{engine}_{sanitize_filename(query)}_{timestamp}.html"
    filepath = output_dir / filename

    placeholder = get_svg_placeholder()
    tasks: list[tuple[str, Path, str]] = []

    for i, res in enumerate(results):
        if not download_thumbs or not res.img_url:
            res.local_thumb = placeholder
            continue

        ext = os.path.splitext(urlparse(res.img_url).path)[1].lower() or ".jpg"
        if len(ext) > 5 or not re.fullmatch(r"\.[a-z0-9]{2,5}", ext):
            ext = ".jpg"

        thumb_name = f"{sanitize_filename(html.unescape(res.title))}_{i}{ext}"
        local_path = thumbs_dir / thumb_name

        # Referer: prefer engine base, but item link can also help on some hosts.
        referer = res.engine or (urlparse(res.link).scheme + "://" + urlparse(res.link).netloc)

        res.local_thumb = f"{thumbs_dir.name}/{thumb_name}"

        if not local_path.exists() or local_path.stat().st_size == 0:
            tasks.append((res.img_url, local_path, referer))

    # Download thumbs
    if download_thumbs and tasks:
        print(f"{NEON['CYAN']}Downloading {len(tasks)} thumbnails...{NEON['RESET']}")
        if ASYNC_AVAILABLE:
            sem = asyncio.Semaphore(max(1, workers))
            async with get_aio_session(limit=max(20, workers)) as session:
                await asyncio.gather(*(download_thumb_async(session, u, p, sem, r) for (u, p, r) in tasks))
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
                session = build_session()
                list(
                    tqdm(
                        executor.map(lambda t: download_thumb_sync(session, t[0], t[1], t[2]), tasks),
                        total=len(tasks),
                    )
                )

    # Build cards
    cards_html_parts: list[str] = []
    for res in results:
        thumb_src = res.local_thumb or placeholder

        # If local file was intended but missing -> fallback placeholder
        if thumb_src.startswith(f"{thumbs_dir.name}/"):
            local_path = thumbs_dir / Path(thumb_src).name
            if not local_path.exists() or local_path.stat().st_size == 0:
                thumb_src = placeholder

        duration = (res.time or "").replace("N/A", "").strip()
        duration_badge = f'<div class="duration-badge">{html.escape(duration)}</div>' if duration else ""

        views = (res.views or "N/A").strip()
        if views == "N/A":
            views_text = ""
        else:
            views_text = html.escape(views)

        channel = (res.channel or "N/A").strip()
        channel_text = "" if channel == "N/A" else html.escape(channel)

        leftmeta = "<div class='leftmeta'>"
        leftmeta += f"<span>{views_text}</span>" if views_text else "<span></span>"
        leftmeta += f"<span>{channel_text}</span>" if channel_text else "<span></span>"
        leftmeta += "</div>"

        cards_html_parts.append(
            f"""
    <div class="card">
      <a href="{res.link}" target="_blank" rel="noopener noreferrer" class="thumb-wrap">
        <img class="thumb" src="{placeholder}" data-src="{thumb_src}" alt="{res.title}">
        {duration_badge}
        <div class="play-overlay"></div>
      </a>
      <div class="info">
        <h3 class="title"><a href="{res.link}" target="_blank" rel="noopener noreferrer">{res.title}</a></h3>
        <div class="meta">
          {leftmeta}
          <button class="copy-btn" onclick="copyLink('{res.link}')">Copy Link</button>
        </div>
      </div>
    </div>
            """.rstrip()
        )

    cards_html = "\n".join(cards_html_parts)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(
            HTML_TEMPLATE.format(
                query=html.escape(query),
                engine=html.escape(engine),
                count=len(results),
                date=datetime.now().strftime("%Y-%m-%d %H:%M"),
                cards=cards_html,
            )
        )

    return filepath


def export_json(results: list[VideoResult], query: str, engine: str, output_dir: Path) -> Path:
    ensure_dir(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{engine}_{sanitize_filename(query)}_{timestamp}.json"
    filepath = output_dir / filename
    payload = {
        "query": query,
        "engine": engine,
        "count": len(results),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "results": [r.to_dict() for r in results],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return filepath


# ── Main ─────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Ultimate Video Search & Scraper V4")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=sorted(ENGINE_MAP.keys()), help="Search engine")
    parser.add_argument("-l", "--limit", type=int, default=DEFAULT_LIMIT, help="Max results")
    parser.add_argument("-p", "--page", type=int, default=DEFAULT_PAGE, help="Start page (1-based)")
    parser.add_argument("-o", "--open", action="store_true", help="Open the generated HTML")
    parser.add_argument("-w", "--workers", type=int, default=DEFAULT_WORKERS, help="Concurrent thumbnail downloads")

    parser.add_argument("--proxy", help="Proxy URL (http://user:pass@host:port)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help="HTTP timeout seconds")

    parser.add_argument("--no-thumbs", action="store_true", help="Do not download thumbnails (use placeholders)")
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Output directory for HTML/JSON")
    parser.add_argument("--thumbdir", type=Path, default=DEFAULT_THUMBS_DIR, help="Thumbnail directory")

    parser.add_argument("--json", action="store_true", help="Also export results to JSON")
    parser.add_argument("--use-selenium", action="store_true", help="Force Selenium for this run (if installed)")
    parser.add_argument("--headful", action="store_true", help="Run Selenium with a visible browser window")

    args = parser.parse_args()

    # Interactive prompt if query omitted
    if not args.query:
        print(f"{NEON['CYAN']}=== Video Search Ultimate V4 ==={NEON['RESET']}")
        q = input(f"{NEON['YELLOW']}Enter Query: {NEON['RESET']}").strip()
        if not q:
            raise SystemExit(0)
        args.query = q

        print(f"\nEngines: {', '.join(sorted(ENGINE_MAP.keys()))}")
        eng = input(f"{NEON['YELLOW']}Choose Engine [{DEFAULT_ENGINE}]: {NEON['RESET']}").strip()
        if eng:
            if eng not in ENGINE_MAP:
                print(f"{NEON['RED']}Unknown engine: {eng}{NEON['RESET']}")
                raise SystemExit(2)
            args.engine = eng

    if args.limit < 1:
        print(f"{NEON['RED']}--limit must be >= 1{NEON['RESET']}")
        raise SystemExit(2)
    if args.page < 1:
        print(f"{NEON['RED']}--page must be >= 1{NEON['RESET']}")
        raise SystemExit(2)

    session = build_session(args.proxy, timeout=args.timeout)

    cfg = ENGINE_MAP[args.engine]
    driver = None
    needs_js = bool(cfg.get("requires_js"))
    want_selenium = args.use_selenium or needs_js

    if want_selenium:
        if not SELENIUM_AVAILABLE:
            if needs_js:
                print(f"{NEON['RED']}Engine requires Selenium but it's not installed. Results may be poor.{NEON['RESET']}")
            else:
                print(f"{NEON['YELLOW']}Selenium not installed; continuing without it.{NEON['RESET']}")
        else:
            print(f"{NEON['MAGENTA']}Initializing Selenium...{NEON['RESET']}")
            driver = create_selenium_driver(headless=not args.headful)
            if not driver and needs_js:
                print(f"{NEON['RED']}Selenium failed to start; cannot reliably scrape this engine.{NEON['RESET']}")

    try:
        print(f"{NEON['GREEN']}Searching '{args.query}' on {args.engine}...{NEON['RESET']}")
        results = search_engine(session, args.engine, args.query, args.limit, args.page, driver=driver)

        if not results:
            print(f"{NEON['RED']}No results found.{NEON['RESET']}")
            raise SystemExit(1)

        print(f"{NEON['CYAN']}Found {len(results)} results. Building gallery...{NEON['RESET']}")

        if ASYNC_AVAILABLE:
            outfile = asyncio.run(
                build_gallery(
                    results,
                    args.query,
                    args.engine,
                    args.workers,
                    output_dir=args.outdir,
                    thumbs_dir=args.thumbdir,
                    download_thumbs=not args.no_thumbs,
                )
            )
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            outfile = loop.run_until_complete(
                build_gallery(
                    results,
                    args.query,
                    args.engine,
                    args.workers,
                    output_dir=args.outdir,
                    thumbs_dir=args.thumbdir,
                    download_thumbs=not args.no_thumbs,
                )
            )

        print(f"{NEON['GREEN']}Gallery saved: {NEON['WHITE']}{outfile.absolute()}{NEON['RESET']}")

        if args.json:
            jfile = export_json(results, args.query, args.engine, args.outdir)
            print(f"{NEON['GREEN']}JSON saved:   {NEON['WHITE']}{jfile.absolute()}{NEON['RESET']}")

        if args.open:
            import webbrowser

            webbrowser.open(outfile.absolute().as_uri())

    except KeyboardInterrupt:
        print(f"\n{NEON['YELLOW']}Aborted by user.{NEON['RESET']}")
        raise SystemExit(130)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()