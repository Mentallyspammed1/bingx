#!/usr/bin/env python3
"""vsearch.py  •  2025-09-12 (PYRMETHUS-ENHANCED-V4)"""

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
import unicodedata
import webbrowser
from collections.abc import AsyncGenerator, Sequence
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta
from pathlib import Path
from string import Template
from typing import Any, Final
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from requests.adapters import HTTPAdapter
from requests.adapters import Retry

try:
    import aiohttp
    ASYNC_AVAILABLE: bool = True
except ImportError:
    ASYNC_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    SELENIUM_AVAILABLE: bool = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

init(autoreset=True)

NEON: Final[dict[str, str]] = {
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

LOG_FMT: Final[str] = f"{NEON['CYAN']}%(asctime)s{NEON['RESET']} [%(levelname)s] {NEON['GREEN']}%(message)s{NEON['RESET']}"

class WizardFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.engine = getattr(record, 'engine', 'VOID')
        return True

logger = logging.getLogger("Pyrmethus")
logger.setLevel(logging.INFO)
logger.addFilter(WizardFilter())
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(LOG_FMT))
logger.addHandler(handler)

for noisy in ("urllib3", "chardet", "requests", "aiohttp", "selenium"):
    logging.getLogger(noisy).setLevel(logging.CRITICAL)

THUMBNAILS_DIR: Final[Path] = Path.home() / ".cache" / "vsearch_thumbs"
OUTPUT_DIR: Final[Path] = Path.cwd() / "vsearch_library"
DEFAULT_ENGINE: Final[str] = "pexels"
DEFAULT_LIMIT: Final[int] = 40
DEFAULT_TIMEOUT: Final[int] = 20
DEFAULT_DELAY: Final[tuple[float, float]] = (2.0, 4.5)
DEFAULT_CACHE_TTL: Final[int] = 14

REALISTIC_USER_AGENTS: Final[list[str]] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
]

ENGINE_MAP: Final[dict[str, dict[str, Any]]] = {
    "pexels": {
        "url": "https://www.pexels.com",
        "search_path": "/search/videos/{query}/?page={page}",
        "requires_js": False,
        "video_item_selector": "article[data-testid='video-card']",
        "link_selector": "a[data-testid='video-card-link']",
        "title_selector": "img[data-testid='video-card-img']",
        "title_attribute": "alt",
        "img_selector": "img[data-testid='video-card-img']",
        "fallback_selectors": {"title": [], "img": [], "link": []}
    },
    "dailymotion": {
        "url": "https://www.dailymotion.com",
        "search_path": "/search/{query}/videos?page={page}",
        "requires_js": True,
        "video_item_selector": "div[data-testid='video-card']",
        "link_selector": "a[data-testid='card-link']",
        "title_selector": "div[data-testid='card-title']",
        "img_selector": "img[data-testid='card-thumbnail']",
        "time_selector": "span[data-testid='card-duration']",
        "fallback_selectors": {"title": [], "img": [], "link": []}
    },
    "xnxx": {
        "url": "https://www.xnxx.com",
        "search_path": "/search/{query}/{page}/",
        "requires_js": False,
        "video_item_selector": "div.mosaic-video, div.thumb-block",
        "link_selector": "a[href*='/video-']",
        "title_selector": "p.videoThumbTitle a, span.title",
        "img_selector": "img.lazy, img[data-src]",
        "time_selector": "span.duration",
        "fallback_selectors": {"title": [".title"], "img": ["img.thumb-image"], "link": ["a"]}
    },
    "xvideos": {
        "url": "https://www.xvideos.com",
        "search_path": "/?k={query}&p={page}",
        "requires_js": False,
        "video_item_selector": "div.mozaique > div",
        "link_selector": "a[href*='/video']",
        "title_selector": "p.title a",
        "img_selector": "img[data-src]",
        "time_selector": ".duration",
        "fallback_selectors": {"title": [".title"], "img": [".thumb img"], "link": ["a"]}
    },
    "pornhub": {
        "url": "https://www.pornhub.com",
        "search_path": "/video/search?search={query}&page={page}",
        "requires_js": True,
        "video_item_selector": "li.pcVideoListItem, div.videoBox",
        "link_selector": "a[href*='/view_video.php']",
        "title_selector": "span.title, a.video-title",
        "img_selector": "img[data-mediabook], img[data-src]",
        "time_selector": "var.duration",
        "fallback_selectors": {"title": [".videoTitle"], "img": ["img.thumb_img"], "link": []}
    },
    "xhamster": {
        "url": "https://xhamster.com",
        "search_path": "/search/{query}/{page}",
        "requires_js": True,
        "video_item_selector": "div.video-thumb, div[data-video-id]",
        "link_selector": "a.video-thumb__image-container",
        "title_selector": "a.video-thumb__name",
        "img_selector": "img.thumb-image-container__image",
        "time_selector": "span.duration",
        "fallback_selectors": {"title": [".title"], "img": ["img[data-src]"], "link": ["a"]}
    },
    "spankbang": {
        "url": "https://spankbang.com",
        "search_path": "/s/{query}/{page}/",
        "requires_js": True,
        "video_item_selector": "div.video-item",
        "link_selector": "a.n",
        "title_selector": "a.n",
        "img_selector": "img[data-src]",
        "time_selector": "span.l",
        "fallback_selectors": {"title": [".t"], "img": ["img.cover"], "link": ["a"]}
    },
    "youjizz": {
        "url": "https://www.youjizz.com",
        "search_path": "/search/{query}-{page}.html",
        "requires_js": True,
        "video_item_selector": "div.video-thumb",
        "link_selector": "a.frame",
        "title_selector": "div.video-title",
        "img_selector": "img[data-original]",
        "time_selector": "span.time",
        "fallback_selectors": {"title": [], "img": ["img.lazy"], "link": []}
    },
    "motherless": {
        "url": "https://motherless.com",
        "search_path": "/term/videos/{query}?page={page}",
        "requires_js": False,
        "video_item_selector": "div.thumb",
        "link_selector": "a.img-container",
        "title_selector": "span.caption-title",
        "img_selector": "img.static",
        "time_selector": "span.thumb-duration",
        "fallback_selectors": {"title": [], "img": ["img"], "link": []}
    },
    "redtube": {
        "url": "https://www.redtube.com",
        "search_path": "/?search={query}&page={page}",
        "requires_js": False,
        "video_item_selector": "li.video_item",
        "link_selector": "a.video_link",
        "title_selector": "span.video_title",
        "img_selector": "img.video_thumb",
        "time_selector": "span.duration",
        "fallback_selectors": {"title": [], "img": ["img[data-src]"], "link": []}
    },
}

