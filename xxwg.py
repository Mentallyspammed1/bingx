import asyncio
import aiohttp
import os
import re
import sys
import logging
import webbrowser
from datetime import datetime
from typing import List, Dict, Any, Union
from bs4 import BeautifulSoup
from colorama import Fore, init, Style
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from fake_useragent import UserAgent
from tqdm.asyncio import tqdm_asyncio # CORRECTED: Import tqdm_asyncio
from urllib.parse import quote # Correct import for URL encoding

# Initialize Colorama for colored output
init(autoreset=True)

# Neon color scheme
NEON_CYAN = Fore.CYAN
NEON_MAGENTA = Fore.MAGENTA
NEON_GREEN = Fore.GREEN
NEON_YELLOW = Fore.YELLOW
NEON_RED = Fore.RED
NEON_BLUE = Fore.BLUE
NEON_WHITE = Fore.WHITE
NEON_BRIGHT = Style.BRIGHT
RESET_ALL = Style.RESET_ALL

# Custom Neon Log Formatter
class NeonLogFormatter(logging.Formatter):
    def format(self, record):
        log_message = super().format(record)
        level_color = ""
        if record.levelno == logging.INFO:
            level_color = NEON_GREEN
        elif record.levelno == logging.WARNING:
            level_color = NEON_YELLOW
        elif record.levelno == logging.ERROR:
            level_color = NEON_RED
        elif record.levelno == logging.CRITICAL:
            level_color = NEON_BRIGHT + NEON_RED
            
        # Format for timestamp and level, then add message
        return f"{NEON_CYAN}{datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')}{RESET_ALL} - {level_color}{record.levelname}{RESET_ALL} - {record.message}"

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if logger.hasHandlers(): # Clear existing handlers to prevent duplicate logs on re-run
    logger.handlers.clear()
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(NeonLogFormatter())
logger.addHandler(stream_handler)

# Suppress noisy external library warnings
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("fake_useragent").setLevel(logging.WARNING)

# Global defaults
THUMBNAILS_DIR = "downloaded_thumbnails"
DEFAULT_SEARCH_LIMIT = 30
DEFAULT_PAGE_NUMBER = 1
DEFAULT_ENGINE = "pornhub"
DEFAULT_SOUP_SLEEP = 2.0 # Delay between page fetches

