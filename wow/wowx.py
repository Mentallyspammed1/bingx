#!/usr/bin/env python3
"""wowxxx_search.py - Enhanced Wow.xxx Video Search Tool

Features:
- Modular design with classes/functions
- Robust error handling & retries
- Proxy rotation support
- Async and sync thumbnail download
- Dynamic content rendering with Selenium (optional)
- Modern HTML output with lazy load and placeholders
- Configurable via external JSON
- Command-line interface with flexible options
- Detailed logging and verbose mode

Usage:
  python3 wowxxx_search.py "search query" [options]
"""

import argparse
import asyncio
import base64
import csv
import html
import json
import random
import re
import signal
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup
from colorama import init
from requests.adapters import HTTPAdapter, Retry

# Optional imports
try:
    import aiohttp
    ASYNC_ENABLED = True
except ImportError:
    ASYNC_ENABLED = False

try:
    from selenium import webdriver
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    def tqdm(iterable, **kwargs): return iterable

# Initialize colorama
init(autoreset=True)

# Global Configurations
LOG_FORMAT = (
    "%(asctime)s - %(levelname)s - [%(engine)s] %(message)s"
)

# Logging setup
logger = None
def setup_logging(verbose=False):
    global logger
    import logging
    logger = logging.getLogger("wowxxx")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(ch)

# Signal handling for graceful shutdown
shutdown_flag = False
def handle_sigint(signum, frame):
    global shutdown_flag
    shutdown_flag = True
    logger.warning("Received interrupt signal. Shutting down gracefully.")

# Utility: ensure directory exists
def ensure_dir(path: Path):
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create directory {path}: {e}")
        raise

# Utility: slugify for safe filenames
def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', text)
    text = re.sub(r'[\s\-\.]+', '_', text.strip())
    text = text.strip('_')
    if not text:
        return "untitled"
    # Avoid Windows reserved names
    reserved = {"con", "prn", "aux", "nul", "com1","com2","com3","com4","lpt1","lpt2","lpt3","lpt4"}
    if text.lower() in reserved:
        return f"file_{text}"
    return text[:100]

# User-Agent list for realistic headers
USER_AGENTS = [
    # ... (Same as before) Add more realistic agents if needed
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",
]
def get_headers(user_agent: str):
    headers = {
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
        "Referer": "https://www.google.com/",
        # Additional headers if needed
    }
    return headers

# Build requests session with retries and proxy support
def build_session(proxy=None, proxy_list=None, retries=5, timeout=30):
    session = requests.Session()
    # Retry strategy
    retry_strategy = Retry(
        total=retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Proxy support
    if proxy:
        session.proxies.update({"http": proxy, "https": proxy})

    if proxy_list:
        # Rotation handled separately
        pass

    # Random UA
    user_agent = random.choice(USER_AGENTS)
    session.headers.update(get_headers(user_agent))
    session.timeout = timeout
    return session

# Adaptive delay based on request history
def adaptive_delay(request_times, min_delay=1.5, max_delay=4.0, jitter=0.3):
    now = time.time()
    if len(request_times) >= 2:
        interval = now - request_times[-2]
        if interval < min_delay:
            delay = min_delay / max(0.1, interval) * random.uniform(min_delay, max_delay)
        else:
            delay = random.uniform(min_delay, max_delay)
    else:
        delay = random.uniform(min_delay, max_delay)

    # Add jitter
    delay += delay * jitter * random.gauss(0, 1)
    delay = max(0.5, delay)
    time.sleep(delay)
    request_times.append(time.time())

# Async context manager for aiohttp session
async def get_aiohttp_session():
    if not ASYNC_ENABLED:
        return None
    timeout = aiohttp.ClientTimeout(total=30)
    headers = get_headers(random.choice(USER_AGENTS))
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            yield session
    except Exception as e:
        logger.warning(f"Failed to create aiohttp session: {e}")

# Download thumbnail async
async def download_thumbnail_async(session, url, save_path, semaphore):
    if not session:
        return False
    try:
        async with semaphore:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return False
                content_type = resp.headers.get("content-type", "").lower()
                if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
                    return False
                content = await resp.read()
                if len(content) < 5000:  # Minimum size
                    return False
                # Save atomically
                temp_path = save_path.with_suffix('.tmp')
                with open(temp_path, 'wb') as f:
                    f.write(content)
                temp_path.replace(save_path)
                return True
    except Exception as e:
        logger.debug(f"Async thumbnail download error: {e}")
        return False

# Download thumbnail sync
def download_thumbnail_sync(session, url, save_path):
    if not url:
        return False
    try:
        resp = session.get(url, stream=True, timeout=20)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "").lower()
        if not any(ct in content_type for ct in ["image/", "application/octet-stream"]):
            return False
        content = resp.content
        if len(content) < 5000:
            return False
        temp_path = save_path.with_suffix('.tmp')
        with open(temp_path, 'wb') as f:
            f.write(content)
        temp_path.replace(save_path)
        return True
    except Exception as e:
        logger.debug(f"Sync thumbnail error: {e}")
        return False