def get_headers() -> dict[str, str]:
    ua = random.choice(REALISTIC_USER_AGENTS)
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

def ensure_dir(path: Path) -> None:
    with suppress(OSError):
        path.mkdir(parents=True, exist_ok=True)

def enhanced_slugify(text: str) -> str:
    if not text: return "void"
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    return re.sub(r'[-\s]+', '_', text)[:64]

def build_session(proxies: list[str] | None = None) -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=50, pool_maxsize=100)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    if proxies:
        p = random.choice(proxies)
        session.proxies = {"http": p, "https": p}
    return session

def create_phantom_driver() -> webdriver.Chrome | None:
    if not SELENIUM_AVAILABLE: return None
    try:
        opts = ChromeOptions()
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument(f"--user-agent={random.choice(REALISTIC_USER_AGENTS)}")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option('useAutomationExtension', False)
        driver = webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(DEFAULT_TIMEOUT)
        return driver
    except WebDriverException:
        return None

def extract_video_data(item: Any, cfg: dict, base_url: str) -> dict | None:
    try:
        title = "Untitled Essence"
        for sel in [cfg["title_selector"]] + cfg["fallback_selectors"]["title"]:
            el = item.select_one(sel)
            if el:
                title = el.get(cfg.get("title_attribute", ""), el.get_text(strip=True)) or title
                break
        link = "#"
        for sel in [cfg["link_selector"]] + cfg["fallback_selectors"]["link"]:
            el = item.select_one(sel)
            if el and el.has_attr("href"):
                link = urljoin(base_url, el["href"])
                break
        if link == "#" or len(title) < 2: return None
        img_url = None
        for sel in [cfg["img_selector"]] + cfg["fallback_selectors"]["img"]:
            el = item.select_one(sel)
            if el:
                for attr in ["data-src", "src", "data-original", "data-lazy", "data-mfsrc"]:
                    if el.has_attr(attr):
                        val = el[attr]
                        if val and not val.startswith("data:"):
                            img_url = urljoin(base_url, val)
                            break
                if img_url: break
        duration = "N/A"
        if "time_selector" in cfg:
            el = item.select_one(cfg["time_selector"])
            if el: duration = el.get_text(strip=True)
        return {
            "title": html.escape(title),
            "link": link,
            "img_url": img_url,
            "duration": duration,
            "engine": base_url
        }
    except Exception:
        return None

