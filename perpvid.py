#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
video_search_enhanced.py  •  2025-08-07 (ULTIMATE-2025-ENHANCED)

Ultra-robust, AI-driven video search engine supporting multiple adult and general video sites with:
- Async Playwright browser support for JS rendering
- LLM-powered extraction fallback (OpenAI or Ollama)
- Distributed caching (Redis / SQLite)
- Concurrent thumbnail downloads with aiohttp
- Stealth user-agent rotation and proxy support
- Structured logging with Rich
- FastAPI server + CLI interface
"""

import asyncio
import hashlib
import html
import logging
import os
import random
import re
import sys
import time
from argparse import ArgumentParser
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse, quote_plus

import aiohttp
import httpx
import orjson
import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from playwright.async_api import async_playwright
from pydantic import BaseModel
from requests.adapters import HTTPAdapter, Retry
from rich.console import Console
from rich.logging import RichHandler
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from redis import Redis
from tenacity import retry, stop_after_attempt, wait_exponential

# Initialize colorama for colored terminal output
init(autoreset=True)
console = Console()

# ── Constants and Configuration ────────────────────────────────────────────
VERSION = "2.5.1"

THUMBNAILS_DIR = Path("downloaded_thumbnails")
CACHE_DIR = Path(".cache")
LOG_FILE = "video_search.log"

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_TIMEOUT = 30
DEFAULT_CACHE_TTL = 3600  # seconds

# ── Configure Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=console, rich_tracebacks=True)]
)
logger = logging.getLogger("video_search")


# ── Utility Functions ──────────────────────────────────────────────────────
def ensure_dir(path: Path):
    """Ensure the directory exists."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")


def slugify(text: str) -> str:
    """Slugify text to be filesystem safe."""
    text = re.sub(r'[^\w\s-]', '', text.lower())
    return re.sub(r'[-\s]+', '_', text.strip())


def get_cache_key(query: str, engine: str, page: int) -> str:
    """Generate a cache key for lookup."""
    key_raw = f"{engine}:{query}:{page}"
    return hashlib.md5(key_raw.encode()).hexdigest()


# ── Cache Backend Interfaces ───────────────────────────────────────────────
class CacheBackend:
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL):
        raise NotImplementedError

    def close(self):
        pass


class RedisCache(CacheBackend):
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        try:
            self.client = Redis(host=host, port=port, db=db, decode_responses=True)
            self.client.ping()
            logger.info("✅ Connected to Redis cache.")
        except Exception as e:
            logger.warning(f"Redis cache connection failed: {e}")
            self.client = None

    def get(self, key: str) -> Optional[Any]:
        if not self.client:
            return None
        val = self.client.get(key)
        if val:
            try:
                return orjson.loads(val)
            except Exception:
                return None
        return None

    def set(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL):
        if not self.client:
            return
        try:
            self.client.setex(key, ttl, orjson.dumps(value))
        except Exception as e:
            logger.debug(f"Failed to set cache key {key}: {e}")

    def close(self):
        if self.client:
            self.client.close()


