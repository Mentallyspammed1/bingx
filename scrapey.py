#!/usr/bin/env python3

"""Enhanced Bing Image Downloader Script
-------------------------------------
Downloads images from Bing based on user queries and filters,
renames them sequentially within a query-specific subfolder,
extracts comprehensive local file metadata (size, dimensions, format, mode,
DPI, GIF frame count, animation status),
saves the metadata to a JSON file in the base output directory,
and generates a master manifest JSON file for web viewing.
"""

import json
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import glob # Channeling the glob spirits for manifest generation

# Third-party Libraries
# requests is used implicitly by bing_image_downloader
from bing_image_downloader import downloader
from colorama import Back, Fore, Style, init
from tqdm import tqdm

# Attempt to import Pillow for image metadata; provide guidance if missing
try:
    from PIL import Image, UnidentifiedImageError, ImageSequence
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None  # type: ignore
    UnidentifiedImageError = None  # type: ignore
    ImageSequence = None # type: ignore


# --- Constants: The Pillars of the Operation ---
DEFAULT_OUTPUT_DIR: str = "downloads"
MAX_FILENAME_LENGTH: int = 200  # Max length for base filename derived from query
METADATA_FILENAME_PREFIX: str = "metadata_"
MASTER_MANIFEST_FILENAME: str = "master_image_manifest.json" # The grand ledger of images

# --- Initialize Colorama: Infusing the Terminal with Light ---
init(autoreset=True)


# --- Configure Colored Logging: Whispers from the Ether ---
class ColoredFormatter(logging.Formatter):
    """Custom logging formatter with Pyrmethus's chosen hues."""
    COLORS = {
        "DEBUG": Fore.CYAN,
        "INFO": Fore.GREEN,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Back.WHITE + Style.BRIGHT,
    }

    def format(self, record: logging.LogRecord) -> str:
        """Formats the log record with appropriate colors."""
        log_fmt = (
            f"%(asctime)s - {self.COLORS.get(record.levelname, Fore.WHITE)}"
            f"%(levelname)s{Style.RESET_ALL} - %(message)s"
        )
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


# Setup Logger: The Oracle's Voice
logger = logging.getLogger(__name__)  # Using __name__ for hierarchical wisdom
logger.propagate = False  # Preventing echoes from the root logger
if not logger.handlers:  # Ensuring the oracle speaks but once
    handler = logging.StreamHandler(sys.stdout)  # Directing whispers to stdout
    handler.setFormatter(ColoredFormatter())  # Applying Pyrmethus's color sigils
    logger.addHandler(handler)
logger.setLevel(logging.INFO)  # Setting the default level of revelation


# --- User Feedback Functions: Guiding the Seeker ---
def print_header(text: str) -> None:
    """Prints a formatted header, marking new phases of the ritual."""
    bar = "═" * (len(text) + 4)
    print(Fore.YELLOW + Style.BRIGHT + f"\n{bar}")
    print(Fore.YELLOW + Style.BRIGHT + f"  {text}  ")
    print(Fore.YELLOW + Style.BRIGHT + f"{bar}\n")


