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

# Enhanced logging with context
class ContextFilter(logging.Filter):
    def filter(self, record):
        record.engine = getattr(record, 'engine', 'unknown')
        record.query = getattr(record, 'query', 'unknown')
        return True

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
logger.addFilter(ContextFilter())

# Suppress noisy loggers
for noisy in ("urllib3", "chardet", "requests", "aiohttp", "selenium"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


# Optional async and selenium support
try:
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False
    
try:
    import undetected_chromedriver as uc
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, WebDriverException
    SELENIUM_AVAILABLE = True
except ImportError:
    logger.info("Selenium libraries not found. To scrape JavaScript-heavy sites, install with: pip install selenium undetected-chromedriver")
    SELENIUM_AVAILABLE = False

def create_selenium_driver() -> Optional[uc.Chrome]:
    """Create Selenium driver for JavaScript-heavy sites using undetected-chromedriver."""
    if not SELENIUM_AVAILABLE:
        return None
        
    try:
        options = uc.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        logger.info("Initializing undetected-chromedriver...")
        # This forces undetected-chromedriver to download the driver if it's missing.
        driver = uc.Chrome(options=options, driver_executable_path=None, browser_executable_path=None)
        driver.set_page_load_timeout(45)
        logger.info("Selenium driver created successfully.")
        return driver
    except Exception as e:
        logger.warning(f"Failed to create Selenium driver: {e}", exc_info=True)
        return None


def extract_with_selenium(driver: webdriver.Chrome, url: str, cfg: Dict) -> List:
    """Extract data using Selenium for JavaScript-heavy sites[2]."""
    try:
        driver.get(url)
        
        # Wait for video items to load
        wait = WebDriverWait(driver, 10)
        found_element = False
        for selector in cfg["video_item_selector"].split(','):
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector.strip())))
                found_element = True
                logger.debug(f"Selenium found element with selector: {selector.strip()}")
                break
            except TimeoutException:
                logger.debug(f"Selenium did not find element with selector: {selector.strip()}")
                continue
        
        if not found_element:
            logger.warning(f"Selenium could not find any video items with provided selectors for {url}")
            return []
        
        # Additional wait to ensure dynamic content loads
        time.sleep(2)
        
        # Get page source and parse with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")
        logger.debug(f"Selenium parsed soup: {soup.prettify()}")

        # Save page source to file for debugging if in debug mode and engine is Pornhub
        if logger.level <= logging.DEBUG and cfg.get("url") == "https://www.pornhub.com":
            debug_file_path = Path("pornhub_debug.html")
            try:
                with open(debug_file_path, "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                logger.debug(f"Pornhub debug HTML saved to: {debug_file_path}")
            except Exception as e:
                logger.error(f"Failed to save debug HTML: {e}")

        return extract_video_items(soup, cfg)
        
    except (TimeoutException, WebDriverException) as e:
        logger.warning(f"Selenium extraction failed for {url}: {e}")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred during Selenium extraction for {url}: {e}")
        return []

try:
    from tqdm import tqdm
except ModuleNotFoundError:
    def tqdm(iterable, **kwargs):  # type: ignore
        return iterable


# ── Enhanced Defaults ────────────────────────────────────────────────────
THUMBNAILS_DIR = "downloaded_thumbnails"
VSEARCH_DIR = "vsearch"
DEFAULT_ENGINE = "pexels"
DEFAULT_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_FORMAT = "html"
DEFAULT_TIMEOUT = 25
DEFAULT_DELAY = (1.5, 4.0)  # Random delay with jitter
DEFAULT_MAX_RETRIES = 5
DEFAULT_WORKERS = 12

# Enhanced User-Agent rotation based on 2025 browser statistics[1][2][3]
REALISTIC_USER_AGENTS = [
    # Chrome on Windows (most common)
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox variations
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.2277.83",
]

# Realistic browser headers to avoid bot detection[2][3]
def get_realistic_headers(user_agent: str) -> Dict[str, str]:
    """Generate realistic browser headers based on User-Agent."""
    return {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": random.choice([
            "en-US,en;q=0.9",
            "en-GB,en;q=0.9",
            "en-US,en;q=0.8,es;q=0.6",
        ]),
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

