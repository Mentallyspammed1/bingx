"""
Enhanced Video Scraper 2025+
A robust, modular, and maintainable solution for scraping video sites,
with modern anti-blocking, error handling, and user-first design.

Features:
- Modern Python 3.10+ with type hints and dataclasses
- Async/threading support for better performance
- Advanced anti-detection with rotating proxies and headers
- Configuration file support (JSON/YAML)
- Rich CLI with progress bars and better UX
- Parallel thumbnail downloads
- Enhanced HTML templates with modern CSS
- Comprehensive error handling and logging
- Security hardening and robots.txt compliance
- Cross-platform compatibility

Dependencies:
    pip install requests beautifulsoup4 colorama fake-useragent rich pydantic pathvalidate aiohttp aiohttp-socks
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import random
import re
import sys
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Callable, Iterator, Coroutine
from urllib.parse import urlparse, urljoin

import aiohttp
from bs4 import BeautifulSoup
from colorama import Fore, init as colorama_init, Style
from pydantic import BaseModel, ValidationError, Field, HttpUrl, PositiveInt
from aiohttp_socks import ProxyConnector

# Optional rich import for better CLI
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich import print as rprint
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

# Optional fake-useragent for dynamic user agents
try:
    from fake_useragent import UserAgent
    FAKE_UA_AVAILABLE = True
    ua = UserAgent()
except ImportError:
    FAKE_UA_AVAILABLE = False
    ua = None

colorama_init(autoreset=True)

# Enhanced Color Scheme with Rich support
class Colors:
    CYAN = Fore.CYAN
    MAGENTA = Fore.MAGENTA
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    RED = Fore.RED
    BLUE = Fore.BLUE
    WHITE = Fore.WHITE
    BRIGHT = Style.BRIGHT
    RESET_ALL = Style.RESET_ALL

# Enhanced Logging Configuration
LOG_FORMAT = (
    f"{Colors.CYAN}%(asctime)s{Colors.RESET_ALL} - "
    f"{Colors.MAGENTA}%(levelname)s{Colors.RESET_ALL} - "
    f"{Colors.GREEN}%(name)s{Colors.RESET_ALL} - "
    f"%(message)s"
)

def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """Setup enhanced logging with optional file output"""
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))
    
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        handlers=handlers,
        force=True
    )
    
    # Suppress noisy external libraries
    for lib in ["urllib3", "chardet", "requests", "fake_useragent", "aiohttp", "asyncio"]:
        logging.getLogger(lib).setLevel(logging.WARNING)
    
    return logging.getLogger("enhanced_scraper")

logger = setup_logging()

# Enhanced Configuration with Pydantic
class ScrapingConfig(BaseModel):
    """Configuration for scraping operations"""
    min_delay: float = 1.0
    max_delay: float = 5.0
    request_timeout: PositiveInt = 15
    max_retries: PositiveInt = 3
    exponential_backoff: bool = True
    max_concurrent_downloads: PositiveInt = 5
    respect_robots_txt: bool = True
    use_proxy: bool = False
    proxy_list: List[str] = Field(default_factory=list)
    custom_headers: Dict[str, str] = Field(default_factory=dict)
    
class EngineConfig(BaseModel):
    """Configuration for a scraping engine"""
    name: str
    url: HttpUrl
    search_path: str
    video_item_selector: str
    title_selector: str
    img_selector: str
    link_selector: str
    page_param: str = "page"
    query_param: str = "q"
    quality_selectors: Dict[str, str] = Field(default_factory=dict)
    rate_limit: float = 1.0
    max_pages: PositiveInt = 50
    custom_params: Dict[str, Any] = Field(default_factory=dict)

@dataclass
class VideoItem:
    """Enhanced video item with comprehensive metadata"""
    title: str
    img_url: str
    link: str
    quality: str = "N/A"
    duration: str = "N/A"
    views: str = "N/A"
    upload_date: str = "N/A"
    channel_name: str = "N/A"
    channel_link: str = "#"
    thumbnail_path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

# Global Configuration
DEFAULT_CONFIG = ScrapingConfig()
THUMBNAILS_DIR = "downloaded_thumbnails"
CONFIG_FILE = "scraper_config.json"
OUTPUT_DIR = Path("scraper_output")

# Modern User-Agent Pool for 2025
FALLBACK_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
]

# Enhanced Engine Configurations
ENGINE_CONFIGS = {
    "xhamster": EngineConfig(
        name="xhamster",
        url="https://xhamster.com",
        search_path="/search",
        video_item_selector="div.video-box",
        title_selector="a.video-box-title",
        img_selector=".video-thumb-preview img",
        link_selector="a.video-box-title",
        quality_selectors={
            "4K": "span.thumb-image-container__duration--4k",
            "HD": "span.thumb-image-container__duration--hd"
        },
        rate_limit=2.0,
        max_pages=50
    ),
    "example": EngineConfig(
        name="example",
        url="https://example.com",
        search_path="/search",
        video_item_selector="div.video-item",
        title_selector="h3",
        img_selector="img",
        link_selector="a",
        rate_limit=1.0,
        max_pages=10
    )
}

# Enhanced Custom Exceptions
class ScrapingError(Exception):
    """Base exception for scraping errors"""
    def __init__(self, message: str, engine: str = "", url: str = ""):
        super().__init__(message)
        self.message = message # Store message for __str__
        self.engine = engine
        self.url = url
        self.timestamp = datetime.now()

    



class RateLimitError(ScrapingError):
    """Exception for rate limiting issues"""
    pass

class BlockedError(ScrapingError):
    """Exception for when scraper is blocked"""
    pass

class ParseError(ScrapingError):
    """Exception for parsing issues"""
    pass

class ConfigurationError(ScrapingError):
    """Exception for configuration issues"""
    pass

# Enhanced Utility Functions
def get_user_agent() -> str:
    """Get a random user agent with fallback"""
    if FAKE_UA_AVAILABLE:
        try:
            return ua.random
        except Exception:
            pass
    return random.choice(FALLBACK_USER_AGENTS)

def get_dynamic_headers() -> Dict[str, str]:
    """Generate a dynamic set of browser-like headers"""
    return {
        'User-Agent': get_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
        'DNT': '1'
    }

def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """Enhanced filename sanitization with Unicode support"""
    if not filename:
        return "unknown_title"
    
    # Remove HTML entities and tags
    filename = re.sub(r'<[^>]+>', '', filename)
    filename = re.sub(r'&[#\w]+;', '', filename)
    
    # Replace problematic characters while preserving Unicode
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'[\r\n\t]+', ' ', filename)
    filename = re.sub(r'\s+', '_', filename).strip('_')
    
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    
    # Limit length for filesystem compatibility
    if len(filename) > max_length:
        filename = filename[:max_length-3] + "..."
    
    return filename if filename else "unnamed_video"

def ensure_directory_exists(directory: Union[str, Path], clean: bool = False) -> Path:
    """Enhanced directory management with pathlib"""
    path = Path(directory)
    
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            logger.info(f"{Colors.GREEN}Created directory: {path}{Colors.RESET_ALL}")
        
        if clean and path.exists():
            cleaned_count = 0
            for file_path in path.glob("*"):
                if file_path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                    except OSError as e:
                        logger.warning(f"Could not remove {file_path.name}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"{Colors.GREEN}Cleaned {cleaned_count} old thumbnails{Colors.RESET_ALL}")
        
        return path
    
    except OSError as e:
        logger.error(f"{Colors.RED}Directory error for {path}: {e}{Colors.RESET_ALL}")
        raise

def load_config(config_path: Union[str, Path] = CONFIG_FILE) -> Dict[str, Any]:
    """Load configuration from JSON file"""
    path = Path(config_path)
    if not path.exists():
        return {}
    
    try:
        with path.open('r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Could not load config from {path}: {e}")
        return {}

def save_config(config: Dict[str, Any], config_path: Union[str, Path] = CONFIG_FILE) -> None:
    """Save configuration to JSON file"""
    path = Path(config_path)
    try:
        with path.open('w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Configuration saved to {path}")
    except OSError as e:
        logger.warning(f"Could not save config to {path}: {e}")

# Async Proxy Manager
class ProxyManager:
    """Manages a list of proxies, performing health checks and rotation"""
    def __init__(self, proxy_list: List[str]):
        self.proxies = proxy_list
        self.working_proxies = []
        self.current_proxy_index = 0
        self.lock = asyncio.Lock()
    
    async def _check_proxy(self, proxy: str) -> Optional[str]:
        """Asynchronously check if a proxy is working"""
        try:
            connector = ProxyConnector.from_url(proxy)
            async with aiohttp.ClientSession(connector=connector, raise_for_status=True, timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get('https://httpbin.org/ip'):
                    logger.debug(f"Proxy is working: {proxy}")
                    return proxy
        except Exception as e:
            logger.debug(f"Proxy failed check: {proxy} - {e}")
            return None
            
    async def check_all_proxies(self) -> None:
        """Asynchronously check all proxies and populate working_proxies list"""
        if not self.proxies:
            self.working_proxies = []
            return
            
        rprint("[bold blue]Checking proxy list for health...[/]")
        tasks = [self._check_proxy(proxy) for proxy in self.proxies]
        checked_proxies = await asyncio.gather(*tasks)
        self.working_proxies = [p for p in checked_proxies if p]
        
        if self.working_proxies:
            rprint(f"[bold green]Found {len(self.working_proxies)} working proxies.[/]")
        else:
            rprint("[bold red]No working proxies found. Using direct connection.[/]")
    
    async def get_connector(self) -> Optional[ProxyConnector]:
        """Get a rotating proxy connector"""
        async with self.lock:
            if not self.working_proxies:
                return None
            
            proxy_url = self.working_proxies[self.current_proxy_index % len(self.working_proxies)]
            self.current_proxy_index += 1
            logger.debug(f"Using proxy: {proxy_url}")
            return ProxyConnector.from_url(proxy_url)

# Modern Async Scraper Class
class AsyncScraper:
    """Async scraper with modern anti-detection and performance optimizations"""
    
    def __init__(self, engine_config: EngineConfig, scraping_config: ScrapingConfig = None):
        self.engine_config = engine_config
        self.config = scraping_config or DEFAULT_CONFIG
        self.last_request_time = 0.0
        self.request_count = 0
        self.robots_cache: Dict[str, Any] = {}
        self.proxy_manager = ProxyManager(self.config.proxy_list)
        self.semaphore = asyncio.Semaphore(10) # Limit concurrent requests to a single domain

    async def initialize(self) -> None:
        """Initialize the proxy manager"""
        if self.config.use_proxy:
            await self.proxy_manager.check_all_proxies()

    @asynccontextmanager
    async def get_session(self):
        """Context manager for aiohttp session with proxy and headers"""
        connector = None
        if self.config.use_proxy and self.proxy_manager.working_proxies:
            connector = await self.proxy_manager.get_connector()

        headers = get_dynamic_headers()
        headers.update(self.config.custom_headers)
        
        timeout = aiohttp.ClientTimeout(total=self.config.request_timeout)

        async with aiohttp.ClientSession(connector=connector, headers=headers, timeout=timeout) as session:
            yield session

    async def _intelligent_wait(self) -> None:
        """Async intelligent rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        base_delay = self.engine_config.rate_limit
        
        human_factor = random.uniform(0.7, 1.3)
        jitter = random.uniform(0, 0.5)
        wait_time = (base_delay * human_factor) + jitter
        
        if time_since_last < wait_time:
            actual_wait = wait_time - time_since_last
            logger.debug(f"Rate limiting: waiting {actual_wait:.2f}s...")
            await asyncio.sleep(actual_wait)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    async def make_request_async(self, url: str, params: Dict[str, Any] = None, 
                                 retries: int = None) -> Optional[str]:
        """Async request method with comprehensive error handling"""
        retries = retries or self.config.max_retries
        params = params or {}
        
        async with self.semaphore:
            for attempt in range(retries + 1):
                try:
                    if not self._check_robots_txt(url):
                        raise BlockedError(f"URL blocked by robots.txt: {url}", self.engine_config.name, url)
                    
                    await self._intelligent_wait()
                    
                    async with self.get_session() as session:
                        async with session.get(url, params=params, ssl=False) as response:
                            if response.status == 200:
                                logger.debug(f"Successfully fetched: {url}")
                                return await response.text()
                            elif response.status == 403:
                                raise BlockedError(f"Access forbidden (403): {url}", self.engine_config.name, url)
                            elif response.status == 404:
                                logger.warning(f"Resource not found (404): {url}")
                                return None
                            elif response.status == 429:
                                raise RateLimitError(f"Rate limited (429): {url}", self.engine_config.name, url)
                            elif 500 <= response.status < 600:
                                raise ScrapingError(f"Server error ({response.status}): {url}", 
                                                    self.engine_config.name, url)
                            else:
                                response.raise_for_status()
                                return await response.text()
                        
                except (RateLimitError, BlockedError) as e:
                    if attempt < retries:
                        wait_time = (2 ** attempt) * 5 + random.uniform(1, 5)
                        logger.warning(f"Temporary block (attempt {attempt + 1}/{retries + 1}): {e}")
                        logger.info(f"Extended wait: {wait_time:.2f}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Permanently blocked after {retries + 1} attempts: {e}")
                        return None
                
                except aiohttp.ClientError as e:
                    if attempt < retries:
                        wait_time = (2 ** attempt) + random.uniform(0, 1) if self.config.exponential_backoff else self.config.min_delay
                        logger.warning(f"Request failed (attempt {attempt + 1}/{retries + 1}): {str(e)}")
                        logger.info(f"Retrying in {wait_time:.2f}s...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"Request failed after {retries + 1} attempts: {str(e)}")
                        return None
            
            return None

    def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt with caching (sync)"""
        # This part remains synchronous as RobotFileParser is not async-friendly
        if not self.config.respect_robots_txt:
            return True
        
        parsed_url = urlparse(url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        if base_url not in self.robots_cache:
            try:
                robots_url = f"{base_url}/robots.txt"
                rp = RobotFileParser()
                rp.set_url(robots_url)
                rp.read()
                self.robots_cache[base_url] = rp
                logger.debug(f"Loaded robots.txt for {base_url}")
            except Exception as e:
                logger.debug(f"Could not fetch robots.txt for {base_url}: {e}")
                self.robots_cache[base_url] = None
        
        rp = self.robots_cache[base_url]
        if rp:
            allowed = rp.can_fetch('*', url)
            if not allowed:
                logger.warning(f"URL blocked by robots.txt: {url}")
            return allowed
        
        return True

    def _parse_videos(self, html_content: str, page: int, limit: int) -> List[VideoItem]:
        """Parse HTML content for video items"""
        config = self.engine_config
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            video_items = soup.select(config.video_item_selector)
            
            if not video_items:
                logger.warning(f"No video items found on page {page}. Selector: {config.video_item_selector}")
                return []
            
            results = []
            
            for idx, item in enumerate(video_items[:limit]):
                try:
                    title = "Untitled Video"
                    title_element = item.select_one(config.title_selector)
                    if title_element:
                        title = (title_element.get_text(strip=True) or 
                                title_element.get('title') or 
                                title_element.get('alt') or 
                                f"Video {idx + 1}")
                    
                    img_url = ""
                    img_element = item.select_one(config.img_selector)
                    if img_element:
                        img_url = (img_element.get("data-src") or 
                                  img_element.get("src") or 
                                  img_element.get("data-thumb") or "")
                        if img_url and not img_url.startswith('http'):
                            img_url = urljoin(str(config.url), img_url)
                    
                    link = "#"
                    link_element = item.select_one(config.link_selector)
                    if link_element:
                        link = link_element.get("href", "#")
                        if link and link != "#" and not link.startswith('http'):
                            link = urljoin(str(config.url), link)
                    
                    quality = "N/A"
                    for qual, selector in config.quality_selectors.items():
                        if item.select_one(selector):
                            quality = qual
                            break
                    
                    video = VideoItem(
                        title=title.strip(),
                        img_url=img_url,
                        link=link,
                        quality=quality,
                        metadata={
                            'engine': config.name,
                            'page': page,
                            'index': idx,
                            'extracted_at': datetime.now().isoformat()
                        }
                    )
                    
                    results.append(video)
                    logger.debug(f"Parsed video {idx + 1} from page {page}: {title[:50]}...")
                    
                except Exception as e:
                    logger.warning(f"Error parsing video {idx + 1} on page {page}: {str(e)}")
                    continue
            
            return results
        
        except Exception as e:
            raise ParseError(f"Failed to parse search results on page {page}: {str(e)}", config.name)

    async def search_videos_async(self, query: str, limit: int, page: int = 1) -> List[VideoItem]:
        """Asynchronously search for videos on a single page"""
        config = self.engine_config
        
        search_url = urljoin(str(config.url), config.search_path)
        params = {config.query_param: query}
        
        if page > 1:
            params[config.page_param] = page
        
        params.update(config.custom_params)
        
        logger.info(f"Searching '{query}' on {config.name} (page {page})...")
        html_content = await self.make_request_async(search_url, params)
        
        if not html_content:
            logger.error(f"Failed to fetch search results for: {query} (page {page})")
            return []
        
        try:
            results = self._parse_videos(html_content, page, limit)
            logger.info(f"Successfully parsed {len(results)} videos from page {page}")
            return results
        except ParseError as e:
            logger.error(str(e))
            return []

def download_thumbnail(scraper: AsyncScraper, video: VideoItem, 
                      output_dir: Path, progress_callback: Callable = None) -> bool:
    """Enhanced thumbnail download with progress tracking"""
    if not video.img_url or not video.img_url.startswith('http'):
        return False
    
    try:
        # Determine file extension
        parsed_url = urlparse(video.img_url)
        ext = Path(parsed_url.path).suffix.lower()
        if not ext or ext not in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
            ext = '.jpg'
        
        # Create safe filename
        safe_title = sanitize_filename(video.title, 80)
        filename = f"{safe_title}_{hash(video.link) % 10000:04d}{ext}"
        filepath = output_dir / filename
        
        # Download with validation
        response = requests.get(video.img_url, headers=get_dynamic_headers(), timeout=scraper.config.request_timeout)
        response.raise_for_status()

        # Validate content
        content_type = response.headers.get('content-type', '').lower()
        if not any(img_type in content_type for img_type in ['image/', 'application/octet-stream']):
            logger.debug(f"Unexpected content type for {video.img_url}: {content_type}")
            return False
        
        content_length = response.headers.get('content-length')
        if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB limit
            logger.warning(f"File too large ({content_length} bytes): {video.img_url}")
            return False
        
        # Atomic write
        temp_filepath = filepath.with_suffix(filepath.suffix + '.tmp')
        with temp_filepath.open('wb') as f:
            f.write(response.content)
        
        temp_filepath.rename(filepath)
        video.thumbnail_path = str(filepath.relative_to(output_dir.parent))
        
        if progress_callback:
            progress_callback()
        
        logger.debug(f"Downloaded thumbnail: {filename}")
        return True
        
    except Exception as e:
        logger.warning(f"Thumbnail download failed for '{video.title}': {e}")
        # Clean up temp file
        temp_filepath = filepath.with_suffix(filepath.suffix + '.tmp')
        if temp_filepath.exists():
            try:
                temp_filepath.unlink()
            except OSError:
                pass
        return False

def download_thumbnails_parallel(scraper: AsyncScraper, videos: List[VideoItem], 
                                output_dir: Path) -> tuple[int, int]:
    """Download thumbnails in parallel with progress tracking"""
    thumbnails_dir = ensure_directory_exists(output_dir / THUMBNAILS_DIR)
    
    successful = 0
    failed = 0
    
    if RICH_AVAILABLE and console:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Downloading thumbnails...", total=len(videos))
            
            def update_progress():
                nonlocal successful
                successful += 1
                progress.advance(task)
            
            with ThreadPoolExecutor(max_workers=scraper.config.max_concurrent_downloads) as executor:
                future_to_video = {
                    executor.submit(download_thumbnail, scraper, video, thumbnails_dir, update_progress): video
                    for video in videos if video.img_url
                }
                
                for future in as_completed(future_to_video):
                    if not future.result():
                        failed += 1
    else:
        # Fallback without progress bar
        logger.info(f"Downloading {len(videos)} thumbnails...")
        with ThreadPoolExecutor(max_workers=scraper.config.max_concurrent_downloads) as executor:
            futures = [
                executor.submit(download_thumbnail, scraper, video, thumbnails_dir)
                for video in videos if video.img_url
            ]
            
            for future in as_completed(futures):
                if future.result():
                    successful += 1
                else:
                    failed += 1
    
    logger.info(f"Thumbnails: {successful} downloaded, {failed} failed")
    return successful, failed

async def scrape_all_pages_async(scraper: AsyncScraper, query: str, limit: int) -> List[VideoItem]:
    """Scrape all pages asynchronously and combine results"""
    all_results = []
    
    num_pages_to_scrape = min(scraper.engine_config.max_pages, (limit + 19) // 20)
    
    tasks = [scraper.search_videos_async(query, limit=limit, page=i+1) for i in range(num_pages_to_scrape)]
    
    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Scraping search pages...", total=num_pages_to_scrape)
            
            page_tasks = [
                (page_num, scraper.search_videos_async(query, limit=limit, page=page_num))
                for page_num in range(1, num_pages_to_scrape + 1)
            ]
            
            for page_num, task_coro in page_tasks:
                results = await task_coro
                all_results.extend(results)
                progress.update(task, advance=1, description=f"Scraping page {page_num}/{num_pages_to_scrape}...")
                
                if len(all_results) >= limit:
                    break
    else:
        results = await asyncio.gather(*tasks)
        for page_results in results:
            all_results.extend(page_results)
            if len(all_results) >= limit:
                break
    
    return all_results[:limit]


def generate_modern_html(videos: List[VideoItem], query: str, engine_config: EngineConfig, 
                        output_dir: Path, theme: str = "dark") -> Optional[Path]:
    """Generate modern HTML with enhanced styling and responsiveness"""
    if not videos:
        logger.warning(f"{Colors.YELLOW}No videos found. No HTML generated.{Colors.RESET_ALL}")
        return None
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        query_safe = sanitize_filename(query, 50)
        filename = f"{engine_config.name}_search_{query_safe}_{timestamp}.html"
        output_file = output_dir / filename
        
        # Theme configuration
        themes = {
            "dark": {
                "bg_primary": "#0a0a0a",
                "bg_secondary": "#1a1a2e",
                "bg_card": "#16213e",
                "text_primary": "#ffffff",
                "text_secondary": "#b0b0b0",
                "accent": "#00d4aa",
                "accent_secondary": "#ff6b6b",
                "border": "rgba(255, 255, 255, 0.1)"
            },
            "light": {
                "bg_primary": "#ffffff",
                "bg_secondary": "#f8f9fa",
                "bg_card": "#ffffff",
                "text_primary": "#212529",
                "text_secondary": "#6c757d",
                "accent": "#007bff",
                "accent_secondary": "#dc3545",
                "border": "rgba(0, 0, 0, 0.1)"
            }
        }
        
        colors = themes.get(theme, themes["dark"])
        
        # Enhanced HTML template
        html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Search results for '{query}' from {engine_config.name}">
    <title>🎬 {query} | {engine_config.name.title()} Search Results</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@300;400;500&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {{
            --bg-primary: {colors["bg_primary"]};
            --bg-secondary: {colors["bg_secondary"]};
            --bg-card: {colors["bg_card"]};
            --text-primary: {colors["text_primary"]};
            --text-secondary: {colors["text_secondary"]};
            --accent: {colors["accent"]};
            --accent-secondary: {colors["accent_secondary"]};
            --border: {colors["border"]};
            --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
        }}
        
        body {{
            background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
            color: var(--text-primary);
        }}

        .light-theme {{
            --bg-primary: #ffffff;
            --bg-secondary: #f8f9fa;
            --bg-card: #ffffff;
            --text-primary: #212529;
            --text-secondary: #6c757d;
            --accent: #007bff;
            --accent-secondary: #dc3545;
            --border: rgba(0, 0, 0, 0.1);
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem;
            background: var(--bg-card);
            border-radius: 1rem;
            box-shadow: var(--shadow-lg);
            border: 1px solid var(--border);
            backdrop-filter: blur(10px);
        }}
        
        .header h1 {{
            font-size: clamp(2rem, 5vw, 3.5rem);
            font-weight: 700;
            background: linear-gradient(135deg, var(--accent), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 1rem;
        }}
        
        .search-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-top: 2rem;
        }}
        
        .stat-card {{
            background: rgba(255, 255, 255, 0.05);
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid var(--border);
            transition: all 0.3s ease;
        }}
        
        .stat-card:hover {{
            transform: translateY(-2px);
            box-shadow: var(--shadow);
        }}
        
        .stat-label {{
            font-size: 0.875rem;
            color: var(--text-secondary);
            font-weight: 500;
        }}
        
        .stat-value {{
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--accent);
            font-family: 'Fira Code', monospace;
        }}
        
        .video-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 2rem;
            margin-top: 3rem;
        }}
        
        .video-card {{
            background: var(--bg-card);
            border-radius: 1rem;
            overflow: hidden;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
            position: relative;
            height: fit-content;
        }}
        
        .video-card:hover {{
            transform: translateY(-8px) scale(1.02);
            box-shadow: var(--shadow-lg);
        }}
        
        .image-container {{
            position: relative;
            overflow: hidden;
            aspect-ratio: 16/9;
        }}
        
        .video-card img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            transition: transform 0.4s ease;
        }}
        
        .video-card:hover img {{
            transform: scale(1.1);
        }}
        
        .quality-badge {{
            position: absolute;
            top: 0.75rem;
            right: 0.75rem;
            background: linear-gradient(135deg, var(--accent-secondary), #e53e3e);
            color: white;
            padding: 0.25rem 0.5rem;
            border-radius: 0.375rem;
            font-size: 0.75rem;
            font-weight: 600;
            z-index: 10;
            box-shadow: var(--shadow);
        }}
        
        .play-overlay {{
            position: absolute;
            inset: 0;
            background: rgba(0, 0, 0, 0.4);
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease;
        }}
        
        .video-card:hover .play-overlay {{
            opacity: 1;
        }}
        
        .play-button {{
            width: 4rem;
            height: 4rem;
            background: var(--accent);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 1.5rem;
            transform: scale(0.8);
            transition: transform 0.3s ease;
        }}
        
        .video-card:hover .play-button {{
            transform: scale(1);
        }}
        
        .video-info {{
            padding: 1.5rem;
        }}
        
        .video-title {{
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--text-primary);
            text-decoration: none;
            display: block;
            margin-bottom: 1rem;
            line-height: 1.4;
            transition: color 0.3s ease;
        }}
        
        .video-title:hover {{
            color: var(--accent);
        }}
        
        .video-meta {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 1rem;
        }}
        
        .meta-tag {{
            background: rgba(255, 255, 255, 0.1);
            padding: 0.25rem 0.5rem;
            border-radius: 0.375rem;
            font-size: 0.75rem;
            font-weight: 500;
            border: 1px solid var(--border);
            transition: all 0.3s ease;
        }}
        
        .meta-tag:hover {{
            background: rgba(255, 255, 255, 0.2);
            transform: translateY(-1px);
        }}
        
        .footer {{
            margin-top: 4rem;
            padding: 2rem;
            text-align: center;
            background: var(--bg-card);
            border-radius: 1rem;
            border: 1px solid var(--border);
            box-shadow: var(--shadow);
        }}
        
        .footer-stats {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-bottom: 1rem;
            flex-wrap: wrap;
        }}
        
        .footer-stat {{
            text-align: center;
        }}
        
        .footer-stat-number {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--accent);
            font-family: 'Fira Code', monospace;
        }}
        
        .footer-stat-label {{
            font-size: 0.875rem;
            color: var(--text-secondary);
        }}
        
        .theme-toggle {{
            position: fixed;
            top: 2rem;
            right: 2rem;
            width: 3rem;
            height: 3rem;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.3s ease;
            z-index: 1000;
            box-shadow: var(--shadow);
        }}
        
        .theme-toggle:hover {{
            transform: scale(1.1);
            box-shadow: var(--shadow-lg);
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            
            .video-grid {{
                grid-template-columns: 1fr;
                gap: 1.5rem;
            }}
            
            .search-stats {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .footer-stats {{
                gap: 1rem;
            }}
        }}
        
        @media (max-width: 480px) {{
            .search-stats {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body class="{'light-theme' if theme == 'light' else ''}">
    <div class="theme-toggle" onclick="toggleTheme()" title="Toggle Theme">
        <i class="fas fa-moon" id="theme-icon"></i>
    </div>
    
    <div class="container">
        <header class="header">
            <h1><i class="fas fa-play-circle"></i> Video Search Results</h1>
            <p style="font-size: 1.125rem; margin-bottom: 1rem; color: var(--text-secondary);">
                Search results for "<strong>{query}</strong>" from <strong>{engine_config.name.title()}</strong>
            </p>
            
            <div class="search-stats">
                <div class="stat-card">
                    <div class="stat-label">Query</div>
                    <div class="stat-value">"{query}"</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Engine</div>
                    <div class="stat-value">{engine_config.name.title()}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Results Found</div>
                    <div class="stat-value">{len(videos)}</div>
                </div>
                <div class="stat-card">
                    <div class="stat-label">Generated</div>
                    <div class="stat-value">{datetime.now().strftime('%H:%M')}</div>
                </div>
            </div>
        </header>
        
        <main class="video-grid">'''
        
        # Generate video cards
        for idx, video in enumerate(videos):
            thumbnail_path = video.thumbnail_path or "https://via.placeholder.com/640x360?text=No+Image+Available"
            
            # Convert relative path for web
            if video.thumbnail_path and not video.thumbnail_path.startswith('http'):
                thumbnail_path = video.thumbnail_path.replace('\\', '/')
            
            html_content += f'''
            <article class="video-card">
                <a href="{video.link}" target="_blank" rel="noopener noreferrer" title="{video.title}">
                <div class="image-container">
                    {f'<div class="quality-badge">{video.quality}</div>' if video.quality != 'N/A' else ''}
                    <img src="{thumbnail_path}" alt="{video.title}" loading="lazy" 
                         onerror="this.src='https://via.placeholder.com/640x360?text=Image+Error&bg=2a2a4a&color=ffffff';">
                    <div class="play-overlay">
                        <div class="play-button">
                            <i class="fas fa-play"></i>
                        </div>
                    </div>
                </div>
                </a>
                <div class="video-info">
                    <a href="{video.link}" class="video-title" target="_blank" rel="noopener noreferrer" 
                       title="{video.title}">
                        {video.title}
                    </a>
                    <div class="video-meta">
                        {f'<span class="meta-tag"><i class="fas fa-medal"></i> {video.quality}</span>' if video.quality != 'N/A' else ''}
                        <span class="meta-tag"><i class="fas fa-hashtag"></i> {idx + 1}</span>
                        <span class="meta-tag"><i class="fas fa-globe"></i> {engine_config.name}</span>
                        {f'<span class="meta-tag"><i class="fas fa-clock"></i> {video.duration}</span>' if video.duration != 'N/A' else ''}
                    </div>
                </div>
            </article>'''
        
        # Calculate statistics
        quality_counts = {}
        for video in videos:
            quality_counts[video.quality] = quality_counts.get(video.quality, 0) + 1
        
        thumbnail_count = sum(1 for video in videos if video.thumbnail_path)
        
        html_content += f'''
        </main>
        
        <footer class="footer">
            <div class="footer-stats">
                <div class="footer-stat">
                    <div class="footer-stat-number">{len(videos)}</div>
                    <div class="footer-stat-label">Videos Found</div>
                </div>
                <div class="footer-stat">
                    <div class="footer-stat-number">{thumbnail_count}</div>
                    <div class="footer-stat-label">Thumbnails</div>
                </div>
                <div class="footer-stat">
                    <div class="footer-stat-number">{len(quality_counts)}</div>
                    <div class="footer-stat-label">Quality Types</div>
                </div>
            </div>
            <p style="color: var(--text-secondary); margin-bottom: 0.5rem;">
                Generated by Enhanced Video Scraper 2025+ | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
            <p style="color: var(--text-secondary); font-size: 0.875rem;">
                Theme: {theme.title()} | Engine: {engine_config.name.title()} | 
                Results: {len(videos)} videos from "{query}"
            </p>
        </footer>
    </div>
    
    <script>
        const darkThemeCSS = `
            :root {{
                --bg-primary: #0a0a0a;
                --bg-secondary: #1a1a2e;
                --bg-card: #16213e;
                --text-primary: #ffffff;
                --text-secondary: #b0b0b0;
                --accent: #00d4aa;
                --accent-secondary: #ff6b6b;
                --border: rgba(255, 255, 255, 0.1);
            }}
        `;

        const lightThemeCSS = `
            :root {{
                --bg-primary: #ffffff;
                --bg-secondary: #f8f9fa;
                --bg-card: #ffffff;
                --text-primary: #212529;
                --text-secondary: #6c757d;
                --accent: #007bff;
                --accent-secondary: #dc3545;
                --border: rgba(0, 0, 0, 0.1);
            }}
        `;

        const styleTag = document.createElement('style');
        document.head.appendChild(styleTag);
        
        function applyTheme(theme) {{
            if (theme === 'light') {{
                styleTag.textContent = lightThemeCSS;
                document.getElementById('theme-icon').className = 'fas fa-sun';
            }} else {{
                styleTag.textContent = darkThemeCSS;
                document.getElementById('theme-icon').className = 'fas fa-moon';
            }}
        }}

        function toggleTheme() {{
            const currentTheme = localStorage.getItem('theme') === 'light' ? 'dark' : 'light';
            localStorage.setItem('theme', currentTheme);
            applyTheme(currentTheme);
        }}
        
        // Load saved theme or default
        const savedTheme = localStorage.getItem('theme') || '{theme}';
        applyTheme(savedTheme);
        
        // Lazy loading enhancement
        if ('IntersectionObserver' in window) {{
            const imageObserver = new IntersectionObserver((entries, observer) => {{
                entries.forEach(entry => {{
                    if (entry.isIntersecting) {{
                        const img = entry.target;
                        img.src = img.dataset.src || img.src;
                        img.classList.remove('lazy');
                        observer.unobserve(img);
                    }}
                }});
            }});
            
            document.querySelectorAll('img[loading="lazy"]').forEach(img => {{
                imageObserver.observe(img);
            }});
        }}
    </script>
</body>
</html>'''
        
        # Write HTML file
        with output_file.open('w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"{Colors.GREEN}Enhanced HTML generated: {output_file}{Colors.RESET_ALL}")
        return output_file
    
    except Exception as e:
        logger.error(f"{Colors.RED}Failed to generate HTML: {e}{Colors.RESET_ALL}")
        return None

# Main CLI Logic
def display_welcome_message():
    """Display a rich welcome message"""
    if RICH_AVAILABLE:
        rprint(Panel(
            "[bold green]Enhanced Video Scraper 2025+[/]\n"
            "A robust, modular, and performant solution for scraping video sites.",
            title="[bold cyan]Welcome[/]",
            title_align="left",
            border_style="blue"
        ))
    else:
        print(f"{Colors.GREEN}{Colors.BRIGHT}Enhanced Video Scraper 2025+{Colors.RESET_ALL}")
        print("A robust, modular, and performant solution for scraping video sites.")

def display_engines():
    """Display available engines"""
    if RICH_AVAILABLE:
        table = Table(title="[bold magenta]Available Scraping Engines[/]", style="white")
        table.add_column("Engine Name", style="cyan")
        table.add_column("URL", style="green")
        table.add_column("Max Pages", style="yellow")
        for name, config in ENGINE_CONFIGS.items():
            table.add_row(name, str(config.url), str(config.max_pages))
        rprint(table)
    else:
        print(f"\n{Colors.MAGENTA}--- Available Scraping Engines ---{Colors.RESET_ALL}")
        for name, config in ENGINE_CONFIGS.items():
            print(f"  {Colors.CYAN}{name}{Colors.RESET_ALL}: {config.url} (Max Pages: {config.max_pages})")
    print("\n")

async def main():
    """Main function to run the CLI"""
    display_welcome_message()
    
    # Load and validate global config
    try:
        loaded_config = load_config()
        scraping_config = ScrapingConfig.parse_obj(loaded_config)
    except ValidationError as e:
        logger.error(f"Configuration file {CONFIG_FILE} is invalid: {e}")
        logger.warning(f"Using default scraping configuration. Please fix {CONFIG_FILE} if you want custom settings.")
        scraping_config = DEFAULT_CONFIG
    
    display_engines()
    
    parser = argparse.ArgumentParser(description="Enhanced Video Scraper CLI")
    parser.add_argument("-q", "--query", type=str, help="Search query for videos")
    parser.add_argument("-e", "--engine", type=str, choices=ENGINE_CONFIGS.keys(), help="Scraping engine to use")
    parser.add_argument("-l", "--limit", type=int, default=20, help="Maximum number of videos to scrape")
    parser.add_argument("-d", "--download-thumbnails", action="store_true", help="Download thumbnails for videos")
    parser.add_argument("-o", "--open-html", action="store_true", help="Open generated HTML file in a web browser")
    parser.add_argument("-c", "--clean", action="store_true", help="Clean old thumbnails before scraping")
    parser.add_argument("-t", "--theme", type=str, default="dark", choices=["dark", "light"], help="HTML theme")
    
    args = parser.parse_args()
    
    if RICH_AVAILABLE:
        if not args.query:
            args.query = Prompt.ask("[bold cyan]Enter a search query[/]")
        if not args.engine:
            args.engine = Prompt.ask("[bold cyan]Select an engine[/]", choices=list(ENGINE_CONFIGS.keys()))
    else:
        if not args.query:
            args.query = input(f"{Colors.CYAN}Enter a search query: {Colors.RESET_ALL}")
        if not args.engine:
            args.engine = input(f"{Colors.CYAN}Select an engine ({', '.join(ENGINE_CONFIGS.keys())}): {Colors.RESET_ALL}")
    
    if not args.query or not args.engine or args.engine not in ENGINE_CONFIGS:
        logger.error("Invalid query or engine. Please provide both.")
        return
    
    engine_config = ENGINE_CONFIGS[args.engine]
    output_dir = ensure_directory_exists(OUTPUT_DIR, clean=args.clean)
    
    # Initialize async scraper
    async_scraper = AsyncScraper(engine_config, scraping_config)
    await async_scraper.initialize()
    
    try:
        logger.info(f"{Colors.GREEN}Starting scraping operation on {engine_config.name.title()}...{Colors.RESET_ALL}")
        videos = await scrape_all_pages_async(async_scraper, args.query, args.limit)
        
        if not videos:
            logger.warning(f"{Colors.YELLOW}No videos found for query '{args.query}' on {engine_config.name}.{Colors.RESET_ALL}")
            return
            
        logger.info(f"{Colors.GREEN}Scraping complete. Found {len(videos)} videos.{Colors.RESET_ALL}")
        
        if args.download_thumbnails:
            download_thumbnails_parallel(async_scraper, videos, output_dir)

        html_file = generate_modern_html(videos, args.query, engine_config, output_dir, theme=args.theme)
        
        if html_file and args.open_html:
            try:
                webbrowser.open_new_tab(f"file://{os.path.abspath(html_file)}")
                logger.info(f"{Colors.GREEN}Opened {html_file.name} in your web browser.{Colors.RESET_ALL}")
            except Exception as e:
                logger.error(f"{Colors.RED}Could not open web browser: {e}{Colors.RESET_ALL}")
    
    except Exception as e:
        logger.error(f"{Colors.RED}A critical error occurred: {str(e)}{Colors.RESET_ALL}")
    
    if RICH_AVAILABLE:
        rprint("\n[bold cyan]Scraping task finished. Goodbye![/]")
    else:
        print(f"\n{Colors.CYAN}Scraping task finished. Goodbye!{Colors.RESET_ALL}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user. Exiting gracefully.")