class SQLiteCache(CacheBackend):
    def __init__(self, db_path: Path = CACHE_DIR / "cache.db"):
        ensure_dir(db_path.parent)
        import sqlite3
        self.db_path = db_path
        self.sqlite3 = sqlite3
        self._init_db()

    def _init_db(self):
        with self.sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    value BLOB,
                    expires REAL
                )
                """
            )

    def get(self, key: str) -> Optional[Any]:
        now = time.time()
        try:
            with self.sqlite3.connect(self.db_path) as conn:
                row = conn.execute(
                    "SELECT value FROM cache WHERE key=? AND expires > ?",
                    (key, now),
                ).fetchone()
                if row:
                    return orjson.loads(row[0])
        except Exception:
            return None
        return None

    def set(self, key: str, value: Any, ttl: int = DEFAULT_CACHE_TTL):
        expires = time.time() + ttl
        try:
            with self.sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "REPLACE INTO cache (key, value, expires) VALUES (?, ?, ?)",
                    (key, orjson.dumps(value), expires),
                )
        except Exception as e:
            logger.debug(f"SQLite cache set failed: {e}")

    def close(self):
        pass


# ── Engine Configuration ────────────────────────────────────────────────────
@dataclass
class EngineConfig:
    url: str
    search_path: str
    page_param: Optional[str] = None
    requires_js: bool = False
    video_item_selector: str = ""
    link_selector: str = ""
    title_selector: str = ""
    img_selector: str = ""
    time_selector: Optional[str] = None
    channel_name_selector: Optional[str] = None
    channel_link_selector: Optional[str] = None
    meta_selector: Optional[str] = None
    fallback_selectors: Optional[Dict[str, List[str]]] = None

    # Additional attribute for title alt attribute if needed
    title_attribute: Optional[str] = None


ENGINE_MAP: Dict[str, EngineConfig] = {
    "pexels": EngineConfig(
        url="https://www.pexels.com",
        search_path="/search/videos/{query}/",
        page_param="page",
        video_item_selector="article[data-testid='video-card']",
        link_selector="a[data-testid='video-card-link']",
        title_selector="img[data-testid='video-card-img']",
        img_selector="img[data-testid='video-card-img']",
        title_attribute="alt",
    ),
    "pornhub": EngineConfig(
        url="https://www.pornhub.com",
        search_path="/video/search?search={query}",
        page_param="page",
        requires_js=True,  # Pornhub is JS-heavy now
        video_item_selector="li.pcVideoListItem, div.videoblock, div.videoblock-container",
        link_selector="a.previewVideo, a.thumb, div.videoblock__link",
        title_selector="a.previewVideo .title, a.thumb .title, .videoblock__title",
        img_selector="img[src], img[data-src], img[data-lazy]",
        time_selector="var.duration, .duration, .videoblock__duration",
        channel_name_selector=".usernameWrap a, .channel-name, .videoblock__channel",
        channel_link_selector=".usernameWrap a, .channel-link",
        meta_selector=".views, .video-views, .videoblock__views",
        fallback_selectors={
            "title": [".title", "a[title]", "[data-title]"],
            "img": ["img[data-thumb]", "img[src]"],
            "link": ["a[href*='/view_video.php']", "a.video-link"],
        },
    ),
    "xnxx": EngineConfig(
        url="https://www.xnxx.com",
        search_path="/search/{query}/",
        page_param="p",
        requires_js=False,
        video_item_selector="div.mozaique > div.thumb-block, .video-block",
        link_selector=".thumb-under > a, .video-link",
        title_selector=".thumb-under > a, .video-title",
        img_selector="img[data-src], .thumb img",
        time_selector=".duration, .video-duration",
        meta_selector=".video-views, .views",
        fallback_selectors={
            "title": ["a[title]", ".title", "p.title"],
            "img": ["img[data-src]", "img[src]"],
            "link": ["a[href*='/video']"],
        },
    ),
    "spankbang": EngineConfig(
        url="https://spankbang.com",
        search_path="/search/{query}/",
        page_param="page",
        requires_js=False,
        video_item_selector="div.thumbnail-item, div.video-item",
        link_selector="a.thumbnail-link, a.video-link",
        title_selector="a.video-title, a[title]",
        img_selector="img[data-src], img[src]",
        time_selector="span.duration, div.duration",
        channel_name_selector="a.channel-name, span.uploader-name",
        meta_selector="span.views, div.views",
        fallback_selectors={
            "title": ["a[title]", ".video-title"],
            "img": ["img[data-src]", "img[src]"],
            "link": ["a[href*='/video/']"],
        },
    ),
    "xhamster": EngineConfig(
        url="https://xhamster.com",
        search_path="/search/{query}",
        page_param="page",
        requires_js=True,
        video_item_selector="div.thumb-list__item.video-thumb",
        link_selector="a.video-thumb__image-container[data-role='thumb-link']",
        title_selector="a.video-thumb-info__name[data-role='thumb-link']",
        img_selector="img.thumb-image-container__image[data-role='thumb-preview-img']",
        time_selector="div.thumb-image-container__duration div.tiny-8643e",
        meta_selector="div.video-thumb-views",
        channel_name_selector="a.video-uploader__name",
        channel_link_selector="a.video-uploader__name",
        fallback_selectors={
            "title": ["a[title]"],
            "img": ["img[data-src]", "img[src]"],
            "link": ["a[href*='/videos/']"],
        },
    ),
    "dailymotion": EngineConfig(
        url="https://www.dailymotion.com",
        search_path="/search/{query}/videos",
        page_param="page",
        requires_js=False,
        video_item_selector=".video-item",
        link_selector="a.video-link",
        title_selector=".video-title",
        img_selector="img",
    ),
}


# ── LLM Extraction Fallback ────────────────────────────────────────────────
class LLMExtractor:
    def __init__(self, provider: str = "openai", model: str = "gpt-3.5-turbo"):
        self.provider = provider
        self.model = model
        self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OLLAMA_API_KEY")
        self.base_url = (
            os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            if provider == "ollama"
            else None
        )
        if not self.api_key:
            logger.warning(
                "⚠️ LLM API key not found; LLM fallback will not work properly."
            )

    async def extract(self, html_content: str, selectors: dict) -> List[dict]:
        prompt = (
            f"Extract video items from the given HTML content using these selectors as hints:\n"
            f"Title: {selectors.get('title_selector', 'N/A')}\n"
            f"Link: {selectors.get('link_selector', 'N/A')}\n"
            f"Image: {selectors.get('img_selector', 'N/A')}\n\n"
            f"Return a JSON array with fields title, link, img_url, time, channel_name, and meta.\n"
            f"HTML snippet:\n"
            f"{html_content[:10000]}"
        )
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                if self.provider == "openai":
                    headers = {"Authorization": f"Bearer {self.api_key}"}
                    resp = await client.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers=headers,
                        json={
                            "model": self.model,
                            "messages": [{"role": "user", "content": prompt}],
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    return orjson.loads(content)
                elif self.provider == "ollama":
                    resp = await client.post(
                        f"{self.base_url}/api/generate",
                        json={"model": self.model, "prompt": prompt, "format": "json"},
                    )
                    resp.raise_for_status()
                    response_data = resp.json()
                    return orjson.loads(response_data["response"])
        except Exception as e:
            logger.warning(f"LLM extraction failed: {e}")
            return []


# ── Playwright Manager for JS Rendering ────────────────────────────────────
class PlaywrightManager:
    def __init__(self):
        self.browser = None
        self.context = None

    async def launch(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent=random.choice(DEFAULT_USER_AGENTS),
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            ignore_https_errors=True,
            # Disable images and CSS to speed up loading (optional, can skip if images needed)
            # extra_http_headers={"Accept": "*/*"},
        )
        return self.context

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()


# ── HTTP Session Setup ─────────────────────────────────────────────────────
def create_session(proxy: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT) -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": random.choice(DEFAULT_USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        }
    )
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
        logger.info(f"🌐 Using proxy: {proxy}")
    session.timeout = timeout
    return session


# ── Core Scraping Logic ─────────────────────────────────────────────────────
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
async def scrape_page(
    session: requests.Session,
    engine: str,
    query: str,
    page: int,
    cache: CacheBackend,
    use_playwright: bool = False,
    llm_extractor: Optional[LLMExtractor] = None,
) -> List[Dict]:
    cfg = ENGINE_MAP.get(engine)
    if not cfg:
        logger.error(f"❌ Unknown engine: {engine}")
        return []

    cache_key = get_cache_key(query, engine, page)
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"🎯 Cache hit for {engine} page {page}")
        return cached

    base_url = cfg.url
    # Build search URL carefully
    search_url = urljoin(base_url, cfg.search_path.format(query=quote_plus(query)))
    if page > 1 and cfg.page_param:
        sep = "&" if "?" in search_url else "?"
        search_url += f"{sep}{cfg.page_param}={page}"

    logger.info(f"🔍 Fetching: {search_url}")

    html_content = None

    # Use Playwright if required or requested
    if use_playwright or cfg.requires_js:
        pw = PlaywrightManager()
        try:
            context = await pw.launch()
            page_obj = await context.new_page()
            await page_obj.goto(search_url, wait_until="networkidle")
            # Add wait to ensure content loads
            await page_obj.wait_for_timeout(2000)
            html_content = await page_obj.content()
            await pw.close()
        except Exception as exc:
            logger.warning(f"⚠️ Playwright failed: {exc}")
            html_content = None
    else:
        try:
            resp = session.get(search_url, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            html_content = resp.text
        except Exception as exc:
            logger.warning(f"⚠️ HTTP request failed: {exc}")

    if not html_content:
        logger.error(f"❌ No content fetched for page {page}")
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    items = soup.select(cfg.video_item_selector)

    # Fallback: LLM extraction if no results found and LLM extractor is enabled
    if not items and llm_extractor:
        logger.info("🧩 LLM fallback extraction triggered")
        extracted = await llm_extractor.extract(html_content, cfg.__dict__)
        cache.set(cache_key, extracted)
        return extracted

    results = []

    for item in items:
        # Extract title
        title_el = item.select_one(cfg.title_selector)
        if cfg.title_attribute:
            title_text = title_el.get(cfg.title_attribute, "").strip() if title_el else ""
        else:
            title_text = title_el.get_text(strip=True) if title_el else ""

        if not title_text:
            title_text = "Untitled"

        # Extract link
        link_el = item.select_one(cfg.link_selector)
        link = urljoin(base_url, link_el["href"]) if link_el and link_el.has_attr("href") else "#"

        # Extract image
        img_el = item.select_one(cfg.img_selector)
        img_url = None
        if img_el:
            for attr in ("data-src", "src", "data-lazy", "data-original"):
                if img_el.has_attr(attr):
                    img_url = img_el[attr]
                    break
            if img_url:
                img_url = urljoin(base_url, img_url)

        # Extract other metadata (time, channel, meta)
        def extract_text(sel: Optional[str]) -> str:
            if not sel:
                return "N/A"
            el = item.select_one(sel)
            return el.get_text(strip=True) if el else "N/A"

        time_text = extract_text(cfg.time_selector)
        channel_name = extract_text(cfg.channel_name_selector)
        meta_text = extract_text(cfg.meta_selector)

        results.append(
            {
                "title": html.escape(title_text),
                "link": link,
                "img_url": img_url,
                "time": time_text,
                "channel_name": channel_name,
                "meta": meta_text,
                "source_engine": engine,
                "extracted_at": datetime.now().isoformat(),
            }
        )

    cache.set(cache_key, results)
    return results


# ── Async Thumbnail Downloader ─────────────────────────────────────────────
@asynccontextmanager
async def download_session():
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        yield session


async def download_thumbnail(session: aiohttp.ClientSession, url: str, path: Path) -> bool:
    if not url or not path.parent.exists():
        return False
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.read()
                if len(data) < 10 * 1024 * 1024:  # Limit 10MB
                    with open(path, "wb") as f:
                        f.write(data)
                    return True
    except Exception as e:
        logger.debug(f"⚠️ Download failed {url}: {e}")
    return False


async def download_thumbnail_with_retry(
    session: aiohttp.ClientSession, url: str, path: Path, semaphore: asyncio.Semaphore
):
    async with semaphore:
        for attempt in range(3):
            if await download_thumbnail(session, url, path):
                return True
            await asyncio.sleep(1)
    return False


# ── Generate HTML Output for Results ──────────────────────────────────────
async def generate_html(results: List[Dict], query: str, engine: str) -> Path:
    ensure_dir(THUMBNAILS_DIR)
    out_file = Path(f"{engine}_{slugify(query)}_{int(time.time())}.html")

    sem = asyncio.Semaphore(10)
    async with download_session() as sess:
        tasks = []
        for i, res in enumerate(results):
            img_url = res.get("img_url")
            if img_url:
                ext = Path(urlparse(img_url).path).suffix or ".jpg"
                thumb_path = THUMBNAILS_DIR / f"thumb_{i}{ext}"
                if not thumb_path.exists():
                    tasks.append(download_thumbnail_with_retry(sess, img_url, thumb_path, sem))

        await asyncio.gather(*tasks, return_exceptions=True)

    with out_file.open("w", encoding="utf-8") as f:
        f.write(
            f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Search Results for '{query}' on {engine}</title>
<style>
body {{ font-family: Arial, sans-serif; background: #121212; color: #ddd; padding: 1rem; }}
.results {{ display: flex; flex-wrap: wrap; gap: 1rem; }}
.video {{ width: 320px; background: #222; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.7); }}
.video img {{ width: 320px; height: 180px; object-fit: cover; display: block; }}
.video h3 {{ margin: 0.5rem; font-size: 1rem; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.video a {{ color: #66fcf1; text-decoration: none; }}
</style></head><body>
<h1>Search Results for '{html.escape(query)}' on {engine}</h1>
<div class="results">
"""
        )
        for i, res in enumerate(results):
            ext = Path(urlparse(res.get("img_url", "")).path).suffix or ".jpg"
            thumb_file = THUMBNAILS_DIR / f"thumb_{i}{ext}"
            thumb_url = thumb_file.as_posix() if thumb_file.exists() else "https://via.placeholder.com/320x180?text=No+Image"
            f.write(
                f"""<div class="video">
  <a href="{res['link']}" target="_blank" rel="noopener noreferrer">
    <img src="{thumb_url}" alt="{res['title']}" loading="lazy">
    <h3>{res['title']}</h3>
  </a>
  <div style="padding:0 0.5rem 0.75rem 0.5rem; font-size: 0.8rem;">
    <span>Duration: {res.get('time', 'N/A')}</span><br>
    <span>Channel: {res.get('channel_name', 'N/A')}</span><br>
    <span>{res.get('meta', '')}</span>
  </div>
</div>"""
            )
        f.write("</div></body></html>")

    logger.info(f"📄 HTML saved at {out_file}")
    return out_file


