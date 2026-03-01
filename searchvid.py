#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
searchvid.py  •  2025-08-01 (ARCHITECT-UPGRADED)

Senior Architect Version:
- Object-Oriented Scraper Design
- Asynchronous Thumbnail Pipeline
- Robust Error Recovery & Circuit Breaking
- Modern 2025 UI/UX HTML Output
- Comprehensive CLI Interface
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
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Sequence, Tuple, Union
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from requests.adapters import HTTPAdapter, Retry

# Optional dependencies with graceful degradation
try:
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False
    
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    def tqdm(iterable, **kwargs): return iterable

# --- Constants & Configuration ---
init(autoreset=True)
NEON = {
    "CYAN": Fore.CYAN, "MAGENTA": Fore.MAGENTA, "GREEN": Fore.GREEN,
    "YELLOW": Fore.YELLOW, "RED": Fore.RED, "BLUE": Fore.BLUE,
    "WHITE": Fore.WHITE, "BRIGHT": Style.BRIGHT, "RESET": Style.RESET_ALL,
}

DEFAULT_TIMEOUT = 25
DEFAULT_DELAY = (1.5, 3.5)
DEFAULT_MAX_RETRIES = 3
THUMBNAILS_DIR = Path("vsearch_data/thumbnails")
RESULTS_DIR = Path("vsearch_results")

REALISTIC_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.2277.83"
]

ENGINE_MAP: Dict[str, Dict[str, Any]] = {
    "pexels": {
        "url": "https://www.pexels.com",
        "search_path": "/search/videos/{query}/",
        "page_param": "page",
        "requires_js": False,
        "video_item_selector": "article[data-testid='video-card'], .spacing_item__S_S8f",
        "link_selector": "a[href*='/video/']",
        "title_selector": "img[alt]",
        "title_attribute": "alt",
        "img_selector": "img[src*='images.pexels.com']",
        "channel_name_selector": "a[data-testid='video-card-user-avatar-link']",
    },
    "dailymotion": {
        "url": "https://www.dailymotion.com",
        "search_path": "/search/{query}/videos",
        "page_param": "page",
        "requires_js": True,
        "video_item_selector": "div[data-testid='video-card']",
        "link_selector": "a[data-testid='card-link']",
        "title_selector": "div[data-testid='card-title']",
        "img_selector": "img[data-testid='card-thumbnail']",
        "time_selector": "span[data-testid='card-duration']",
    },
    "pornhub": {
        "url": "https://www.pornhub.com",
        "search_path": "/video/search?search={query}",
        "page_param": "page",
        "requires_js": False,
        "video_item_selector": "li.pcVideoListItem",
        "link_selector": "a.previewVideo",
        "title_selector": "span.title",
        "img_selector": "img[data-src], img[src]",
        "time_selector": "var.duration",
        "meta_selector": "span.views",
    },
    "xvideos": {
        "url": "https://www.xvideos.com",
        "search_path": "/?k={query}",
        "page_param": "p",
        "requires_js": False,
        "video_item_selector": "div.thumb-block",
        "link_selector": "div.thumb-under a",
        "title_selector": "div.thumb-under a",
        "img_selector": "img[data-src]",
        "time_selector": "span.duration",
    },
    "fullpornxxx": {
        "url": "https://fullpornxxx.net",
        "search_path": "/search/videos/{query}/",
        "page_param": "page",
        "requires_js": False,
        "video_item_selector": "div.well-sm",
        "link_selector": "a",
        "title_selector": "span.video-title",
        "img_selector": "img",
        "time_selector": "span.duration",
    }
}

# --- Logging Setup ---
class ContextFilter(logging.Filter):
    def filter(self, record):
        record.engine = getattr(record, 'engine', 'SYSTEM')
        return True

LOG_FMT = f"{NEON['CYAN']}%(asctime)s{NEON['RESET']} [%(engine)s] %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT)
logger = logging.getLogger("VideoSearch")
logger.addFilter(ContextFilter())

# --- Core Utilities ---

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9\s\-_]", "", text).strip().replace(" ", "_")
    return text[:50] or "result"

def get_headers() -> Dict[str, str]:
    ua = random.choice(REALISTIC_USER_AGENTS)
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

# --- Scraper Engine ---