# Site configurations - NOW WITH FALLBACK SELECTORS!
SITE_CONFIGS = {
    "pornhub": {
        "name": "Pornhub",
        "base_url": "https://www.pornhub.com",
        "search_path": "/video/search?search={query}&page={page}",
        "selectors": {
            "videos": [
                "li.pcVideoListItem",  # Primary selector
                "div.video-list-item",  # Fallback 1 (common alternative)
                "div.video-item"        # Fallback 2 (generic)
            ],
            "title": [
                "a.link-title", # More specific
                ".title a",
                ".video-title",
                "[data-title]"
            ],
            "link": [
                "a.link-title", # More specific
                ".title a",
                "a[href*='/view/']", # Generic link containing view
            ],
            "img": [
                "img.js-responsive-img", # More specific
                ".js-pop img",
                ".thumbnail img",
                "[data-src]",
                "[src]"
            ],
            "quality": [
                "span.hd-thumbnail", # Specific for HD mark
                ".videoUHD",
                ".quality-badge",
                "[data-quality]"
            ],
            "duration": [
                "var.duration",
                ".duration",
                ".video-duration",
                "[data-duration]"
            ],
            "channel_name": [
                "div.video-detailed-info a.usernameLink",
                ".usernameWrap a",
                ".channel-link",
                "[data-channel]"
            ],
            "channel_link": [ # Often same as channel_name link, but good to have explicit
                "div.video-detailed-info a.usernameLink",
                ".usernameWrap a",
                ".channel-link",
                "a[href*='/model/']", # Generic model link
                "a[href*='/channels/']", # Generic channel link
            ],
        },
    },
    "xvideos": {
        "name": "Xvideos",
        "base_url": "https://www.xvideos.com",
        "search_path": "/?k={query}&p={page}",
        "selectors": {
            "videos": [
                "div.mozaique > div",
                "div.thumb-block" # Common alternative
            ],
            "title": [
                "a[title]",
                ".thumb-under a"
            ],
            "link": [
                "a[title]",
                ".thumb-under a"
            ],
            "img": [
                "img",
                ".thumb img"
            ],
            "quality": [
                "span.video-hd-mark",
                ".quality-badge"
            ],
            "duration": [
                "span.duration",
                ".duration"
            ],
            "channel_name": [
                "a.channel",
                ".channel-link"
            ],
            "channel_link": [
                "a.channel",
                ".channel-link"
            ],
        },
    },
    "spankbang": {
        "name": "Spankbang",
        "base_url": "https://spankbang.com",
        "search_path": "/s/{query}/{page}/",
        "selectors": {
            "videos": [
                "div.video-item",
                ".video-box" # Common alternative
            ],
            "title": [
                "h2 a",
                ".n"
            ],
            "link": [
                "h2 a",
                "a[href^='/']" # Generic relative link
            ],
            "img": [
                "img.lazy",
                ".cover img",
                "[data-src]",
                "[src]"
            ],
            "quality": [
                "span.q",
                ".q"
            ],
            "duration": [
                "span.l",
                ".l"
            ],
            "channel_name": [
                "a.u",
                ".channel-link"
            ],
            "channel_link": [
                "a.u",
                ".channel-link"
            ],
        },
    },
    "xhamster": { # New site configuration for Xhamster
        "name": "Xhamster",
        "base_url": "https://xhamster.com",
        "search_path": "/search/{query}/{page}", # Xhamster often uses /search/query/page_number
        "selectors": {
            "videos": [
                "div.thumb-list__item",
                "div.video-list-item",
                "div.video-item"
            ],
            "title": [
                ".video-title a",
                ".title a",
                "a[title]"
            ],
            "link": [
                ".video-title a",
                ".title a",
                "a[href*='/videos/']"
            ],
            "img": [
                "img[data-src]",
                "img[src]",
                ".thumb-img img"
            ],
            "quality": [
                ".badge-hd",
                ".hd-mark",
                ".quality-badge"
            ],
            "duration": [
                ".duration",
                ".video-duration"
            ],
            "channel_name": [
                ".ch-name a",
                ".channel-name a",
                ".user-name a"
            ],
            "channel_link": [
                ".ch-name a",
                ".channel-name a",
                ".user-name a"
            ],
        },
    },
    "xnxx": { # New site configuration for XNXX
        "name": "XNXX",
        "base_url": "https://www.xnxx.com",
        "search_path": "/search/{query}/{page}", # XNXX often uses /search/query/page_number
        "selectors": {
            "videos": [
                "div.mozaique > div.thumb-block",
                "div.thumb-block"
            ],
            "title": [
                "a[title]",
                ".thumb-under a"
            ],
            "link": [
                "a[title]",
                ".thumb-under a"
            ],
            "img": [
                "img[data-src]",
                "img[src]",
                ".thumb img"
            ],
            "quality": [
                "span.video-hd-mark",
                ".quality-badge"
            ],
            "duration": [
                "span.duration",
                ".duration"
            ],
            "channel_name": [
                "a.channel",
                ".channel-link",
                ".name a"
            ],
            "channel_link": [
                "a.channel",
                ".channel-link",
                ".name a"
            ],
        },
    },
    "greenporn": { # New site configuration for GreenPorn
        "name": "GreenPorn",
        "base_url": "https://www.green.porn",
        "search_path": "/search?q={query}&page={page}", # GreenPorn likely uses 1-based pagination.
        "selectors": {
            "videos": [
                "div.video-item-container",
                "div.video-item",
                ".video-card"
            ],
            "title": [
                ".video-title a",
                ".video-card-title a",
                "a[title]"
            ],
            "link": [
                ".video-title a",
                ".video-card-title a",
                "a[href^='/']"
            ],
            "img": [
                "img[data-src]",
                "img[src]",
                ".thumb-image img"
            ],
            "quality": [
                ".quality-badge",
                ".hd-label",
                ".quality"
            ],
            "duration": [
                ".duration",
                ".video-duration",
                ".time"
            ],
            "channel_name": [
                ".channel-name a",
                ".user-name a",
                ".uploader-name a"
            ],
            "channel_link": [
                ".channel-name a",
                ".user-name a",
                ".uploader-name a"
            ],
        },
    },
}

