import datetime
import html
import importlib  # For dynamic module importing
import inspect  # For checking function signatures
import logging
import sys
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

# Assuming ratelimit is installed
from ratelimit import limits, sleep_and_retry  # type: ignore

# Static imports for pornLib clients will be removed and handled dynamically.

# Engine mapping for dynamic import
ENGINE_MODULE_MAP = {
    'xvideos': {'module': 'xvideos', 'class': 'XVideos'},
    'pornhub': {'module': 'pornhub', 'class': 'Pornhub'},
    'redtube': {'module': 'redtube', 'class': 'Redtube'},
    'youporn': {'module': 'youporn', 'class': 'Youporn'},
}

# ==============================================================================
# Dynamic PornLib Client Loader
# ==============================================================================
def _get_pornlib_client_dynamically(engine_name: str) -> Optional[Any]:
    """
    Dynamically imports and returns the pornLib client for the specified engine.
    Assumes 'scoutbaker/pornLib' is installed and its modules (xvideos, pornhub, etc.)
    are directly importable.
    Returns the client instance or None on failure.
    """
    engine_name_lower = engine_name.lower()
    if engine_name_lower not in ENGINE_MODULE_MAP:
        logger.critical(f"Unsupported engine: {engine_name}. Supported are: {', '.join(ENGINE_MODULE_MAP.keys())}")
        return None

    engine_details = ENGINE_MODULE_MAP[engine_name_lower]
    module_to_import = engine_details['module']
    class_to_instantiate = engine_details['class']

    try:
        logger.debug(f"Dynamically importing module: '{module_to_import}' for engine '{engine_name}'")
        # Attempt to import the module directly (e.g., 'xvideos', 'pornhub')
        client_module = importlib.import_module(module_to_import)
        
        logger.debug(f"Getting class '{class_to_instantiate}' from module '{module_to_import}'")
        ClientClass = getattr(client_module, class_to_instantiate)
        
        logger.info(f"Successfully loaded class '{class_to_instantiate}' from '{module_to_import}'. Instantiating client.")
        return ClientClass()

    except ImportError as e:
        logger.critical(f"Failed to import module '{module_to_import}' for engine '{engine_name}'. Error: {e}")
        logger.critical(
            f"Please ensure '{module_to_import}' from 'scoutbaker/pornLib' is installed and accessible in your Python path. "
            f"Also, verify that the module name in xvid.py's ENGINE_MODULE_MAP ('{module_to_import}') "
            f"matches the actual module name from your pornLib version."
        )
        return None
    except AttributeError as e:
        logger.critical(f"AttributeError: Could not find class '{class_to_instantiate}' in module '{module_to_import}' for engine '{engine_name}'. Error: {e}")
        logger.critical(f"This might indicate an outdated/changed version of the '{module_to_import}' client from 'scoutbaker/pornLib'.")
        return None
    except Exception as e:
        logger.critical(f"An unexpected error occurred while dynamically loading client for '{engine_name}': {e}", exc_info=True)
        return None

# ==============================================================================
# Configuration
# ==============================================================================