def print_success(text: str) -> None:
    """Logs a success message, a blessing from the digital realm."""
    logger.info(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")


def print_warning(text: str) -> None:
    """Logs a warning message, a whisper of caution."""
    logger.warning(f"{Fore.YELLOW}! {text}{Style.RESET_ALL}")


def print_error(text: str) -> None:
    """Logs an error message, a discordant note in the symphony."""
    logger.error(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")


def print_info(text: str) -> None:
    """Prints an informational message directly, a guiding light."""
    print(Fore.CYAN + Style.NORMAL + f"➤ {text}")


# --- Utility Functions: Tools of the Trade ---
def sanitize_filename(name: str) -> str:
    """Cleanses a string for use as a filename, removing impurities and truncating."""
    # Removing characters that might displease file systems
    sanitized = "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).strip()
    # Replacing spaces with underscores for harmony
    sanitized = '_'.join(filter(None, sanitized.split(' ')))
    sanitized = '_'.join(filter(None, sanitized.split('_'))) # Normalize multiple underscores
    # Limiting length to prevent overflow
    return sanitized[:MAX_FILENAME_LENGTH]


def create_directory(path: str) -> bool:
    """Conjures a directory into existence if it does not already manifest."""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError as e:
        print_error(f"Failed to forge directory {path}: {e}")
        return False


def rename_files(file_paths: List[str], base_query: str) -> List[str]:
    """Renames downloaded files sequentially with a sanitized query prefix.
    Returns a list of final paths for files that were processed.
    If a file is renamed, its new path is in the list.
    If renaming failed or was skipped for an existing file, its original path is in the list.
    Files from input that were not found or were not files are skipped and not in the output list.
    (Adopted from bimgx.py for robustness)
    """
    final_paths_after_rename: List[str] = []
    if not file_paths:
        print_warning("No file paths provided for the renaming ritual.") # Retained scrapey.py's wording
        return []

    sanitized_query = sanitize_filename(base_query)
    if not sanitized_query:
        sanitized_query = "image"  # Fallback base name
        print_warning(f"Query '{base_query}' sanitized to empty string, using fallback 'image'.")

    first_valid_dir = next((os.path.dirname(p) for p in file_paths if p), None)
    if first_valid_dir is None and file_paths:
         print_error("Cannot discern the directory for renaming files. All paths are invalid.") # Retained scrapey.py's wording
         return list(file_paths)
    elif first_valid_dir is None and not file_paths:
         return []

    dir_name = first_valid_dir if first_valid_dir is not None else "."

    print_info(f"Imbuing {len(file_paths)} files in '{dir_name}' with the prefix '{sanitized_query}'...") # Retained scrapey.py's wording

    sorted_file_paths = sorted(file_paths) # bimgx.py sorts for consistency

    actual_renames_count = 0

    for idx, old_path in enumerate(
        tqdm(sorted_file_paths, desc=Fore.BLUE + "🔄 Renaming Files", unit="file", ncols=100, leave=False), start=1 # Retained scrapey.py's tqdm desc
    ):
        current_file_final_path = old_path

        try:
            if not os.path.exists(old_path):
                print_warning(f"File not found for renaming (already transformed or vanished?): {old_path}") # Retained scrapey.py's wording
                continue
            if not os.path.isfile(old_path):
                 print_warning(f"Path is not a tangible file, skipping rename: {old_path}") # Retained scrapey.py's wording
                 continue

            _, ext = os.path.splitext(old_path)
            new_base_name = f"{sanitized_query}_{idx}"
            new_filename = f"{new_base_name}{ext}"
            potential_new_path = os.path.join(dir_name, new_filename)

            target_path_for_rename = potential_new_path
            collision_counter = 1

            while os.path.exists(target_path_for_rename):
                try:
                    if os.path.samefile(old_path, target_path_for_rename):
                        logger.debug(f"Skipping rename for {os.path.basename(old_path)} as target name '{os.path.basename(target_path_for_rename)}' is identical and points to the same file.")
                        target_path_for_rename = old_path
                        break
                except FileNotFoundError:
                    print_warning(f"File not found during samefile check: {old_path} or {target_path_for_rename}")
                    target_path_for_rename = old_path
                    break

                new_filename = f"{new_base_name}_{collision_counter}{ext}"
                target_path_for_rename = os.path.join(dir_name, new_filename)
                collision_counter += 1
                if collision_counter > 100:
                    print_error(f"Could not find a unique name for {os.path.basename(old_path)} after 100 attempts. Skipping rename for this file.")
                    target_path_for_rename = old_path
                    break

            if old_path == target_path_for_rename:
                pass
            else:
                try:
                    os.rename(old_path, target_path_for_rename)
                    current_file_final_path = target_path_for_rename
                    actual_renames_count +=1
                except OSError as e:
                    print_error(f"Error transforming {os.path.basename(old_path)} to {os.path.basename(target_path_for_rename)}: {e}") # Retained scrapey.py's wording for error
                except Exception as e:
                    print_error(f"An unforeseen error occurred during renaming {os.path.basename(old_path)} to {os.path.basename(target_path_for_rename)}: {e}") # Retained scrapey.py's wording

            final_paths_after_rename.append(current_file_final_path)

        except Exception as e:
            print_error(f"An unexpected anomaly occurred while processing {os.path.basename(old_path)} for renaming: {e}. Retaining original path.") # Retained scrapey.py's wording
            if os.path.exists(old_path):
                 final_paths_after_rename.append(old_path)

    if final_paths_after_rename:
        print_success(f"Successfully processed {len(final_paths_after_rename)} files for renaming. Actual transformations: {actual_renames_count}.") # Harmonized log message
    elif file_paths:
        print_warning("No files were successfully processed for renaming (e.g., all source files missing).")

    return final_paths_after_rename


def apply_filters(**kwargs: str | None) -> str:
    """Weaves Bing filter query parameters, guiding the scrying lens."""
    filters: List[str] = []
    # Mapping seeker-friendly keys to Bing's arcane filter syntax
    filter_map: Dict[str, str] = {
        "size": "Size:{}",
        "color": "Color:{}",
        "type": "Type:{}",
        "layout": "Layout:{}",
        "people": "People:{}",
        "date": "Date:{}",
        "license": "License:{}",
    }

    for key, value in kwargs.items():
        if value and value.strip():
            formatted_value = value.strip()
            # Apply specific formatting as per bimgx.py's logic for better compatibility
            if key == "color":
                if formatted_value.lower() == "coloronly": formatted_value = "ColorOnly"
                elif formatted_value.lower() == "monochrome": formatted_value = "Monochrome"
                else: formatted_value = formatted_value.capitalize() # Default for other colors
            elif key in ["size", "type", "layout", "people", "date", "license"]:
                 # Most Bing filters capitalize the value (e.g. Size:Large, Type:Photo)
                 formatted_value = formatted_value.capitalize()
            # For other keys not explicitly handled, use capitalized value if that's a general good default,
            # or pass as is if Bing is inconsistent. Current scrapey capitalized all.
            # Sticking to bimgx.py's explicit list for capitalization. Other filters, if any, pass value as is (or capitalized by default).
            # The current filter_map only includes keys that bimgx.py capitalizes, so this is fine.
            else: # For any other filter keys that might be added to filter_map later
                formatted_value = formatted_value.capitalize()


            if template := filter_map.get(key):
                filters.append(template.format(formatted_value))
            else:
                print_warning(f"Unknown filter key '{key}' provided. It shall be ignored by the scrying lens.")

    # The library expects a simple string with '+' separators for its 'filter' parameter.
    return "+".join(filters)


# --- Core Functions: The Heart of the Spell ---
def download_images_with_bing(
    query: str,
    output_dir_base: str,  # The base directory provided by user
    limit: int,
    timeout: int,
    adult_filter_off: bool,
    extra_filters: str,
    site_filter: Optional[str] = None
) -> List[str]:
    """Summons images from the Bing realm and returns their manifested paths."""
    effective_query = query
    if site_filter:
        # Weaving the site filter into the query string
        effective_query += f" site:{site_filter}"

    # The downloader creates a sub-chamber named after the 'query' argument given to it.
    # This will be 'effective_query' if a site_filter is applied.
    query_based_subdir_name = effective_query # Use effective_query here
    query_specific_output_dir = os.path.join(output_dir_base, query_based_subdir_name)

    downloaded_files: List[str] = []
    try:
        print_info(f"Initiating scrying for query: '{Fore.YELLOW}{effective_query}{Fore.CYAN}'")
        print_info(f"Manifesting images into: '{query_specific_output_dir}'")
        print_info(f"Applying ethereal filters: '{extra_filters}'" if extra_filters else "No extra filters applied.")

        # Invoke the downloader. It manages its own ethereal connections.
        downloader.download(
            query=effective_query,
            limit=limit,
            output_dir=output_dir_base,
            adult_filter_off=adult_filter_off,
            force_replace=False,  # Preserving existing manifestations
            timeout=timeout,
            filter=extra_filters,
            verbose=False  # Pyrmethus handles the primary feedback
        )
        print_success("The bing-image-downloader ritual has concluded.")

        # --- Discovering Manifested Files ---
        print_info(f"Searching for manifested files in: {query_specific_output_dir}")
        if os.path.isdir(query_specific_output_dir):
            found_count = 0
            for filename in os.listdir(query_specific_output_dir):
                full_path = os.path.join(query_specific_output_dir, filename)
                if os.path.isfile(full_path):
                    downloaded_files.append(full_path)
                    found_count += 1
            if found_count > 0:
                print_success(f"Discovered {found_count} manifested image(s) in the target chamber.")
            else:
                print_warning(f"The download ritual concluded, but no images were found in {query_specific_output_dir}. "
                              "Verify the query, filters, or permissions.")
        else:
            print_warning(f"Could not find the expected manifestation chamber: {query_specific_output_dir}. "
                          "The download might have failed silently or placed images elsewhere.")

    except KeyboardInterrupt:
        print_warning("Download ritual interrupted by the seeker's will.")
        raise  # Propagate the interruption
    except Exception as e:
        print_error(f"The download ritual failed: {e}")
        logger.debug("Traceback for downloader error:", exc_info=True)
        return []  # Return an empty list on failure

    return downloaded_files


def get_local_file_metadata(file_path: str, query_based_subdir_name: str) -> Dict[str, Any]:
    """
    Extracts comprehensive intrinsic properties from a local image manifestation.
    Includes size, dimensions, format, mode, DPI, and GIF frame count/animation status.
    """
    metadata: Dict[str, Any] = {
        "file_path": file_path,
        "filename": os.path.basename(file_path),
        "query_based_subdir_name": query_based_subdir_name,
        "file_size_bytes": None,
        "dimensions": None,  # Format "WxH"
        "width": None,
        "height": None,
        "format": None,      # e.g., 'JPEG', 'PNG', 'GIF'
        "mode": None,        # e.g., 'RGB', 'L', 'P'
        "dpi": None,         # Tuple (x_dpi, y_dpi)
        "is_animated": False, # True for animated GIFs
        "frame_count": None, # Number of frames for animated images
        "error": None
    }
    try:
        if not os.path.exists(file_path):
            metadata["error"] = "File does not exist at time of metadata extraction."
            logger.debug(f"File not found for metadata extraction: {metadata['filename']}")
            return metadata
        if not os.path.isfile(file_path):
             metadata["error"] = "Path is not a tangible file."
             logger.debug(f"Path is not a tangible file, skipping metadata: {metadata['filename']}")
             return metadata

        # Ascertain file size
        try:
            metadata["file_size_bytes"] = os.path.getsize(file_path)
        except OSError as size_err:
             metadata["error"] = f"OS error getting size: {size_err}"
             logger.warning(f"Could not discern size for {metadata['filename']}: {size_err}")

        # Ascertain image dimensions and other properties using Pillow's wisdom
        if PIL_AVAILABLE and Image:
            try:
                with Image.open(file_path) as img:
                    metadata["width"], metadata["height"] = img.size
                    metadata["dimensions"] = f"{img.width}x{img.height}"
                    metadata["format"] = img.format
                    metadata["mode"] = img.mode
                    metadata["dpi"] = img.info.get('dpi') # DPI is a tuple (x, y)

                    # Check for animation (primarily for GIFs)
                    if img.format == 'GIF':
                        try:
                            # Attempt to iterate through frames to count them
                            frame_count = 0
                            for _frame in ImageSequence.Iterator(img):
                                frame_count += 1
                            metadata["frame_count"] = frame_count
                            metadata["is_animated"] = frame_count > 1
                        except Exception as gif_err:
                            metadata["error"] = f"{metadata['error']}; GIF frame count error: {gif_err}" if metadata['error'] else f"GIF frame count error: {gif_err}"
                            logger.warning(f"Error counting GIF frames for {metadata['filename']}: {gif_err}")

            except UnidentifiedImageError:
                err_msg = "Cannot identify image file (Pillow's gaze is clouded). Possibly corrupted or not an image."
                metadata["error"] = f"{metadata['error']}; {err_msg}" if metadata['error'] else err_msg
                logger.warning(f"Unidentified image format for {metadata['filename']}.")
            except Exception as img_err:
                err_msg = f"Error reading image properties with Pillow: {img_err}"
                metadata["error"] = f"{metadata['error']}; {err_msg}" if metadata['error'] else err_msg
                logger.warning(f"Could not discern full image properties for {metadata['filename']}: {img_err}")
        elif not PIL_AVAILABLE:
            err_msg = "Pillow library not installed. Advanced image properties (dimensions, format, etc.) will remain a mystery."
            metadata["error"] = f"{metadata['error']}; {err_msg}" if metadata['error'] else err_msg
            print_warning("Pillow library not found. Image dimensions and other properties will not be extracted. Install it using: pip install Pillow")

    except OSError as e:
        err_msg = f"OS error accessing file: {e}"
        metadata["error"] = f"{metadata['error']}; {err_msg}" if metadata['error'] else err_msg
        print_error(f"Error accessing {metadata['filename']} for metadata: {e}")
    except Exception as e:
        err_msg = f"An unforeseen error occurred during metadata extraction: {e}"
        metadata["error"] = f"{metadata['error']}; {err_msg}" if metadata['error'] else err_msg
        print_error(f"Unexpected error processing {metadata['filename']}: {e}")

    return metadata


def extract_metadata_parallel(image_paths: List[str], query_based_subdir_name: str) -> List[Dict[str, Any]]:
    """Extracts local file metadata for multiple images concurrently, harnessing parallel energies."""
    if not image_paths:
        return []

    if not PIL_AVAILABLE:
        print_warning("Pillow library not found. Image dimensions and other advanced properties will not be extracted. Install it using: pip install Pillow")

    metadata_list: List[Dict[str, Any]] = []
    # Adjusting workers based on the nature of the task (I/O bound)
    max_workers = min(16, (os.cpu_count() or 1) * 2 + 4)

    print_info(f"Extracting intrinsic properties from {len(image_paths)} local manifestations using up to {max_workers} parallel threads...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submitting tasks to the ethereal workers
        futures = {executor.submit(get_local_file_metadata, path, query_based_subdir_name): path for path in image_paths}

        # Processing results as they emerge from the ether with a progress sigil
        for future in tqdm(futures, total=len(image_paths), desc=Fore.BLUE + "📄 Extracting Metadata", unit="file", ncols=100, leave=False):
            original_path = futures[future]
            try:
                result = future.result()
                metadata_list.append(result)
            except Exception as e:
                print_error(f"Error processing future result for {os.path.basename(original_path)}: {e}")
                metadata_list.append({
                    "file_path": original_path,
                    "filename": os.path.basename(original_path),
                    "query_based_subdir_name": query_based_subdir_name,
                    "file_size_bytes": None,
                    "dimensions": None,
                    "width": None, "height": None, "format": None, "mode": None, "dpi": None,
                    "is_animated": False, "frame_count": None,
                    "error": f"Future processing error: {e}"
                })

    print_success(f"Metadata extraction completed for {len(metadata_list)} manifestations.")
    return metadata_list


def save_metadata(metadata_list: List[Dict[str, Any]], output_dir_base: str, query: str) -> bool:
    """Records the collected metadata into a JSON scroll within the base output directory."""
    if not metadata_list:
        print_warning("No metadata collected to inscribe.")
        return False

    sanitized_query = sanitize_filename(query)
    if not sanitized_query:
        sanitized_query = "unknown_query"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    metadata_filename = f"{METADATA_FILENAME_PREFIX}{sanitized_query}_{timestamp}.json"
    metadata_file_path = os.path.join(output_dir_base, metadata_filename)

    print_info(f"Attempting to inscribe metadata to: {metadata_file_path}")
    try:
        if not create_directory(output_dir_base): # Ensuring the scroll chamber exists
             print_error(f"Cannot inscribe metadata, base output directory '{output_dir_base}' does not exist and couldn't be forged.")
             return False

        with open(metadata_file_path, "w", encoding='utf-8') as f:
            json.dump(metadata_list, f, indent=4, ensure_ascii=False)
        print_success(f"Metadata inscribed successfully to: {metadata_file_path}")
        return True
    except OSError as e:
        print_error(f"Failed to inscribe metadata to {metadata_file_path}: {e}")
        return False
    except Exception as e:
        print_error(f"An unexpected error occurred while inscribing metadata: {e}")
        return False


def generate_master_manifest(output_dir_base: str) -> None:
    """
    Scans all individual metadata JSON scrolls and combines them into a single grand ledger.
    This master ledger will be the key to the image_viewer.html's scrying pool.
    """
    print_header("✨ Forging the Master Image Manifest ✨")
    master_manifest_data: List[Dict[str, Any]] = []
    metadata_files_found = glob.glob(os.path.join(output_dir_base, f"{METADATA_FILENAME_PREFIX}*.json"))

    if not metadata_files_found:
        print_warning(f"No individual metadata JSON scrolls found in '{output_dir_base}'. The Master Manifest will be empty.")
        return

    print_info(f"Discovered {len(metadata_files_found)} individual metadata scrolls to merge.")

    # Use a set to track unique file paths to avoid duplicates in the master manifest
    # This can happen if scrapey.py is run multiple times for the same query
    unique_entries: Dict[str, Dict[str, Any]] = {}

    for meta_file_path in tqdm(metadata_files_found, desc=Fore.BLUE + "Merging Metadata Scrolls", unit="file", ncols=100, leave=False):
        try:
            with open(meta_file_path, "r", encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    for entry in data:
                        # Use a unique identifier for each image, e.g., its full relative path
                        # Assuming 'file_path' is unique and relative to the base output dir
                        if 'file_path' in entry:
                            # Normalize path for consistent keys (e.g., replace backslashes on Windows)
                            normalized_path = os.path.normpath(entry['file_path'])
                            unique_entries[normalized_path] = entry
                else:
                    print_warning(f"Skipping malformed metadata scroll (not a list): {os.path.basename(meta_file_path)}")
        except json.JSONDecodeError as e:
            print_error(f"Error deciphering JSON from {os.path.basename(meta_file_path)}: {e}")
        except Exception as e:
            print_error(f"An unexpected error occurred while reading {os.path.basename(meta_file_path)}: {e}")

    master_manifest_data = list(unique_entries.values())

    master_manifest_path = os.path.join(output_dir_base, MASTER_MANIFEST_FILENAME)

    try:
        with open(master_manifest_path, "w", encoding='utf-8') as f:
            json.dump(master_manifest_data, f, indent=4, ensure_ascii=False)
        print_success(f"Master manifest forged successfully: {master_manifest_path} (Contains {len(master_manifest_data)} unique entries).")
    except OSError as e:
        print_error(f"Failed to forge master manifest to {master_manifest_path}: {e}")
    except Exception as e:
        print_error(f"An unexpected error occurred while forging master manifest: {e}")


# --- User Input Function: The Seeker's Intent ---
def get_user_input() -> Dict[str, Any]:
    """Gathers and validates the seeker's intent for the scrying process."""
    inputs: Dict[str, Any] = {}

    print_header("🔍 Articulating Your Intent")

    # Query: The focus of the scrying
    while True:
        query = input(Fore.CYAN + "⌨️  Enter your Search Query (e.g., 'red cars', 'mountain landscape'): " + Fore.WHITE).strip()
        if query:
            inputs["query"] = query
            break
        else:
            print_warning("Your search query cannot be an empty whisper.")

    # Output Directory: The destined chamber for manifestations
    output_dir_base = input(
        Fore.CYAN + f"📂 Enter Base Output Directory (images will manifest in a subfolder named after your query here) [default: {DEFAULT_OUTPUT_DIR}]: " + Fore.WHITE
    ).strip() or DEFAULT_OUTPUT_DIR
    inputs["output_dir_base"] = output_dir_base

    # Numerical Inputs: Limits and Patience
    while True:
        try:
            limit_str = input(Fore.CYAN + "🔢 Max Images to Manifest (e.g., 50): " + Fore.WHITE).strip()
            limit = int(limit_str)
            if limit > 0:
                inputs["limit"] = limit
                break
            else:
                print_warning("The number of images must be a positive integer.")
        except ValueError:
            print_error("Invalid input. Please enter a whole number.")

    while True:
        try:
            timeout_str = input(Fore.CYAN + "⏳ Download Timeout per image (seconds, e.g., 60): " + Fore.WHITE).strip()
            timeout = int(timeout_str)
            if timeout > 0:
                inputs["timeout"] = timeout
                break
            else:
                print_warning("Timeout duration must be positive.")
        except ValueError:
            print_error("Invalid input. Please enter a whole number.")

    # Adult Filter: Veiling or Unveiling
    adult_filter_off_input = input(Fore.CYAN + "🔞 Disable the adult filter? (y/N): " + Fore.WHITE).strip().lower()
    inputs["adult_filter_off"] = adult_filter_off_input == 'y'

    # Filter Inputs: Fine-tuning the Scrying Lens
    print_header("🎨 Ethereal Search Filters (Optional - Press Enter to pass)")
    print_info("Examples: Size:Large, Type:Photo, Layout:Wide, License:Share")
    inputs["filters"] = {
        "size": input(
            Fore.CYAN + "📏 Size (Small, Medium, Large, Wallpaper): " + Fore.WHITE
        ).strip(),
        "color": input(
            Fore.CYAN + "🎨 Color (ColorOnly, Monochrome): " + Fore.WHITE
        ).strip(),
        "type": input(
            Fore.CYAN + "🖼️  Type (Photo, Clipart, Line, AnimatedGif, Transparent): " + Fore.WHITE
        ).strip(),
        "layout": input(
            Fore.CYAN + "📐 Layout (Square, Wide, Tall): " + Fore.WHITE
        ).strip(),
        "people": input(
            Fore.CYAN + "👥 People (Face, Portrait): " + Fore.WHITE
        ).strip(),
        "date": input(
            Fore.CYAN + "📅 Date (PastDay, PastWeek, PastMonth, PastYear): " + Fore.WHITE
        ).strip(),
        "license": input(
            Fore.CYAN + "📜 License (Any, Public, Share, ShareCommercially, Modify, ModifyCommercially): " + Fore.WHITE
        ).strip(),
    }
    inputs["site_filter"] = input(
            Fore.CYAN + "🌐 Filter by specific site (e.g., wikipedia.org, flickr.com): " + Fore.WHITE
        ).strip()

    return inputs


# --- Main Application: The Orchestration of the Ritual ---
def main() -> None:
    """Main function to orchestrate the image scrying and manifestation process."""
    start_time = datetime.now()
    print_header("🌟 Enhanced Bing Image Scrying & Manifestation 🌟")
    print_info("Dependencies: requests, bing-image-downloader, colorama, tqdm, Pillow")
    if not PIL_AVAILABLE:
        print_warning("Pillow library not installed. Image dimensions and other advanced properties cannot be extracted. Install it using: pip install Pillow")

    try:
        user_inputs = get_user_input()

        query: str = user_inputs["query"]
        output_dir_base: str = user_inputs["output_dir_base"]
        limit: int = user_inputs["limit"]
        timeout: int = user_inputs["timeout"]
        adult_filter_off: bool = user_inputs["adult_filter_off"]
        filters_dict: Dict[str, str] = user_inputs["filters"]
        site_filter: Optional[str] = user_inputs["site_filter"]

        # Ensuring the base manifestation chamber exists *before* scrying
        if not create_directory(output_dir_base):
            print_error(f"Cannot proceed without the base manifestation chamber: {output_dir_base}")
            sys.exit(1)

        # Preparing the filter string for the scrying lens
        filter_string = apply_filters(**filters_dict)

        print_header("🚀 Initiating the Scrying Process")

        # --- Scrying (Download) ---
        # This returns the paths to successfully manifested images
        downloaded_file_paths = download_images_with_bing(
            query, output_dir_base, limit, timeout, adult_filter_off, filter_string, site_filter
        )

        if not downloaded_file_paths:
            print_warning("No images were manifested or discovered. Verify your query, filters, or permissions. Exiting gracefully.")
            generate_master_manifest(output_dir_base) # Still attempt to update the grand ledger
            return

        # The downloader creates a sub-chamber based on effective_query (if site filter used) or query.
        # This name is needed for metadata and locating files.
        effective_query_for_subdir = query
        if site_filter:
            effective_query_for_subdir += f" site:{site_filter}"
        query_based_subdir_name_for_metadata = effective_query_for_subdir

        # --- Renaming Ritual ---
        # The renaming happens in-place, transforming the filenames.
        renamed_paths = rename_files(downloaded_file_paths, query)

        # renamed_paths from the new rename_files function contains final paths of successfully processed files
        # (either new name or original name if rename failed/skipped but file exists).
        # It will be shorter than downloaded_file_paths if some files disappeared before renaming.
        paths_for_metadata = renamed_paths # Directly use the result

        # Fallback logic similar to bimgx.py, if rename_files returns empty but there were downloads
        if not paths_for_metadata and downloaded_file_paths:
            print_warning("Renaming ritual yielded no usable file paths. "
                          "Attempting metadata extraction on original downloaded paths if they still exist.")
            paths_for_metadata = [p for p in downloaded_file_paths if os.path.exists(p) and os.path.isfile(p)]

        # --- Extracting Metadata ---
        metadata = []
        if paths_for_metadata:
             metadata = extract_metadata_parallel(paths_for_metadata, query_based_subdir_name_for_metadata)
        else:
            print_warning("No valid file paths remained after scrying/renaming to extract metadata from.")

        # --- Inscribing Metadata ---
        if metadata:
            save_metadata(metadata, output_dir_base, query)
        else:
            print_warning("No metadata was generated for inscription.")

        # --- Forging the Master Manifest (The Grand Ledger) ---
        generate_master_manifest(output_dir_base)

        # --- Final Revelation: Summary of the Ritual ---
        print_header("📊 Revelation Summary")
        total_downloaded = len(downloaded_file_paths)
        total_renamed = len(renamed_paths)
        total_metadata_extracted = len(metadata)
        errors_in_metadata = sum(1 for item in metadata if item.get("error"))

        print_info(f"Initial manifestations found after scrying: {total_downloaded}")
        print_info(f"Manifestations successfully processed for renaming: {total_renamed}")
        print_info(f"Metadata records inscribed: {total_metadata_extracted}")
        if errors_in_metadata > 0:
            print_warning(f"Encountered errors during metadata extraction for {errors_in_metadata} manifestation(s). Consult the individual scroll: '{METADATA_FILENAME_PREFIX}{sanitize_filename(query)}_*.json'.")

        if metadata:
            print_info("First few metadata revelations:")
            for item in metadata[:min(5, len(metadata))]:
                size_str = f"{item.get('file_size_bytes', 'N/A')} bytes"
                dim_str = item.get('dimensions', 'N/A')
                format_str = item.get('format', 'N/A')
                mode_str = item.get('mode', 'N/A')
                frames_str = f"Frames: {item['frame_count']}" if item.get('is_animated') else ""
                error_str = f"{Fore.RED}(Error: {item['error']}){Style.RESET_ALL}" if item.get("error") else ""
                print(f"  - {Fore.MAGENTA}{item['filename']}{Style.RESET_ALL}: Dims: {dim_str}, Format: {format_str}, Mode: {mode_str} {frames_str} {error_str}")
            if len(metadata) > 5:
                print(f"  ... and {len(metadata) - 5} more secrets.")
        else:
            print_warning("No metadata was extracted or inscribed.")

        end_time = datetime.now()
        duration = end_time - start_time
        print_success(f"\nOperation completed in {duration.total_seconds():.2f} seconds! The ritual is complete.")

    except KeyboardInterrupt:
        print_error("\nOperation cancelled by the seeker's will (Ctrl+C detected). The ritual is halted.")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nAn unexpected critical anomaly occurred during the ritual: {e}")
        logger.exception("Unhandled exception trace:")
        sys.exit(1)


if __name__ == "__main__":
    main()