# Helper functions
def ensure_directory_exists(directory_path: str):
    """Creates a directory if it doesn't exist."""
    try:
        os.makedirs(directory_path, exist_ok=True)
        logger.info(f"{NEON_GREEN}Created directory: {directory_path}{RESET_ALL}")
    except OSError as e:
        logger.error(f"{NEON_RED}Error creating directory {directory_path}: {e}{RESET_ALL}")
        raise

def sanitize_filename(filename: str) -> str:
    """Sanitizes a string for use as a filename, ensuring it's valid and concise."""
    if not filename:
        return "unknown_title"
    filename = re.sub(r'[<>:"/\\|?*]', '', filename) # Remove invalid characters
    filename = re.sub(r'[\s]+', '_', filename).strip("_") # Replace spaces with underscores
    filename = re.sub(r'__+', '_', filename) # Replace multiple underscores with one
    max_len = 100
    return filename[:max_len] if len(filename) > max_len else filename

class EnhancedConcurrentAdultSiteScraper:
    """
    Enhanced asynchronous scraper for adult websites like Pornhub, Xvideos, and Spankbang.
    Utilizes aiohttp for concurrent requests, tenacity for retries, and fake_useragent for user-agent rotation.
    Incorporates fallback selectors for improved resilience to website structure changes.
    """
    def __init__(self, soup_sleep: float = DEFAULT_SOUP_SLEEP):
        self.ua = UserAgent()
        self.soup_sleep = soup_sleep # Delay between page fetches for politeness
        logger.info(f"{NEON_CYAN}Initialized EnhancedConcurrentAdultSiteScraper with soup_sleep={self.soup_sleep:.1f}s{RESET_ALL}")
        
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(3), # Increased wait time slightly for network issues
           retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
           before_sleep=lambda retry_state: logger.warning(
               f"{NEON_YELLOW}Retrying {retry_state.fn.__name__} (attempt {retry_state.attempt_number}/{retry_state.max_attempts})... Error: {retry_state.outcome.exception()}{RESET_ALL}"
           ))
    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> str:
        """
        Fetches a page asynchronously with retry mechanism.
        Raises aiohttp.ClientError or asyncio.TimeoutError on failure to trigger retry.
        """
        headers = {"User-Agent": self.ua.random}
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as response: # Increased timeout
                response.raise_for_status() # Raises aiohttp.ClientResponseError for 4xx/5xx responses
                logger.debug(f"{NEON_BLUE}Successfully fetched: {url}{RESET_ALL}")
                return await response.text()
        except aiohttp.ClientResponseError as e:
            logger.error(f"{NEON_RED}HTTP Error fetching {url}: Status {e.status} - {e.message}{RESET_ALL}")
            raise # Re-raise to trigger retry
        except aiohttp.ClientConnectionError as e:
            logger.error(f"{NEON_RED}Connection Error fetching {url}: {e}{RESET_ALL}")
            raise # Re-raise to trigger retry
        except asyncio.TimeoutError:
            logger.error(f"{NEON_RED}Timeout fetching {url}{RESET_ALL}")
            raise # Re-raise to trigger retry
        except Exception as e:
            logger.error(f"{NEON_RED}Unexpected Error fetching {url}: {e}{RESET_ALL}")
            raise # Re-raise for tenacity

    def _find_element_with_fallbacks(self, soup_obj: BeautifulSoup, selectors: List[str]) -> Union[BeautifulSoup, None]:
        """
        Attempts to find an element using a list of fallback CSS selectors.
        Returns the first found element or None if none are found.
        """
        for selector in selectors:
            element = soup_obj.select_one(selector)
            if element:
                return element
        return None

    async def process_video(self, item_soup: BeautifulSoup, site_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a single video item's BeautifulSoup object using site-specific selectors with fallbacks.
        Extracts title, links, image URLs, quality, duration, and channel info.
        """
        video = {}
        try:
            selectors = site_config["selectors"]
            base_url = site_config["base_url"]

            # Title
            title_tag = self._find_element_with_fallbacks(item_soup, selectors["title"])
            title = title_tag.get_text(strip=True) if title_tag else "N/A"

            # Link
            link_tag = self._find_element_with_fallbacks(item_soup, selectors["link"])
            link = link_tag["href"] if link_tag and link_tag.get("href") else "#"
            if link and not link.startswith("http"): # Ensure link is absolute
                link = base_url + link

            # Thumbnail Image URL
            img_tag = self._find_element_with_fallbacks(item_soup, selectors["img"])
            img_url = img_tag.get("data-src") or img_tag.get("src") if img_tag else "https://via.placeholder.com/300x200?text=No+Image"
            if img_url and not img_url.startswith("http") and not img_url.startswith("data:image"): # Handle relative and data URIs
                img_url = base_url + img_url

            # Quality
            quality_tag = self._find_element_with_fallbacks(item_soup, selectors["quality"])
            quality = quality_tag.get_text(strip=True) if quality_tag else "N/A"

            # Duration
            duration_tag = self._find_element_with_fallbacks(item_soup, selectors["duration"])
            duration = duration_tag.get_text(strip=True) if duration_tag else "N/A"
            
            # Channel Name
            channel_name_tag = self._find_element_with_fallbacks(item_soup, selectors["channel_name"])
            channel_name = channel_name_tag.get_text(strip=True) if channel_name_tag else "N/A"
            
            # Channel Link
            channel_link_tag = self._find_element_with_fallbacks(item_soup, selectors["channel_link"])
            channel_link = channel_link_tag["href"] if channel_link_tag and channel_link_tag.get("href") else "#"
            if channel_link and not channel_link.startswith("http"): # Ensure channel link is absolute
                channel_link = base_url + channel_link

            video = {
                "title": title,
                "img_url": img_url, # Original URL for downloading
                "link": link,
                "quality": quality,
                "time": duration,
                "channel_name": channel_name,
                "channel_link": channel_link,
                "img_local_path": "https://via.placeholder.com/300x200?text=No+Image" # Placeholder for local path
            }
            return video
        except Exception as e:
            # Log specific details about which element might have failed
            logger.error(f"{NEON_RED}Error processing video item for '{video.get('title', 'N/A')}': {e}. This item might be malformed or selectors need adjustment.{RESET_ALL}")
            return {} # Return empty dict or partial data on error

    async def scrape_site(self, engine_name: str, query: str, limit: int = DEFAULT_SEARCH_LIMIT, page: int = DEFAULT_PAGE_NUMBER) -> List[Dict]:
        """
        Scrapes a specified website asynchronously for video metadata.
        Manages fetching, parsing, and concurrent processing of video items.
        """
        engine_config = SITE_CONFIGS.get(engine_name)
        if not engine_config:
            logger.critical(f"{NEON_RED}Unsupported engine: {engine_name}. Please choose from {', '.join(SITE_CONFIGS.keys())}.{RESET_ALL}")
            return []

        search_url = f"{engine_config['base_url']}{engine_config['search_path'].format(query=quote(query), page=page)}"
        logger.info(f"{NEON_BLUE}Starting scrape for '{query}' on {engine_config['name']} (page {page})... URL: {search_url}{RESET_ALL}")

        videos_data: List[Dict] = []
        async with aiohttp.ClientSession() as session:
            try:
                html = await self.fetch_page(session, search_url)
                soup = BeautifulSoup(html, 'html.parser')
                
                # Use fallback selectors for the main video items
                video_items_selectors = engine_config["selectors"]["videos"]
                video_items = []
                for selector in video_items_selectors:
                    found_items = soup.select(selector)
                    if found_items:
                        video_items = found_items
                        logger.info(f"{NEON_GREEN}Found video items using selector: '{selector}'{RESET_ALL}")
                        break
                
                if not video_items:
                    logger.warning(f"{NEON_YELLOW}No video items found on {engine_config['name']} for query '{query}' (page {page}) using any of the provided selectors: {video_items_selectors}. Website structure might have changed.{RESET_ALL}")
                    return []
                
                # Process videos concurrently up to the limit
                tasks = []
                for item in video_items[:limit]:
                    task = asyncio.create_task(self.process_video(item, engine_config))
                    tasks.append(task)
                
                # Use tqdm_asyncio for an async progress bar during video parsing
                processed_results = await tqdm_asyncio(asyncio.gather(*tasks, return_exceptions=True), desc=f"{NEON_BLUE}Parsing videos from {engine_name}{RESET_ALL}")
                
                # Filter out any exceptions or empty dictionaries from processing errors
                videos_data = [r for r in processed_results if isinstance(r, dict) and r]
                logger.info(f"{NEON_GREEN}Successfully processed {len(videos_data)} video items from {engine_config['name']}.{RESET_ALL}")

            except Exception as e: # Catch any errors from fetch_page or initial soup parsing
                logger.error(f"{NEON_RED}Error during scraping of {engine_config['name']} for query '{query}': {e}{RESET_ALL}")
        
        await asyncio.sleep(self.soup_sleep) # Politeness delay between major page scrapes
        return videos_data

    async def download_thumbnails(self, videos: List[Dict], output_base_dir: str, engine_name: str) -> List[Dict]:
        """
        Downloads thumbnails concurrently for a list of video metadata dictionaries.
        Updates the 'img_local_path' field in each video dictionary with the local path.
        """
        if not videos:
            return []

        engine_thumbnail_dir = os.path.join(output_base_dir, THUMBNAILS_DIR, engine_name)
        ensure_directory_exists(engine_thumbnail_dir)
        logger.info(f"{NEON_BLUE}Starting concurrent thumbnail download to: {engine_thumbnail_dir}{RESET_ALL}")

        async with aiohttp.ClientSession() as session:
            tasks = []
            for idx, video in enumerate(videos):
                if video["img_url"].startswith("http"):
                    task = asyncio.create_task(self._download_single_thumbnail(session, video, engine_thumbnail_dir, idx))
                    tasks.append(task)
                elif not video["img_url"].startswith("data:image"): # Log only if it's not a data URI
                    logger.warning(f"{NEON_YELLOW}Skipping thumbnail download for '{video.get('title', 'N/A')}' due to non-HTTP/data URI: {video['img_url']}{RESET_ALL}")
            
            # Use tqdm_asyncio for an async progress bar during thumbnail download
            downloaded_results = await tqdm_asyncio(asyncio.gather(*tasks, return_exceptions=True), desc=f"{NEON_BLUE}Downloading thumbnails{RESET_ALL}")
            
            # Update original video list with local paths or error placeholders
            for i, result in enumerate(downloaded_results):
                if i < len(videos): # Defensive check
                    original_video = videos[i]  
                    if isinstance(result, dict) and "thumbnail_path" in result:
                        original_video["img_local_path"] = result["thumbnail_path"]
                    else:
                        logger.warning(f"{NEON_YELLOW}Thumbnail download failed for '{original_video.get('title', 'N/A')}' (video index {i}). Using placeholder.{RESET_ALL}")
                        original_video["img_local_path"] = "https://via.placeholder.com/300x200?text=Download+Error"
            
            logger.info(f"{NEON_GREEN}Completed concurrent thumbnail downloads. {len(videos)} videos processed.{RESET_ALL}")
            return videos # Return the modified list

    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1), # Smaller retry for single thumbnail
           retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
           before_sleep=lambda retry_state: logger.warning(
               f"{NEON_YELLOW}Retrying thumbnail download for '{retry_state.args[1].get('title', 'N/A')}' (attempt {retry_state.attempt_number}/{retry_state.max_attempts})... Error: {retry_state.outcome.exception()}{RESET_ALL}"
           ))
    async def _download_single_thumbnail(self, session: aiohttp.ClientSession, video: Dict, output_dir: str, index: int) -> Dict:
        """
        Downloads a single thumbnail and returns a dictionary with the local path.
        Designed to be called concurrently.
        """
        try:
            # Sanitize filename, ensuring uniqueness with index
            sanitized_title = sanitize_filename(video.get("title", "unknown_video"))
            filename = f"{sanitized_title}_{index}.jpg"
            filepath = os.path.join(output_dir, filename)
            
            headers = {"User-Agent": self.ua.random}
            async with session.get(video["img_url"], headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response.raise_for_status()
                with open(filepath, 'wb') as f:
                    while True:
                        chunk = await response.content.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
            
            logger.debug(f"{NEON_BLUE}Downloaded thumbnail for '{video.get('title', 'N/A')}' to {filepath}{RESET_ALL}")
            # Return path relative to the script's execution directory for HTML
            return {"title": video["title"], "thumbnail_path": os.path.relpath(filepath, os.getcwd()).replace(os.sep, '/')}
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            logger.error(f"{NEON_RED}Network/Timeout error downloading thumbnail for '{video.get('title', 'N/A')}' from {video['img_url']}: {e}{RESET_ALL}")
            raise # Re-raise for tenacity
        except Exception as e:
            logger.error(f"{NEON_RED}Error saving thumbnail for '{video.get('title', 'N/A')}' to {filepath}: {e}{RESET_ALL}")
            # Do not re-raise other exceptions here, let them be caught by gather and logged.
            return {"title": video["title"], "thumbnail_path": "https://via.placeholder.com/300x200?text=Error"}


# HTML generation function
def generate_html_output(results: List[Dict[str, Any]], query: str, engine_name: str, search_limit: int, page_number: int, output_dir: str = ".", custom_filename: str = None):
    """Generates an HTML file with search results."""
    if not results:
        logger.warning(f"{NEON_YELLOW}No results to generate HTML for query '{query}' on {engine_name}{RESET_ALL}")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    query_part_sanitized = sanitize_filename(query)
    
    if custom_filename:
        output_filename = os.path.join(output_dir, custom_filename)
    else:
        output_filename = os.path.join(output_dir, f"{engine_name}_search_{query_part_sanitized}_p{page_number}_{timestamp}.html")

    ensure_directory_exists(output_dir)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Search Results for '{query}' on {engine_name}</title>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1a1a2e; color: #e0e0e0; margin: 0; padding: 20px; }}
            .container {{ max-width: 1300px; margin: 20px auto; padding: 30px; background: #2a2a4a; border-radius: 12px; box-shadow: 0 0 20px rgba(0, 255, 255, 0.5); border: 1px solid #00ffff; }}
            h1 {{ color: #00ffff; text-align: center; margin-bottom: 15px; text-shadow: 0 0 8px #00ffff; }}
            h2 {{ color: #ff69b4; text-align: center; margin-bottom: 30px; }}
            .metadata {{ text-align: center; margin-bottom: 25px; font-size: 1.1em; color: #aaa; }}
            .video-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 25px; }}
            .video-item {{ background: #3a3a5a; border-radius: 10px; overflow: hidden; transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out; border: 1px solid #4a4a6a; }}
            .video-item:hover {{ transform: translateY(-7px); box-shadow: 0 8px 25px rgba(0, 170, 255, 0.7); }}
            .video-item a {{ text-decoration: none; color: inherit; display: block; }}
            .video-item img {{ width: 100%; height: 180px; object-fit: cover; border-bottom: 1px solid #4a4a6a; }}
            .video-info {{ padding: 15px; }}
            .video-info h3 {{ margin: 5px 0 10px 0; color: #ff69b4; font-size: 1.2em; line-height: 1.4; }}
            .video-info h3 a {{ color: #ff69b4; text-decoration: none; transition: color 0.2s; }}
            .video-info h3 a:hover {{ color: #00ffff; }}
            .video-meta {{ font-size: 0.9em; color: #aaa; display: flex; flex-wrap: wrap; gap: 8px 15px; }}
            .video-meta span {{ display: flex; align-items: center; }}
            .video-meta span strong {{ margin-right: 5px; color: #e0e0e0; }}
            .video-meta a {{ color: #00ffff; text-decoration: none; transition: color 0.2s; }}
            .video-meta a:hover {{ color: #ff69b4; }}
            .footer {{ text-align: center; margin-top: 40px; font-size: 0.9em; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Neon Search Results</h1>
            <h2>Query: '{query}' on {engine_name}</h2>
            <div class="metadata">
                <p>Displaying {len(results)} of up to {search_limit} results from page {page_number}</p>
                <p>Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            <div class="video-grid">
    """

    for video in results:
        # Use img_local_path which is relative to the script's working directory,
        # assuming output_dir is also relative to the working directory.
        img_src = video.get('img_local_path', 'https://via.placeholder.com/300x200?text=Image+Error')
        html_content += f"""
                <div class="video-item">
                    <a href="{video['link']}" target="_blank" rel="noopener noreferrer">
                        <img src="{img_src}" alt="{video['title']}" onerror="this.src='https://via.placeholder.com/300x200?text=Image+Error'; this.style.opacity='0.5';">
                    </a>
                    <div class="video-info">
                        <h3><a href="{video['link']}" target="_blank" rel="noopener noreferrer">{video['title']}</a></h3>
                        <div class="video-meta">
                            <span><strong>Quality:</strong> {video['quality']}</span>
                            <span><strong>Time:</strong> {video['time']}</span>
                            <span><strong>Channel:</strong> <a href="{video['channel_link']}" target="_blank" rel="noopener noreferrer">{video['channel_name']}</a></span>
                        </div>
                    </div>
                </div>
        """

    html_content += """
            </div>
            <div class="footer">
                <p>Scraping performed with respect to robots.txt (where applicable) and website terms of service.</p>
                <p>Developed with Python, requests, BeautifulSoup, asyncio, aiohttp, tenacity, and Colorama.</p>
            </div>
        </div>
    </body>
    </html>
    """

    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"{NEON_GREEN}HTML output saved to: {output_filename}{RESET_ALL}")
        return output_filename
    except OSError as e:
        logger.error(f"{NEON_RED}Error saving HTML file to {output_filename}: {e}{RESET_ALL}")
        return None

