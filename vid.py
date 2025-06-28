import importlib  # For dynamic module importing
import logging
import os
import re  # Added for sanitizing filenames
import sys
import webbrowser
from datetime import datetime

import requests  # Added for downloading thumbnails
from colorama import Fore, Style, init

# Initialize Colorama for cross-platform colored output
init(autoreset=True)

# --- Configuration & Logging ---
# Neon color scheme
NEON_CYAN = Fore.CYAN
NEON_MAGENTA = Fore.MAGENTA
NEON_GREEN = Fore.GREEN
NEON_YELLOW = Fore.YELLOW
NEON_RED = Fore.RED
NEON_BLUE = Fore.BLUE
NEON_WHITE = Fore.WHITE
NEON_BRIGHT = Style.BRIGHT
NEON_DIM = Style.DIM
RESET_ALL = Style.RESET_ALL

LOG_FORMAT = (
    f"{NEON_CYAN}%(asctime)s{RESET_ALL} - "
    f"{NEON_MAGENTA}%(levelname)s{RESET_ALL} - "
    f"{NEON_GREEN}%(message)s{RESET_ALL}"
)
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, handlers=[
    logging.StreamHandler(sys.stdout)
])
logger = logging.getLogger(__name__)

# Suppress noisy external library warnings
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("chardet").setLevel(logging.WARNING)
# logging.getLogger("requests").setLevel(logging.WARNING) # Keep requests logs for now for debugging downloads

# --- Global Defaults ---
THUMBNAILS_DIR = "downloaded_thumbnails"
DEFAULT_SOUP_SLEEP = 1.0
DEFAULT_SEARCH_LIMIT = 30
DEFAULT_PAGE_NUMBER = 1 # Note: Most pornLib forks don't directly support 'page' in search()
DEFAULT_ENGINE = 'xvideos'

# Engines mapping - we will load these dynamically
# The key is the user-friendly name, the value is the relative import path within pornLib
ENGINE_MODULE_MAP = {
    'xvideos': 'xvideos.XVideos',
    'pornhub': 'pornhub.Pornhub',
    'redtube': 'redtube.Redtube',
    'youporn': 'youporn.Youporn',
}

# --- Dynamic PornLib Client Loading ---
def get_pornlib_client(engine_name: str):
    """
    Dynamically imports and returns the pornLib client for the specified engine.
    Handles ImportErrors gracefully if a specific client is missing.
    """
    try:
        # Import the base pornLib module first
        global pornLib # Make pornLib available globally once imported
        if 'pornLib' not in sys.modules:
            pornLib = importlib.import_module('pornLib')
            logger.info(f"{NEON_GREEN}Base pornLib module imported successfully!{RESET_ALL}")
        else:
            pornLib = sys.modules['pornLib'] # Already imported

        if engine_name not in ENGINE_MODULE_MAP:
            raise ValueError(f"Unsupported engine: {engine_name}. Supported are: {', '.join(ENGINE_MODULE_MAP.keys())}")

        module_path, class_name = ENGINE_MODULE_MAP[engine_name].rsplit('.', 1)
        
        # Import the specific submodule (e.g., pornLib.xvideos)
        submodule = importlib.import_module(f'pornLib.{module_path}')
        
        # Get the client class from the submodule
        client_class = getattr(submodule, class_name)
        
        return client_class()

    except ImportError as e:
        logger.critical(f"{NEON_RED}Failed to import pornLib or its '{engine_name}' client. Error: {e}{RESET_ALL}")
        logger.critical(f"{NEON_RED}Please ensure pornLib is installed and the specific module for '{engine_name}' exists.{RESET_ALL}")
        logger.critical(f"{NEON_RED}Try reinstalling from a reliable source like: {NEON_YELLOW}pip install git+https://github.com/scoutbaker/pornLib.git{RESET_ALL}")
        return None
    except AttributeError as e:
        logger.critical(f"{NEON_RED}AttributeError: Could not find '{class_name}' in '{module_path}' for '{engine_name}'. Error: {e}{RESET_ALL}")
        logger.critical(f"{NEON_RED}This often means the pornLib version is outdated or the class name/structure has changed.{RESET_ALL}")
        return None
    except Exception as e:
        logger.critical(f"{NEON_RED}An unexpected error occurred while loading the '{engine_name}' client: {e}{RESET_ALL}")
        return None

