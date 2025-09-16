import datetime
import html
import logging
import sys
import webbrowser  # Re-added for auto-opening HTML files
from dataclasses import dataclass
from pathlib import Path
from typing import Any  # Explicitly import Optional

import pornLib  # Assuming this library exists and is installed
from ratelimit import limits, sleep_and_retry  # type: ignore

# ==============================================================================
# Configuration
# ==============================================================================

# --- Logging Configuration ---
LOG_LEVEL = logging.DEBUG # Changed to DEBUG for more detailed output
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- Rate Limiting Configuration ---
API_CALLS_LIMIT = 50
API_PERIOD_SECONDS = 60

# --- Default Settings (Used in prompts) ---
DEFAULT_OUTPUT_DIR_STR = "." # Default as string for input prompt
DEFAULT_SEARCH_LIMIT = 30
DEFAULT_PAGE = 1
DEFAULT_ENGINE = "xvideos"
VALID_ENGINES = ["xvideos", "pornhub", "redtube", "youporn"] # Added explicit list of valid engines
DEFAULT_SOUP_SLEEP = 1.0
DEFAULT_FILENAME_PREFIX = "{engine}_search_{query_part}_{timestamp}"
DEFAULT_AUTO_OPEN = "y"

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
    preview_url: str | None = None # URL for the short preview video (e.g., MP4/WebM)
    quality: str | int | None = None
    time: str | None = None # Video duration
    channel_name: str | None = None
    channel_link: str | None = None

@dataclass
class VideoDownloadDataClass:
    low: str | None = None
    high: str | None = None
    hls: str | None = None # HLS streaming URL

@dataclass
class Tags:
    name: str | None = None
    id: str | None = None

