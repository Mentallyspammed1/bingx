#!/usr/bin/env python3
"""
video_search.py • ULTIMATE EDITION V4.2 • 2025-12-19
Enhanced for Bash/Termux/Python environments.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import html
import logging
import random
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from requests.adapters import Retry

# --- Dependency Management ---
try:
    from colorama import Fore
    from colorama import Style
    from colorama import init as colorama_init
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    class Fore: CYAN=MAGENTA=GREEN=YELLOW=RED=BLUE=WHITE=RESET=""
    class Style: BRIGHT=RESET_ALL=""
    def colorama_init(autoreset: bool = True): pass

try:
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

try:
    from selenium import webdriver
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

# ── Logging & UI ────────────────────────────────────────────────────────
colorama_init(autoreset=True)
NEON = {
    "CYAN": Fore.CYAN, "MAGENTA": Fore.MAGENTA, "GREEN": Fore.GREEN,
    "YELLOW": Fore.YELLOW, "RED": Fore.RED, "BLUE": Fore.BLUE,
    "WHITE": Fore.WHITE, "BRIGHT": Style.BRIGHT, "RESET": Style.RESET_ALL,
}

LOG_FMT = f"{NEON['CYAN']}%(asctime)s{NEON['RESET']} - %(message)s"
logger = logging.getLogger("video_search")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(LOG_FMT, datefmt="%H:%M:%S"))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# ── Configuration ────────────────────────────────────────────────────────
DEFAULT_ENGINE = "pexels"
DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_TIMEOUT = 20
DEFAULT_WORKERS = 12
DEFAULT_OUTPUT_DIR = Path("vsearch_results")
DEFAULT_THUMBS_DIR = Path("downloaded_thumbnails")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
]

ENGINE_MAP: dict[str, dict[str, Any]] = {
    "pexels": {
        "url": "https://www.pexels.com",
        "search_path": "/search/videos/{query}/",
        "page_param": "page",
        "requires_js": False,
        "per_page": 24,
        "video_item_selector": "article[data-testid='video-card']",
        "link_selector": "a[href*='/video/']",
        "title_selector": "img",
        "title_attribute": "alt",
        "img_selector": "img",
        "img_attribute": "src",
    },
    "xhamster": {
        "url": "https://xhamster.com",
        "search_path": "/search/{query}",
        "page_param": "page",
        "requires_js": True,
        "per_page": 30,
        "video_item_selector": "div.video-thumb, article.video-thumb",
        "link_selector": "a.video-thumb__image-container, a.thumb-image",
        "title_selector": "div.video-thumb-info__name, .video-thumb__name",
        "img_selector": "img.thumb-image-container__image, img",
        "time_selector": "div.thumb-image-container__duration, .duration",
    },
    "pornhub": {
        "url": "https://www.pornhub.com",
        "search_path": "/video/search?search={query}",
        "page_param": "page",
        "requires_js": False,
        "per_page": 30,
        "video_item_selector": "li.pcVideoListItem",
        "link_selector": "a.previewVideo",
        "title_selector": "span.title a",
        "img_selector": "img",
        "img_attribute": "data-src",
        "time_selector": "var.duration",
    }
}

@dataclasses.dataclass(slots=True)
class VideoResult:
    title: str
    link: str
    img_url: str | None = None
    time: str = "N/A"
    channel: str = "N/A"
    engine: str = ""
    local_thumb: str | None = None

    def to_dict(self) -> dict: return dataclasses.asdict(self)

# ── Helper Utilities ─────────────────────────────────────────────────────

def get_headers(referer: str | None = None) -> dict:
    h = {"User-Agent": random.choice(USER_AGENTS), "Accept": "*/*"}
    if referer: h["Referer"] = referer
    return h

def sanitize_filename(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[-\s]+", "_", re.sub(r"[^\w\s-]", "", text).strip().lower())
    return text[:80]

def build_session(proxy: str | None = None) -> requests.Session:
    s = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    if proxy: s.proxies.update({"http": proxy, "https": proxy})
    s.headers.update(get_headers())
    return s

def process_item(item, cfg: dict, base_url: str) -> VideoResult | None:
    try:
        l_el = item.select_one(cfg["link_selector"])
        if not l_el or not l_el.get("href"): return None
        link = urljoin(base_url, l_el.get("href"))

        t_el = item.select_one(cfg["title_selector"])
        title = "Untitled"
        if t_el:
            attr = cfg.get("title_attribute")
            title = (t_el.get(attr) if attr else t_el.get_text()) or "Untitled"

        img_url = None
        i_el = item.select_one(cfg["img_selector"])
        if i_el:
            img_attr = cfg.get("img_attribute", "src")
            img_url = i_el.get(img_attr) or i_el.get("data-src") or i_el.get("src")
            if img_url: img_url = urljoin(base_url, img_url)

        return VideoResult(
            title=html.escape(title.strip()),
            link=link,
            img_url=img_url,
            time=item.select_one(cfg.get("time_selector", "N/A")).get_text() if cfg.get("time_selector") and item.select_one(cfg["time_selector"]) else "N/A",
            engine=base_url
        )
    except Exception: return None

# ── Scraper & Gallery Logic ──────────────────────────────────────────────

async def download_thumb_async(session, url, path, referer):
    try:
        async with session.get(url, headers=get_headers(referer), timeout=10) as resp:
            if resp.status == 200:
                content = await resp.read()
                with open(path, "wb") as f: f.write(content)
                return True
    except: return False
    return False

async def build_gallery(results, query, engine, workers, outdir, thumbdir, download_thumbs):
    outdir.mkdir(parents=True, exist_ok=True)
    thumbdir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = outdir / f"{engine}_{sanitize_filename(query)}_{timestamp}.html"
    placeholder = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAzMjAgMTgwIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjMWUxZTFlIi8+PHBhdGggZD0iTTE0MCA3MGw2MCAzMC02MCAzMCIgZmlsbD0iIzk5OSIvPjwvc3ZnPg=="

    if download_thumbs and ASYNC_AVAILABLE:
        logger.info(f"Downloading thumbnails using {workers} workers...")
        async with aiohttp.ClientSession() as session:
            tasks = []
            for i, res in enumerate(results):
                if res.img_url:
                    t_path = thumbdir / f"t_{timestamp}_{i}.jpg"
                    tasks.append(download_thumb_async(session, res.img_url, t_path, res.engine))
                    res.local_thumb = f"{thumbdir.name}/{t_path.name}"
                else:
                    res.local_thumb = placeholder
            await asyncio.gather(*tasks)

    cards = []
    for res in results:
        cards.append(f"""
        <div class="card" style="background:#1e293b; border-radius:12px; overflow:hidden; border:1px solid #334155; transition: 0.3s;">
            <a href="{res.link}" target="_blank" style="text-decoration:none;">
                <img loading="lazy" src="{res.local_thumb or placeholder}" style="width:100%; aspect-ratio:16/9; object-fit:cover;">
                <div style="padding:12px;">
                    <h4 style="margin:0; font-size:14px; color:#f8fafc; line-height:1.4; height:40px; overflow:hidden;">{res.title}</h4>
                    <div style="font-size:12px; color:#38bdf8; margin-top:8px; font-weight:bold;">{res.time}</div>
                </div>
            </a>
        </div>""")

    html_tmpl = f"""<!DOCTYPE html>
    <html lang="en" style="background:#0f172a; color:#f8fafc; font-family: sans-serif;">
    <head>
        <meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Search: {query}</title>
    </head>
    <body style="padding:20px; max-width:1400px; margin:auto;">
        <h1 style="border-bottom: 2px solid #334155; padding-bottom:10px;">{query} <small style="color:#94a3b8;">({engine})</small></h1>
        <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(260px, 1fr)); gap:20px; margin-top:20px;">
            {"".join(cards)}
        </div>
    </body></html>"""

    with open(filepath, "w", encoding="utf-8") as f: f.write(html_tmpl)
    return filepath

# ── Main ─────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Ultimate Video Scraper V4.2")
    parser.add_argument("query", nargs="?", help="Search term")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=list(ENGINE_MAP.keys()))
    parser.add_argument("-l", "--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("-w", "--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--no-thumbs", action="store_true")
    args = parser.parse_args()

    if not args.query:
        args.query = input(f"{NEON['YELLOW']}Enter Search Query: {NEON['RESET']}")
        if not args.query: return

    cfg = ENGINE_MAP[args.engine]
    session = build_session()

    # FIXED: Corrected multi-line variable assignment syntax
    needs_js = bool(cfg.get("requires_js"))
    want_selenium = (not args.no_thumbs) and needs_js

    results = []
    logger.info(f"{NEON['GREEN']}Searching '{args.query}' on {args.engine}...{NEON['RESET']}")

    search_url = cfg["url"] + cfg["search_path"].format(query=quote_plus(args.query), page=1)

    try:
        resp = session.get(search_url, timeout=DEFAULT_TIMEOUT)
        soup = BeautifulSoup(resp.text, "html.parser")
        items = soup.select(cfg["video_item_selector"])

        for item in items[:args.limit]:
            res = process_item(item, cfg, cfg["url"])
            if res: results.append(res)

        if not results:
            logger.error("No results found.")
            return

        logger.info(f"Scraped {len(results)} items. Building gallery...")

        output = asyncio.run(build_gallery(
            results, args.query, args.engine, args.workers,
            DEFAULT_OUTPUT_DIR, DEFAULT_THUMBS_DIR, not args.no_thumbs
        ))

        print(f"\n{NEON['GREEN']}SUCCESS: {NEON['WHITE']}{output.absolute()}{NEON['RESET']}")

    except KeyboardInterrupt:
        print(f"\n{NEON['YELLOW']}Operation cancelled by user.{NEON['RESET']}")

if __name__ == "__main__":
    main()
