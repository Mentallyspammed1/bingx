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

import glob  # Channeling the glob spirits for manifest generation
import json
import logging
import os
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from typing import Any  # Tuple removed

# Third-party Libraries
# requests is used implicitly by bing_image_downloader
from bing_image_downloader import downloader
from colorama import Back, Fore, init, Style
from tqdm import tqdm

# Attempt to import Pillow for image metadata; provide guidance if missing
try:
    from PIL import Image, ImageSequence, UnidentifiedImageError
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
    """Prints an informational message directly, a guiding light.
    Use logger.info for messages that should be part of the standard log output.
    This function is for direct, transient user feedback not intended for log files.
    """
    print(Fore.CYAN + Style.NORMAL + f"➤ {text}")


# --- Utility Functions: Tools of the Trade ---
def sanitize_filename(name: str) -> str:
    """Cleanses a string for use as a filename, removing impurities and truncating."""
    # Removing characters that might displease file systems
    sanitized = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
    # Replacing spaces with underscores for harmony
    sanitized = "_".join(filter(None, sanitized.split(" ")))
    sanitized = "_".join(filter(None, sanitized.split("_"))) # Normalize multiple underscores
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


def rename_files(file_paths: list[str], base_query: str) -> list[str]:
    """Renames downloaded files sequentially with a sanitized query prefix.
    Returns a list of final paths for files that were processed.
    If a file is renamed, its new path is in the list.
    If renaming failed or was skipped for an existing file, its original path is in the list.
    Files from input that were not found or were not files are skipped and not in the output list.
    (Adopted from bimgx.py for robustness)
    """
    final_paths_after_rename: list[str] = []
    if not file_paths:
        print_warning("No file paths provided for the renaming ritual.") # Retained scrapey.py's wording
        return []

    sanitized_query: str = sanitize_filename(base_query)
    if not sanitized_query:
        sanitized_query = "image"  # Fallback base name
        print_warning(f"Query '{base_query}' sanitized to empty string, using fallback 'image'.")

    first_valid_dir: str | None = next((os.path.dirname(p) for p in file_paths if p), None)
    if first_valid_dir is None and file_paths:
         print_error("Cannot discern the directory for renaming files. All paths are invalid.") # Retained scrapey.py's wording
         return list(file_paths)
    if first_valid_dir is None and not file_paths:
         return []

    dir_name: str = first_valid_dir if first_valid_dir is not None else "."

    logger.info(f"Imbuing {len(file_paths)} files in '{dir_name}' with the prefix '{sanitized_query}'...")

    sorted_file_paths: list[str] = sorted(file_paths) # bimgx.py sorts for consistency

    actual_renames_count: int = 0

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

            _, ext_str = os.path.splitext(old_path) # Renamed ext to ext_str to avoid conflict with any potential 'ext' module
            new_base_name: str = f"{sanitized_query}_{idx}"
            new_filename: str = f"{new_base_name}{ext_str}"
            potential_new_path: str = os.path.join(dir_name, new_filename)

            target_path_for_rename: str = potential_new_path
            collision_counter: int = 1

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

                new_filename = f"{new_base_name}_{collision_counter}{ext_str}"
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
    filters: list[str] = []
    # Mapping seeker-friendly keys to Bing's arcane filter syntax
    filter_map: dict[str, str] = {
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
            formatted_value: str = value.strip()
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

            template: str | None = filter_map.get(key)
            if template:
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
    site_filter: str | None = None
) -> list[str]:
    """Summons images from the Bing realm and returns their manifested paths."""
    effective_query: str = query
    if site_filter:
        # Weaving the site filter into the query string
        effective_query += f" site:{site_filter}"

    # The downloader creates a sub-chamber named after the 'query' argument given to it.
    # This is 'effective_query', which includes the site filter if provided.
    query_based_subdir_name: str = effective_query
    query_specific_output_dir: str = os.path.join(output_dir_base, query_based_subdir_name)

    downloaded_files: list[str] = []
    try:
        logger.info(f"Initiating scrying for query: '{Fore.YELLOW}{effective_query}{Style.RESET_ALL}'") # Added Style.RESET_ALL
        logger.info(f"Manifesting images into: '{query_specific_output_dir}'")
        logger.info(f"Applying ethereal filters: '{extra_filters}'" if extra_filters else "No extra filters applied.")

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
        logger.info(f"Searching for manifested files in: {query_specific_output_dir}")
        if os.path.isdir(query_specific_output_dir):
            found_count: int = 0
            for filename_str in os.listdir(query_specific_output_dir): # Renamed filename to filename_str
                full_path: str = os.path.join(query_specific_output_dir, filename_str)
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