# ── Enhanced Engine Configurations ─────────────────────────────────────────
ENGINE_MAP: Dict[str, Dict[str, Any]] = {
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
            "img": ["img[data-src]", "img[src]", "img[data-lazy]", "img[data-testid='video-card-img']"], # Added data-testid for robustness
            "link": ["a[href*='/video/']", "a.video-link"]
        }
    },
    "dailymotion": {
        "url": "https://www.dailymotion.com",
        "search_path": "/search/{query}/videos",
        "page_param": "page",
        "requires_js": True,  # Dailymotion loads content dynamically
        "video_item_selector": 'div[data-testid="video-card"], .video-item',
        "link_selector": 'a[data-testid="card-link"], .video-link',
        "title_selector": 'div[data-testid="card-title"], .video-title',
        "img_selector": 'img[data-testid="card-thumbnail"], img.thumbnail',
        "time_selector": 'span[data-testid="card-duration"], .duration',
        "channel_name_selector": 'div[data-testid="card-owner-name"], .owner-name',
        "channel_link_selector": 'a[data-testid="card-owner-link"], .owner-link',
        "fallback_selectors": {
            "title": [".video-title", "h3", "[title]"],
            "img": ["img[src]", "img[data-src]", "img[data-testid='card-thumbnail']"], # Added data-testid for robustness
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
            "title": ["a[title]"],
            "img": ["img[data-src]", "img[src]", "img[data-role='thumb-preview-img']"], # Added data-role for robustness
            "link": ["a[href*='/videos/']"]
        }
    },
    "pornhub": {
        "url": "https://www.pornhub.com",
        "search_path": "/video/search?search={query}",
        "gif_search_path": "/gifs/search?search={query}",
        "page_param": "page",
        "requires_js": True,
        "video_item_selector": "li.pcVideoListItem, div.phimage, div.videoblock, div.video-item", # More generic selectors
        "link_selector": "a.previewVideo, a.thumb, a[href*='/view_video.php'], .video-link, .videoblock__link", # More generic
        "title_selector": "a.previewVideo .title, a.thumb .title, .video-title, .videoblock__title, a[title]", # More generic
        "img_selector": "img[src], img[data-src], img[data-lazy], img[data-thumb]",
        "time_selector": "var.duration, .duration, .videoblock__duration, span.duration", # More generic
        "channel_name_selector": ".usernameWrap a, .channel-name, .videoblock__channel, a[href*='/users/']", # More generic
        "channel_link_selector": ".usernameWrap a, .channel-link, a[href*='/users/']", # More generic
        "meta_selector": ".views, .video-views, .videoblock__views, span.views", # More generic
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
            "img": ["img[data-src]", "img[src]", ".thumb img"], # Added .thumb img for robustness
            "link": ["a[href*='/video']"]
        }
    },
    "xnxx": {
        "url": "https://www.xnxx.com",
        "search_path": "/search/{query}/",
        "page_param": "p",
        "requires_js": False,
        "video_item_selector": "div.mozaique > div.thumb-block",
        "link_selector": ".thumb-under > a",
        "title_selector": ".thumb-under > a",
        "img_selector": "img[data-src], img[src]", # Added img[src]
        "time_selector": "span.duration",
        "meta_selector": "span.video-views",
        "fallback_selectors": {
            "title": ["a[title]", "p.title"],
            "img": ["img[src]", "img[data-src]"], # Reordered for priority
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
        "img_selector": "img.img-responsive.lazy, img[data-original], img[src]", # Added img[src]
        "img_attribute": "data-original",
        "time_selector": "span.time",
        "meta_selector": "span.views",
        "fallback_selectors": {
            "title": ["a[title]"],
            "img": ["img[data-original]", "img[src]", "img.img-responsive.lazy"], # Reordered for priority
            "link": ["a[href*='/videos/']"]
        }
    },
    "spankbang": {
        "url": "https://spankbang.com",
        "search_path": "/s/{query}/{page}/",
        "page_param": "",
        "requires_js": True,
        "video_item_selector": "div.video-item",
        "link_selector": "a.video-item__link",
        "title_selector": "a.video-item__title",
        "img_selector": "img.video-item__img, img[data-src], img[src]", # Added img[src]
        "time_selector": "div.video-item__duration",
        "meta_selector": "div.video-item__views",
        "fallback_selectors": {
            "title": ["a[title]"],
            "img": ["img[data-src]", "img[src]", "img.video-item__img"], # Reordered for priority
            "link": ["a[href*='/video']"]
        }
    },
}