def get_search_results(session: requests.Session, engine: str, query: str, limit: int, page: int) -> list[dict]:
    cfg = ENGINE_MAP.get(engine)
    if not cfg: return []
    results: list[dict] = []
    driver = create_phantom_driver() if cfg["requires_js"] else None
    try:
        for p in range(page, page + 5):
            if len(results) >= limit: break
            url = urljoin(cfg["url"], cfg["search_path"].format(query=quote_plus(query), page=p))
            logger.info(f"Piercing veil {p} of {engine}...")
            try:
                if driver:
                    driver.get(url)
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "body")))
                    time.sleep(2)
                    soup = BeautifulSoup(driver.page_source, "lxml")
                else:
                    resp = session.get(url, headers=get_headers(), timeout=DEFAULT_TIMEOUT)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "lxml")
                items = soup.select(cfg["video_item_selector"])
                for i in items:
                    if len(results) >= limit: break
                    data = extract_video_data(.uniform(*DEFAULT_DELAY))
            except Exception as e:
                logger.error(f"Veil {p} resisted: {e}")
                break
    finally:
        if driver: driver.quit()
    return results

@asynccontextmanager
async def get_aio_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout, headers=get_headers()) as session:
        yield session

async def download_thumb(session: aiohttp.ClientSession, url: str, path: Path, sem: asyncio.Semaphore) -> bool:
    if path.exists(): return True
    async with sem:
        try:
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    if len(content) > 1024:
                        path.write_bytes(content)
                        return True
        except Exception:
            pass
    return False

ENHANCED_HTML_TEMPLATE = Template("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pyrmethus - $query</title>
    <style>
        :root {
            --bg: #050505; --card: #111111; --accent: #00f2ff; --text: #e0e0e0;
            --dim: #888; --shadow: rgba(0, 242, 255, 0.15);
        }
        body {
            background: var(--bg); color: var(--text); font-family: 'Segoe UI', Roboto, sans-serif;
            margin: 0; padding: 20px;
        }
        header {
            text-align: center; padding: 40px 0; border-bottom: 1px solid #222; margin-bottom: 40px;
        }
        h1 {
            color: var(--accent); font-size: 2.5em; text-transform: uppercase; letter-spacing: 4px;
            margin: 0; text-shadow: 0 0 15px var(--shadow);
        }
        .meta { color: var(--dim); margin-top: 10px; font-size: 0.9em; }
        .grid {
            display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 25px; max-width: 1400px; margin: 0 auto;
        }
        .card {
            background: var(--card); border-radius: 12px; overflow: hidden;
            transition: transform 0.3s, box-shadow 0.3s; border: 1px solid #222;
        }
        .card:hover {
            transform: translateY(-5px); box-shadow: 0 10px 20px rgba(0,0,0,0.5), 0 0 15px var(--shadow);
            border-color: var(--accent);
        }
        .thumb-box { position: relative; width: 100%; height: 180px; background: #000; overflow: hidden; }
        .thumb-box img { width: 100%; height: 100%; object-fit: cover; opacity: 0; transition: opacity 0.5s; }
        .thumb-box img.loaded { opacity: 1; }
        .duration {
            position: absolute; bottom: 8px; right: 8px; background: rgba(0,0,0,0.8);
            padding: 2px 6px; border-radius: 4px; font-size: 0.75em; color: var(--accent);
        }
        .info { padding: 15px; }
        .title {
            font-size: 1em; font-weight: 600; line-height: 1.4; height: 2.8em;
            overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
        }
        a { color: inherit; text-decoration: none; transition: color 0.2s; }
        .title a:hover { color: var(--accent); }
        .search-container { max-width: 600px; margin: 20px auto 40px; }
        #filterInput {
            width: 100%; padding: 12px 20px; background: #111; border: 1px solid #333;
            border-radius: 25px; color: #fff; outline: none; transition: border-color 0.3s;
        }
        #filterInput:focus { border-color: var(--accent); }
    </style>
</head>
<body>
    <header>
        <h1>$query</h1>
        <div class="meta">Channeling $engine &bull; $count Essences Found</div>
        <div class="search-container">
            <input type="text" id="filterInput" placeholder="Filter essences..." onkeyup="filterCards()">
        </div>
    </header>
    <div class="grid" id="videoGrid">
        $content
    </div>
    <script>
        function filterCards() {
            let input = document.getElementById('filterInput').value.toLowerCase();
            let cards = document.getElementsByClassName('card');
            for (let card of cards) {
                let title = card.querySelector('.title').innerText.toLowerCase();
                card.style.display = title.includes(input) ? "" : "none";
            }
        }
        document.addEventListener("DOMContentLoaded", function() {
            let observer = new IntersectionObserver((entries, obs) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        let img = entry.target;
                        img.src = img.dataset.src;
                        img.onload = () => img.classList.add('loaded');
                        obs.unobserve(img);
                    }
                });
            }, { threshold: 0.1 });
            document.querySelectorAll('img[data-src]').forEach(img => observer.observe(img));
        });
    </script>