def get_local_file_metadata(file_path: str, query_based_subdir_name: str) -> dict[str, Any]:
    """
    Extracts comprehensive intrinsic properties from a local image manifestation.
    Includes size, dimensions, format, mode, DPI, and GIF frame count/animation status.
    """
    metadata: dict[str, Any] = {
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
        if PIL_AVAILABLE and Image and ImageSequence: # Added ImageSequence to condition
            try:
                with Image.open(file_path) as img: # type: ignore[attr-defined] # img is of type PIL.Image.Image
                    img_pil: Image.Image = img # type: ignore[attr-defined]
                    metadata["width"], metadata["height"] = img_pil.size
                    metadata["dimensions"] = f"{img_pil.width}x{img_pil.height}"
                    metadata["format"] = img_pil.format
                    metadata["mode"] = img_pil.mode
                    metadata["dpi"] = img_pil.info.get("dpi") # DPI is a tuple (x, y)

                    # Check for animation (primarily for GIFs)
                    if img_pil.format == "GIF":
                        try:
                            # Attempt to iterate through frames to count them
                            frame_count: int = 0
                            for _frame in ImageSequence.Iterator(img_pil): # type: ignore[attr-defined]
                                frame_count += 1
                            metadata["frame_count"] = frame_count
                            metadata["is_animated"] = frame_count > 1
                        except Exception as gif_err:
                            err_msg_gif: str = f"GIF frame count error: {gif_err}"
                            metadata["error"] = f"{metadata['error']}; {err_msg_gif}" if metadata["error"] else err_msg_gif
                            logger.warning(f"Error counting GIF frames for {metadata['filename']}: {gif_err}")

            except UnidentifiedImageError: # type: ignore[misc] # UnidentifiedImageError is defined if PIL_AVAILABLE
                err_msg_unidentified: str = "Cannot identify image file (Pillow's gaze is clouded). Possibly corrupted or not an image."
                metadata["error"] = f"{metadata['error']}; {err_msg_unidentified}" if metadata["error"] else err_msg_unidentified
                logger.warning(f"Unidentified image format for {metadata['filename']}.")
            except Exception as img_err:
                err_msg_pil: str = f"Error reading image properties with Pillow: {img_err}"
                metadata["error"] = f"{metadata['error']}; {err_msg_pil}" if metadata["error"] else err_msg_pil
                logger.warning(f"Could not discern full image properties for {metadata['filename']}: {img_err}")
        elif not PIL_AVAILABLE:
            err_msg_no_pil: str = "Pillow library not installed. Advanced image properties (dimensions, format, etc.) will remain a mystery."
            # This specific print_warning is fine here as it's inside a per-file function and might be useful if main check was missed
            print_warning("Pillow library not found. Image dimensions and other properties will not be extracted. Install it using: pip install Pillow")
            metadata["error"] = f"{metadata['error']}; {err_msg_no_pil}" if metadata["error"] else err_msg_no_pil


    except OSError as e_os:
        err_msg_os: str = f"OS error accessing file: {e_os}"
        metadata["error"] = f"{metadata['error']}; {err_msg_os}" if metadata["error"] else err_msg_os
        print_error(f"Error accessing {metadata['filename']} for metadata: {e_os}")
    except Exception as e_gen:
        err_msg_general: str = f"An unforeseen error occurred during metadata extraction: {e_gen}"
        metadata["error"] = f"{metadata['error']}; {err_msg_general}" if metadata["error"] else err_msg_general
        print_error(f"Unexpected error processing {metadata['filename']}: {e_gen}")

    return metadata


def extract_metadata_parallel(image_paths: list[str], query_based_subdir_name: str) -> list[dict[str, Any]]:
    """Extracts local file metadata for multiple images concurrently, harnessing parallel energies."""
    if not image_paths:
        return []

    if not PIL_AVAILABLE:
        print_warning("Pillow library not found. Image dimensions and other advanced properties will not be extracted. Install it using: pip install Pillow")

    metadata_list: list[dict[str, Any]] = []
    # Adjusting workers based on the nature of the task (I/O bound)
    max_workers: int = min(16, (os.cpu_count() or 1) * 2 + 4)

    logger.info(f"Extracting intrinsic properties from {len(image_paths)} local manifestations using up to {max_workers} parallel threads...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submitting tasks to the ethereal workers
        # Using Future type hint for keys in the dictionary
        futures: dict[Future[dict[str, Any]], str] = {
            executor.submit(get_local_file_metadata, path, query_based_subdir_name): path for path in image_paths
        }

        # Processing results as they emerge from the ether with a progress sigil
        for future in tqdm(futures, total=len(image_paths), desc=Fore.BLUE + "📄 Extracting Metadata", unit="file", ncols=100, leave=False):
            original_path: str = futures[future]
            try:
                result: dict[str, Any] = future.result()
                metadata_list.append(result)
            except Exception as e:
                print_error(f"Error processing future result for {os.path.basename(original_path)}: {e}")
                # Create a fallback metadata entry in case of error during future.result()
                error_metadata_entry: dict[str, Any] = {
                    "file_path": original_path, # The original path of the file
                    "filename": os.path.basename(original_path), # The base name of the file
                    "query_based_subdir_name": query_based_subdir_name, # The subdirectory name based on the query
                    "file_size_bytes": None, # File size in bytes, None if not determined
                    "dimensions": None,  # Image dimensions as "WidthxHeight", None if not determined
                    "width": None, # Image width in pixels, None if not determined
                    "height": None, # Image height in pixels, None if not determined
                    "format": None,      # Image format (e.g., 'JPEG', 'PNG'), None if not determined
                    "mode": None,        # Image mode (e.g., 'RGB', 'L'), None if not determined
                    "dpi": None,         # Image DPI as a tuple (x_dpi, y_dpi), None if not determined
                    "is_animated": False, # True if the image is animated, False otherwise
                    "frame_count": None, # Number of frames if animated, None otherwise
                    "error": f"Future processing error: {e}" # Error message if processing failed
                }
                metadata_list.append(error_metadata_entry)

    print_success(f"Metadata extraction completed for {len(metadata_list)} manifestations.")
    return metadata_list


def save_metadata(metadata_list: list[dict[str, Any]], output_dir_base: str, query: str) -> bool:
    """Records the collected metadata into a JSON scroll within the base output directory."""
    if not metadata_list:
        print_warning("No metadata collected to inscribe.")
        return False

    sanitized_query_str: str = sanitize_filename(query) # Renamed sanitized_query to avoid conflict
    if not sanitized_query_str:
        sanitized_query_str = "unknown_query"
    timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    metadata_filename: str = f"{METADATA_FILENAME_PREFIX}{sanitized_query_str}_{timestamp}.json"
    metadata_file_path: str = os.path.join(output_dir_base, metadata_filename)

    logger.info(f"Attempting to inscribe metadata to: {metadata_file_path}")
    try:
        if not create_directory(output_dir_base): # Ensuring the scroll chamber exists
             print_error(f"Cannot inscribe metadata, base output directory '{output_dir_base}' does not exist and couldn't be forged.")
             return False

        with open(metadata_file_path, "w", encoding="utf-8") as f:
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
    master_manifest_data: list[dict[str, Any]] = [] # Holds all unique image metadata entries
    metadata_files_found: list[str] = glob.glob(os.path.join(output_dir_base, f"{METADATA_FILENAME_PREFIX}*.json"))

    if not metadata_files_found:
        print_warning(f"No individual metadata JSON scrolls found in '{output_dir_base}'. The Master Manifest will be empty.")
        return

    logger.info(f"Discovered {len(metadata_files_found)} individual metadata scrolls to merge.")

    # Using a dictionary to store unique entries, with normalized file path as key.
    # This handles cases where the same file might appear in multiple metadata JSONs
    # (e.g., if script is run multiple times for same query before manifest generation for that query).
    unique_entries: dict[str, dict[str, Any]] = {}

    for meta_file_path_str in tqdm(metadata_files_found, desc=Fore.BLUE + "Merging Metadata Scrolls", unit="file", ncols=100, leave=False): # Renamed meta_file_path
        try:
            with open(meta_file_path_str, encoding="utf-8") as f:
                # Load the JSON data, which should be a list of metadata dictionaries
                data_from_scroll: list[dict[str, Any]] = json.load(f)
                if isinstance(data_from_scroll, list):
                    for entry in data_from_scroll:
                        if isinstance(entry, dict) and "file_path" in entry and isinstance(entry["file_path"], str):
                            # Normalize the file path to use as a unique key
                            # This helps avoid duplicates if paths are slightly different but refer to the same file
                            # (e.g. mixed slashes on different OS, though os.path.join should mostly handle this)
                            normalized_path: str = os.path.normpath(entry["file_path"])
                            unique_entries[normalized_path] = entry
                        else:
                            print_warning(f"Skipping malformed entry in {os.path.basename(meta_file_path_str)}: entry is not a dict or missing 'file_path'.")
                else:
                    print_warning(f"Skipping malformed metadata scroll (not a list): {os.path.basename(meta_file_path_str)}")
        except json.JSONDecodeError as e_json:
            print_error(f"Error deciphering JSON from {os.path.basename(meta_file_path_str)}: {e_json}")
        except Exception as e_read:
            print_error(f"An unexpected error occurred while reading {os.path.basename(meta_file_path_str)}: {e_read}")

    master_manifest_data = list(unique_entries.values()) # Convert unique entries dict values to a list

    master_manifest_file_path: str = os.path.join(output_dir_base, MASTER_MANIFEST_FILENAME) # Renamed master_manifest_path

    try:
        with open(master_manifest_file_path, "w", encoding="utf-8") as f:
            json.dump(master_manifest_data, f, indent=4, ensure_ascii=False)
        print_success(f"Master manifest forged successfully: {master_manifest_file_path} (Contains {len(master_manifest_data)} unique entries).")
    except OSError as e:
        print_error(f"Failed to forge master manifest to {master_manifest_path}: {e}")
    except Exception as e:
        print_error(f"An unexpected error occurred while forging master manifest: {e}")


# --- User Input Function: The Seeker's Intent ---
def get_user_input() -> dict[str, Any]:
    """Gathers and validates the seeker's intent for the scrying process."""
    inputs: dict[str, Any] = {}

    print_header("🔍 Articulating Your Intent")

    # Query: The focus of the scrying
    while True:
        query = input(Fore.CYAN + "⌨️  Enter your Search Query (e.g., 'red cars', 'mountain landscape'): " + Fore.WHITE).strip()
        if query:
            inputs["query"] = query
            break
        print_warning("Your search query cannot be an empty whisper.")

    # Output Directory: The destined chamber for manifestations
    output_dir_base = input(
        Fore.CYAN + f"📂 Enter Base Output Directory (images will manifest in a subfolder named after your query here) [default: {DEFAULT_OUTPUT_DIR}]: " + Fore.WHITE
    ).strip() or DEFAULT_OUTPUT_DIR
    inputs["output_dir_base"] = output_dir_base

    # Numerical Inputs: Limits and Patience
    while True:
        try:
            limit_str = input(Fore.CYAN + "🔢 Enter Max Images to Manifest (e.g., 50): " + Fore.WHITE).strip()
            limit = int(limit_str)
            if limit > 0:
                inputs["limit"] = limit
                break
            print_warning("The number of images must be a positive integer.")
        except ValueError:
            print_error("Invalid input. Please enter a whole number.")

    while True:
        try:
            timeout_str = input(Fore.CYAN + "⏳ Enter Download Timeout per image (seconds, e.g., 60): " + Fore.WHITE).strip()
            timeout = int(timeout_str)
            if timeout > 0:
                inputs["timeout"] = timeout
                break
            print_warning("Timeout duration must be positive.")
        except ValueError:
            print_error("Invalid input. Please enter a whole number.")

    # Adult Filter: Veiling or Unveiling
    adult_filter_off_input = input(Fore.CYAN + "🔞 Disable the adult filter? (y/N): " + Fore.WHITE).strip().lower()
    inputs["adult_filter_off"] = adult_filter_off_input == "y"

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
        # This initial check is crucial for user awareness.
        print_warning("Pillow library not installed. Image dimensions and other advanced properties cannot be extracted. Install it using: pip install Pillow")

    try:
        user_inputs: dict[str, Any] = get_user_input()

        query: str = user_inputs["query"]
        output_dir_base_str: str = user_inputs["output_dir_base"] # Renamed output_dir_base
        limit_val: int = user_inputs["limit"] # Renamed limit
        timeout_val: int = user_inputs["timeout"] # Renamed timeout
        adult_filter_off_bool: bool = user_inputs["adult_filter_off"] # Renamed adult_filter_off
        filters_dict_map: dict[str, str] = user_inputs["filters"] # Renamed filters_dict
        site_filter_str: str | None = user_inputs["site_filter"] # Renamed site_filter

        # Ensuring the base manifestation chamber exists *before* scrying
        if not create_directory(output_dir_base_str):
            print_error(f"Cannot proceed without the base manifestation chamber: {output_dir_base_str}")
            sys.exit(1)

        # Preparing the filter string for the scrying lens
        filter_string: str = apply_filters(**filters_dict_map)

        print_header("🚀 Initiating the Scrying Process")
        # No print_info here, download_images_with_bing has its own logger.info for initiation

        # --- Scrying (Download) ---
        # This returns the paths to successfully manifested images
        downloaded_file_paths: list[str] = download_images_with_bing(
            query, output_dir_base_str, limit_val, timeout_val, adult_filter_off_bool, filter_string, site_filter_str
        )

        if not downloaded_file_paths:
            print_warning("No images were manifested or discovered. Verify your query, filters, or permissions. Exiting gracefully.")
            generate_master_manifest(output_dir_base_str) # Still attempt to update the grand ledger
            return

        # Determine the subdirectory name used by the downloader, which is needed for metadata.
        # This incorporates the site filter if one was used.
        effective_query_for_subdir: str = query
        if site_filter_str:
            effective_query_for_subdir += f" site:{site_filter_str}"
        # This is the name of the folder within output_dir_base where images for this query are stored.
        query_based_subdir_name_for_metadata: str = effective_query_for_subdir


        # --- Renaming Ritual ---
        # The renaming happens in-place, transforming the filenames using the original query (without site:)
        renamed_paths: list[str] = rename_files(downloaded_file_paths, query)

        # renamed_paths from the new rename_files function contains final paths of successfully processed files
        # (either new name or original name if rename failed/skipped but file exists).
        # It will be shorter than downloaded_file_paths if some files disappeared before renaming.
        paths_for_metadata: list[str] = renamed_paths # Use the paths of renamed (or original if rename failed) files

        # Fallback: If renaming somehow resulted in no paths, but we had downloaded files,
        # try to use the original downloaded paths for metadata extraction.
        # This ensures that if renaming fails catastrophically for all files,
        # we don't lose the chance to get metadata for successfully downloaded files.
        if not paths_for_metadata and downloaded_file_paths:
            print_warning("Renaming ritual yielded no usable file paths. "
                          "Attempting metadata extraction on original downloaded paths if they still exist.")
            paths_for_metadata = [p for p in downloaded_file_paths if os.path.exists(p) and os.path.isfile(p)]

        # --- Extracting Metadata ---
        extracted_metadata_list: list[dict[str, Any]] = [] # Renamed metadata
        if paths_for_metadata:
             # Pass query_based_subdir_name_for_metadata so each metadata entry knows its query-specific subfolder
             extracted_metadata_list = extract_metadata_parallel(paths_for_metadata, query_based_subdir_name_for_metadata)
        else:
            print_warning("No valid file paths remained after scrying/renaming to extract metadata from.")

        # --- Inscribing Metadata ---
        if extracted_metadata_list:
            save_metadata(extracted_metadata_list, output_dir_base_str, query)
        else:
            print_warning("No metadata was generated for inscription.")

        # --- Forging the Master Manifest (The Grand Ledger) ---
        # This should always run to ensure the master manifest is up-to-date,
        # even if the current run yielded no new images or metadata.
        generate_master_manifest(output_dir_base_str)

        # --- Final Revelation: Summary of the Ritual ---
        print_header("📊 Revelation Summary")
        total_downloaded_count: int = len(downloaded_file_paths) # Renamed total_downloaded
        total_renamed_count: int = len(renamed_paths) # Renamed total_renamed
        total_metadata_extracted_count: int = len(extracted_metadata_list) # Renamed total_metadata_extracted
        errors_in_metadata_count: int = sum(1 for item in extracted_metadata_list if item.get("error")) # Renamed errors_in_metadata

        # These are part of the final summary, direct print to user is fine.
        print_info(f"Initial manifestations found after scrying: {total_downloaded_count}")
        print_info(f"Manifestations successfully processed for renaming: {total_renamed_count}")
        print_info(f"Metadata records inscribed: {total_metadata_extracted_count}")
        if errors_in_metadata_count > 0:
            print_warning(f"Encountered errors during metadata extraction for {errors_in_metadata_count} manifestation(s). Consult the individual scroll: '{METADATA_FILENAME_PREFIX}{sanitize_filename(query)}_*.json'.")

        if extracted_metadata_list:
            # This is part of the final summary, direct print to user is fine.
            print_info("First few metadata revelations:")
            for item_metadata in extracted_metadata_list[:min(5, len(extracted_metadata_list))]: # Renamed item
                size_str: str = f"{item_metadata.get('file_size_bytes', 'N/A')} bytes"
                dim_str: str = item_metadata.get("dimensions", "N/A")
                format_str: str = item_metadata.get("format", "N/A")
                mode_str: str = item_metadata.get("mode", "N/A")
                frames_str: str = f"Frames: {item_metadata.get('frame_count')}" if item_metadata.get("is_animated") else ""
                error_str: str = f"{Fore.RED}(Error: {item_metadata.get('error')}){Style.RESET_ALL}" if item_metadata.get("error") else ""
                print(f"  - {Fore.MAGENTA}{item_metadata.get('filename')}{Style.RESET_ALL}: Dims: {dim_str}, Format: {format_str}, Mode: {mode_str} {frames_str} {error_str}")
            if len(extracted_metadata_list) > 5:
                print(f"  ... and {len(extracted_metadata_list) - 5} more secrets.")
        else:
            print_warning("No metadata was extracted or inscribed.")

        end_time: datetime = datetime.now()
        duration: timedelta = end_time - start_time # type: ignore # timedelta is imported with datetime
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
