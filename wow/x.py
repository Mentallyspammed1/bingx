#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
wowxxx_search_enhanced.py - Advanced Video Search Tool for wow.xxx
Enhanced version with improved architecture, performance, and robustness.

Features:
- Modular architecture with separate concerns
- Advanced rate limiting with exponential backoff
- Intelligent request distribution and load balancing
- Session persistence and recovery
- Result caching and deduplication
- Multi-threaded page scraping with async thumbnail downloads
- Comprehensive error handling and retry strategies
- Detailed logging and monitoring
- Export to multiple formats (HTML, JSON, CSV, Excel)
- Resume capability for interrupted searches

Usage:
  python3 wowxxx_search_enhanced.py "query" [options]

Example:
  python3 wowxxx_search_enhanced.py "teen" -l 100 --parallel 3
  python3 wowxxx_search_enhanced.py "milf" --resume last_search.state
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import concurrent.futures
import csv
import dataclasses
import hashlib
import html
import json
import logging
import os
import pickle
import random
import re
import signal
import sys
import threading
import time
import unicodedata
import uuid
import warnings
import webbrowser
from collections import defaultdict, deque
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timedelta
from enum import Enum, auto
from functools import lru_cache, wraps
from pathlib import Path
from typing import (
    Any, AsyncGenerator, Callable, Deque, Dict, List, Optional, 
    Protocol, Sequence, Set, Tuple, Type, Union
)
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from requests.adapters import HTTPAdapter, Retry

# Optional dependencies
try:
    import aiohttp
    ASYNC_AVAILABLE = True
except ImportError:
    ASYNC_AVAILABLE = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
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
    def tqdm(iterable, **kwargs):
        return iterable

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

# Disable Selenium in Termux
if 'TERMUX_VERSION' in os.environ:
    SELENIUM_AVAILABLE = False

# Initialize colorama
init(autoreset=True)

# ═════════════════════════════════════════════════════════════════════════════
# Configuration and Constants
# ═════════════════════════════════════════════════════════════════════════════

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

# Directory structure
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
THUMBNAILS_DIR = DATA_DIR / "thumbnails"
RESULTS_DIR = DATA_DIR / "results"
STATE_DIR = DATA_DIR / "state"
LOG_DIR = DATA_DIR / "logs"

# Create directories
for directory in [DATA_DIR, CACHE_DIR, THUMBNAILS_DIR, RESULTS_DIR, STATE_DIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Enhanced User Agents with realistic browser versions
REALISTIC_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.6.1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
]

# ═════════════════════════════════════════════════════════════════════════════
# Enhanced Logging System
# ═════════════════════════════════════════════════════════════════════════════