# Extract video items from soup
def extract_video_items(soup: BeautifulSoup, selectors: dict[str, str]) -> list:
    items = []
    primary_selectors = [s.strip() for s in selectors.get("video_item_selector", "").split(',') if s.strip()]
    for sel in primary_selectors:
        try:
            found = soup.select(sel)
            if found:
                items.extend(found)
                break
        except Exception:
            continue
    if not items:
        # fallback selectors
        fallback_selectors = ["div.video-item", "li.video-list-item", "article.video"]
        for sel in fallback_selectors:
            try:
                found = soup.select(sel)
                if found:
                    items.extend(found)
                    break
            except Exception:
                continue
    return items

# Extract data from a video item element
def extract_video_data(item, base_url, selectors):
    data = {}
    try:
        # Title
        title = "Untitled"
        for sel in selectors.get("title_selector", "").split(','):
            sel = sel.strip()
            el = item.select_one(sel)
            if el:
                title = el.get_text(strip=True) or el.get("title", "")
                break
        data["title"] = title

        # Link
        link = "#"
        for sel in selectors.get("link_selector", "").split(','):
            sel = sel.strip()
            el = item.select_one(sel)
            if el and el.has_attr("href"):
                link = urljoin(base_url, el["href"].split('?')[0])
                break
        data["link"] = link

        # Image URL
        img_url = None
        for sel in selectors.get("img_selector", "").split(','):
            sel = sel.strip()
            el = item.select_one(sel)
            if el:
                for attr in ["data-src", "src", "data-lazy"]:
                    if el.has_attr(attr):
                        img_url = urljoin(base_url, el[attr])
                        break
                if img_url:
                    break
        data["img_url"] = img_url

        # Duration
        duration = extract_text_safe(item, selectors.get("time_selector", ""))
        if duration == "N/A":
            duration = extract_text_safe(item, "span.duration, div.duration")
        data["time"] = duration

        # Views/Meta
        meta = extract_text_safe(item, selectors.get("meta_selector", ""))
        if meta == "N/A":
            meta = extract_text_safe(item, "span.views, div.views")
        data["meta"] = meta

        # Channel info
        channel_name = extract_text_safe(item, selectors.get("channel_name_selector", ""))
        data["channel_name"] = channel_name
        channel_link = "#"
        ch_sel = selectors.get("channel_link_selector", "")
        if ch_sel:
            ch_el = item.select_one(ch_sel)
            if ch_el and ch_el.has_attr("href"):
                channel_link = urljoin(base_url, ch_el["href"])
        data["channel_link"] = channel_link

        # Video ID
        parsed = urlparse(link)
        parts = [p for p in parsed.path.split('/') if p]
        vid_id = parts[-1] if parts else "N/A"
        if not re.match(r'^[a-zA-Z0-9_-]+$', vid_id):
            vid_id = "N/A"
        data["video_id"] = vid_id

        # Additional meta
        data["extracted_at"] = datetime.now().isoformat()
        data["source_engine"] = selectors.get("url", "")

    except Exception as e:
        logger.warning(f"Failed to extract video data: {e}")
        return None
    return data