class VideoScraper:
    def __init__(self, proxy: Optional[str] = None):
        self.session = self._build_session(proxy)
        self.driver: Optional[webdriver.Chrome] = None

    def _build_session(self, proxy: Optional[str]) -> requests.Session:
        session = requests.Session()
        retries = Retry(total=DEFAULT_MAX_RETRIES, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        if proxy:
            session.proxies = {"http": proxy, "https": proxy}
        return session

    def init_selenium(self):
        if not SELENIUM_AVAILABLE: return
        options = ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument(f"user-agent={random.choice(REALISTIC_USER_AGENTS)}")
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
        except Exception as e:
            logger.error(f"Selenium init failed: {e}")

    def close(self):
        if self.driver:
            self.driver.quit()
        self.session.close()

    def fetch_page(self, url: str, use_js: bool = False) -> str:
        if use_js and self.driver:
            self.driver.get(url)
            WebDriverWait(self.driver, 15).until(lambda d: d.execute_script("return document.readyState") == "complete")
            return self.driver.page_source
        
        resp = self.session.get(url, headers=get_headers(), timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        return resp.text

    def parse_results(self, html_content: str, engine_cfg: Dict, base_url: str) -> List[Dict]:
        soup = BeautifulSoup(html_content, "html.parser")
        results = []
        items = soup.select(engine_cfg["video_item_selector"])
        
        for item in items:
            try:
                link_el = item.select_one(engine_cfg["link_selector"])
                if not link_el: continue
                
                link = urljoin(base_url, link_el.get("href", ""))
                title_el = item.select_one(engine_cfg["title_selector"])
                title = "Untitled"
                if title_el:
                    attr = engine_cfg.get("title_attribute")
                    title = title_el.get(attr) if attr else title_el.get_text(strip=True)

                img_el = item.select_one(engine_cfg["img_selector"])
                img_url = ""
                if img_el:
                    img_url = img_el.get("data-src") or img_el.get("src") or img_el.get("data-original")
                    if img_url: img_url = urljoin(base_url, img_url)

                results.append({
                    "title": title,
                    "link": link,
                    "img_url": img_url,
                    "duration": item.select_one(engine_cfg.get("time_selector", "N/A")).get_text(strip=True) if engine_cfg.get("time_selector") and item.select_one(engine_cfg.get("time_selector")) else "N/A",
                    "meta": item.select_one(engine_cfg.get("meta_selector", "N/A")).get_text(strip=True) if engine_cfg.get("meta_selector") and item.select_one(engine_cfg.get("meta_selector")) else "N/A",
                    "engine": base_url
                })
            except Exception as e:
                logger.debug(f"Item parse error: {e}")
                continue
        return results

# --- Async Downloader ---

class AsyncDownloader:
    def __init__(self, concurrency: int = 10):
        self.semaphore = asyncio.Semaphore(concurrency)

    async def download_one(self, session: aiohttp.ClientSession, url: str, dest: Path) -> Optional[Path]:
        if not url or not url.startswith("http"): return None
        async with self.semaphore:
            try:
                async with session.get(url, timeout=15) as resp:
                    if resp.status == 200:
                        content = await resp.read()
                        dest.write_bytes(content)
                        return dest
            except Exception:
                return None

    async def run(self, tasks: List[Tuple[str, Path]]):
        if not ASYNC_AVAILABLE:
            logger.warning("aiohttp not found. Skipping async downloads.")
            return
        
        async with aiohttp.ClientSession(headers=get_headers()) as session:
            jobs = [self.download_one(session, url, dest) for url, dest in tasks]
            await asyncio.gather(*jobs)

# --- Exporters ---

class ResultExporter:
    @staticmethod
    def to_html(query: str, engine: str, results: List[Dict], output_path: Path):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Inline SVG for placeholder
        placeholder = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxMDAlIiBoZWlnaHQ9IjEwMCUiIHZpZXdCb3g9IjAgMCAxMDAgMTAwIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMWExYTJlIi8+PHRleHQgeD0iNTAiIHk9IjU1IiBmaWxsPSIjNGE0YTVlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LXNpemU9IjQwIj7wn4isPC90ZXh0Pjwvc3ZnPg=="

        html_content = f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search: {query}</title>
    <style>
        :root {{ --bg: #0a0a12; --card: #161625; --text: #e0e0e0; --accent: #00d4ff; --border: #2a2a3a; }}
        body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; margin: 0; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 25px; max-width: 1400px; margin: 0 auto; }}
        .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; transition: 0.3s; }}
        .card:hover {{ transform: translateY(-5px); border-color: var(--accent); box-shadow: 0 10px 20px rgba(0,0,0,0.5); }}
        .thumb {{ width: 100%; height: 180px; background: #000; position: relative; }}
        .thumb img {{ width: 100%; height: 100%; object-fit: cover; }}
        .duration {{ position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.8); padding: 2px 6px; border-radius: 4px; font-size: 12px; }}
        .info {{ padding: 15px; }}
        .title {{ font-size: 15px; font-weight: 600; margin-bottom: 10px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; height: 40px; }}
        .meta {{ font-size: 12px; color: #888; display: flex; justify-content: space-between; }}
        a {{ text-decoration: none; color: inherit; }}
        .btn {{ display: inline-block; margin-top: 10px; color: var(--accent); font-size: 13px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{html.escape(query)}</h1>
        <p>{len(results)} results from {engine} • {timestamp}</p>
    </div>
    <div class="grid">"""

        for res in results:
            thumb = res.get('local_thumb') or res.get('img_url') or placeholder
            html_content += f"""
        <div class="card">
            <a href="{res['link']}" target="_blank">
                <div class="thumb">
                    <img src="{thumb}" loading="lazy" onerror="this.src='{placeholder}'">
                    <span class="duration">{html.escape(res['duration'])}</span>
                </div>
                <div class="info">
                    <div class="title">{html.escape(res['title'])}</div>
                    <div class="meta">
                        <span>{html.escape(res['meta'])}</span>
                        <span>{urlparse(res['engine']).netloc}</span>
                    </div>
                    <span class="btn">WATCH VIDEO →</span>
                </div>
            </a>
        </div>"""

        html_content += "</div></body></html>"
        output_path.write_text(html_content, encoding="utf-8")

    @staticmethod
    def to_json(results: List[Dict], output_path: Path):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

    @staticmethod
    def to_csv(results: List[Dict], output_path: Path):
        if not results: return
        keys = results[0].keys()
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(results)

# --- Main Orchestrator ---

async def run_search(args):
    engine_name = args.engine.lower()
    if engine_name not in ENGINE_MAP:
        logger.error(f"Engine {engine_name} not supported.")
        return

    cfg = ENGINE_MAP[engine_name]
    scraper = VideoScraper(proxy=args.proxy)
    
    if cfg.get("requires_js"):
        logger.info(f"Engine {engine_name} requires JavaScript. Initializing Selenium...")
        scraper.init_selenium()

    all_results = []
    query_slug = slugify(args.query)
    
    try:
        # Pagination loop
        for p in range(1, args.pages + 1):
            logger.info(f"Scraping page {p} of {args.pages}...", extra={'engine': engine_name.upper()})
            
            # Build URL
            search_url = urljoin(cfg["url"], cfg["search_path"].format(query=quote_plus(args.query)))
            if p > 1:
                sep = "&" if "?" in search_url else "?"
                search_url += f"{sep}{cfg['page_param']}={p}"

            html_data = scraper.fetch_page(search_url, use_js=cfg.get("requires_js"))
            page_results = scraper.parse_results(html_data, cfg, cfg["url"])
            
            if not page_results:
                logger.warning("No more results found.")
                break
                
            all_results.extend(page_results)
            if len(all_results) >= args.limit:
                all_results = all_results[:args.limit]
                break
            
            time.sleep(random.uniform(*DEFAULT_DELAY))

        logger.info(f"Found {len(all_results)} total results.")

        # Thumbnail processing
        if args.download_thumbs and all_results:
            logger.info("Starting asynchronous thumbnail download...")
            THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)
            downloader = AsyncDownloader(concurrency=15)
            tasks = []
            for i, res in enumerate(all_results):
                if res['img_url']:
                    ext = Path(urlparse(res['img_url']).path).suffix or ".jpg"
                    if len(ext) > 5: ext = ".jpg"
                    dest = THUMBNAILS_DIR / f"{query_slug}_{i}{ext}"
                    tasks.append((res['img_url'], dest))
                    res['local_thumb'] = str(dest.relative_to(Path.cwd()))
            
            await downloader.run(tasks)

        # Export
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = RESULTS_DIR / f"search_{query_slug}_{engine_name}_{timestamp}"

        if "html" in args.format:
            out = base_filename.with_suffix(".html")
            ResultExporter.to_html(args.query, engine_name, all_results, out)
            logger.info(f"HTML report generated: {out}")
            if args.open:
                import webbrowser
                webbrowser.open(out.absolute().as_uri())

        if "json" in args.format:
            out = base_filename.with_suffix(".json")
            ResultExporter.to_json(all_results, out)
            logger.info(f"JSON data exported: {out}")

        if "csv" in args.format:
            out = base_filename.with_suffix(".csv")
            ResultExporter.to_csv(all_results, out)
            logger.info(f"CSV data exported: {out}")

    finally:
        scraper.close()

def main():
    parser = argparse.ArgumentParser(description="Advanced Video Search Scraper 2025")
    parser.add_argument("query", help="Search keywords")
    parser.add_argument("-e", "--engine", default="pexels", choices=list(ENGINE_MAP.keys()), help="Search engine to use")
    parser.add_argument("-l", "--limit", type=int, default=20, help="Max results to return")
    parser.add_argument("-p", "--pages", type=int, default=1, help="Number of pages to scrape")
    parser.add_argument("-f", "--format", nargs="+", default=["html"], choices=["html", "json", "csv"], help="Output formats")
    parser.add_argument("--proxy", help="Proxy URL (e.g. http://user:pass@host:port)")
    parser.add_argument("--download-thumbs", action="store_true", help="Download thumbnails locally")
    parser.add_argument("--open", action="store_true", help="Open HTML result in browser automatically")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_search(args))
    except KeyboardInterrupt:
        logger.info("Search aborted by user.")
    except Exception as e:
        logger.error(f"Critical failure: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()