# --- Helper Functions ---
def ensure_directory_exists(directory_path: str) -> None:
    """Creates a directory if it doesn't exist."""
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path)
            logger.info(f"{NEON_GREEN}Created directory: {directory_path}{RESET_ALL}")
        except OSError as e:
            logger.error(f"{NEON_RED}Error creating directory {directory_path}: {e}{RESET_ALL}")
            raise

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a string to be suitable for use as a filename.
    Removes or replaces characters that are problematic in filenames.
    Limits length to avoid issues with max filename length on some OS.
    """
    if not filename:
        return "unknown_title"
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'[\s-]+', '_', filename).strip('_')
    return filename[:100]

def download_file(session: requests.Session, url: str, local_filepath: str, timeout: int = 15) -> bool:
    """
    Downloads a file from a URL to a local path using a requests session.
    Returns True if successful, False otherwise.
    """
    try:
        logger.debug(f"Attempting to download: {url} to {local_filepath}")
        response = session.get(url, stream=True, timeout=timeout)
        response.raise_for_status()
        with open(local_filepath, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info(f"{NEON_GREEN}Successfully downloaded to {local_filepath}{RESET_ALL}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"{NEON_RED}Error downloading {url}: {e}{RESET_ALL}")
        return False
    except OSError as e:
        logger.error(f"{NEON_RED}Error saving file to {local_filepath}: {e}{RESET_ALL}")
        return False
    except Exception as e:
        logger.error(f"{NEON_RED}An unexpected error occurred during download: {e}{RESET_ALL}")
        return False

# --- Search Functionality ---
def search(
    session: requests.Session,
    query: str,
    limit: int,
    engine: str,
    page: int,
    driver: Optional[webdriver.Chrome] = None
) -> List[Dict]:
    """
    Performs a search using a specified engine and returns parsed results.
    """
    if engine not in ENGINE_MAP:
        logger.error(f"{NEON_RED}Unsupported engine: {engine}{RESET_ALL}")
        return []

    engine_config = ENGINE_MAP[engine]
    base_url = engine_config["url"]
    search_path = engine_config["search_path"]
    page_param = engine_config.get("page_param", "page")

    search_url = urljoin(base_url, f"{search_path}?q={query.replace(' ', '+')}")
    if page > 1:
        search_url += f"&{page_param}={page}"

    try:
        logger.info(f"Searching at URL: {search_url}")
        
        if engine_config.get("requires_js", False) and driver:
            video_items = extract_with_selenium(driver, search_url, engine_config)
        else:
            response = session.get(search_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            video_items = soup.select(engine_config["video_item_selector"])

        results = []
        for idx, item in enumerate(video_items[:limit]):
            try:
                title_tag = item.select_one(engine_config["title_selector"])
                img_tag = item.select_one(engine_config["img_selector"])
                link_tag = item.select_one(engine_config["link_selector"])

                title = title_tag.text.strip() if title_tag else "Untitled"
                img_url = None
                if img_tag:
                    img_url = img_tag.get("data-src") or img_tag.get("src")
                link = link_tag["href"] if link_tag and "href" in link_tag.attrs else None

                if link:
                    link = urljoin(base_url, link)
                if img_url:
                    img_url = urljoin(base_url, img_url)

                results.append({
                    "title": title,
                    "img_url": img_url,
                    "link": link,
                    "quality": "N/A",
                    "time": "N/A",
                    "channel_name": "N/A",
                    "channel_link": "#"
                })

            except Exception as e:
                logger.warning(f"{NEON_YELLOW}Error parsing an item: {e}{RESET_ALL}")
                continue

        logger.info(f"Found {len(results)} results for query '{query}'.")
        return results

    except requests.exceptions.RequestException as e:
        logger.error(f"{NEON_RED}Request error during search: {e}{RESET_ALL}")
        return []
    except Exception as e:
        logger.error(f"{NEON_RED}Unexpected error during search: {e}{RESET_ALL}")
        return []

# --- HTML Output Generation ---
def generate_html_output(
    session: requests.Session,
    results: List[Dict],
    query: str,
    engine: str,
    search_limit: int,
    output_dir: str,
    prefix_format: str
) -> Optional[str]:
    """
    Generates an HTML file with search results, downloading thumbnails locally.
    """
    if not results:
        logger.warning(f"{NEON_YELLOW}No videos found for query '{query}'. No HTML file generated.{RESET_ALL}")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    query_part = sanitize_filename(query)
    filename_prefix = prefix_format.format(engine=engine, query_part=query_part, timestamp=timestamp)
    output_filename = os.path.join(output_dir, f"{filename_prefix}.html")

    ensure_directory_exists(output_dir)
    local_thumbs_dir = os.path.join(output_dir, THUMBNAILS_DIR)
    ensure_directory_exists(local_thumbs_dir)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Search Results for '{query}' on {engine}</title>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Share Tech Mono', monospace; background: linear-gradient(to bottom, #1a1a2e, #0a0a1e); color: #e0e0e0; margin: 0; padding: 20px; line-height: 1.6; }}
            .container {{ max-width: 1400px; margin: 0 auto; padding: 30px; background-color: #2a2a4a; border-radius: 12px; box-shadow: 0 0 20px rgba(0, 255, 255, 0.6), 0 0 30px rgba(255, 0, 255, 0.4); border: 2px solid #00ffff; }}
            h1 {{ font-family: 'Orbitron', sans-serif; color: #00ffff; text-align: center; margin-bottom: 15px; text-shadow: 0 0 8px rgba(0, 255, 255, 0.9); }}
            .search-params {{ text-align: center; margin-bottom: 30px; color: #aaffaa; font-size: 0.95em; border: 1px dashed #00ff00; padding: 10px; border-radius: 5px; background-color: rgba(0, 255, 0, 0.05); }}
            .search-params p {{ margin: 5px 0; }}
            .video-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 25px; margin-top: 30px; }}
            .video-item {{ background-color: #3a3a5a; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.6); transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out; display: flex; flex-direction: column; }}
            .video-item:hover {{ transform: translateY(-8px); box-shadow: 0 8px 25px rgba(0, 255, 255, 0.8), 0 8px 35px rgba(255, 0, 255, 0.6); }}
            .video-item img {{ width: 100%; height: 200px; object-fit: cover; border-bottom: 2px solid #00ffff; }}
            .video-info {{ padding: 20px; display: flex; flex-direction: column; justify-content: space-between; flex-grow: 1; }}
            .video-info h3 {{ margin-top: 0; margin-bottom: 15px; font-size: 1.2em; color: #ff69b4; line-height: 1.3; }}
            .video-info a {{ text-decoration: none; color: #ff69b4; transition: color 0.2s, text-shadow 0.2s; }}
            .video-info a:hover {{ color: #ffa0d0; text-decoration: underline; }}
            .video-meta {{ font-size: 0.8em; color: #aaa; margin-top: auto; display: flex; flex-wrap: wrap; gap: 5px; padding-top: 10px; }}
            .video-meta span {{ background-color: rgba(0, 255, 255, 0.1); padding: 4px 8px; border-radius: 4px; border: 1px solid rgba(0, 255, 255, 0.3); white-space: nowrap; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Search Results</h1>
            <div class="search-params">
                <p><strong>Engine:</strong> {engine} | <strong>Query:</strong> {query} | <strong>Limit:</strong> {search_limit} Videos</p>
                <p><em>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
            </div>
            <div class="video-grid">
    """

    for idx, video in enumerate(results):
        title = video.get("title", "N/A")
        img_url = video.get("img_url")
        link = video.get("link", "#")
        quality = video.get("quality", "N/A")
        video_time = video.get("time", "N/A")
        channel_name = video.get("channel_name", "N/A")
        channel_link = video.get("channel_link", "#")

        local_img_path = "https://via.placeholder.com/300x200?text=No+Image"
        if img_url:
            try:
                file_ext = os.path.splitext(img_url.split('?'))[-1] or '.jpg'
                thumb_filename = f"{sanitize_filename(title)}_{idx}{file_ext}"
                local_filepath = os.path.join(local_thumbs_dir, thumb_filename)
                if download_file(session, img_url, local_filepath):
                    local_img_path = os.path.join(THUMBNAILS_DIR, thumb_filename)
            except Exception as e:
                logger.warning(f"Could not process thumbnail for '{title}': {e}")

        html_content += f"""
                <div class="video-item">
                    <a href="{link}" target="_blank" rel="noopener noreferrer">
                        <img src="{local_img_path}" alt="{title}" onerror="this.onerror=null; this.src='https://via.placeholder.com/300x200?text=Image+Error';">
                    </a>
                    <div class="video-info">
                        <h3><a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a></h3>
                        <div class="video-meta">
                            {f'<span>Quality: {quality}</span>' if quality != 'N/A' else ''}
                            {f'<span>Time: {video_time}</span>' if video_time != 'N/A' else ''}
                            {f'<span>Channel: <a href="{channel_link}" target="_blank" rel="noopener noreferrer">{channel_name}</a></span>' if channel_name != 'N/A' else ''}
                        </div>
                    </div>
                </div>
        """

    html_content += """
            </div>
        </div>
    </body>
    </html>
    """

    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"{NEON_GREEN}HTML output saved to: {NEON_WHITE}{output_filename}{RESET_ALL}")
        return output_filename
    except OSError as e:
        logger.error(f"{NEON_RED}Error saving HTML file: {e}{RESET_ALL}")
        return None