# Main asynchronous execution function
async def main():
    logger.info(f"{NEON_CYAN}{NEON_BRIGHT}--- Starting Enhanced Concurrent Adult Site Scraper ---{RESET_ALL}")

    query = input(f"{NEON_YELLOW}Enter search query: {RESET_ALL}").strip()
    if not query:
        logger.critical(f"{NEON_RED}Search query cannot be empty. Exiting.{RESET_ALL}")
        sys.exit(1)

    try:
        limit_input = input(f"{NEON_YELLOW}Max results per page? [{DEFAULT_SEARCH_LIMIT}]: {RESET_ALL}")
        limit = int(limit_input) if limit_input else DEFAULT_SEARCH_LIMIT
        if limit <= 0:
            logger.warning(f"{NEON_YELLOW}Invalid limit '{limit_input}', using default: {DEFAULT_SEARCH_LIMIT}{RESET_ALL}")
            limit = DEFAULT_SEARCH_LIMIT
    except ValueError:
        logger.error(f"{NEON_RED}Invalid limit input, using default: {DEFAULT_SEARCH_LIMIT}{RESET_ALL}")
        limit = DEFAULT_SEARCH_LIMIT

    try:
        page_input = input(f"{NEON_YELLOW}Page number to scrape? [{DEFAULT_PAGE_NUMBER}]: {RESET_ALL}")
        page = int(page_input) if page_input else DEFAULT_PAGE_NUMBER
        if page <= 0:
            logger.warning(f"{NEON_YELLOW}Invalid page number '{page_input}', using default: {DEFAULT_PAGE_NUMBER}{RESET_ALL}")
            page = DEFAULT_PAGE_NUMBER
    except ValueError:
        logger.error(f"{NEON_RED}Invalid page number input, using default: {DEFAULT_PAGE_NUMBER}{RESET_ALL}")
        page = DEFAULT_PAGE_NUMBER

    available_engines = ', '.join(SITE_CONFIGS.keys())
    engine = input(f"{NEON_YELLOW}Select engine ({available_engines}) [{DEFAULT_ENGINE}]: {RESET_ALL}").strip().lower()
    if engine not in SITE_CONFIGS:
        logger.warning(f"{NEON_YELLOW}Unsupported engine '{engine}'. Using default: {DEFAULT_ENGINE}{RESET_ALL}")
        engine = DEFAULT_ENGINE

    try:
        soup_sleep_input = input(f"{NEON_YELLOW}Delay between page requests (seconds)? [{DEFAULT_SOUP_SLEEP:.1f}]: {RESET_ALL}")
        soup_sleep = float(soup_sleep_input) if soup_sleep_input else DEFAULT_SOUP_SLEEP
        if soup_sleep < 0:
            logger.warning(f"{NEON_YELLOW}Invalid sleep value '{soup_sleep_input}', using default: {DEFAULT_SOUP_SLEEP:.1f}{RESET_ALL}")
            soup_sleep = DEFAULT_SOUP_SLEEP
    except ValueError:
        logger.error(f"{NEON_RED}Invalid sleep value input, using default: {DEFAULT_SOUP_SLEEP:.1f}{RESET_ALL}")
        soup_sleep = DEFAULT_SOUP_SLEEP

    output_dir = input(f"{NEON_YELLOW}Output directory for HTML and thumbnails? [.]: {RESET_ALL}").strip() or "."
    
    scraper = EnhancedConcurrentAdultSiteScraper(soup_sleep=soup_sleep)
    
    # Perform the scrape
    scraped_videos = await scraper.scrape_site(engine_name=engine, query=query, limit=limit, page=page)

    if scraped_videos:
        # Download thumbnails for the scraped videos
        final_videos_with_paths = await scraper.download_thumbnails(scraped_videos, output_dir, engine)
        
        # Generate HTML output
        html_file_path = generate_html_output(
            results=final_videos_with_paths,
            query=query,
            engine_name=engine,
            search_limit=limit,
            page_number=page,
            output_dir=output_dir,
            custom_filename=None # Let the function generate filename based on defaults
        )

        if html_file_path:
            auto_open_input = input(f"{NEON_YELLOW}Auto-open HTML in browser? (y/n) [y]: {RESET_ALL}").strip().lower()
            if auto_open_input == "y" or not auto_open_input: # Default to 'y' if empty
                try:
                    abs_html_path = os.path.abspath(html_file_path)
                    webbrowser.open(f"file:///{abs_html_path}")
                    logger.info(f"{NEON_GREEN}Opened {abs_html_path} in browser.{RESET_ALL}")
                except Exception as e:
                    logger.error(f"{NEON_RED}Failed to auto-open HTML file: {e}{RESET_ALL}")
            else:
                logger.info(f"{NEON_BLUE}HTML file not auto-opened. You can find it at: {html_file_path}{RESET_ALL}")
        else:
            logger.error(f"{NEON_RED}HTML report could not be generated due to previous errors or no results.{RESET_ALL}")
    else:
        logger.warning(f"{NEON_YELLOW}No videos were scraped. HTML report will not be generated.{RESET_ALL}")
    
    logger.info(f"{NEON_CYAN}{NEON_BRIGHT}--- Enhanced Concurrent Adult Site Scraper Finished ---{RESET_ALL}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info(f"\n{NEON_MAGENTA}Operation interrupted by the user. Exiting gracefully.{RESET_ALL}")
    except Exception as e:
        logger.critical(f"{NEON_RED}An unhandled critical error occurred: {e}{RESET_ALL}")
        sys.exit(1)