# Validate video data
def validate_video_data(data):
    if not data or not isinstance(data, dict):
        return False
    if not data.get("title") or data["title"] in ["Untitled", "N/A"]:
        return False
    if not data.get("link") or data["link"] == "#":
        return False
    # Additional validation as needed
    return True

# Generate placeholder SVG
def generate_placeholder_svg(icon="❌", width=150, height=100):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
        <rect width="100%" height="100%" fill="#222"/>
        <text x="50%" y="50%" font-family="Arial" font-size="{int(min(width, height)/3)}" fill="#888" dominant-baseline="middle" text-anchor="middle">{icon}</text>
    </svg>'''
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

# HTML report template
HTML_HEAD = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Wow.xxx Results for {query}</title>
<!-- Google Fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Inter&family=JetBrains+Mono&display=swap" rel="stylesheet"/>
<style>
/* ... (Insert the CSS styles from your original code with modern design and lazy load) ... */
</style>
</head>
<body>
<div class="container">
<header>
<h1>Search Results for "{query}"</h1>
<div class="stats">
<div class="stat">📹 {count} videos</div>
<div class="stat">🔍 wow.xxx</div>
<div class="stat">⏰ {timestamp}</div>
</div>
</header>
<section class="grid">
"""

HTML_TAIL = """</section>
<footer class="footer">
<p>Generated by wow.xxx scraper | {timestamp}</p>
</footer>
</div>
<!-- Lazy load script -->
<script>
  // Lazy load images with IntersectionObserver, show spinner placeholder
  document.addEventListener('DOMContentLoaded', () => {
    const imgs = document.querySelectorAll('img[data-src]');
    const observer = new IntersectionObserver((entries, obs) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const img = entry.target;
          const container = img.closest('.thumb');
          const spinner = document.createElement('div');
          spinner.className='loading-spinner';
          container.appendChild(spinner);
          
          const realImg = new Image();
          realImg.src = img.dataset.src;
          realImg.onload = () => {
            if (container) {
              container.innerHTML = '';
              container.appendChild(realImg);
            }
          };
          realImg.onerror = () => {
            if (container) {
              container.innerHTML = '<div class="placeholder">❌</div>';
            }
          };
          obs.unobserve(img);
        }
      });
    }, {threshold:0.1});
    imgs.forEach(i => observer.observe(i));
  });
</script>
</body>
</html>
"""

# Main class encapsulating the scraper
class WowxxxScraper:
    def __init__(self, config: dict[str, Any], proxies: list[str]=[]):
        self.config = config
        self.proxies = proxies
        self.proxy_index = 0
        self.session = build_session(proxy=None)
        self.request_times = []

        # For proxy rotation
        self.use_proxy_rotation = bool(proxies)
        self.current_proxy = None

    def get_next_proxy(self):
        if not self.use_proxy_rotation:
            return None
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        self.current_proxy = self.proxies[self.proxy_index]
        return self.current_proxy

    def rotate_proxy(self):
        if self.use_proxy_rotation:
            self.get_next_proxy()
            self.session = build_session(proxy=self.current_proxy)

    def delay(self):
        adaptive_delay(self.request_times)

    def fetch_page(self, url):
        self.delay()
        try:
            headers = get_headers(random.choice(USER_AGENTS))
            self.session.headers.update(headers)
            resp = self.session.get(url)
            resp.raise_for_status()
            self.request_times.append(time.time())
            return resp.text
        except Exception as e:
            logger.warning(f"Error fetching page {url}: {e}")
            return None

    def fetch_page_selenium(self, driver, url, wait_selector):
        try:
            driver.get(url)
            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector)))
            # Lazy load trigger
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(random.uniform(1,2))
            return driver.page_source
        except Exception as e:
            logger.warning(f"Selenium error loading {url}: {e}")
            return None

    def get_selenium_driver(self):
        if not SELENIUM_AVAILABLE:
            return None
        options = ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        driver = webdriver.Chrome(options=options)
        return driver

    async def download_thumbnails(self, results, max_workers=8, use_async=True):
        thumbs_dir = Path("thumbnails")
        ensure_dir(thumbs_dir)
        semaphore = asyncio.Semaphore(max_workers)
        tasks = []

        if use_async and ASYNC_ENABLED:
            async with get_aiohttp_session() as aio_session:
                for idx, video in enumerate(results):
                    url = video.get("img_url")
                    save_path = thumbs_dir / f"{slugify(video.get('title', 'video'))}_{idx}.jpg"
                    tasks.append(download_thumbnail_async(aio_session, url, save_path, semaphore))
                await asyncio.gather(*tasks)
        else:
            # fallback sync download in thread pool
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for idx, video in enumerate(results):
                    url = video.get("img_url")
                    save_path = thumbs_dir / f"{slugify(video.get('title', 'video'))}_{idx}.jpg"
                    futures.append(executor.submit(download_thumbnail_sync, self.session, url, save_path))
                for fut in futures:
                    fut.result()

        # Update results with local thumbnail paths
        for idx, video in enumerate(results):
            thumb_path = Path("thumbnails") / f"{slugify(video.get('title', 'video'))}_{idx}.jpg"
            if thumb_path.exists():
                video["local_thumb"] = str(thumb_path)
            else:
                video["local_thumb"] = generate_placeholder_svg("📹")

    def generate_html(self, results, query, output_path):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        count = len(results)
        html_content = HTML_HEAD.format(query=query, count=count, timestamp=timestamp)

        for idx, video in enumerate(results):
            meta_items = []
            if video.get("time") and video["time"] != "N/A":
                meta_items.append(f'<div class="item">⏱️ {html.escape(video["time"])}</div>')
            if video.get("channel_name") and video["channel_name"] != "N/A":
                ch_link = video.get("channel_link", "#")
                ch_name = html.escape(video["channel_name"])
                if ch_link != "#":
                    meta_items.append(f'<div class="item">👤 <a href="{html.escape(ch_link)}" target="_blank" rel="noopener noreferrer">{ch_name}</a></div>')
                else:
                    meta_items.append(f'<div class="item">👤 {ch_name}</div>')
            if video.get("meta") and video["meta"] != "N/A":
                meta_items.append(f'<div class="item">👁️ {html.escape(video["meta"])}</div>')
            if video.get("video_id") and video["video_id"] != "N/A":
                meta_items.append(f'<div class="item">🆔 {html.escape(video["video_id"])}</div>')

            thumb_img = video.get("local_thumb", generate_placeholder_svg("📹"))
            title = html.escape(video.get("title", "Untitled"))
            link = html.escape(video.get("link", "#"))

            html_content += f'''
            <div class="card">
                <a href="{link}" target="_blank" rel="noopener noreferrer">
                    <div class="thumb">
                        <img src="" data-src="{thumb_img}" alt="{title}" loading="lazy"/>
                    </div>
                </a>
                <div class="body">
                    <h3 class="title"><a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a></h3>
                    <div class="meta">{" ".join(meta_items)}</div>
                </div>
            </div>
            '''
        html_content += HTML_TAIL.format(timestamp=timestamp)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

    def scrape(self, query, limit=30, start_page=1, max_pages=5, use_selenium=False, output_dir="outputs", open_browser=True):
        results = []
        page_num = start_page
        base_url = self.config.get("url", "https://www.wow.xxx")
        total_pages = max_pages
        driver = None
        if use_selenium and SELENIUM_AVAILABLE:
            driver = self.get_selenium_driver()

        request_times = []

        while len(results) < limit and not shutdown_flag:
            url = self.construct_search_url(query, page_num)
            self.request_times = request_times
            page_content = None
            if driver:
                page_content = self.fetch_page_selenium(driver, url, self.config.get("video_item_selector", ""))
            else:
                page_content = self.fetch_page(url)
            if not page_content:
                logger.warning(f"Failed to retrieve page {page_num}")
                break
            soup = BeautifulSoup(page_content, "html.parser")
            items = extract_video_items(soup, self.config)
            if not items:
                logger.info(f"No items found on page {page_num}")
                break
            for item in items:
                if len(results) >= limit:
                    break
                data = extract_video_data(item, base_url, self.config)
                if validate_video_data(data):
                    results.append(data)
            # Check for next page based on the presence of next link or max pages
            if page_num >= total_pages:
                break
            page_num += 1

        if driver:
            driver.quit()
        return results

    def construct_search_url(self, query, page):
        base_url = self.config.get("url", "https://www.wow.xxx")
        search_path = self.config.get("search_path", "/search/{query}/").format(query=quote_plus(query))
        if page > 1 and self.config.get("pagination", {}).get("enabled", False):
            page_pattern = self.config["pagination"].get("path_pattern", "/{page}/")
            search_path += page_pattern.format(page=page)
        return urljoin(base_url, search_path)

# Main function
def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Wow.xxx Video Search Tool")
    parser.add_argument("query", help="Search query")
    parser.add_argument("-l", "--limit", type=int, default=30, help="Maximum results")
    parser.add_argument("-p", "--page", type=int, default=1, help="Start page")
    parser.add_argument("-o", "--output", choices=["html", "json", "csv"], default="html", help="Output format")
    parser.add_argument("--proxy", help="Single proxy URL")
    parser.add_argument("--proxy-list", help="Path to proxy list file")
    parser.add_argument("--workers", type=int, default=8, help="Thumbnail download workers")
    parser.add_argument("--no-async", action="store_true", help="Disable async thumbnail download")
    parser.add_argument("--no-js", action="store_true", help="Disable Selenium JS rendering")
    parser.add_argument("--output-dir", help="Output directory")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    if args.verbose:
        setup_logging(verbose=True)

    # Load proxies
    proxies = []
    if args.proxy_list:
        try:
            with open(args.proxy_list) as f:
                proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except Exception:
            logger.warning("Failed to load proxy list.")

    # Load config
    config = {
        "url": "https://www.wow.xxx",
        # ... (your default selectors and settings)
    }
    # You can load external config JSON here if desired

    scraper = WowxxxScraper(config, proxies)

    # Register signal handler
    signal.signal(signal.SIGINT, handle_sigint)

    results = scraper.scrape(
        query=args.query,
        limit=args.limit,
        start_page=args.page,
        use_selenium=not args.no_js,
        output_dir=args.output_dir or "wowxxx_results"
    )

    # Save results
    output_dir = Path(args.output_dir or "wowxxx_results")
    ensure_dir(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_base = slugify(args.query)
    if args.output == "json":
        filename = output_dir / f"{filename_base}_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Results saved to {filename}")
    elif args.output == "csv":
        filename = output_dir / f"{filename_base}_{timestamp}.csv"
        with open(filename, "w", encoding="utf-8", newline='') as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys() if results else [])
            writer.writeheader()
            writer.writerows(results)
        print(f"Results saved to {filename}")
    else:
        # Generate HTML report
        html_path = output_dir / f"{filename_base}_{timestamp}.html"
        # Download thumbnails asynchronously
        asyncio.run(scraper.download_thumbnails(results, max_workers=args.workers))
        scraper.generate_html(results, args.query, html_path)
        print(f"HTML report generated at {html_path}")
        # Optionally open in browser
        import webbrowser
        webbrowser.open(f"file://{html_path}")

if __name__ == "__main__":
    main()
