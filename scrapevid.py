import logging
import os
import sys
import webbrowser
from datetime import datetime
import re
import argparse
from urllib.parse import urljoin
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
from colorama import Fore, init, Style

# --- Dependencies ---
# To install required libraries, run:
# pip install requests beautifulsoup4 colorama

# Initialize Colorama for cross-platform colored output
init(autoreset=True)

# --- Configuration & Logging ---
NEON_CYAN = Fore.CYAN
NEON_MAGENTA = Fore.MAGENTA
NEON_GREEN = Fore.GREEN
NEON_YELLOW = Fore.YELLOW
NEON_RED = Fore.RED
NEON_BLUE = Fore.BLUE
NEON_WHITE = Fore.WHITE
NEON_BRIGHT = Style.BRIGHT
RESET_ALL = Style.RESET_ALL

LOG_FORMAT = (
    f"{NEON_CYAN}%(asctime)s{RESET_ALL} - "
    f"{NEON_MAGENTA}%(levelname)s{RESET_ALL} - "
    f"{NEON_GREEN}%(message)s{RESET_ALL}"
)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, handlers=[    logging.StreamHandler(sys.stdout)
])
logger = logging.getLogger(__name__)

# Suppress noisy external library warnings
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("chardet").setLevel(logging.WARNING)

# --- Global Defaults ---
THUMBNAILS_DIR = "downloaded_thumbnails"
DEFAULT_SEARCH_LIMIT = 30
DEFAULT_PAGE_NUMBER = 1
DEFAULT_ENGINE = "example"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# Engines mapping - expand with supported sites as needed.
ENGINE_MAP = {
    "example": {
        "url": "https://example.com",
        "search_path": "/search",
        "video_item_selector": "div.video-item",
        "title_selector": "h3",
        "img_selector": "img",
        "link_selector": "a",
        "page_param": "page"
    },
    # Add more engines here with their specific selectors and URL parameters
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
    page: int
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
        response = session.get(search_url, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []

        video_items = soup.select(engine_config["video_item_selector"])
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

    try:
        with requests.Session() as session:
            session.headers.update({"User-Agent": USER_AGENT})

            results = search(
                session=session,
                query=settings["query"],
                limit=settings["limit"],
                engine=settings["engine"],
                page=settings["page"]
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

    logger.info(f"{NEON_CYAN}{NEON_BRIGHT}--- Script Finished ---{RESET_ALL}")

if __name__ == "__main__":
    main()