# --- Helper Functions ---
def ensure_directory_exists(directory_path: str):
    """Creates a directory if it doesn't exist."""
    if not os.path.exists(directory_path):
        try:
            os.makedirs(directory_path)
            logger.info(f"{NEON_GREEN}Created directory: {directory_path}{RESET_ALL}")
        except OSError as e:
            logger.error(f"{NEON_RED}Error creating directory {directory_path}: {e}{RESET_ALL}")
            raise # Re-raise the exception if directory creation fails

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a string to be suitable for use as a filename.
    Removes or replaces characters that are problematic in filenames.
    Limits length to avoid issues with max filename length on some OS.
    """
    if not filename:
        return "unknown_title"
    # Remove punctuation and problematic characters, replace spaces with underscores
    filename = re.sub(r'[^\w\s-]', '', filename.lower())
    filename = re.sub(r'[-\s]+', '_', filename).strip('_')
    # Limit length
    max_len = 100 # Max length for the sanitized part
    if len(filename) > max_len:
        filename = filename[:max_len]
    return filename if filename else "sanitized_empty_title"

def download_file(url: str, local_filepath: str, timeout: int = 10) -> bool:
    """
    Downloads a file from a URL to a local path.
    Returns True if successful, False otherwise.
    """
    try:
        logger.debug(f"Attempting to download: {url} to {local_filepath}")
        response = requests.get(url, stream=True, timeout=timeout, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code == 200:
            with open(local_filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logger.info(f"{NEON_GREEN}Successfully downloaded {url} to {local_filepath}{RESET_ALL}")
            return True
        else:
            logger.warning(f"{NEON_YELLOW}Failed to download {url}. Status code: {response.status_code}{RESET_ALL}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"{NEON_RED}Error downloading {url}: {e}{RESET_ALL}")
        return False
    except OSError as e:
        logger.error(f"{NEON_RED}Error saving file to {local_filepath}: {e}{RESET_ALL}")
        return False

# --- PornClient Class ---
class PornClient:
    def __init__(self, engine_name: str, soup_sleep: float = DEFAULT_SOUP_SLEEP):
        self.engine_name = engine_name.lower()
        self.soup_sleep = soup_sleep
        self._client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initializes the specific pornLib client."""
        logger.info(f"{NEON_BLUE}Attempting to initialize client for '{self.engine_name}'...{RESET_ALL}")
        self._client = get_pornlib_client(self.engine_name)
        
        if self._client:
            logger.info(f"{NEON_GREEN}Successfully initialized PornLib Client: engine='{self.engine_name}', soup_sleep={self.soup_sleep:.2f}s{RESET_ALL}")
        else:
            raise RuntimeError(f"Failed to initialize PornLib client for '{self.engine_name}'. Check logs above.{RESET_ALL}")

    def search(self, query: str, limit: int = DEFAULT_SEARCH_LIMIT, page: int = DEFAULT_PAGE_NUMBER):
        """
        Performs a search using the initialized pornLib client.
        Note: The 'page' parameter is often not directly supported by pornLib's search methods.
              It will be logged but not passed to the underlying pornLib search if not supported.
        """
        if not self._client:
            logger.error(f"{NEON_RED}PornLib client not initialized for {self.engine_name}. Cannot perform search.{RESET_ALL}")
            return []

        logger.info(f"{NEON_BLUE}Performing search for query: '{query}' on {self.engine_name}...{RESET_ALL}")

        # Prepare directory for thumbnails for this engine
        engine_thumbnail_dir = os.path.join(THUMBNAILS_DIR, self.engine_name)
        try:
            ensure_directory_exists(engine_thumbnail_dir)
        except Exception as e:
            logger.error(f"{NEON_RED}Could not create thumbnail directory {engine_thumbnail_dir}. Thumbnails will not be downloaded. Error: {e}{RESET_ALL}")
            # Optionally, decide if you want to proceed without thumbnails or halt.
            # For now, we'll proceed and use online URLs.

        try:
            import inspect
            sig = inspect.signature(self._client.search)
            search_kwargs = {'keyword': query, 'limit': limit}
            if 'page' in sig.parameters:
                search_kwargs['page'] = page
                logger.debug(f"PornLib client for '{self.engine_name}' supports 'page' parameter.")
            else:
                logger.warning(f"{NEON_YELLOW}Warning: PornLib client for '{self.engine_name}' does not appear to support a 'page' parameter directly in its search method. Fetching first {limit} results only.{RESET_ALL}")

            logger.debug(f"Attempting search on engine '{self.engine_name}' with params: {search_kwargs}")
            results = self._client.search(**search_kwargs)

            parsed_results = []
            if results:
                for i, item in enumerate(results):
                    if hasattr(item, 'title') and hasattr(item, 'img') and hasattr(item, 'link'):
                        original_img_url = item.img
                        local_img_path = original_img_url # Default to original URL

                        if original_img_url and isinstance(original_img_url, str) and original_img_url.startswith('http'):
                            try:
                                video_title_sanitized = sanitize_filename(item.title if item.title else f"video_{i}")
                                # Try to get extension from URL, default to .jpg
                                img_ext = os.path.splitext(original_img_url)[1]
                                if not img_ext or len(img_ext) > 5: # basic check for valid extension
                                    img_ext = ".jpg"

                                thumbnail_filename = f"{video_title_sanitized}_{i}{img_ext}"
                                local_filepath = os.path.join(engine_thumbnail_dir, thumbnail_filename)

                                # Ensure engine_thumbnail_dir actually exists before downloading
                                if os.path.exists(engine_thumbnail_dir):
                                    if download_file(original_img_url, local_filepath):
                                        # Use relative path for HTML
                                        local_img_path = os.path.join(THUMBNAILS_DIR, self.engine_name, thumbnail_filename)
                                    else:
                                        logger.warning(f"{NEON_YELLOW}Failed to download thumbnail for '{item.title}'. Using original URL.{RESET_ALL}")
                                else:
                                    logger.warning(f"{NEON_YELLOW}Thumbnail directory {engine_thumbnail_dir} not available. Using original URL for '{item.title}'.{RESET_ALL}")

                            except Exception as e: # Catch any error during file path creation or download
                                logger.error(f"{NEON_RED}Error processing thumbnail for '{item.title}': {e}. Using original URL.{RESET_ALL}")

                        parsed_results.append({
                            'title': item.title,
                            'img': local_img_path, # This will be local path if download succeeded, else original URL
                            'link': item.link,
                            'quality': getattr(item, 'quality', 'N/A'),
                            'time': getattr(item, 'time', 'N/A'),
                            'channel_name': getattr(item, 'channel_name', 'N/A'),
                            'channel_link': getattr(item, 'channel_link', '#'),
                        })
                    else:
                        logger.warning(f"{NEON_YELLOW}Skipping unrecognized video item #{i+1} due to missing core attributes (title, img, link). Item type: {type(item)}. Raw item: {item}{RESET_ALL}")
            
            logger.info(f"{NEON_GREEN}Search yielded {len(parsed_results)} parsed results from engine '{self.engine_name}'.{RESET_ALL}")
            return parsed_results
        except Exception as e:
            logger.error(f"{NEON_RED}Error during search on {self.engine_name}: {e}{RESET_ALL}")
            return []