# ── FastAPI Server Setup ───────────────────────────────────────────────────
app = FastAPI(title="Video Search API", version=VERSION)

class SearchRequest(BaseModel):
    query: str
    engine: str = "pexels"
    limit: int = DEFAULT_LIMIT
    page: int = DEFAULT_PAGE
    proxy: Optional[str] = None
    use_playwright: bool = False
    llm_provider: Optional[str] = None


@app.get("/search")
async def search_videos(
    query: str = Query(..., min_length=1),
    engine: str = Query("pexels"),
    limit: int = Query(DEFAULT_LIMIT),
    page: int = Query(DEFAULT_PAGE),
    proxy: Optional[str] = Query(None),
    use_playwright: bool = Query(False),
    llm_provider: Optional[str] = Query(None),
):
    if engine not in ENGINE_MAP:
        raise HTTPException(400, detail=f"Invalid engine '{engine}'")

    session = create_session(proxy=proxy)
    cache = RedisCache() if os.getenv("USE_REDIS") else SQLiteCache()
    llm = LLMExtractor(llm_provider) if llm_provider else None

    results = await scrape_page(session, engine, query, page, cache, use_playwright, llm)
    limited_results = results[:limit]
    return {"query": query, "engine": engine, "results_count": len(limited_results), "results": limited_results}