# --- Main Interactive Logic ---
def run_interactive_mode() -> Dict:
    """Runs the script in interactive mode, prompting the user for input."""
    logger.info(f"{NEON_CYAN}{NEON_BRIGHT}--- Starting Search Script (Interactive Mode) ---{RESET_ALL}")

    query = input(f"{NEON_YELLOW}Enter search query: {RESET_ALL}{NEON_BRIGHT}")
    if not query:
        logger.critical(f"{NEON_RED}Search query cannot be empty. Exiting.{RESET_ALL}")
        sys.exit(1)

    try:
        limit_input = input(f"{NEON_YELLOW}Max results to fetch? [{DEFAULT_SEARCH_LIMIT}]: {RESET_ALL}{NEON_BRIGHT}")
        search_limit = int(limit_input) if limit_input.strip() else DEFAULT_SEARCH_LIMIT
        if search_limit <= 0: raise ValueError("must be positive")
    except ValueError:
        logger.warning(f"{NEON_RED}Invalid limit. Using default: {DEFAULT_SEARCH_LIMIT}{RESET_ALL}")
        search_limit = DEFAULT_SEARCH_LIMIT

    try:
        page_input = input(f"{NEON_YELLOW}Page number? [{DEFAULT_PAGE_NUMBER}]: {RESET_ALL}{NEON_BRIGHT}")
        page_number = int(page_input) if page_input.strip() else DEFAULT_PAGE_NUMBER
        if page_number <= 0: raise ValueError("must be positive")
    except ValueError:
        logger.warning(f"{NEON_RED}Invalid page number. Using default: {DEFAULT_PAGE_NUMBER}{RESET_ALL}")
        page_number = DEFAULT_PAGE_NUMBER

    available_engines = ", ".join(ENGINE_MAP.keys())
    engine_input = input(f"{NEON_YELLOW}Search engine? [{DEFAULT_ENGINE}] (Options: {available_engines}): {RESET_ALL}{NEON_BRIGHT}")
    engine = engine_input.lower().strip() or DEFAULT_ENGINE
    if engine not in ENGINE_MAP:
        logger.critical(f"{NEON_RED}Unsupported engine '{engine}'. Please choose from: {available_engines}{RESET_ALL}")
        sys.exit(1)

    output_dir = input(f"{NEON_YELLOW}Output directory? [.]: {RESET_ALL}{NEON_BRIGHT}").strip() or "."

    default_prefix = "{engine}_search_{query_part}_{timestamp}"
    prefix_format = input(f"{NEON_YELLOW}Filename prefix format? [{default_prefix}]: {RESET_ALL}{NEON_BRIGHT}").strip() or default_prefix

    auto_open_input = input(f"{NEON_YELLOW}Auto-open HTML file (y/n)? [y]: {RESET_ALL}{NEON_BRIGHT}")
    auto_open = auto_open_input.lower().strip() not in ("n", "no")

    return {
        "query": query,
        "limit": search_limit,
        "page": page_number,
        "engine": engine,
        "output_dir": output_dir,
        "prefix_format": prefix_format,
        "auto_open": auto_open
    }

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Search a video engine and generate an HTML report with cached thumbnails.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("query", nargs="?", help="The search query. If omitted, runs in interactive mode.")
    parser.add_argument("-l", "--limit", type=int, default=DEFAULT_SEARCH_LIMIT, help=f"Max results to fetch. Default: {DEFAULT_SEARCH_LIMIT}")
    parser.add_argument("-p", "--page", type=int, default=DEFAULT_PAGE_NUMBER, help=f"Page number to search. Default: {DEFAULT_PAGE_NUMBER}")
    parser.add_argument("-e", "--engine", default=DEFAULT_ENGINE, choices=ENGINE_MAP.keys(), help=f"Search engine to use. Default: {DEFAULT_ENGINE}")
    parser.add_argument("-o", "--output-dir", default=".", help="Directory to save the output HTML and thumbnails. Default: current directory")
    parser.add_argument("--no-open", action="store_true", help="Prevent automatically opening the HTML file in a browser.")

    args = parser.parse_args()

    if args.query:
        settings = {
            "query": args.query,
            "limit": args.limit,
            "page": args.page,
            "engine": args.engine,
            "output_dir": args.output_dir,
            "prefix_format": "{engine}_search_{query_part}_{timestamp}",
            "auto_open": not args.no_open
        }
        logger.info(f"{NEON_CYAN}{NEON_BRIGHT}--- Running in Command-Line Mode ---{RESET_ALL}")
    else:
        settings = run_interactive_mode()

    logger.info(f"{NEON_CYAN}--- Settings Summary ---{RESET_ALL}")
    for key, value in settings.items():
        logger.info(f"  {NEON_BLUE}{key.replace('_', ' ').title()}:{RESET_ALL} {value}")
    logger.info(f"{NEON_CYAN}------------------------{RESET_ALL}")

    driver = None
    try:
        if ENGINE_MAP[settings["engine"]].get("requires_js", False) and SELENIUM_AVAILABLE:
            driver = create_selenium_driver()
            if not driver:
                logger.error(f"{NEON_RED}Failed to initialize Selenium driver. Cannot scrape JavaScript-heavy site.{RESET_ALL}")
                sys.exit(1)

        with requests.Session() as session:
            session.headers.update({"User-Agent": USER_AGENT})

            results = search(
                session=session,
                query=settings["query"],
                limit=settings["limit"],
                engine=settings["engine"],
                page=settings["page"],
                driver=driver
            )

            html_file = generate_html_output(
                session=session,
                results=results,
                query=settings["query"],
                engine=settings["engine"],
                search_limit=settings["limit"],
                output_dir=settings["output_dir"],
                prefix_format=settings["prefix_format"]
            )

        if html_file and settings["auto_open"]:
            logger.info(f"{NEON_MAGENTA}Attempting to open {html_file} in your default browser...{RESET_ALL}")
            try:
                webbrowser.open(f"file://{os.path.abspath(html_file)}")
            except Exception as e:
                logger.error(f"{NEON_RED}Failed to open HTML file in browser: {e}. You can open it manually: {NEON_WHITE}{os.path.abspath(html_file)}{RESET_ALL}")
        elif html_file:
            logger.info(f"{NEON_BLUE}HTML file generated at: {NEON_WHITE}{os.path.abspath(html_file)}{RESET_ALL}")

    except Exception as e:
        logger.critical(f"{NEON_RED}An unhandled error occurred: {e}{RESET_ALL}", exc_info=True)

    finally:
        if driver:
            driver.quit()

    logger.info(f"{NEON_CYAN}{NEON_BRIGHT}--- Script Finished ---{RESET_ALL}")

if __name__ == "__main__":
    main()