# --- HTML Output Generation ---
def generate_html_output(results, query, engine, search_limit, output_dir=".", prefix_format="{engine}_search_{query_part}_{timestamp}"):
    """
    Generates an HTML file with the search results.
    """
    if not results:
        logger.warning(f"{NEON_YELLOW}No videos found for query '{query}' using engine '{engine}'. No HTML file generated.{RESET_ALL}")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    query_part = query.replace(" ", "_").lower()
    
    filename_prefix = prefix_format.format(engine=engine, query_part=query_part, timestamp=timestamp)
    output_filename = os.path.join(output_dir, f"{filename_prefix}.html")

    os.makedirs(output_dir, exist_ok=True)
    # Ensure THUMBNAILS_DIR exists at the root level where HTML might be, or adjust path logic
    # This is a general ensure, specific engine subdirectories are handled in search
    ensure_directory_exists(THUMBNAILS_DIR)


    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PornLib Search Results for '{query}' on {engine}</title>
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&family=Share+Tech+Mono&display=swap" rel="stylesheet">
        <style>
            @keyframes neon-glow {{
                0%, 100% {{ text-shadow: 0 0 5px #0ff, 0 0 10px #0ff, 0 0 15px #0ff, 0 0 20px #0ff; }}
                50% {{ text-shadow: 0 0 2px #0ff, 0 0 4px #0ff, 0 0 6px #0ff; }}
            }}
            @keyframes border-glow {{
                0% {{ box-shadow: 0 0 5px rgba(0, 255, 255, 0.5), 0 0 10px rgba(0, 255, 255, 0.3); }}
                50% {{ box-shadow: 0 0 2px rgba(0, 255, 255, 0.2), 0 0 4px rgba(0, 255, 255, 0.1); }}
                100% {{ box-shadow: 0 0 5px rgba(0, 255, 255, 0.5), 0 0 10px rgba(0, 255, 255, 0.3); }}
            }}

            body {{
                font-family: 'Share Tech Mono', monospace; /* Techy font */
                background: linear-gradient(to bottom, #1a1a2e, #0a0a1e); /* Dark gradient */
                color: #e0e0e0;
                margin: 0;
                padding: 20px;
                line-height: 1.6;
            }}
            .container {{
                max-width: 1400px;
                margin: 0px auto;
                padding: 30px;
                background-color: #2a2a4a; /* Slightly lighter dark blue */
                border-radius: 12px;
                box-shadow: 0 0 20px rgba(0, 255, 255, 0.6), 0 0 30px rgba(255, 0, 255, 0.4); /* Dual neon glow */
                border: 2px solid #00ffff;
                animation: border-glow 3s infinite alternate;
            }}
            h1, h2 {{
                font-family: 'Orbitron', sans-serif; /* Modern techy font */
                color: #00ffff; /* Neon blue */
                text-align: center;
                margin-bottom: 25px;
                text-shadow: 0 0 8px rgba(0, 255, 255, 0.9);
                animation: neon-glow 2s infinite alternate;
            }}
            h2 {{
                font-size: 1.5em;
                color: #ff69b4; /* Neon pink */
                text-shadow: 0 0 6px rgba(255, 105, 180, 0.7);
            }}
            .search-params {{
                text-align: center;
                margin-bottom: 30px;
                color: #aaffaa; /* Light green */
                font-size: 0.95em;
                border: 1px dashed #00ff00;
                padding: 10px;
                border-radius: 5px;
                background-color: rgba(0, 255, 0, 0.05);
            }}
            .video-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 25px;
                margin-top: 30px;
            }}
            .video-item {{
                background-color: #3a3a5a;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.6);
                transition: transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out, border-color 0.3s ease-in-out;
                border: 2px solid #00aaff; /* Subtle blue border */
            }}
            .video-item:hover {{
                transform: translateY(-8px);
                box-shadow: 0 8px 25px rgba(0, 255, 255, 0.8), 0 8px 35px rgba(255, 0, 255, 0.6);
                border-color: #ff00ff; /* Pink on hover */
            }}
            .video-item img {{
                width: 100%;
                height: 200px;
                object-fit: cover;
                border-bottom: 2px solid #00ffff;
                transition: border-color 0.3s;
            }}
            .video-item:hover img {{
                border-color: #ff00ff;
            }}
            .video-info {{
                padding: 20px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                height: calc(100% - 200px); /* Adjust height based on image */
            }}
            .video-info h3 {{
                margin-top: 0;
                margin-bottom: 15px;
                font-size: 1.2em;
                color: #ff69b4; /* Neon pink for titles */
                line-height: 1.3;
                text-shadow: 0 0 3px rgba(255, 105, 180, 0.5);
            }}
            .video-info a {{
                text-decoration: none;
                color: #ff69b4;
                transition: color 0.2s, text-shadow 0.2s;
            }}
            .video-info a:hover {{
                color: #ffa0d0;
                text-decoration: underline;
                text-shadow: 0 0 5px rgba(255, 160, 208, 0.8);
            }}
            .video-meta {{
                font-size: 0.8em;
                color: #aaa;
                margin-top: 10px;
                display: flex;
                flex-wrap: wrap;
                gap: 5px;
            }}
            .video-meta span {{
                background-color: rgba(0, 255, 255, 0.1);
                padding: 4px 8px;
                border-radius: 4px;
                border: 1px solid rgba(0, 255, 255, 0.3);
                white-space: nowrap;
            }}
            .video-meta .quality {{ color: #00ff00; font-weight: bold; }} /* Bright green */
            .video-meta .time {{ color: #ffff00; }} /* Bright yellow */
            .video-meta .channel a {{ color: #8a2be2; text-decoration: none; }} /* Blue Violet */
            .video-meta .channel a:hover {{ text-decoration: underline; color: #b19cd9; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Neon Search Results</h1>
            <h2>Query: '{query}' on {engine}</h2>
            <div class="search-params">
                <strong>Engine:</strong> {engine} |
                <strong>Query:</strong> {query} |
                <strong>Limit:</strong> {search_limit} Videos
            </div>
            <div class="video-grid">
    """

    for video in results:
        title = video.get('title', 'N/A')
        img = video.get('img', 'https://via.placeholder.com/300x200?text=No+Image')
        link = video.get('link', '#')
        quality = video.get('quality', 'N/A')
        video_time = video.get('time', 'N/A')
        channel_name = video.get('channel_name', 'N/A')
        channel_link = video.get('channel_link', '#')

        html_content += f"""
                <div class="video-item">
                    <a href="{link}" target="_blank" rel="noopener noreferrer">
                        <img src="{img}" alt="{title}" onerror="this.onerror=null; this.src='https://via.placeholder.com/300x200?text=Image+Error';">
                    </a>
                    <div class="video-info">
                        <h3><a href="{link}" target="_blank" rel="noopener noreferrer">{title}</a></h3>
                        <div class="video-meta">
                            {f'<span class="quality">Quality: {quality}</span>' if quality and quality != 'N/A' else ''}
                            {f'<span class="time">Time: {video_time}</span>' if video_time and video_time != 'N/A' else ''}
                            {f'<span class="channel">Channel: <a href="{channel_link}" target="_blank" rel="noopener noreferrer">{channel_name}</a></span>' if channel_name and channel_name != 'N/A' else ''}
                        </div>
                    </div>
                </div>
        """
    # Small fix for image onerror handling in case a local path is broken or an online URL also fails client-side.
    # The path logic in generate_html_output assumes that if item['img'] is a local path,
    # it's relative to the project root (e.g., "downloaded_thumbnails/engine/file.jpg").
    # If the HTML file is in `output_dir` (e.g. "./output/"), and THUMBNAILS_DIR is at root,
    # paths like "../downloaded_thumbnails/engine/file.jpg" might be needed if output_dir is not "."
    # However, the current generate_html_output saves HTML to output_dir (default '.'),
    # so paths like "downloaded_thumbnails/[engine]/[file].jpg" should work if THUMBNAILS_DIR
    # is in the same root as the script and where HTML is generated.
    # The current implementation of local_img_path is already relative like "downloaded_thumbnails/xvideos/title.jpg"
    # This should work fine if the HTML is generated in the project root.
    # If HTML is in a subfolder (e.g. `results/`), then image paths would need to be `../downloaded_thumbnails/...`
    # For now, assuming HTML and downloaded_thumbnails are siblings or HTML is at root.

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

# --- Main Script Logic ---
def main():
    logger.info(f"{NEON_CYAN}{NEON_BRIGHT}--- Starting PornLib Search Script (Interactive Mode) ---{RESET_ALL}")

    query = input(f"{NEON_YELLOW}Enter search query: {RESET_ALL}{NEON_BRIGHT}")
    if not query:
        logger.critical(f"{NEON_RED}Search query cannot be empty. Exiting.{RESET_ALL}")
        sys.exit(1)
    
    # Input validation for search_limit
    try:
        limit_input = input(f"{NEON_YELLOW}Max results to fetch? [{DEFAULT_SEARCH_LIMIT}]: {RESET_ALL}{NEON_BRIGHT}")
        search_limit = int(limit_input) if limit_input.strip() else DEFAULT_SEARCH_LIMIT
        logger.debug(f"User selected search limit: {search_limit}")
        if search_limit <= 0:
            raise ValueError("Search limit must be a positive number.")
    except ValueError as e:
        logger.error(f"{NEON_RED}Invalid search limit: {e}. Using default: {DEFAULT_SEARCH_LIMIT}{RESET_ALL}")
        search_limit = DEFAULT_SEARCH_LIMIT

    # Input validation for page_number
    try:
        page_input = input(f"{NEON_YELLOW}Page number? [{DEFAULT_PAGE_NUMBER}] (Note: May not be supported by all engines): {RESET_ALL}{NEON_BRIGHT}")
        page_number = int(page_input) if page_input.strip() else DEFAULT_PAGE_NUMBER
        logger.debug(f"User selected page number: {page_number}")
        if page_number <= 0:
            raise ValueError("Page number must be a positive number.")
    except ValueError as e:
        logger.error(f"{NEON_RED}Invalid page number: {e}. Using default: {DEFAULT_PAGE_NUMBER}{RESET_ALL}")
        page_number = DEFAULT_PAGE_NUMBER

    # Engine selection
    available_engines = ', '.join(ENGINE_MODULE_MAP.keys())
    engine_input = input(f"{NEON_YELLOW}PornLib engine? [{DEFAULT_ENGINE}] (Options: {available_engines}): {RESET_ALL}{NEON_BRIGHT}")
    engine = engine_input.lower().strip() if engine_input.strip() else DEFAULT_ENGINE
    logger.debug(f"User selected engine: {engine}")

    if engine not in ENGINE_MODULE_MAP:
        logger.critical(f"{NEON_RED}Unsupported engine '{engine}'. Please choose from: {available_engines}{RESET_ALL}")
        sys.exit(1)

    # Input validation for soup_sleep
    try:
        soup_sleep_input = input(f"{NEON_YELLOW}Soup sleep (seconds)? [{DEFAULT_SOUP_SLEEP}]: {RESET_ALL}{NEON_BRIGHT}")
        soup_sleep = float(soup_sleep_input) if soup_sleep_input.strip() else DEFAULT_SOUP_SLEEP
        logger.debug(f"User selected soup sleep: {soup_sleep}")
        if soup_sleep < 0:
            raise ValueError("Soup sleep cannot be negative.")
    except ValueError as e:
        logger.error(f"{NEON_RED}Invalid soup sleep value: {e}. Using default: {DEFAULT_SOUP_SLEEP}{RESET_ALL}")
        soup_sleep = DEFAULT_SOUP_SLEEP

    # Output directory
    output_dir_input = input(f"{NEON_YELLOW}Output directory? [.]: {RESET_ALL}{NEON_BRIGHT}")
    output_dir = output_dir_input.strip() if output_dir_input.strip() else "."
    logger.debug(f"User selected output directory: {output_dir}")

    # Filename prefix format
    default_prefix_format = "{engine}_search_{query_part}_{timestamp}"
    filename_prefix_format_input = input(f"{NEON_YELLOW}Filename prefix format? [{default_prefix_format}]: {RESET_ALL}{NEON_BRIGHT}")
    filename_prefix_format = filename_prefix_format_input.strip() if filename_prefix_format_input.strip() else default_prefix_format
    logger.debug(f"User selected filename prefix format: {filename_prefix_format}")

    # Auto-open HTML
    auto_open_input = input(f"{NEON_YELLOW}Auto-open HTML file (y/n)? [y]: {RESET_ALL}{NEON_BRIGHT}")
    auto_open_html = auto_open_input.lower().strip() in ('y', 'yes', '')
    logger.debug(f"User selected auto-open HTML: {auto_open_html}")

    logger.info(f"{NEON_CYAN}--- Settings Summary ---{RESET_ALL}")
    logger.info(f"  {NEON_BLUE}Engine:{RESET_ALL} {engine}")
    logger.info(f"  {NEON_BLUE}Query:{RESET_ALL} '{query}'")
    logger.info(f"  {NEON_BLUE}Limit:{RESET_ALL} {search_limit}")
    logger.info(f"  {NEON_BLUE}Page:{RESET_ALL} {page_number} (Note: May not be used by pornLib search)")
    logger.info(f"  {NEON_BLUE}Output Dir:{RESET_ALL} '{output_dir}'")
    logger.info(f"  {NEON_BLUE}Auto-open HTML:{RESET_ALL} {auto_open_html}")
    logger.info(f"{NEON_CYAN}------------------------{RESET_ALL}")

    client = None
    try:
        client = PornClient(engine_name=engine, soup_sleep=soup_sleep)
    except RuntimeError:
        logger.critical(f"{NEON_RED}Exiting due to critical client initialization failure.{RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"{NEON_RED}An unexpected error occurred during client initialization: {e}. Exiting.{RESET_ALL}")
        sys.exit(1)

    try:
        results = client.search(query=query, limit=search_limit, page=page_number)
        html_file = generate_html_output(results, query, engine, search_limit, output_dir, filename_prefix_format)

        if html_file and auto_open_html:
            logger.info(f"{NEON_MAGENTA}Attempting to open {html_file} in your default browser...{RESET_ALL}")
            try:
                webbrowser.open(f"file://{os.path.abspath(html_file)}")
            except webbrowser.Error:
                logger.error(f"{NEON_RED}Could not open browser. Please ensure a web browser is configured and accessible, or open the file manually: {NEON_WHITE}{os.path.abspath(html_file)}{RESET_ALL}")
            except Exception as e:
                logger.error(f"{NEON_RED}Failed to open HTML file in browser: {e}. You can open it manually: {NEON_WHITE}{os.path.abspath(html_file)}{RESET_ALL}")
        elif html_file:
            logger.info(f"{NEON_BLUE}HTML file generated: {NEON_WHITE}{os.path.abspath(html_file)}{RESET_ALL}")
    except Exception as e:
        logger.critical(f"{NEON_RED}An unhandled error occurred during search or HTML generation: {e}{RESET_ALL}")

    logger.info(f"{NEON_CYAN}{NEON_BRIGHT}--- Script Finished. Have a productive day! 😻 ---{RESET_ALL}")

if __name__ == "__main__":
    main()