@app.get("/health")
def health():
    return {"status": "ok", "version": VERSION}


@app.get("/", response_class=HTMLResponse)
def docs():
    return """
    <h1>Video Search API</h1>
    <p>Use the <a href="/docs">/docs</a> endpoint for interactive API documentation.</p>
    """


# ── CLI Interface ─────────────────────────────────────────────────────────
def main():
    parser = ArgumentParser(description="AI-Enhanced Video Search Engine")
    parser.add_argument("query", nargs="?", help="Search query")
    parser.add_argument(
        "-e", "--engine", default="pexels", choices=list(ENGINE_MAP.keys()), help="Target search engine"
    )
    parser.add_argument("-l", "--limit", type=int, default=DEFAULT_LIMIT, help="Number of results to return")
    parser.add_argument("-p", "--page", type=int, default=DEFAULT_PAGE, help="Page number to fetch")
    parser.add_argument("--api", action="store_true", help="Launch FastAPI server")
    parser.add_argument(
        "--playwright", action="store_true", help="Use Playwright for JS-required sites"
    )
    parser.add_argument(
        "--llm",
        choices=["openai", "ollama"],
        help="Enable LLM fallback extraction",
    )
    parser.add_argument("--proxy", type=str, help="HTTP proxy URL")
    parser.add_argument("--no-open", action="store_true", help="Do not open output HTML automatically")
    args = parser.parse_args()

    if args.api:
        import uvicorn
        logger.info(f"🚀 Launching API server version {VERSION}")
        uvicorn.run(app, host="0.0.0.0", port=8000)
        return

    if not args.query:
        parser.error("Query argument required unless --api is used")

    ensure_dir(THUMBNAILS_DIR)
    ensure_dir(CACHE_DIR)

    cache = RedisCache() if os.getenv("USE_REDIS") else SQLiteCache()
    session = create_session(args.proxy)
    llm_extractor = LLMExtractor(args.llm) if args.llm else None

    # Run scraper async
    results = asyncio.run(
        scrape_page(session, args.engine, args.query, args.page, cache, args.playwright, llm_extractor)
    )
    results = results[: args.limit]

    if not results:
        logger.error("❌ No videos found.")
        sys.exit(1)

    logger.info(f"✅ Found {len(results)} videos for '{args.query}' on {args.engine}")

    out_html = asyncio.run(generate_html(results, args.query, args.engine))

    if not args.no_open:
        import webbrowser

        webbrowser.open(out_html.as_uri())


if __name__ == "__main__":
    main()
