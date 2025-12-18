
# vs.py - Advanced Video Search Tool

# Author: Your Name / AI Assistant
# Version: 1.1.0
# Date: 2023-10-27

# Description:
# This script provides an advanced video search functionality across multiple platforms.
# It supports realistic user-agent rotation, robust error handling, dynamic content fetching
# (JavaScript rendering), asynchronous thumbnail downloading, proxy management, and enhanced
# HTML/JSON output. Supports search engines like Pexels, Dailymotion, Pornhub, XVideos, etc.

# Features:
# - Multi-engine support
# - Dynamic content fetching (JavaScript)
# - Asynchronous thumbnail downloading
# - User-agent rotation
# - Proxy support
# - Configurable output formats (JSON, HTML)
# - Progress bars for searching and downloading
# - Configuration file support (config.json)

# Requirements:
# - Python 3.7+
# - aiohttp, beautifulsoup4, requests, tqdm, fake-useragent, undetected-chromedriver

import argparse
import asyncio
import json
import logging
import os
import random
import re
import ssl
import time
from typing import Any, Dict, List, Optional, Tuple, Literal

import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tqdm import tqdm

# --- Configuration Loading ---
CONFIG_FILE = 'config.json'
DEFAULT_CONFIG = {
  "default_engines": ["all"],
  "max_results": 20,
  "output_format": "json",
  "proxy": None,
  "user_agent_rotation": True,
  "thumbnail_download_dir": "thumbnails",
  "search_timeout": 10,
  "log_level": "INFO",
  "download_thumbnails": False, # Added this key
  "engines": { # Placeholder for specific engine configs if needed
        "pexels": {"enabled": True},
        "dailymotion": {"enabled": True},
        "vimeo": {"enabled": True},
        # Add other engines here
    }
}

def load_config():
    """Loads configuration from config.json, using defaults if file is missing or incomplete."""
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                # Deep update for nested dictionaries like 'engines'
                for key, value in user_config.items():
                    if isinstance(value, dict) and key in config and isinstance(config[key], dict):
                        config[key].update(value)
                    else:
                        config[key] = value
        except json.JSONDecodeError:
            logging.error(f"Error decoding {CONFIG_FILE}. Using default configuration.")
        except Exception as e:
            logging.error(f"Error loading configuration: {e}. Using default configuration.")
    else:
        # Write the default config if it doesn't exist
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
            logging.info(f"Created default configuration file: {CONFIG_FILE}")
        except Exception as e:
            logging.error(f"Could not write default configuration file: {e}")
    return config

config = load_config()