# ==============================================================================
# PornClient Class
# ==============================================================================
class PornClient:
    """A client to interact with various pornographic video engines using the pornLib library.
    Handles engine initialization and rate-limited searches.
    """
    def __init__(self, engine: str = DEFAULT_ENGINE, soup_sleep: float = DEFAULT_SOUP_SLEEP):
        if engine not in VALID_ENGINES:
            raise ValueError(f"Invalid engine: '{engine}'. Valid engines are: {', '.join(VALID_ENGINES)}")
        self.engine = engine
        self.soup_sleep = soup_sleep # This parameter is passed to PornLib constructor

        try:
            # Ensure pornLib is available before trying to instantiate
            if "pornLib" not in sys.modules and "pornlib" not in sys.modules:
                raise ImportError("pornLib module does not appear to be correctly imported or installed.")
            # Initialize the generic PornLib client with the specified engine
            self.client = pornLib.PornLib(engine=engine, soupSleep=soup_sleep)
            logger.info(f"Successfully initialized PornLib Client: engine='{engine}', soup_sleep={soup_sleep:.2f}s")
        except ImportError as ie:
            logger.critical(f"Fatal Error: pornLib library not found or incomplete. Please install it (e.g., 'pip install pornlib'). Error: {ie}")
            raise # Re-raise to stop execution if core library is missing
        except Exception as e:
            logger.critical(f"Fatal Error: Failed to initialize pornLib client for engine '{engine}'. Error: {e}", exc_info=True)
            raise RuntimeError(f"PornClient initialization failed for engine '{engine}': {e}") from e

    def _is_valid_url(self, url: str | None) -> bool:
        """Helper to check if a string is a valid HTTP(S) URL."""
        return bool(url) and (url.startswith("http://") or url.startswith("https://"))

    def _parse_video_results(self, results_raw: Any) -> list[VideoDataClass]:
        """Parses raw results from pornLib into a list of VideoDataClass objects."""
        if results_raw is None:
            logger.debug("Received None for video results, returning empty list.")
            return []
        if not isinstance(results_raw, list):
            logger.warning(f"Expected list for video results, got {type(results_raw)}. Returning empty.")
            return []

        videos: list[VideoDataClass] = []
        required_keys = ["title", "link"] # 'img' is also required but has fallback handling

        for i, item in enumerate(results_raw):
            video: VideoDataClass | None = None
            try:
                # Prioritize dict format from pornLib, then check for existing dataclass/object
                if isinstance(item, dict):
                    # Validate essential keys are present and not None
                    if not all(item.get(k) is not None for k in required_keys):
                        logger.warning(f"Skipping video dict item #{i + 1} due to missing essential keys. Data: {item}")
                        continue

                    # Extract and validate URLs, using fallback for thumbnails
                    img_url_raw = str(item.get("thumb", item.get("img", ""))).strip()
                    img_url = img_url_raw if self._is_valid_url(img_url_raw) else FALLBACK_THUMBNAIL_URL
                    if img_url == FALLBACK_THUMBNAIL_URL and img_url_raw:
                        logger.warning(f"Invalid or missing thumbnail URL for video '{item.get('title', 'N/A')}' (Index {i}): '{img_url_raw}'. Using fallback.")

                    preview_url_raw = str(item.get("preview", item.get("preview_url", ""))).strip()
                    preview_url = preview_url_raw if self._is_valid_url(preview_url_raw) else None
                    if preview_url is None and preview_url_raw:
                        logger.warning(f"Invalid or missing preview URL for video '{item.get('title', 'N/A')}' (Index {i}): '{preview_url_raw}'. Preview will be unavailable.")

                    video = VideoDataClass(
                        title=str(item["title"]),
                        img=img_url,
                        link=str(item["link"]),
                        preview_url=preview_url,
                        quality=item.get("quality"),
                        time=str(item.get("duration", item.get("time"))).strip() if item.get("duration") or item.get("time") else None, # Common keys for duration
                        channel_name=str(item.get("channel", item.get("uploader_name"))).strip() if item.get("channel") or item.get("uploader_name") else None, # Common keys for channel
                        channel_link=str(item.get("channel_link")).strip() if item.get("channel_link") else None,
                    )
                elif isinstance(item, VideoDataClass):
                    # If it's already a VideoDataClass, use it after basic validation
                    if not all([item.title, item.img, item.link]):
                        logger.warning(f"Skipping existing VideoDataClass item #{i + 1} due to missing essential attributes.")
                        continue
                    # Ensure URLs are valid, even if it's an existing dataclass
                    item.img = item.img if self._is_valid_url(item.img) else FALLBACK_THUMBNAIL_URL
                    item.preview_url = item.preview_url if self._is_valid_url(item.preview_url) else None
                    video = item
                else:
                    logger.warning(f"Skipping unrecognized video item #{i + 1} type: {type(item)}. Item: {item!r}")
                    continue

                if video:
                    videos.append(video)
            except Exception as e:
                logger.error(f"Error parsing video item #{i + 1}: {item!r}. Error: {e}", exc_info=False)
        return videos

    @sleep_and_retry # type: ignore
    @limits(calls=API_CALLS_LIMIT, period=API_PERIOD_SECONDS) # type: ignore
    def list_videos(self, limit: int = 12) -> list[VideoDataClass]:
        """Fetches a list of trending/recent videos using the selected engine.
        Handles rate limiting and robust error parsing.
        """
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("Limit must be a positive integer.")
        logger.debug(f"Attempting to fetch {limit} videos using list method for engine '{self.engine}'...")
        try:
            videos_raw = self.client.list(limit=limit) # Try with limit first
            videos = self._parse_video_results(videos_raw)
            logger.info(f"Fetched and parsed {len(videos)} videos (requested list limit: {limit}).")
            return videos
        except TypeError as te:
            # Some pornLib engines might not support 'limit' in list()
            if "limit" in str(te).lower():
                logger.warning(f"Engine '{self.engine}' list method may not support 'limit'. Trying without limit.")
                try:
                    videos_raw = self.client.list() # Retry without limit
                    videos = self._parse_video_results(videos_raw)
                    # Manually apply limit after parsing
                    limited_videos = videos[:limit]
                    logger.info(f"Fetched {len(videos)} via list (without explicit limit), returning first {len(limited_videos)}.")
                    return limited_videos
                except Exception as e_retry:
                    logger.error(f"Error during list retry for engine '{self.engine}': {e_retry}", exc_info=True)
                    raise RuntimeError(f"Failed list retry on engine '{self.engine}': {e_retry}") from e_retry
            else:
                logger.error(f"TypeError during list call for engine '{self.engine}': {te}", exc_info=True)
                raise RuntimeError(f"Failed list videos on engine '{self.engine}': {te}") from te
        except Exception as e:
            logger.error(f"Error during list call for engine '{self.engine}': {e}", exc_info=True)
            raise RuntimeError(f"Failed list videos on engine '{self.engine}': {e}") from e

    @sleep_and_retry # type: ignore
    @limits(calls=API_CALLS_LIMIT, period=API_PERIOD_SECONDS) # type: ignore
    def search_videos(self, keyword: str | None = None, page: int | None = None, limit: int | None = None, **kwargs: Any) -> list[VideoDataClass]:
        """Performs a search using the selected engine and returns a list of VideoDataClass objects.
        Includes robust data parsing and URL validation.
        """
        search_params: dict[str, Any] = {k: v for k, v in kwargs.items() if v is not None}
        if keyword: search_params["keyword"] = keyword
        if page and page > 1: search_params["page"] = page # Pass page to client, it might support it
        if limit: search_params["limit"] = limit # Pass limit to client, it might support it

        search_description_parts: list[str] = [f"{k}='{v}'" for k, v in search_params.items()]
        search_description = ", ".join(search_description_parts) if search_description_parts else "no specific criteria"
        logger.debug(f"Attempting search on engine '{self.engine}' with params: {search_params} (User requested: {search_description})")

        if not search_params:
            raise ValueError("Search requires at least one supported criterion (e.g., keyword).")

        try:
            videos_raw = self.client.search(**search_params)
            videos = self._parse_video_results(videos_raw)
            logger.info(f"Search yielded {len(videos)} parsed results from engine '{self.engine}'.")

            # If the engine didn't respect 'limit', manually truncate if needed.
            if limit and len(videos) > limit:
                logger.info(f"Truncating {len(videos)} results to requested limit of {limit} (engine may not have supported limit directly).")
                videos = videos[:limit]
            return videos
        except TypeError as te:
            # This often means a parameter like 'page' or 'limit' isn't supported by the client's search method.
            logger.warning(f"TypeError during search call for engine '{self.engine}' with params {search_params}. This might mean some parameters are not supported by the engine's API. Error: {te}", exc_info=True)
            # Try a fallback search without the problematic parameters if needed, or re-raise
            # For now, we'll re-raise as it's a critical error for the requested search.
            raise RuntimeError(f"Failed search on engine '{self.engine}' due to parameter issue: {te}") from te
        except Exception as e:
            logger.error(f"Error during search call for engine '{self.engine}': {e}", exc_info=True)
            raise RuntimeError(f"Failed search videos on engine '{self.engine}': {e}") from e