# Configure logging for better debugging in Termux
LOG_LEVEL = logging.DEBUG
logging.basicConfig(
    level=LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

API_CALLS_LIMIT = 50
API_PERIOD_SECONDS = 60

DEFAULT_OUTPUT_DIR_STR = "."
DEFAULT_SEARCH_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_ENGINE = "xvideos"
# VALID_ENGINES will be derived from ENGINE_MODULE_MAP.keys() for consistency
VALID_ENGINES = list(ENGINE_MODULE_MAP.keys())
DEFAULT_SOUP_SLEEP = 1.0 # This parameter is passed to PornClient but internal pornLib clients handle actual sleep.
DEFAULT_FILENAME_PREFIX = "{engine}_search_{query_part}_{timestamp}"
DEFAULT_AUTO_OPEN = 'y'

# Fallback image for failed thumbnails - feel free to replace with your custom neon image!
FALLBACK_THUMBNAIL_URL = "https://via.placeholder.com/280x158.png?text=Thumbnail+Unavailable"
# Example of a custom neon fallback:
# FALLBACK_THUMBNAIL_URL = "https://i.imgur.com/example-neon-fallback.png"

# ==============================================================================
# Data Classes
# ==============================================================================
@dataclass
class VideoDataClass:
    title: str
    img: str # URL for thumbnail
    link: str # URL to the full video page
    preview_url: Optional[str] = None # URL for the short preview video (e.g., MP4/WebM)
    quality: Optional[str | int] = None
    time: Optional[str] = None # Video duration
    channel_name: Optional[str] = None
    channel_link: Optional[str] = None

@dataclass
class VideoDownloadDataClass:
    low: Optional[str] = None
    high: Optional[str] = None
    hls: Optional[str] = None # HLS streaming URL

@dataclass
class Tags:
    name: Optional[str] = None
    id: Optional[str] = None

# ==============================================================================
# PornClient Class
# ==============================================================================

class PornClient:
    """
    A client to interact with various pornographic video engines using the pornLib library.
    Handles engine initialization and rate-limited searches.
    """
    def __init__(self, engine: str = DEFAULT_ENGINE, soup_sleep: float = DEFAULT_SOUP_SLEEP):
        if engine not in VALID_ENGINES:
            raise ValueError(f"Invalid engine: {engine}. Valid engines are: {', '.join(VALID_ENGINES)}")
        self.engine = engine
        self.soup_sleep = soup_sleep # This might be used by underlying pornLib clients
        self._client: Any = self._initialize_client(engine) # Store the initialized pornLib client

    def _initialize_client(self, engine: str) -> Any:
        """Initializes the appropriate client from pornLib based on the engine name."""
        logger.debug(f"Attempting to initialize pornLib client for engine: {engine} using dynamic loader.")
        # The actual loading logic will be replaced by a call to the new get_pornlib_client function
        # This section will be updated in a subsequent step.
        # For now, let's make it clear it's a placeholder for the dynamic client loading.
        client = _get_pornlib_client_dynamically(engine) # Placeholder for the new dynamic loader
        if not client:
            # _get_pornlib_client_dynamically will handle its own logging for critical errors.
            raise RuntimeError(f"Failed to initialize PornLib client for '{engine}' using dynamic loader.")
        return client

    @sleep_and_retry
    @limits(calls=API_CALLS_LIMIT, period=API_PERIOD_SECONDS)
    def search(self, query: str, limit: int = DEFAULT_SEARCH_LIMIT, page: int = DEFAULT_PAGE) -> list[VideoDataClass]:
        """
        Performs a search using the selected engine and returns a list of VideoDataClass objects.
        Includes robust data parsing and URL validation.
        """
        logger.info(f"Searching {self.engine} for '{query}' (limit={limit}, page={page})...")
        results: list[VideoDataClass] = []
        try:
            # Dynamically determine if the client's search method supports 'page'
            search_kwargs = {'keyword': query} # 'keyword' is standard in pornLib
            
            # Some clients might take 'limit', others might not.
            # Most pornLib search methods don't standardize 'limit' in the call,
            # results are often sliced after. For now, we assume limit is handled by slicing.
            # If a client explicitly supports 'limit' in its signature, it could be added here.

            client_search_signature = inspect.signature(self._client.search)
            if 'page' in client_search_signature.parameters:
                search_kwargs['page'] = page
                logger.debug(f"Client for '{self.engine}' supports 'page' parameter. Using page={page}.")
            else:
                if page != DEFAULT_PAGE: # Only warn if user tried to use a non-default page
                    logger.warning(f"Client for '{self.engine}' does not support 'page' parameter in its search method. Ignoring page={page}.")
            
            # Call the actual pornLib client's search method with appropriate arguments
            logger.debug(f"Calling {self.engine} client search with arguments: {search_kwargs}")
            search_data = self._client.search(**search_kwargs)
            logger.debug(f"Raw search results from {self.engine} (first 2 items): {search_data[:2]}")

            # Ensure search_data is a list before slicing, some clients might return None on no results
            if search_data is None:
                search_data = []
                logger.warning(f"Search on {self.engine} for '{query}' returned None. Treating as empty results.")


            for i, item in enumerate(search_data): # Slicing for 'limit' will be done after parsing all available
                if len(results) >= limit: # Respect the limit
                    break

                # Extract and validate data, providing fallbacks
                title: str = item.get('title', 'No Title Available').strip() or 'No Title Available'
                link: str = item.get('url', '#').strip() or '#'

                img_url_raw: str = item.get('thumb', item.get('img', '')).strip()
                preview_url_raw: str = item.get('preview', item.get('preview_url', '')).strip()

                # Validate image URL
                img_url = img_url_raw if img_url_raw and (img_url_raw.startswith('http://') or img_url_raw.startswith('https://')) else FALLBACK_THUMBNAIL_URL
                if img_url == FALLBACK_THUMBNAIL_URL and img_url_raw:
                    logger.warning(f"Invalid or missing thumbnail URL for video '{title}' (Index {i}): '{img_url_raw}'. Using fallback.")

                # Validate preview URL
                preview_url: Optional[str] = preview_url_raw if preview_url_raw and (preview_url_raw.startswith('http://') or preview_url_raw.startswith('https://')) else None
                if preview_url is None and preview_url_raw:
                    logger.warning(f"Invalid or missing preview URL for video '{title}' (Index {i}): '{preview_url_raw}'. Preview will be unavailable.")

                results.append(VideoDataClass(
                    title=title,
                    img=img_url,
                    link=link,
                    preview_url=preview_url,
                    time=item.get('duration', item.get('time')), # Duration might be 'time' or 'duration'
                    channel_name=item.get('channel', item.get('uploader_name')), # Channel might be 'channel' or 'uploader_name'
                    quality=item.get('quality') # Add quality if available
                ))
            # The 'if len(results) >= limit: break' inside the loop handles the limit.
            # The redundant block below has been removed.
            
            logger.info(f"Successfully parsed {len(results)} videos from {self.engine} for query '{query}'.")
            # If the client doesn't support 'page' and we got results, they are effectively from page 1.
            # The limit is applied to these results.
            
        except Exception as e:
            logger.error(f"Error during search on {self.engine} for query '{query}': {e}", exc_info=True)
            # Depending on severity, you might want to re-raise or return empty results.
            # Returning empty results allows the script to continue and generate an "No Results" HTML page.
        return results

# ==============================================================================
# HTML Generation Function
# ==============================================================================
def generate_html_output(videos: list[VideoDataClass], query: str, filename: str) -> str:
    """
    Generates an HTML string for displaying video search results with enhanced
    thumbnail and video preview loading, and a neon-themed design.
    """
    if not videos:
        return (
            "<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
            "<title>No Results</title><style>body{background-color:#1a1a1a;color:#e0e0e0;font-family:sans-serif;text-align:center;padding-top:50px;}"
            "h1{color:#f0f;text-shadow:0 0 5px #f0f;}</style></head>"
            f"<body><h1>No videos found for query: '{html.escape(query)}'</h1></body></html>"
        )

    safe_query = html.escape(query)
    page_title = f"Search Results for '{safe_query}'"

    css = """
    <style>
        :root {
            --neon-cyan: #08f7fe;
            --neon-green: #39ff14;
            --neon-pink: #f0f;
            --dark-bg: #1a1a1a;
            --medium-dark-bg: #2a2a2a;
            --light-text: #e0e0e0;
            --dim-text: #aaa;
            --shadow-color: rgba(8, 247, 254, 0.4);
            --hover-shadow-color: rgba(57, 255, 20, 0.8);
        }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: var(--dark-bg);
            color: var(--light-text);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        h1 {
            color: var(--neon-cyan);
            text-align: center;
            border-bottom: 2px solid var(--neon-cyan);
            padding-bottom: 15px;
            margin-bottom: 30px;
            text-shadow: 0 0 8px var(--neon-cyan), 0 0 15px var(--shadow-color);
            font-size: 2.5em;
            letter-spacing: 2px;
            text-transform: uppercase;
        }
        p.results-info {
            text-align: center;
            color: var(--dim-text);
            margin-bottom: 30px;
            font-size: 1.1em;
        }
        .results-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 25px;
            max-width: 1400px;
            margin: 0 auto;
            padding-bottom: 50px;
        }
        .video-item {
            background-color: var(--medium-dark-bg);
            border: 1px solid var(--neon-cyan);
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 0 10px var(--shadow-color);
            transition: transform 0.3s ease, box-shadow 0.3s ease, border-color 0.3s ease;
            position: relative;
            display: flex;
            flex-direction: column;
            cursor: pointer; /* Indicate clickable */
        }
        .video-item:hover {
            transform: translateY(-5px) scale(1.02);
            border-color: var(--neon-green);
            box-shadow: 0 0 25px var(--hover-shadow-color), 0 0 10px rgba(57, 255, 20, 0.4);
            z-index: 10;
        }
        .video-item a {
            text-decoration: none;
            color: inherit;
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        .video-item .image-container {
            position: relative;
            width: 100%;
            height: 0;
            padding-bottom: 56.25%; /* 16:9 aspect ratio */
            background-color: #333;
            border-bottom: 1px solid var(--neon-cyan);
            overflow: hidden;
            flex-shrink: 0;
        }
        .video-item:hover .image-container {
            border-bottom-color: var(--neon-green);
        }
        .video-item .image-container img.thumbnail {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: block;
            transition: opacity 0.3s ease-in-out;
            z-index: 1;
            background-color: #333; /* Fallback background for img */
        }
        .video-item .image-container video.preview-video {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            object-fit: cover;
            display: none;
            z-index: 5;
            background-color: #000; /* Black background for video */
        }
        .video-info {
            padding: 15px;
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .video-title {
            font-size: 1.2em;
            font-weight: bold;
            margin: 0 0 10px 0;
            color: var(--neon-pink); /* Use neon pink for titles */
            line-height: 1.4;
            overflow: hidden;
            text-overflow: ellipsis;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            min-height: 2.8em;
            transition: color 0.3s ease;
        }
        .video-item:hover .video-title {
            color: var(--neon-cyan);
        }
        .video-details {
            font-size: 0.9em;
            color: var(--dim-text);
            margin-top: auto;
            display: flex;
            flex-wrap: wrap;
            gap: 8px 12px;
        }
        .video-details span {
            display: inline-block;
            white-space: nowrap;
            background-color: rgba(0, 0, 0, 0.3);
            padding: 4px 8px;
            border-radius: 5px;
            border: 1px solid rgba(8, 247, 254, 0.2);
            transition: background-color 0.3s ease, border-color 0.3s ease;
        }
        .video-item:hover .video-details span {
            background-color: rgba(57, 255, 20, 0.2);
            border-color: rgba(57, 255, 20, 0.4);
        }

        /* Styling for fallback text when image fails */
        .no-image-text {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #888;
            font-style: italic;
            text-align: center;
            padding: 10px;
            display: none;
            z-index: 2;
            width: 90%;
            max-width: 250px;
            font-size: 1.1em;
        }
        .video-item img.thumbnail[data-failed="true"] {
            opacity: 0;
        }
        .video-item img.thumbnail[data-failed="true"] + .no-image-text {
            display: block;
        }
        .video-item.preview-active .image-container img.thumbnail {
            opacity: 0;
            visibility: hidden; /* Hide thumbnail completely when preview is active */
        }
        .video-item.preview-active .image-container video.preview-video {
            display: block;
        }
    </style>
    """

    html_parts = [
        f"<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'><meta name='viewport' content='width=device-width, initial-scale=1.0'><title>{page_title}</title>",
        css,
        f"</head><body><h1>{page_title}</h1><p class='results-info'>Found {len(videos)} videos. Results saved in: {html.escape(filename)}</p><div class='results-container' role='list'>"
    ]

    for i, video in enumerate(videos):
        safe_title = html.escape(video.title)
        safe_link = html.escape(video.link)
        # Use fallback thumbnail if img is missing or invalid (already handled in PornClient.search)
        safe_img_url = html.escape(video.img)
        # Only include preview URL if it's valid and present (already handled in PornClient.search)
        safe_preview_url = html.escape(video.preview_url) if video.preview_url else ""
        safe_time = html.escape(video.time) if video.time else "N/A"
        safe_channel = html.escape(video.channel_name) if video.channel_name else "N/A"
        safe_quality = html.escape(str(video.quality)) if video.quality else "N/A" # Include quality if available

        img_alt_text = f"Thumbnail for {safe_title}"
        preview_attr = f'data-preview-url="{safe_preview_url}"' if safe_preview_url else ''

        # Preload attribute for the first few thumbnails for faster display
        preload_attr = 'preload="auto"' if i < 3 else 'loading="lazy"'

        html_parts.extend([
            f"    <div class='video-item' {preview_attr} role='listitem'><a href='{safe_link}' target='_blank' title='{safe_title}'><div class='image-container'>",
            # onerror handler for thumbnails to set data-failed and use fallback.
            # The fallback URL is passed via Python, so JS doesn't need to know Python's constant.
            f"<img class='thumbnail' src='{safe_img_url}' alt='{img_alt_text}' {preload_attr} onerror='this.setAttribute(\"data-failed\", \"true\"); this.src=\"{FALLBACK_THUMBNAIL_URL}\"; console.warn(\"Failed to load thumbnail:\", this.src);'>",
            "<span class='no-image-text'>Preview Unavailable</span>", # Text for broken image
            "</div><div class='video-info'><div class='video-title'>{safe_title}</div><div class='video-details'><span>Duration: {safe_time}</span>"
        ])
        if safe_channel != "N/A":
            html_parts.append(f"<span>Channel: {safe_channel}</span>")
        if safe_quality != "N/A":
            html_parts.append(f"<span>Quality: {safe_quality}</span>")
        html_parts.extend(["</div></div></a></div>"])

    html_parts.append("</div>")

    # Enhanced JavaScript for robust preview loading and thumbnail error handling.
    # The FALLBACK_THUMBNAIL_URL is passed multiple times for JS clarity.
    js = """
    <script>
        // NOTE: For production, consider removing console.debug messages or using a logging library.
        document.addEventListener('DOMContentLoaded', () => {
            const videoItems = document.querySelectorAll('.video-item');
            let previewTimeout = null;
            const PREVIEW_DELAY_MS = 250; // Delay before preview starts in milliseconds

            videoItems.forEach(item => {
                const imageContainer = item.querySelector('.image-container');
                const previewUrl = item.dataset.previewUrl;
                const thumbnail = item.querySelector('.thumbnail');
                let previewVideoElement = null;

                // --- Thumbnail Error Handling (reinforce and log) ---
                if (thumbnail) {
                    thumbnail.addEventListener('error', () => {
                        console.warn(`JS: Thumbnail failed to load '${thumbnail.src}'. Applying fallback.`);
                        thumbnail.src = '%s'; // Use Python-injected fallback URL
                        thumbnail.setAttribute('data-failed', 'true');
                        // If previewUrl is also missing, ensure "Preview Unavailable" is shown.
                        if (!previewUrl) {
                             item.querySelector('.no-image-text').style.display = 'block';
                        }
                    });
                    thumbnail.addEventListener('load', () => {
                        console.debug(`JS: Thumbnail loaded successfully: '${thumbnail.src}'.`);
                    });
                }

                // --- Preview Video Logic ---
                if (!imageContainer || !previewUrl) {
                    console.debug(`JS: No valid preview URL available for item: ${item.querySelector('.video-title')?.textContent || 'Untitled Video'}. Skipping video preview setup.`);
                    // Ensure the "Preview Unavailable" text shows if no valid preview URL exists
                    if (thumbnail) {
                         thumbnail.setAttribute('data-failed', 'true');
                         const noImageText = item.querySelector('.no-image-text');
                         if(noImageText) noImageText.style.display = 'block';
                    }
                    return; // Exit forEach for this item if no preview is possible
                }

                const createAndPlayPreview = () => {
                    // If preview video already exists, just try to play it again
                    if (previewVideoElement) {
                        previewVideoElement.play().catch(e => {
                            // Autoplay might be prevented, but no need to console.warn on every re-hover if already prevented
                            if (e.name !== 'NotAllowedError') {
                                console.debug(`JS: Re-play prevented for '${previewUrl}': ${e.message}`);
                            }
                        });
                        item.classList.add('preview-active');
                        return;
                    }

                    console.debug(`JS: Creating and attempting to play preview for: '${previewUrl}'.`);
                    previewVideoElement = document.createElement('video');
                    previewVideoElement.classList.add('preview-video');
                    previewVideoElement.src = previewUrl;
                    previewVideoElement.muted = true; // Essential for autoplay in most browsers
                    previewVideoElement.loop = true;
                    previewVideoElement.preload = 'auto'; // Load video data early
                    previewVideoElement.setAttribute('playsinline', ''); // For iOS compatibility

                    // Handle video load errors (network issues, unsupported format, corrupted file)
                    previewVideoElement.addEventListener('error', (e) => {
                        const errorDetails = e.target.error ? e.target.error.message : 'Unknown error';
                        console.warn(`JS: Failed to load preview video '${previewUrl}': ${errorDetails}. Reverting to thumbnail.`);
                        item.classList.remove('preview-active'); // Revert to thumbnail display
                        if (previewVideoElement) {
                            previewVideoElement.remove(); // Clean up the failed video element
                            previewVideoElement = null;
                        }
                        // Optionally: show 'Preview Unavailable' text if video fails after creation
                        if (thumbnail) {
                            thumbnail.src = '%s'; // Fallback if video fails to load
                            thumbnail.setAttribute('data-failed', 'true');
                            const noImageText = item.querySelector('.no-image-text');
                            if(noImageText) noImageText.style.display = 'block';
                        }
                    }, { once: true }); // Listen only once to avoid multiple error reports

                    imageContainer.appendChild(previewVideoElement);

                    // Attempt to play the video and handle promise for autoplay policies
                    const playPromise = previewVideoElement.play();
                    if (playPromise !== undefined) {
                        playPromise.then(() => {
                            console.debug(`JS: Preview started successfully: '${previewUrl}'.`);
                            item.classList.add('preview-active'); // Show video, hide thumbnail
                        }).catch(error => {
                            console.warn(`JS: Autoplay prevented for '${previewUrl}': ${error.message}. Reverting to thumbnail.`);
                            // Clean up if autoplay is blocked
                            if (previewVideoElement) {
                                previewVideoElement.remove();
                                previewVideoElement = null;
                            }
                            item.classList.remove('preview-active'); // Revert to thumbnail
                            // Ensure "Preview Unavailable" text shows here too
                            if (thumbnail) {
                                thumbnail.src = '%s'; // Fallback if autoplay fails
                                thumbnail.setAttribute('data-failed', 'true');
                                const noImageText = item.querySelector('.no-image-text');
                                if(noImageText) noImageText.style.display = 'block';
                            }
                        });
                    }
                };

                const stopAndRemovePreview = () => {
                    clearTimeout(previewTimeout); // Clear any pending preview creation
                    if (previewVideoElement) {
                        console.debug(`JS: Stopping and removing preview: '${previewUrl}'.`);
                        previewVideoElement.pause();
                        previewVideoElement.currentTime = 0; // Reset video to start for next time, if not removed
                        previewVideoElement.remove(); // Remove element to save resources
                        previewVideoElement = null;
                    }
                    item.classList.remove('preview-active'); // Ensure thumbnail is shown
                };

                // --- Event Listeners for Hover ---
                item.addEventListener('mouseenter', () => {
                    clearTimeout(previewTimeout);
                    previewTimeout = setTimeout(createAndPlayPreview, PREVIEW_DELAY_MS);
                });

                item.addEventListener('mouseleave', () => {
                    clearTimeout(previewTimeout);
                    stopAndRemovePreview();
                });

                // When clicking the link, stop preview immediately to avoid background audio/playback
                const link = item.querySelector('a');
                if (link) {
                    link.addEventListener('click', stopAndRemovePreview);
                }
            });
        });
    </script>
    """ % (FALLBACK_THUMBNAIL_URL, FALLBACK_THUMBNAIL_URL, FALLBACK_THUMBNAIL_URL, FALLBACK_THUMBNAIL_URL)

    html_parts.append(js)
    html_parts.append("</body></html>")
    return "\n".join(html_parts)

# ==============================================================================
# Helper Functions
# ==============================================================================

def get_validated_input(prompt: str, validation_func, error_message: str, default_value: Any) -> Any:
    """Helper function to get validated user input, with default display."""
    while True:
        user_input = input(f"{prompt} (default: {default_value}): ").strip()
        if not user_input:
            return default_value
        if validation_func(user_input):
            return user_input
        print(f"Error: {error_message}")

def is_valid_engine(engine: str) -> bool:
    """Checks if the entered engine is among the valid ones."""
    return engine.lower() in VALID_ENGINES

def is_positive_integer(value: str) -> bool:
    """Checks if the value is a string representation of a positive integer."""
    return value.isdigit() and int(value) > 0

def is_yes_no(value: str) -> bool:
    """Checks if the value is 'y' or 'n' (case-insensitive)."""
    return value.lower() in ['y', 'n']

# ==============================================================================
# Main Function
# ==============================================================================

def main():
    logger.info("🚀 Starting the PornHub Search & HTML Generator! 🚀")

    # Get user inputs
    query = input("Enter search query (e.g., 'hot milf'): ").strip()
    if not query:
        logger.error("Search query cannot be empty. Please provide a query to search.")
        return

    engine = get_validated_input(
        f"Enter engine ({'/'.join(VALID_ENGINES)})",
        is_valid_engine,
        f"Invalid engine. Please choose from {', '.join(VALID_ENGINES)}.",
        DEFAULT_ENGINE
    ).lower()

    search_limit = int(get_validated_input(
        "Enter search limit (number of videos to fetch)",
        is_positive_integer,
        "Limit must be a positive integer.",
        DEFAULT_SEARCH_LIMIT
    ))

    page_num = int(get_validated_input(
        "Enter page number",
        is_positive_integer,
        "Page number must be a positive integer.",
        DEFAULT_PAGE
    ))

    output_dir_str = input(f"Enter output directory (default: {DEFAULT_OUTPUT_DIR_STR}): ").strip()
    output_dir = Path(output_dir_str if output_dir_str else DEFAULT_OUTPUT_DIR_STR)

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output directory ensured: {output_dir.resolve()}")
    except OSError as e:
        logger.critical(f"Failed to create output directory '{output_dir}': {e}. Exiting.", exc_info=True)
        return

    auto_open = get_validated_input(
        "Auto-open HTML file in browser?",
        is_yes_no,
        "Please enter 'y' or 'n'.",
        DEFAULT_AUTO_OPEN
    ).lower() == 'y'

    logger.info(f"Initializing PornClient for '{engine}'...")
    try:
        client = PornClient(engine=engine, soup_sleep=DEFAULT_SOUP_SLEEP)
    except Exception as e:
        logger.critical(f"Failed to initialize PornClient: {e}. Exiting.")
        return

    videos = client.search(query=query, limit=search_limit, page=page_num)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # Sanitize query for filename: replace spaces/slashes, truncate to 30 chars
    query_part = "".join(c for c in query if c.isalnum() or c in (' ', '_'))[:30].replace(' ', '_').strip('_')
    if not query_part:
        query_part = "results" # Fallback if query becomes empty after sanitization

    filename_prefix = DEFAULT_FILENAME_PREFIX.format(engine=engine, query_part=query_part, timestamp=timestamp)
    output_html_filename = output_dir / f"{filename_prefix}.html"

    logger.info(f"Generating HTML output to: {output_html_filename}")
    html_content = generate_html_output(videos, query, str(output_html_filename))

    try:
        with open(output_html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"HTML output saved successfully to {output_html_filename}")

        if auto_open:
            webbrowser.open(f'file://{output_html_filename.resolve()}')
            logger.info(f"Opened {output_html_filename} in browser.")
    except OSError as e:
        logger.error(f"Failed to write or open HTML file '{output_html_filename}': {e}", exc_info=True)
    except Exception as e:
        logger.error(f"An unexpected error occurred during file operation: {e}", exc_info=True)

    logger.info("🎉 Script finished! Enjoy your enhanced search results. 🎉")


if __name__ == "__main__":
    # --- Usage Instructions ---
    # 1. Install dependencies: pip install pornlib ratelimit
    #    (Note: 'pornlib' might require specific versions or forks depending on your environment.
    #    If you face issues, check pornlib's GitHub for installation details.)
    # 2. Run the script: python xvid_prompt.py
    # 3. Follow the interactive prompts.
    # 4. Supported engines: xvideos, pornhub, redtube, youporn
    # 5. Review the generated HTML file in your browser. Use your browser's
    #    Developer Tools (F12) -> Console tab for detailed thumbnail and
    #    video preview loading logs.
    # --------------------------
    main()