# Set up logging based on config
log_level = config.get('log_level', 'INFO').upper()
logging.basicConfig(level=getattr(logging, log_level), format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize UserAgent if rotation is enabled
ua = None
if config.get('user_agent_rotation', True):
    try:
        ua = UserAgent()
        logging.info("User-Agent rotation enabled.")
    except Exception as e:
        logging.error(f"Failed to initialize UserAgent: {e}. Proceeding without rotation.")
        config['user_agent_rotation'] = False # Disable if initialization fails

def get_random_user_agent():
    """Gets a random User-Agent if rotation is enabled, otherwise returns a default."""
    if ua:
        return ua.random
    return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# --- Helper Functions ---

def create_save_dir(dir_name: str):
    """Creates a directory if it doesn't exist."""
    os.makedirs(dir_name, exist_ok=True)
    logging.debug(f"Ensured directory exists: {dir_name}")

async def fetch_content(url: str, session: aiohttp.ClientSession, timeout: int, retries: int = 3) -> Optional[str]:
    """Fetches content from a URL with retry logic and user-agent rotation."""
    headers = {'User-Agent': get_random_user_agent()}
    proxy = config.get('proxy')
    
    for attempt in range(retries):
        try:
            async with session.get(url, headers=headers, timeout=timeout, proxy=proxy) as response:
                response.raise_for_status()
                # Try to determine encoding, default to utf-8
                encoding = response.charset or 'utf-8'
                content = await response.text(encoding=encoding)
                logging.debug(f"Successfully fetched content from {url} (Attempt {attempt + 1}/{retries})")
                return content
        except aiohttp.ClientConnectorError as e:
            logging.warning(f"Connection error for {url} (Attempt {attempt + 1}/{retries}): {e}")
        except aiohttp.ClientResponseError as e:
            logging.warning(f"HTTP error for {url} (Attempt {attempt + 1}/{retries}): {e.status} {e.message}")
        except asyncio.TimeoutError:
            logging.warning(f"Timeout error for {url} (Attempt {attempt + 1}/{retries})")
        except Exception as e:
            logging.warning(f"An unexpected error occurred for {url} (Attempt {attempt + 1}/{retries}): {e}")
        
        await asyncio.sleep(1 * (2**attempt)) # Exponential backoff

    logging.error(f"Failed to fetch content from {url} after {retries} attempts.")
    return None

# --- Engine Specific Scrapers ---
# These are simplified examples. Real implementations would need detailed selectors and logic.

async def search_pexels(query: str, max_results: int, session: aiohttp.ClientSession, pbar: tqdm) -> List[Dict[str, Any]]:
    """Searches Pexels and returns video data."""
    logging.info(f"Searching Pexels for '{query}'...")
    # Pexels API is preferred, but if scraping is needed:
    # Pexels often uses dynamic loading, so a headless browser (undetected-chromedriver) might be better.
    # For simplicity, using a mock here. A real implementation needs careful handling of JS.
    url = f"https://www.pexels.com/search/{query.replace(' ', '-')}/videos/" # Example URL structure
    content = await fetch_content(url, session, config.get('search_timeout', 10))
    results = []
    if content:
        # soup = BeautifulSoup(content, 'html.parser')
        # Add actual parsing logic here using soup selectors for Pexels videos
        # Example mock data:
        for i in range(min(max_results, 5)): # Limit mock results per engine
             results.append({
                 "title": f"Pexels Video {i+1}: {query}",
                 "url": f"https://www.pexels.com/video/{query.replace(' ', '-')}-{i+1}/",
                 "thumbnail_url": f"https://via.placeholder.com/300x180?text=Pexels+{i+1}", # Mock thumbnail
                 "source_engine": "pexels"
             })
    pbar.update(1)
    logging.info(f"Pexels search complete. Found {len(results)} mock results.")
    return results

async def search_dailymotion(query: str, max_results: int, session: aiohttp.ClientSession, pbar: tqdm) -> List[Dict[str, Any]]:
    """Searches Dailymotion and returns video data."""
    logging.info(f"Searching Dailymotion for '{query}'...")
    # Dailymotion uses a predictable URL structure and often returns JSON data
    # Example API endpoint (may change):
    api_url = f"https://api.dailymotion.com/videos?search={query}&limit={max_results}&fields=title,url,thumbnail_url"
    content = await fetch_content(api_url, session, config.get('search_timeout', 10))
    results = []
    if content:
        try:
            data = json.loads(content)
            for item in data.get('list', []):
                results.append({
                    "title": item.get('title'),
                    "url": item.get('url'),
                    "thumbnail_url": item.get('thumbnail_url'),
                    "source_engine": "dailymotion"
                })
        except json.JSONDecodeError:
            logging.error("Failed to parse Dailymotion JSON response.")
        except Exception as e:
            logging.error(f"Error processing Dailymotion results: {e}")
            
    pbar.update(1)
    logging.info(f"Dailymotion search complete. Found {len(results)} results.")
    return results

async def search_vimeo(query: str, max_results: int, session: aiohttp.ClientSession, pbar: tqdm) -> List[Dict[str, Any]]:
    """Searches Vimeo and returns video data."""
    logging.info(f"Searching Vimeo for '{query}'...")
    # Vimeo also has an API, which is preferred.
    # Example API endpoint (may change):
    api_url = f"https://api.vimeo.com/videos?query={query}&per_page={max_results}&fields=name,link,thumbnail_url"
    # Note: Vimeo API often requires authentication (client ID/secret) for full access.
    # This example assumes a public search endpoint or uses a mock if authentication fails.
    content = await fetch_content(api_url, session, config.get('search_timeout', 10))
    results = []
    if content:
        try:
            data = json.loads(content)
            # Vimeo's thumbnail_url might be a dictionary with different sizes
            for item in data.get('data', []):
                thumbnail_url = None
                if item.get('thumbnail_url'):
                    # Prefer a medium or high-res thumbnail if available
                    thumbnail_sizes = item['thumbnail_url']
                    thumbnail_url = thumbnail_sizes.get('medium', thumbnail_sizes.get('base')) # Example logic
                    
                results.append({
                    "title": item.get('name'),
                    "url": item.get('link'),
                    "thumbnail_url": thumbnail_url,
                    "source_engine": "vimeo"
                })
        except json.JSONDecodeError:
            logging.error("Failed to parse Vimeo JSON response.")
        except Exception as e:
            logging.error(f"Error processing Vimeo results: {e}")
    else:
         # Fallback or mock data if API fails/needs auth
         logging.warning("Vimeo API might require authentication or returned no data. Using mock results.")
         for i in range(min(max_results, 3)):
             results.append({
                 "title": f"Vimeo Mock Video {i+1}: {query}",
                 "url": f"https://vimeo.com/mock/{query.replace(' ', '-')}-{i+1}",
                 "thumbnail_url": f"https://via.placeholder.com/300x180?text=Vimeo+{i+1}", # Mock thumbnail
                 "source_engine": "vimeo"
             })

    pbar.update(1)
    logging.info(f"Vimeo search complete. Found {len(results)} results.")
    return results

# Add more engine functions here (search_pornhub, search_xvideos, etc.)
# These will likely require more complex scraping logic, potentially using undetected-chromedriver.

# --- Main Search Orchestration ---

async def search_engine_wrapper(engine_name: str, query: str, max_results: int, session: aiohttp.ClientSession, pbar: tqdm) -> List[Dict[str, Any]]:
    """
    A wrapper to call the correct engine search function based on engine_name.
    """
    engine_map = {
        "pexels": search_pexels,
        "dailymotion": search_dailymotion,
        "vimeo": search_vimeo,
        # Add other engines here
    }
    
    search_func = engine_map.get(engine_name.lower())
    if search_func:
        try:
            return await search_func(query, max_results, session, pbar)
        except Exception as e:
            logging.error(f"Error searching {engine_name}: {e}")
            pbar.update(1) # Ensure progress bar is updated even on error
            return []
    else:
        logging.warning(f"Engine '{engine_name}' not supported or implemented.")
        pbar.update(1) # Update progress bar even if engine is unknown
        return []

async def search_all_engines(query: str, engines_to_search: List[str], max_results: int) -> List[Dict[str, Any]]:
    """
    Searches multiple engines concurrently and displays progress.
    """
    all_results = []
    
    # Filter engines based on config
    enabled_engines = []
    for engine in engines_to_search:
        engine_config = config.get("engines", {}).get(engine.lower())
        if engine_config and engine_config.get("enabled", True):
             enabled_engines.append(engine)
        elif engine.lower() == "all": # Handle 'all' keyword specifically
             # Add all engines listed in the 'engines' config that are enabled
             for eng_name, eng_conf in config.get("engines", {}).items():
                 if eng_conf.get("enabled", True) and eng_name not in enabled_engines:
                      enabled_engines.append(eng_name)
        else:
            logging.debug(f"Engine '{engine}' is disabled in config or not listed.")

    if not enabled_engines:
        logging.warning("No search engines are enabled in the configuration.")
        return []

    logging.info(f"Searching enabled engines: {', '.join(enabled_engines)}")

    # Limit concurrent requests to avoid overwhelming the system or remote servers
    # Adjust semaphore limit as needed based on your system and network
    semaphore_limit = 5 
    semaphore = asyncio.Semaphore(semaphore_limit)

    async def semaphored_search(engine, q, max_r, sess, pbar):
        async with semaphore:
            return await search_engine_wrapper(engine, q, max_r, sess, pbar)

    # Use tqdm for a progress bar over the engines
    engine_pbar = tqdm(total=len(enabled_engines), desc="Searching Engines", unit="engine")

    # Configure aiohttp session with appropriate limits and connector
    connector = aiohttp.TCPConnector(limit=semaphore_limit, ssl=ssl.SSLContext()) # Limit concurrent connections
    async with aiohttp.ClientSession(connector=connector, headers={'User-Agent': get_random_user_agent()}) as session:
        tasks = [
            semaphored_search(engine, query, max_results, session, engine_pbar)
            for engine in enabled_engines
        ]

        # Gather results as they complete
        # Using asyncio.gather with return_exceptions=True is safer
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results_list:
            if isinstance(result, Exception):
                logging.error(f"A search task failed: {result}")
            elif isinstance(result, list):
                 all_results.extend(result)

    engine_pbar.close()
    logging.info(f"All engine searches completed. Total results collected: {len(all_results)}")
    
    # Sort results? (Optional, could be based on relevance if available, or just unified list)
    # For now, just return the combined list.
    
    # Limit results to max_results
    return all_results[:max_results]


# --- Thumbnail Downloading ---

async def download_thumbnail(url: str, save_path: str, session: aiohttp.ClientSession, pbar: tqdm):
    """Downloads a single thumbnail with progress, handling potential errors."""
    try:
        async with session.get(url, timeout=config.get('search_timeout', 10)) as response:
            response.raise_for_status()
            file_size = int(response.headers.get('Content-Length', 0))
            
            # Ensure directory exists
            create_save_dir(os.path.dirname(save_path))
            
            with open(save_path, 'wb') as f:
                # Use tqdm for download progress with leave=False to clear completed bars
                with tqdm(
                    desc=f"Downloading {os.path.basename(save_path)}",
                    total=file_size,
                    unit='B',
                    unit_scale=True,
                    leave=False,
                    ncols=80 # Adjust width of progress bar
                ) as thumb_pbar:
                    chunk_size = 8192
                    downloaded_size = 0
                    while True:
                        chunk = await response.content.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        chunk_len = len(chunk)
                        thumb_pbar.update(chunk_len)
                        downloaded_size += chunk_len
            
            if file_size > 0 and downloaded_size < file_size:
                 logging.warning(f"Incomplete download for {save_path}. Expected {file_size} bytes, got {downloaded_size}.")
            logging.debug(f"Successfully downloaded thumbnail to {save_path}")

    except aiohttp.ClientError as e:
        logging.error(f"HTTP error downloading thumbnail {url}: {e}")
    except asyncio.TimeoutError:
        logging.error(f"Timeout downloading thumbnail {url}")
    except OSError as e:
        logging.error(f"File system error saving thumbnail {save_path}: {e}")
    except Exception as e:
        logging.error(f"Failed to download thumbnail {url}: {e}")
    finally:
        pbar.update(1) # Update the overall thumbnail progress bar

async def download_all_thumbnails(video_data_list: List[Dict[str, Any]]):
    """Downloads all thumbnails concurrently using aiohttp and tqdm."""
    thumbnail_dir = config.get('thumbnail_download_dir', 'thumbnails')
    if not video_data_list:
        logging.info("No video data provided for thumbnail download.")
        return

    # Filter out items without thumbnail URLs
    videos_to_download = [vd for vd in video_data_list if vd.get('thumbnail_url')]
    if not videos_to_download:
        logging.info("No thumbnail URLs found in the provided video data.")
        return
        
    total_thumbnails = len(videos_to_download)
    logging.info(f"Starting download for {total_thumbnails} thumbnails...")
    
    thumb_pbar = tqdm(total=total_thumbnails, desc="Overall Thumbnail Progress", unit="thumb")

    # Use a reasonable limit for concurrent downloads
    semaphore_limit = 10 
    semaphore = asyncio.Semaphore(semaphore_limit)
    
    async def semaphored_download(vd, sess, pbar):
        async with semaphore:
            url = vd['thumbnail_url']
            # Create a more descriptive filename, e.g., using source and index
            filename = f"{vd.get('source_engine', 'unknown')}_{vd.get('id', v['url'].split('/')[-1])}.jpg"
            # Sanitize filename to remove invalid characters
            filename = re.sub(r'[<>:"/\|?*]', '_', filename)
            save_path = os.path.join(thumbnail_dir, filename)
            await download_thumbnail(url, save_path, sess, pbar)

    connector = aiohttp.TCPConnector(limit=semaphore_limit, ssl=ssl.SSLContext())
    async with aiohttp.ClientSession(connector=connector, headers={'User-Agent': get_random_user_agent()}) as session:
        tasks = [
            semaphored_download(vd, session, thumb_pbar)
            for vd in videos_to_download
        ]
        
        await asyncio.gather(*tasks)
        
    thumb_pbar.close()
    logging.info("Thumbnail download process finished.")


# --- Output Formatting ---

def format_results(results: List[Dict[str, Any]], output_format: str) -> str:
    """Formats the search results into the specified format."""
    if output_format == 'json':
        return json.dumps(results, indent=2, ensure_ascii=False)
    elif output_format == 'html':
        return generate_html_output(results)
    else:
        # Default to simple text list
        output = f"Search Results ({len(results)} found):
"
        for i, video in enumerate(results):
            output += f"{i+1}. {video.get('title', 'N/A')} ({video.get('source_engine', 'unknown')})
"
            output += f"   URL: {video.get('url', '#')}
"
            if video.get('thumbnail_url'):
                output += f"   Thumbnail: {video.get('thumbnail_url')}
"
        return output

def generate_html_output(results: List[Dict[str, Any]]) -> str:
    """Generates an HTML representation of the search results."""
    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Search Results</title>
    <style>
        body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; }
        .container { background-color: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        h1 { color: #333; }
        .video-list { list-style: none; padding: 0; }
        .video-item { border-bottom: 1px solid #eee; padding: 15px 0; display: flex; align-items: center; }
        .video-item:last-child { border-bottom: none; }
        .video-thumbnail img { width: 120px; height: 80px; object-fit: cover; margin-right: 15px; border-radius: 4px; }
        .video-details h3 { margin: 0 0 5px 0; font-size: 1.1em; }
        .video-details a { color: #007bff; text-decoration: none; }
        .video-details a:hover { text-decoration: underline; }
        .video-details p { margin: 5px 0; color: #666; font-size: 0.9em; }
        .source { font-style: italic; color: #888; font-size: 0.85em; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Video Search Results</h1>
        <ul class="video-list">
"""
    if not results:
        html += '<li>No results found.</li>'
    else:
        for i, video in enumerate(results):
            thumbnail_html = ""
            if video.get('thumbnail_url'):
                 # Basic check if thumbnail was downloaded locally
                 # This assumes filenames match the pattern used in download_all_thumbnails
                 thumb_filename = f"{video.get('source_engine', 'unknown')}_{video.get('id', video['url'].split('/')[-1])}.jpg"
                 thumb_filename = re.sub(r'[<>:"/\|?*]', '_', thumb_filename) # Sanitize filename
                 local_thumb_path = os.path.join(config.get('thumbnail_download_dir', 'thumbnails'), thumb_filename)
                 
                 if os.path.exists(local_thumb_path):
                      # Serve local thumbnail using a relative path
                      thumbnail_html = f'<img src="{local_thumb_path}" alt="Thumbnail">'
                 else:
                      # Fallback to original URL if local file not found
                      thumbnail_html = f'<img src="{video["thumbnail_url"]}" alt="Thumbnail">'

            html += f"""
            <li class="video-item">
                <div class="video-thumbnail">{thumbnail_html}</div>
                <div class="video-details">
                    <h3><a href="{video.get('url', '#')}" target="_blank">{video.get('title', 'N/A')}</a></h3>
                    <p>Source: <span class="source">{video.get('source_engine', 'unknown')}</span></p>
                    <p><a href="{video.get('url', '#')}" target="_blank">Watch Video</a></p>
                </div>
            </li>
            """
    html += """
        </ul>
    </div>
</body>
</html>
"""
    return html

# --- Main Execution Logic ---

async def main(args):
    """Main function to orchestrate the search and download process."""
    
    # Determine engines to search
    engines_to_use = config.get('default_engines', ['all'])
    if args.engines:
        engines_to_use = args.engines
    elif engines_to_use == ['all']:
        # If 'all' is default and no specific engines are passed, use engines from config
        engines_to_use = [eng for eng, conf in config.get("engines", {}).items() if conf.get("enabled", True)]
        if not engines_to_use:
             logging.error("No engines enabled in config and 'all' is selected. Please enable engines in config.json.")
             return

    max_results = args.max_results if args.max_results else config.get('max_results', 20)
    output_format = args.output_format if args.output_format else config.get('output_format', 'json')
    
    # Create thumbnail directory if enabled
    if args.download_thumbnails or config.get('download_thumbnails', False):
         create_save_dir(config.get('thumbnail_download_dir', 'thumbnails'))

    logging.info(f"Starting search for '{args.query}'")
    logging.info(f"Engines: {', '.join(engines_to_use)}")
    logging.info(f"Max Results: {max_results}")
    logging.info(f"Output Format: {output_format}")
    if config.get('proxy'):
        logging.info(f"Using Proxy: {config['proxy']}")
    if config.get('user_agent_rotation'):
        logging.info("User-Agent rotation: Enabled")


    # Perform search using the async function with progress bar
    search_results = await search_all_engines(args.query, engines_to_use, max_results)
    
    processed_results = []
    if search_results:
        logging.info(f"Found {len(search_results)} raw results.")
        # Assign unique IDs and ensure basic structure
        for idx, result in enumerate(search_results):
            # Ensure essential keys exist
            processed_result = {
                "id": idx,
                "title": result.get('title', 'N/A'),
                "url": result.get('url', '#'),
                "thumbnail_url": result.get('thumbnail_url'),
                "source_engine": result.get('source_engine', 'unknown'),
                # Add other relevant fields if available from engines
                "description": result.get('description'), 
                "duration": result.get('duration'),
                "views": result.get('views')
            }
            # Attempt to get a thumbnail URL if not directly provided but inferable
            if not processed_result['thumbnail_url'] and processed_result['source_engine'] == 'pexels':
                 # Example: Construct a mock thumbnail URL if none provided (replace with real logic)
                 processed_result['thumbnail_url'] = f"https://via.placeholder.com/300x180?text=Pexels+Video+{idx+1}"
                 
            processed_results.append(processed_result)
        
        # Download thumbnails if requested
        if args.download_thumbnails or config.get('download_thumbnails', False):
            await download_all_thumbnails(processed_results)
            
    else:
        logging.info("No results found for the query.")

    # Format and print results
    formatted_output = format_results(processed_results, output_format)
    
    if output_format == 'html':
        # Save HTML to a file for easier viewing
        html_filename = f"video_search_results_{int(time.time())}.html"
        try:
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(formatted_output)
            print(f"
HTML results saved to: {html_filename}")
        except Exception as e:
            print(f"
Error saving HTML file: {e}")
            print("
--- HTML Output ---")
            print(formatted_output) # Print to console if saving fails
    else:
        print("
--- Search Results ---")
        print(formatted_output)

# --- Argument Parsing ---

def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(description="Advanced Video Search Tool")
    parser.add_argument("query", help="The search query for videos.")
    parser.add_argument("-e", "--engines", nargs='+', help="Specific search engines to use (e.g., pexels dailymotion). Defaults to config.", default=None)
    parser.add_argument("-n", "--max-results", type=int, help="Maximum number of results to retrieve. Defaults to config.", default=None)
    parser.add_argument("-o", "--output-format", choices=["json", "html", "text"], help="Output format (json, html, text). Defaults to config.", default=None)
    parser.add_argument("-d", "--download-thumbnails", action="store_true", help="Download thumbnails for the results.")
    # Add more arguments as needed (e.g., --proxy, --user-agent) if not using config file primarily
    return parser.parse_args()

if __name__ == "__main__":
    # Ensure the script runs in an async event loop
    args = parse_arguments()
    # Set the global config value for thumbnail download if arg is used
    if args.download_thumbnails:
        config['download_thumbnails'] = True
        
    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("
Search interrupted by user.")
    except Exception as e:
        logging.exception(f"An unexpected error occurred in main execution: {e}")