class LogLevel(Enum):
    """Custom log levels for enhanced logging."""
    TRACE = 5
    DEBUG = 10
    INFO = 20
    SUCCESS = 25
    WARNING = 30
    ERROR = 40
    CRITICAL = 50

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and icons."""
    
    FORMATS = {
        LogLevel.TRACE.value: f"{NEON['WHITE']}[TRACE]",
        LogLevel.DEBUG.value: f"{NEON['BLUE']}[DEBUG]",
        LogLevel.INFO.value: f"{NEON['CYAN']}[INFO]",
        LogLevel.SUCCESS.value: f"{NEON['GREEN']}[✓ SUCCESS]",
        LogLevel.WARNING.value: f"{NEON['YELLOW']}[⚠ WARNING]",
        LogLevel.ERROR.value: f"{NEON['RED']}[✗ ERROR]",
        LogLevel.CRITICAL.value: f"{NEON['RED']}{NEON['BRIGHT']}[☠ CRITICAL]",
    }
    
    def format(self, record):
        log_color = self.FORMATS.get(record.levelno, "")
        record.levelname = f"{log_color}{NEON['RESET']}"
        return super().format(record)

def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> logging.Logger:
    """Set up enhanced logging configuration."""
    logger = logging.getLogger("wowxxx_enhanced")
    logger.setLevel(LogLevel.TRACE.value if verbose else LogLevel.INFO.value)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = ColoredFormatter(
        f"%(levelname)s {NEON['MAGENTA']}%(asctime)s{NEON['RESET']} - %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        file_handler = logging.FileHandler(LOG_DIR / log_file, encoding="utf-8")
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    # Add custom log level
    logging.addLevelName(LogLevel.SUCCESS.value, "SUCCESS")
    logger.success = lambda msg, *args, **kwargs: logger.log(LogLevel.SUCCESS.value, msg, *args, **kwargs)
    
    return logger

# Global logger instance
logger = setup_logging()

# ═════════════════════════════════════════════════════════════════════════════
# Data Models and Types
# ═════════════════════════════════════════════════════════════════════════════

@dataclasses.dataclass
class VideoResult:
    """Enhanced video result with validation and metadata."""
    title: str
    link: str
    img_url: Optional[str] = None
    duration: Optional[str] = None
    views: Optional[str] = None
    channel_name: Optional[str] = None
    channel_link: Optional[str] = None
    upload_date: Optional[str] = None
    quality: Optional[str] = None
    tags: List[str] = dataclasses.field(default_factory=list)
    extracted_at: datetime = dataclasses.field(default_factory=datetime.now)
    source_engine: str = "wowxxx"
    page_number: int = 1
    result_hash: Optional[str] = None
    
    def __post_init__(self):
        """Validate and clean data after initialization."""
        self.title = self._clean_text(self.title)
        self.link = self._validate_url(self.link)
        if self.img_url:
            self.img_url = self._validate_url(self.img_url)
        self.result_hash = self._generate_hash()
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return "Untitled"
        text = html.unescape(text.strip())
        text = re.sub(r'\s+', ' ', text)
        return text[:200]  # Limit length
    
    def _validate_url(self, url: str) -> str:
        """Validate and normalize URL."""
        if not url:
            return ""
        parsed = urlparse(url)
        if not parsed.scheme:
            return f"https://{url}"
        return url
    
    def _generate_hash(self) -> str:
        """Generate unique hash for deduplication."""
        content = f"{self.title}:{self.link}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            **dataclasses.asdict(self),
            "extracted_at": self.extracted_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VideoResult':
        """Create instance from dictionary."""
        if isinstance(data.get("extracted_at"), str):
            data["extracted_at"] = datetime.fromisoformat(data["extracted_at"])
        return cls(**data)

@dataclasses.dataclass
class SearchState:
    """State management for search resumption."""
    query: str
    total_results: List[VideoResult] = dataclasses.field(default_factory=list)
    processed_pages: Set[int] = dataclasses.field(default_factory=set)
    failed_pages: Dict[int, str] = dataclasses.field(default_factory=dict)
    start_time: datetime = dataclasses.field(default_factory=datetime.now)
    last_update: datetime = dataclasses.field(default_factory=datetime.now)
    config: Dict[str, Any] = dataclasses.field(default_factory=dict)
    
    def save(self, filepath: Path):
        """Save state to file."""
        self.last_update = datetime.now()
        with open(filepath, 'wb') as f:
            pickle.dump(self, f)
    
    @classmethod
    def load(cls, filepath: Path) -> 'SearchState':
        """Load state from file."""
        with open(filepath, 'rb') as f:
            return pickle.load(f)

# ═════════════════════════════════════════════════════════════════════════════
# Rate Limiting and Request Management
# ═════════════════════════════════════════════════════════════════════════════

class RateLimiter:
    """Advanced rate limiter with adaptive strategies."""
    
    def __init__(self, 
                 requests_per_second: float = 1.0,
                 burst_size: int = 5,
                 adaptive: bool = True):
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.adaptive = adaptive
        self.tokens = burst_size
        self.max_tokens = burst_size
        self.last_update = time.time()
        self.lock = threading.Lock()
        self.request_history: Deque[float] = deque(maxlen=100)
        self.error_count = 0
        self.success_count = 0
        
    def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens, blocking if necessary. Returns wait time."""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now
            
            # Replenish tokens
            self.tokens = min(
                self.max_tokens,
                self.tokens + elapsed * self.requests_per_second
            )
            
            wait_time = 0.0
            if tokens > self.tokens:
                wait_time = (tokens - self.tokens) / self.requests_per_second
                time.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= tokens
            
            self.request_history.append(now)
            return wait_time
    
    def adjust_rate(self, success: bool):
        """Adjust rate based on request outcomes."""
        if not self.adaptive:
            return
            
        with self.lock:
            if success:
                self.success_count += 1
                # Gradually increase rate on success
                if self.success_count > 10 and self.error_count == 0:
                    self.requests_per_second = min(
                        self.requests_per_second * 1.1,
                        5.0  # Max 5 requests per second
                    )
                    self.success_count = 0
            else:
                self.error_count += 1
                # Immediately decrease rate on errors
                self.requests_per_second = max(
                    self.requests_per_second * 0.5,
                    0.1  # Min 0.1 requests per second
                )
                if self.error_count > 3:
                    # Apply exponential backoff
                    time.sleep(2 ** min(self.error_count - 3, 5))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics."""
        with self.lock:
            recent_requests = sum(
                1 for t in self.request_history 
                if time.time() - t < 60
            )
            return {
                "current_rate": self.requests_per_second,
                "tokens_available": self.tokens,
                "recent_requests": recent_requests,
                "success_count": self.success_count,
                "error_count": self.error_count
            }

class RequestManager:
    """Enhanced request manager with retry logic and session pooling."""
    
    def __init__(self, 
                 rate_limiter: RateLimiter,
                 timeout: int = 30,
                 max_retries: int = 5,
                 proxy_pool: Optional[List[str]] = None):
        self.rate_limiter = rate_limiter
        self.timeout = timeout
        self.max_retries = max_retries
        self.proxy_pool = proxy_pool or []
        self.current_proxy_idx = 0
        self.session_pool: List[requests.Session] = []
        self.session_lock = threading.Lock()
        self._initialize_sessions()
    
    def _initialize_sessions(self, pool_size: int = 5):
        """Initialize session pool with different configurations."""
        for i in range(pool_size):
            session = self._create_session()
            self.session_pool.append(session)
    
    def _create_session(self) -> requests.Session:
        """Create configured session with retry strategy."""
        session = requests.Session()
        
        # Retry strategy with exponential backoff<!--citation:1-->
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=2.0,
            status_forcelist=[429, 500, 502, 503, 504, 520, 521, 522, 524],
            allowed_methods=["GET", "HEAD", "OPTIONS"],
            respect_retry_after_header=True
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=50
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set random user agent
        user_agent = random.choice(REALISTIC_USER_AGENTS)
        session.headers.update(self._get_headers(user_agent))
        
        return session
    
    def _get_headers(self, user_agent: str) -> Dict[str, str]:
        """Get realistic browser headers."""
        return {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
    
    def _get_proxy(self) -> Optional[Dict[str, str]]:
        """Get next proxy from pool."""
        if not self.proxy_pool:
            return None
        
        with self.session_lock:
            proxy = self.proxy_pool[self.current_proxy_idx]
            self.current_proxy_idx = (self.current_proxy_idx + 1) % len(self.proxy_pool)
            return {"http": proxy, "https": proxy}
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make GET request with rate limiting and retry logic."""
        # Acquire rate limit token
        wait_time = self.rate_limiter.acquire()
        if wait_time > 0:
            logger.debug(f"Rate limited, waited {wait_time:.2f}s")
        
        # Get session from pool
        with self.session_lock:
            session = random.choice(self.session_pool)
        
        # Set proxy if available
        if self.proxy_pool:
            kwargs["proxies"] = self._get_proxy()
        
        # Set timeout
        kwargs.setdefault("timeout", self.timeout)
        
        # Implement exponential backoff on rate limit<!--citation:2-->
        retry_delay = 1
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = session.get(url, **kwargs)
                
                # Check for rate limit and handle Retry-After header<!--citation:3-->
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        wait_time = int(retry_after)
                    else:
                        wait_time = retry_delay
                    
                    logger.warning(f"Rate limit hit (429), waiting {wait_time}s")
                    time.sleep(wait_time)
                    retry_delay *= 2  # Exponential backoff
                    self.rate_limiter.adjust_rate(False)
                    continue
                
                response.raise_for_status()
                self.rate_limiter.adjust_rate(True)
                return response
                
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.debug(f"Request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2
                
                self.rate_limiter.adjust_rate(False)
        
        raise last_error or requests.exceptions.RequestException("Max retries exceeded")

# ═════════════════════════════════════════════════════════════════════════════
# Web Scraping Engine
# ═════════════════════════════════════════════════════════════════════════════

class ScrapeEngine:
    """Advanced scraping engine with multiple strategies."""
    
    def __init__(self, 
                 request_manager: RequestManager,
                 config: Dict[str, Any],
                 use_selenium: bool = True):
        self.request_manager = request_manager
        self.config = config
        self.use_selenium = use_selenium and SELENIUM_AVAILABLE
        self.driver = None
        self._driver_lock = threading.Lock()
    
    def _get_selenium_driver(self) -> Optional[webdriver.Chrome]:
        """Get or create Selenium driver."""
        if not self.use_selenium:
            return None
            
        with self._driver_lock:
            if self.driver is None:
                try:
                    options = ChromeOptions()
                    options.add_argument("--headless=new")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")
                    options.add_argument("--disable-gpu")
                    options.add_argument("--disable-web-security")
                    options.add_argument("--disable-features=VizDisplayCompositor")
                    options.add_argument(f"--user-agent={random.choice(REALISTIC_USER_AGENTS)}")
                    options.add_experimental_option("excludeSwitches", ["enable-automation"])
                    options.add_experimental_option('useAutomationExtension', False)
                    
                    self.driver = webdriver.Chrome(options=options)
                    self.driver.execute_script(
                        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                    )
                except Exception as e:
                    logger.error(f"Failed to create Selenium driver: {e}")
                    self.use_selenium = False
                    return None
            
            return self.driver
    
    def scrape_page(self, url: str, page_number: int = 1) -> List[VideoResult]:
        """Scrape a single page with fallback strategies."""
        logger.info(f"Scraping page {page_number}: {url}")
        
        # Try Selenium first if available
        if self.use_selenium:
            results = self._scrape_with_selenium(url, page_number)
            if results:
                return results
        
        # Fallback to regular requests
        return self._scrape_with_requests(url, page_number)
    
    def _scrape_with_selenium(self, url: str, page_number: int) -> List[VideoResult]:
        """Scrape using Selenium for JavaScript-rendered content."""
        driver = self._get_selenium_driver()
        if not driver:
            return []
        
        try:
            driver.get(url)
            
            # Wait for content to load
            wait = WebDriverWait(driver, 15)
            video_selector = self.config["video_item_selector"].split(",")[0].strip()
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, video_selector)))
            
            # Add delay to avoid detection<!--citation:4-->
            time.sleep(random.uniform(1.0, 2.5))
            
            # Get page source
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, "html.parser")
            
            return self._extract_videos(soup, url, page_number)
            
        except Exception as e:
            logger.error(f"Selenium scraping failed: {e}")
            return []
    
    def _scrape_with_requests(self, url: str, page_number: int) -> List[VideoResult]:
        """Scrape using requests library."""
        try:
            response = self.request_manager.get(url)
            soup = BeautifulSoup(response.text, "html.parser")
            return self._extract_videos(soup, url, page_number)
            
        except Exception as e:
            logger.error(f"Request scraping failed: {e}")
            return []
    
    def _extract_videos(self, soup: BeautifulSoup, url: str, page_number: int) -> List[VideoResult]:
        """Extract video data from parsed HTML."""
        results = []
        
        # Find all video items
        video_items = []
        for selector in self.config["video_item_selector"].split(","):
            items = soup.select(selector.strip())
            video_items.extend(items)
        
        if not video_items:
            logger.warning(f"No video items found on page {page_number}")
            return results
        
        for item in video_items:
            try:
                video_data = self._extract_video_data(item, url)
                if video_data:
                    results.append(video_data)
            except Exception as e:
                logger.debug(f"Failed to extract video data: {e}")
                continue
        
        logger.success(f"Extracted {len(results)} videos from page {page_number}")
        return results
    
    def _extract_video_data(self, item, base_url: str) -> Optional[VideoResult]:
        """Extract data for a single video item."""
        # Extract title
        title = self._extract_text(item, self.config["title_selector"])
        if not title:
            title = self._extract_attribute(item, self.config["title_selector"], "title")
        
        # Extract link
        link = self._extract_link(item, self.config["link_selector"], base_url)
        if not link or link == "#":
            return None
        
        # Extract thumbnail
        img_url = self._extract_image(item, self.config["img_selector"], base_url)
        
        # Extract metadata
        duration = self._extract_text(item, self.config.get("time_selector", ""))
        views = self._extract_text(item, self.config.get("meta_selector", ""))
        channel_name = self._extract_text(item, self.config.get("channel_name_selector", ""))
        channel_link = self._extract_link(item, self.config.get("channel_link_selector", ""), base_url)
        
        # Extract quality if available
        quality = self._extract_quality(item)
        
        return VideoResult(
            title=title or "Untitled",
            link=link,
            img_url=img_url,
            duration=duration,
            views=views,
            channel_name=channel_name,
            channel_link=channel_link,
            quality=quality,
            source_engine=self.config.get("url", base_url)
        )
    
    def _extract_text(self, element, selector: str) -> Optional[str]:
        """Extract text from element using selector."""
        if not selector:
            return None
        
        for sel in selector.split(","):
            sel = sel.strip()
            if not sel:
                continue
            
            el = element.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if text:
                    return text
        
        return None
    
    def _extract_attribute(self, element, selector: str, attribute: str) -> Optional[str]:
        """Extract attribute from element using selector."""
        if not selector:
            return None
        
        for sel in selector.split(","):
            sel = sel.strip()
            if not sel:
                continue
            
            el = element.select_one(sel)
            if el and el.has_attr(attribute):
                return el[attribute]
        
        return None
    
    def _extract_link(self, element, selector: str, base_url: str) -> Optional[str]:
        """Extract and normalize link."""
        href = self._extract_attribute(element, selector, "href")
        if href:
            return urljoin(base_url, href)
        return None
    
    def _extract_image(self, element, selector: str, base_url: str) -> Optional[str]:
        """Extract image URL with multiple fallbacks."""
        if not selector:
            return None
        
        for sel in selector.split(","):
            sel = sel.strip()
            if not sel:
                continue
            
            img = element.select_one(sel)
            if img:
                # Try multiple attributes
                for attr in ["data-src", "src", "data-lazy", "data-original", "data-thumb"]:
                    if img.has_attr(attr):
                        img_url = img[attr]
                        if img_url and not img_url.startswith("data:"):
                            return urljoin(base_url, img_url)
        
        return None
    
    def _extract_quality(self, element) -> Optional[str]:
        """Extract video quality indicator."""
        quality_indicators = ["HD", "4K", "1080p", "720p", "480p"]
        text = element.get_text().upper()
        
        for indicator in quality_indicators:
            if indicator in text:
                return indicator
        
        return None
    
    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            with self._driver_lock:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None