# ==============================================================================
# HTML Generation Function
# ==============================================================================
def generate_html_output(videos: list[VideoDataClass], query: str, filename: str) -> str:
    """Generates an HTML string for displaying video search results with enhanced
    thumbnail and video preview loading, and a neon-themed design.
    """
    safe_query = html.escape(query)
    page_title = f"Search Results for '{safe_query}'"

    if not videos:
        return (
            "<!DOCTYPE html><html lang='en'><head><meta charset='UTF-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'>"
            "<title>No Results</title><style>body{background-color:#1a1a1a;color:#e0e0e0;font-family:sans-serif;text-align:center;padding-top:50px;}"
            "h1{color:#f0f;text-shadow:0 0 5px #f0f;}</style></head>"
            f"<body><h1>No videos found for query: '{safe_query}'</h1><p>Try a different query or engine.</p></body></html>"
        )

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
        # Use fallback thumbnail if img is missing or invalid (already handled in PornClient._parse_video_results)
        safe_img_url = html.escape(video.img)
        # Only include preview URL if it's valid and present (already handled in PornClient._parse_video_results)
        safe_preview_url = html.escape(video.preview_url) if video.preview_url else ""
        safe_time = html.escape(video.time) if video.time else "N/A"
        safe_channel = html.escape(video.channel_name) if video.channel_name else "N/A"
        safe_quality = html.escape(str(video.quality)) if video.quality else "N/A" # Include quality if available

        img_alt_text = f"Thumbnail for {safe_title}"
        preview_attr = f'data-preview-url="{safe_preview_url}"' if safe_preview_url else ""

        # Preload attribute for the first few thumbnails for faster display
        preload_attr = 'preload="auto"' if i < 3 else 'loading="lazy"'

        html_parts.extend([
            f"    <div class='video-item' {preview_attr} role='listitem'><a href='{safe_link}' target='_blank' title='{safe_title}'><div class='image-container'>",
            # onerror handler for thumbnails to set data-failed and use fallback.
            # The fallback URL is passed via Python, so JS doesn't need to know Python's constant.
            f"<img class='thumbnail' src='{safe_img_url}' alt='{img_alt_text}' {preload_attr} onerror='this.setAttribute(\"data-failed\", \"true\"); this.src=\"{FALLBACK_THUMBNAIL_URL}\"; console.warn(\"JS: Failed to load thumbnail:\", this.src);'>",
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
                             const noImageText = item.querySelector('.no-image-text');
                             if(noImageText) noImageText.style.display = 'block';
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
# Helper Functions for Input Prompts
# ==============================================================================
def get_validated_input(prompt: str, default: Any, validation_type: type, positive_only: bool = False, choices: list[str] | None = None) -> Any:
    """Gets user input, validates type, handles defaults, ensures positivity if needed, and checks against choices."""
    while True:
        try:
            user_input_str = input(f"{prompt} [{default}]: ").strip()
            if not user_input_str:
                logger.debug(f"User accepted default: {default}")
                return default

            value: Any
            # Attempt type conversion
            if validation_type == int:
                value = int(user_input_str)
            elif validation_type == float:
                value = float(user_input_str)
            elif validation_type == Path:
                value = Path(user_input_str)
            else: # Assume string if no specific type or Path was requested
                value = user_input_str

            # Check for positivity if required
            if positive_only and validation_type in [int, float] and value <= 0:
                print("Input must be a positive number. Please try again.")
                continue

            # Check against predefined choices if provided
            if choices and value not in choices and value.lower() not in [c.lower() for c in choices]:
                print(f"Invalid input. Please choose from: {', '.join(choices)}.")
                continue

            logger.debug(f"User entered valid input: {value}")
            return value

        except ValueError:
            print(f"Invalid input. Please enter a valid {validation_type.__name__}.")
        except Exception as e:
            print(f"An unexpected error occurred during input: {e}")
            continue

# ==============================================================================
# Main Execution Function (Using Prompts)
# ==============================================================================
def main():
    """Main function using interactive prompts to gather info, run client, and generate output."""
    logger.info("--- Starting PornLib Search Script (Interactive Mode) ---")

    # --- Gather Input via Prompts ---
    try:
        search_query = ""
        while not search_query:
            search_query = input("Enter search query: ").strip()
            if not search_query:
                print("Search query cannot be empty. Please provide a query to search.")

        limit = get_validated_input("Max results to fetch?", DEFAULT_SEARCH_LIMIT, int, positive_only=True)
        page = get_validated_input("Page number?", DEFAULT_PAGE, int, positive_only=True)
        engine = get_validated_input("PornLib engine?", DEFAULT_ENGINE, str, choices=VALID_ENGINES).lower() # Validate against VALID_ENGINES
        soup_sleep = get_validated_input("Soup sleep (seconds)?", DEFAULT_SOUP_SLEEP, float, positive_only=False)
        output_dir_str = get_validated_input("Output directory?", DEFAULT_OUTPUT_DIR_STR, str)
        output_dir = Path(output_dir_str) # Convert to Path after getting input
        filename_prefix_format = get_validated_input("Filename prefix format?", DEFAULT_FILENAME_PREFIX, str)
        auto_open_str = get_validated_input("Auto-open HTML file (y/n)?", DEFAULT_AUTO_OPEN, str, choices=["y", "n"])
        auto_open = auto_open_str.lower().startswith("y")

    except (KeyboardInterrupt, EOFError):
        logger.info("\nInput cancelled by user. Exiting.")
        return
    except Exception as e:
        logger.critical(f"Failed to gather input settings: {e}", exc_info=True)
        return # Exit if input fails critically

    logger.info(f"Settings: Engine='{engine}', Query='{search_query}', Limit={limit}, Page={page}, Output='{output_dir}', AutoOpen={auto_open}")

    client: PornClient | None = None
    try:
        # --- Initialize the client ---
        client = PornClient(engine=engine, soup_sleep=soup_sleep)

        # --- Perform Search ---
        logger.info(f"Performing search for query: '{search_query}' on {engine}...")
        search_results: list[VideoDataClass] = client.search_videos(
            keyword=search_query,
            page=page,
            limit=limit
        )

        if search_results:
            logger.info(f"Successfully retrieved and parsed {len(search_results)} videos.")

            # --- Generate Filename ---
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Sanitize query for filename: remove spaces, slashes, non-alphanumeric, truncate
            safe_query_part = "".join(c for c in search_query.replace(" ", "_") if c.isalnum() or c in ["_", "-"])[:40].strip("_")
            if not safe_query_part:
                safe_query_part = "results" # Fallback if query becomes empty after sanitization

            try:
                filename_stem = filename_prefix_format.format(
                    engine=engine, query_part=safe_query_part, timestamp=timestamp
                )
            except KeyError as e:
                logger.error(f"Invalid key in filename prefix format string: {e}. Using default format.")
                filename_stem = DEFAULT_FILENAME_PREFIX.format(
                    engine=engine, query_part=safe_query_part, timestamp=timestamp
                )
            except Exception as fmt_e: # Catch other formatting errors
                logger.error(f"Error formatting filename prefix: {fmt_e}. Using basic name.")
                filename_stem = f"{engine}_search_{timestamp}" # Fallback

            output_filename = f"{filename_stem}.html"
            output_path = output_dir.resolve() / output_filename

            # --- Ensure Output Directory Exists ---
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured output directory exists: {output_dir.resolve()}")
            except OSError as e:
                logger.error(f"Failed to create output directory '{output_dir}': {e}. Check permissions.")
                logger.warning(f"Attempting to save to current directory as a fallback: {Path.cwd()}")
                output_path = Path.cwd() / output_filename # Fallback to current working directory

            # --- Generate HTML ---
            logger.info("Generating HTML output...")
            html_content = generate_html_output(search_results, search_query, output_filename)

            # --- Save HTML to File ---
            logger.info(f"Attempting to save results to: {output_path}")
            try:
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.info(f"Successfully saved results to: {output_path}")
                # --- Auto-open File ---
                if auto_open:
                    try:
                        logger.info("Attempting to open HTML file in default browser...")
                        webbrowser.open(f"file://{output_path.resolve()}")
                        logger.info(f"Opened {output_path} in browser.")
                    except Exception as open_err:
                        logger.warning(f"Could not automatically open file '{output_path}'. Please open it manually. Error: {open_err}")
            except OSError as e:
                logger.error(f"Error saving HTML file '{output_path}': {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Unexpected error writing HTML file: {e}", exc_info=True)

        else:
            logger.warning(f"No videos found for query '{search_query}' using engine '{engine}'. No HTML file generated.")

    # --- Comprehensive Error Handling for Main Logic ---
    except ValueError as ve:
        logger.critical(f"Input/Validation Error: {ve}", exc_info=False)
    except NotImplementedError as nie:
        logger.critical(f"Feature Error: {nie} - This engine/client might not support the requested operation.", exc_info=True)
    except RuntimeError as rte: # Custom runtime errors raised from PornClient methods
        logger.critical(f"Operation Failed: {rte}", exc_info=True)
    except ImportError as ie: # Specifically for pornLib not being found
        logger.critical(f"Dependency Error: {ie} - Please ensure pornLib is installed and accessible.", exc_info=False)
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user (Ctrl+C). Exiting gracefully.")
    except Exception as e:
        logger.critical(f"An unexpected critical error occurred during script execution: {e}", exc_info=True)
    finally:
        logger.info("--- PornLib Search Script Finished ---")


# ==============================================================================
# Script Entry Point
# ==============================================================================

if __name__ == "__main__":
    # --- Usage Instructions ---
    # 1. Install dependencies: pip install pornlib ratelimit
    #    (If 'pornlib' installation causes issues, check its GitHub for specific
    #    installation instructions or forks, as its availability can vary.)
    # 2. Run the script from your Termux terminal: python xvid_prompt.py
    # 3. Follow the interactive prompts to enter your search query and settings.
    # 4. Review the generated HTML file in your browser. For debugging, open
    #    your browser's Developer Tools (F12) and check the Console tab for
    #    detailed thumbnail and video preview loading logs.
    # --------------------------
    main()