</body>
</html>
""")

async def generate_html(results: list[dict], query: str, engine: str, no_thumbs: bool) -> Path:
    ensure_dir(OUTPUT_DIR)
    ensure_dir(THUMBNAILS_DIR)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = OUTPUT_DIR / f"{engine}_{enhanced_slugify(query)}_{ts}.html"
    
    placeholders = []
    if not no_thumbs:
        sem = asyncio.Semaphore(15)
        async with get_aio_session() as session:
            tasks = []
            for i, res in enumerate(results):
                if res["img_url"]:
                    ext = Path(urlparse(res["img_url"]).path).suffix or ".jpg"
                    p = THUMBNAILS_DIR / f"{enhanced_slugify(res['title'])}_{i}{ext}"
                    tasks.append(download_thumb(session, res["img_url"], p, sem))
                    placeholders.append(os.path.relpath(p, OUTPUT_DIR))
                else:
                    tasks.append(asyncio.sleep(0))
                    placeholders.append("")
            await tqdm.gather(*tasks, desc="Summoning Thumbnails")

    cards = []
    for i, res in enumerate(results):
        thumb = placeholders[i] if not no_thumbs and i < len(placeholders) else ""
        card = f"""
        <div class="card">
            <div class="thumb-box">
                <a href="{res['link']}" target="_blank">
                    <img data-src="{thumb}" alt="essence">
                    <div class="duration">{res['duration']}</div>
                </a>
            </div>
            <div class="info">
                <div class="title"><a href="{res['link']}" target="_blank">{res['title']}</a></div>
            </div>
        </div>"""
        cards.append(card)

    html_content = ENHANCED_HTML_TEMPLATE.substitute(
        query=query.upper(),
        engine=engine.upper(),
        count=len(results),
        content="\n".join(cards)
    )
    out_file.write_text(html_content, encoding="utf-8")
    return out_file

def main():
    parser = argparse.ArgumentParser(description="Pyrmethus' Video Search Grimoire")
    parser.add_argument("query", help="Search string")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=list(ENGINE_MAP))
    parser.add_argument("-l", "--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("-p", "--page", type=int, default=1)
    parser.add_argument("-o", "--output", choices=["html", "json"], default="html")
    parser.add_argument("--no-thumbs", action="store_true")
    parser.add_argument("--proxy", help="Optional proxy URL")
    args = parser.parse_args()

    def exit_gracefully(sig, frame):
        sys.exit(0)
    signal.signal(signal.SIGINT, exit_gracefully)

    session = build_session(proxies=[args.proxy] if args.proxy else None)
    logger.info(f"Initiating ritual for '{args.query}' in realm {args.engine}...")
    
    results = get_search_results(session, args.engine, args.query, args.limit, args.page)
    if not results:
        logger.error("Scrying failed: Empty void returned.")
        sys.exit(1)

    if args.output == "json":
        path = OUTPUT_DIR / f"{args.engine}_{enhanced_slugify(args.query)}.json"
        ensure_dir(OUTPUT_DIR)
        path.write_text(json.dumps(results, indent=4), encoding="utf-8")
        logger.info(f"JSON scroll etched: {path}")
    else:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        path = loop.run_until_complete(generate_html(results, args.query, args.engine, args.no_thumbs))
        logger.info(f"HTML grimoire woven: {path}")
        webbrowser.open(f"file://{path.absolute()}")

if __name__ == "__main__":
    main()