# ═════════════════════════════════════════════════════════════════════════════
# Thumbnail Downloader
# ═════════════════════════════════════════════════════════════════════════════

class ThumbnailDownloader:
    """Efficient thumbnail downloader with caching."""
    
    def __init__(self, 
                 cache_dir: Path = THUMBNAILS_DIR,
                 max_workers: int = 20,
                 use_async: bool = True):
        self.cache_dir = cache_dir
        self.max_workers = max_workers
        self.use_async = use_async and ASYNC_AVAILABLE
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = {}
        self._load_cache_index()
    
    def _load_cache_index(self):
        """Load cache index for faster lookups."""
        cache_file = self.cache_dir / ".cache_index.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}
    
    def _save_cache_index(self):
        """Save cache index."""
        cache_file = self.cache_dir / ".cache_index.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(self._cache, f)
        except Exception:
            pass
    
    def _get_cache_path(self, url: str, title: str) -> Path:
        """Generate cache path for thumbnail."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        safe_title = self._slugify(title)[:50]
        ext = Path(urlparse(url).path).suffix or ".jpg"
        return self.cache_dir / f"{safe_title}_{url_hash}{ext}"
    
    def _slugify(self, text: str) -> str:
        """Create safe filename from text."""
        text = unicodedata.normalize("NFKD", text)
        text = re.sub(r'[^\w\s-]', '', text).strip()
        return re.sub(r'[-\s]+', '-', text)
    
    async def download_thumbnails_async(self, videos: List[VideoResult]) -> Dict[str, str]:
        """Download thumbnails asynchronously."""
        if not self.use_async:
            return self.download_thumbnails_sync(videos)
        
        results = {}
        
        async with aiohttp.ClientSession() as session:
            semaphore = asyncio.Semaphore(self.max_workers)
            
            tasks = []
            for video in videos:
                if video.img_url:
                    task = self._download_single_async(session, semaphore, video)
                    tasks.append(task)
            
            completed = await asyncio.gather(*tasks, return_exceptions=True)
            
            for video, result in zip(videos, completed):
                if isinstance(result, str):
                    results[video.link] = result
                else:
                    results[video.link] = self._get_placeholder()
        
        self._save_cache_index()
        return results
    
    async def _download_single_async(self, 
                                   session: aiohttp.ClientSession, 
                                   semaphore: asyncio.Semaphore, 
                                   video: VideoResult) -> str:
        """Download single thumbnail asynchronously."""
        # Check cache
        if video.img_url in self._cache:
            cache_path = Path(self._cache[video.img_url])
            if cache_path.exists():
                return str(cache_path)
        
        cache_path = self._get_cache_path(video.img_url, video.title)
        
        # Download
        async with semaphore:
            try:
                async with session.get(video.img_url, timeout=30) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        # Validate content
                        if len(content) > 0 and len(content) < 10 * 1024 * 1024:
                            with open(cache_path, 'wb') as f:
                                f.write(content)
                            
                            self._cache[video.img_url] = str(cache_path)
                            return str(cache_path)
                            
            except Exception as e:
                logger.debug(f"Failed to download thumbnail: {e}")
        
        return self._get_placeholder()
    
    def download_thumbnails_sync(self, videos: List[VideoResult]) -> Dict[str, str]:
        """Download thumbnails synchronously with thread pool."""
        results = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_video = {
                executor.submit(self._download_single_sync, video): video
                for video in videos if video.img_url
            }
            
            # Use tqdm for progress if available
            futures = concurrent.futures.as_completed(future_to_video)
            if TQDM_AVAILABLE:
                futures = tqdm(futures, total=len(future_to_video), desc="Downloading thumbnails")
            
            for future in futures:
                video = future_to_video[future]
                try:
                    result = future.result()
                    results[video.link] = result
                except Exception as e:
                    logger.debug(f"Thumbnail download failed: {e}")
                    results[video.link] = self._get_placeholder()
        
        self._save_cache_index()
        return results
    
    def _download_single_sync(self, video: VideoResult) -> str:
        """Download single thumbnail synchronously."""
        # Check cache
        if video.img_url in self._cache:
            cache_path = Path(self._cache[video.img_url])
            if cache_path.exists():
                return str(cache_path)
        
        cache_path = self._get_cache_path(video.img_url, video.title)
        
        # Download
        try:
            response = requests.get(video.img_url, timeout=30)
            response.raise_for_status()
            
            # Validate content
            if len(response.content) > 0 and len(response.content) < 10 * 1024 * 1024:
                with open(cache_path, 'wb') as f:
                    f.write(response.content)
                
                self._cache[video.img_url] = str(cache_path)
                return str(cache_path)
                
        except Exception as e:
            logger.debug(f"Failed to download thumbnail: {e}")
        
        return self._get_placeholder()
    
    def _get_placeholder(self) -> str:
        """Get placeholder image as data URI."""
        svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180" viewBox="0 0 320 180">
            <rect width="320" height="180" fill="#1a1a2e"/>
            <text x="160" y="90" font-family="Arial" font-size="60" fill="#4a4a5e" text-anchor="middle" dominant-baseline="middle">📹</text>
        </svg>'''
        return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()

# ═════════════════════════════════════════════════════════════════════════════
# Result Exporters
# ═════════════════════════════════════════════════════════════════════════════

class ResultExporter:
    """Export results to various formats."""
    
    @staticmethod
    def export_html(results: List[VideoResult], 
                   thumbnails: Dict[str, str],
                   query: str,
                   output_path: Path) -> Path:
        """Export results as HTML gallery."""
        html_content = ResultExporter._generate_html(results, thumbnails, query)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_path
    
    @staticmethod
    def _generate_html(results: List[VideoResult], 
                      thumbnails: Dict[str, str],
                      query: str) -> str:
        """Generate HTML content."""
        # Enhanced HTML template with modern design
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Enhanced Search Results</title>
    <style>
        :root {{
            --bg-primary: #0a0a1a;
            --bg-secondary: #16213e;
            --text-primary: #e0e0e0;
            --text-secondary: #a0a0a0;
            --accent: #00d4ff;
            --accent-secondary: #ff006e;
            --border: #2a2a3e;
            --shadow: rgba(0, 0, 0, 0.3);
        }}
        
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem;
            background: var(--bg-secondary);
            border-radius: 12px;
            box-shadow: 0 4px 20px var(--shadow);
        }}
        
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, var(--accent) 0%, var(--accent-secondary) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .stats {{
            display: flex;
            justify-content: center;
            gap: 2rem;
            flex-wrap: wrap;
            margin-top: 1.5rem;
        }}
        
        .stat {{
            background: rgba(0, 212, 255, 0.1);
            padding: 0.5rem 1.5rem;
            border-radius: 20px;
            border: 1px solid var(--accent);
            font-size: 0.9rem;
        }}
        
        .filters {{
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }}
        
        .filter-btn {{
            padding: 0.5rem 1rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        
        .filter-btn:hover {{
            background: var(--accent);
            color: var(--bg-primary);
            transform: translateY(-2px);
        }}
        
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 2rem;
            margin-top: 2rem;
        }}
        
        .card {{
            background: var(--bg-secondary);
            border-radius: 12px;
            overflow: hidden;
            transition: all 0.3s ease;
            box-shadow: 
