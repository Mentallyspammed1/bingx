#!/usr/bin/env python3

"""Enhanced Bing Image Downloader Script
-------------------------------------
Downloads images from Bing based on user queries and filters,
renames them sequentially within a query-specific subfolder,
extracts comprehensive local file metadata (size, dimensions, format, mode,
DPI, GIF frame count, animation status),
saves the metadata to a JSON file in the base output directory,
and generates a master manifest JSON file for web viewing.
Incorporates duplicate detection using perceptual hashing (pHash)
to prevent re-downloading or storing identical images.
"""

import argparse
import json
import logging
import os
import sys
from concurrent.futures import Future
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any

# Third-party Libraries
# requests is used implicitly by bing_image_downloader
# It's good practice to explicitly import if you're using it directly elsewhere too
import requests

try:
    from bing_image_downloader import downloader
except ImportError:
    print("Error: The 'bing-image-downloader' library is not installed.")
    print("Please install it using: pip install bing-image-downloader")
    sys.exit(1)

try:
    from colorama import Back
    from colorama import Fore
    from colorama import Style
    from colorama import init
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    class NoColor: # Dummy class if colorama is not available
        def __getattr__(self, name): return ""
    Fore = NoColor()
    Back = NoColor()
    Style = NoColor()
    def init(autoreset=True): pass # Dummy init

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    def tqdm(iterable, *args, **kwargs): return iterable # Dummy tqdm


# Attempt to import Pillow for image metadata; provide guidance if missing
try:
    from PIL import Image
    from PIL import ImageSequence
    from PIL import UnidentifiedImageError
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None  # type: ignore
    UnidentifiedImageError = None  # type: ignore
    ImageSequence = None # type: ignore

# Attempt to import imagehash for perceptual hashing
try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False
    imagehash = None # type: ignore


# --- Configuration: Tuning the Arcane Constants ---
class Config:
    """Centralized configuration for the image downloader script."""
    DEFAULT_OUTPUT_DIR: Path = Path("bing_images")
    MAX_FILENAME_LENGTH: int = 128
    METADATA_FILENAME_PREFIX: str = "metadata_query_"
    MASTER_MANIFEST_FILENAME: str = "master_manifest.json"
    # Increased workers for I/O bound task, capped at reasonable number
    MAX_METADATA_WORKERS: int = min(32, (os.cpu_count() or 1) * 2 + 8)
    RENAME_COLLISION_LIMIT: int = 500 # Increased collision limit for sequential renaming
    PHASH_THRESHOLD: int = 5 # pHash difference threshold for duplicates (lower is stricter)
    # File extensions to prioritize for image metadata extraction if there are multiple files
    # with the same base name but different extensions (e.g., .webp and .jpg)
    PREFERRED_IMAGE_EXTENSIONS: list[str] = [".png", ".jpeg", ".jpg", ".gif", ".webp", ".bmp"]


# --- Initialize Colorama: Infusing the Terminal with Light ---
if COLORAMA_AVAILABLE:
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
    } if COLORAMA_AVAILABLE else {} # Empty if colorama not available

    def format(self, record: logging.LogRecord) -> str:
        """Formats the log record with appropriate colors."""
        color_prefix = self.COLORS.get(record.levelname, "")
        color_suffix = Style.RESET_ALL if COLORAMA_AVAILABLE else ""
        log_fmt = (
            f"%(asctime)s - {color_prefix}%(levelname)s{color_suffix} - %(message)s"
        )
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


# Setup Logger: The Oracle's Voice
logger = logging.getLogger(__name__)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColoredFormatter())
    logger.addHandler(handler)
logger.setLevel(logging.INFO) # Default to INFO, can be overridden by args


# --- User Feedback Functions: Guiding the Seeker ---
def print_header(text: str) -> None:
    """Prints a formatted header, marking new phases of the ritual."""
    bar_char = "═"
    bar = bar_char * (len(text) + 4)
    print(f"{Fore.YELLOW}{Style.BRIGHT}\n{bar}")
    print(f"  {text}  ")
    print(f"{bar}{Style.RESET_ALL}\n")


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
    print(f"{Fore.CYAN}➤ {text}{Style.RESET_ALL}")


# --- Utility Functions: Tools of the Trade ---
def sanitize_filename(name: str) -> str:
    """Cleanses a string for use as a filename, removing impurities and truncating."""
    # Remove characters that might displease file systems, keep alphanumeric, spaces, underscores, hyphens
    sanitized = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).strip()
    # Replace sequences of spaces/underscores with a single underscore
    sanitized = "_".join(filter(None, sanitized.split())) # Splits by any whitespace and joins with '_'
    sanitized = "_".join(filter(None, sanitized.split("_"))) # Normalize multiple underscores
    # Limit length to prevent overflow
    return sanitized[:Config.MAX_FILENAME_LENGTH]


def create_directory(path: Path) -> bool:
    """Conjures a directory into existence if it does not already manifest."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as e:
        print_error(f"Failed to forge directory {path}: {e}")
        logger.debug(f"Directory creation error traceback: {e}", exc_info=True)
        return False


def rename_files(file_paths: list[Path], base_query: str) -> list[Path]:
    """Renames downloaded files sequentially with a sanitized query prefix.
    Returns a list of final paths for files that were successfully renamed or already had the target name.
    Files that could not be processed (e.g., not found, not a file, rename error) are excluded.
    """
    final_paths_after_rename: list[Path] = []
    if not file_paths:
        logger.debug("No file paths provided for the renaming ritual.")
        return []

    sanitized_query: str = sanitize_filename(base_query)
    if not sanitized_query:
        sanitized_query = "image"
        print_warning(f"Query '{base_query}' sanitized to empty string, using fallback 'image'.")

    # Determine the common parent directory for renaming
    # This assumes all files are in the same subdirectory which is true for bing-image-downloader's output
    first_valid_dir: Path | None = None
    for p in file_paths:
        if p.is_file():
            first_valid_dir = p.parent
            break

    if first_valid_dir is None:
        print_error("Cannot discern the directory for renaming files. All provided paths are invalid or not files.")
        return []

    dir_path: Path = first_valid_dir
    logger.info(f"Imbuing {len(file_paths)} files in '{dir_path}' with the prefix '{sanitized_query}'...")

    # Sort files to ensure consistent sequential naming (e.g., img1, img2, img3)
    sorted_file_paths: list[Path] = sorted(file_paths)
    actual_renames_count: int = 0

    tqdm_instance = tqdm(
        sorted_file_paths,
        desc=f"{Fore.BLUE}🔄 Renaming Files{Style.RESET_ALL}",
        unit="file",
        ncols=100,
        leave=False,
        disable=not TQDM_AVAILABLE
    )

    for idx, old_path in enumerate(tqdm_instance, start=1):
        current_file_final_path = old_path

        try:
            if not old_path.exists():
                logger.debug(f"File not found for renaming (already transformed or vanished?): {old_path.name}")
                continue
            if not old_path.is_file():
                logger.debug(f"Path is not a tangible file, skipping rename: {old_path.name}")
                continue

            ext_str = old_path.suffix
            new_base_name: str = f"{sanitized_query}_{idx:04d}"
            potential_new_path: Path = dir_path / f"{new_base_name}{ext_str}"

            target_path_for_rename: Path = potential_new_path
            collision_counter: int = 1

            while target_path_for_rename.exists():
                # Check if the file already has the desired name and points to the same inode
                # This prevents renaming a file onto itself unnecessarily.
                if old_path.samefile(target_path_for_rename):
                    logger.debug(f"Skipping rename for {old_path.name} as target name '{target_path_for_rename.name}' is identical and points to the same file.")
                    target_path_for_rename = old_path # Effectively, no rename
                    break # Exit collision loop

                # Generate a new name to resolve collision
                new_filename = f"{new_base_name}_{collision_counter}{ext_str}"
                target_path_for_rename = dir_path / new_filename
                collision_counter += 1
                if collision_counter > Config.RENAME_COLLISION_LIMIT:
                    print_error(f"Could not find a unique name for {old_path.name} after {Config.RENAME_COLLISION_LIMIT} attempts. Skipping rename for this file.")
                    target_path_for_rename = old_path # Retain original path on failure
                    break

            if old_path == target_path_for_rename:
                # File already has the desired name or a collision was resolved by using the original name
                final_paths_after_rename.append(current_file_final_path) # Add original path as it's the final one
                continue # Move to next file

            try:
                old_path.rename(target_path_for_rename)
                current_file_final_path = target_path_for_rename
                actual_renames_count += 1
                final_paths_after_rename.append(current_file_final_path)
            except OSError as e:
                print_error(f"Error transforming {old_path.name} to {target_path_for_path.name}: {e}")
                logger.debug(f"Rename OSError traceback: {e}", exc_info=True)
                # If rename fails, we still might want its original path included if it still exists
                if old_path.exists():
                    final_paths_after_rename.append(old_path)
            except Exception as e:
                print_error(f"An unforeseen error occurred during renaming {old_path.name} to {target_path_for_rename.name}: {e}")
                logger.debug(f"Rename unexpected error traceback: {e}", exc_info=True)
                if old_path.exists():
                    final_paths_after_rename.append(old_path)

        except Exception as e:
            print_error(f"An unexpected anomaly occurred while processing {old_path.name} for renaming: {e}. Retaining original path.")
            logger.debug(f"Unexpected renaming loop error traceback: {e}", exc_info=True)
            if old_path.exists():
                final_paths_after_rename.append(old_path)

    tqdm_instance.close()

    if final_paths_after_rename:
        print_success(f"Successfully processed {len(final_paths_after_rename)} files for renaming. Actual transformations: {actual_renames_count}.")
    elif file_paths:
        print_warning("No files were successfully processed for renaming (e.g., all source files missing/invalid).")

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
                else: formatted_value = formatted_value.capitalize()
            elif key in ["size", "type", "layout", "people", "date", "license"]:
                 formatted_value = formatted_value.capitalize()

            template: str | None = filter_map.get(key)
            if template:
                filters.append(template.format(formatted_value))
            else:
                print_warning(f"Unknown filter key '{key}' provided. It shall be ignored by the scrying lens.")
                logger.debug(f"Ignored filter: {key}={value}")

    return "+".join(filters)


# --- Core Functions: The Heart of the Spell ---
def download_images_with_bing(
    query: str,
    output_dir_base: Path,
    limit: int,
    timeout: int,
    adult_filter_off: bool,
    extra_filters: str,
    site_filter: str | None = None
) -> tuple[list[Path], str]: # Returns list of paths and the effective sub-directory name
    """Summons images from the Bing realm and returns their manifested paths
    and the actual subdirectory name created by the downloader.
    """
    effective_query: str = query
    if site_filter:
        effective_query += f" site:{site_filter}"

    query_based_subdir_name: str = effective_query # The folder name will be this string
    query_specific_output_dir: Path = output_dir_base / query_based_subdir_name

    downloaded_files: list[Path] = []
    try:
        logger.info(f"Initiating scrying for query: '{Fore.YELLOW}{effective_query}{Style.RESET_ALL}'")
        logger.info(f"Manifesting images into: '{query_specific_output_dir}'")
        if extra_filters:
            logger.info(f"Applying ethereal filters: '{extra_filters}'")
        else:
            logger.info("No extra filters applied.")

        # Invoke the downloader. It manages its own ethereal connections.
        downloader.download(
            query=effective_query,
            limit=limit,
            output_dir=str(output_dir_base), # downloader expects a string path
            adult_filter_off=adult_filter_off,
            force_replace=False,
            timeout=timeout,
            filter=extra_filters,
            verbose=False
        )
        print_success("The bing-image-downloader ritual has concluded.")

        # --- Discovering Manifested Files ---
        logger.info(f"Searching for manifested files in: {query_specific_output_dir}")
        if query_specific_output_dir.is_dir():
            found_count: int = 0
            # Ensure we only pick files, not subdirectories or other artifacts
            for file_path in query_specific_output_dir.iterdir():
                if file_path.is_file():
                    downloaded_files.append(file_path)
                    found_count += 1
            if found_count > 0:
                print_success(f"Discovered {found_count} manifested image(s) in the target chamber.")
            else:
                print_warning(f"The download ritual concluded, but no images were found in {query_specific_output_dir}. "
                              "Verify the query, filters, or permissions.")
        else:
            print_warning(f"Could not find the expected manifestation chamber: {query_specific_output_dir}. "
                          "The download might have failed silently or placed images elsewhere.")
            logger.debug(f"Subdirectory '{query_specific_output_dir}' does not exist after download.")

    except KeyboardInterrupt:
        print_warning("Download ritual interrupted by the seeker's will.")
        raise
    except requests.exceptions.HTTPError as e:
        print_error(f"HTTP Error during download: {e.response.status_code} - {e.response.reason}")
        logger.debug("Traceback for HTTP error:", exc_info=True)
        return [], query_based_subdir_name
    except requests.exceptions.RequestException as e:
        print_error(f"Network or connection error during download: {e}")
        logger.debug("Traceback for request error:", exc_info=True)
        return [], query_based_subdir_name
    except Exception as e:
        print_error(f"The download ritual failed: {e}")
        logger.debug("Traceback for downloader error:", exc_info=True)
        return [], query_based_subdir_name

    return downloaded_files, query_based_subdir_name


def get_local_file_metadata(file_path: Path, query_based_subdir_name: str) -> dict[str, Any]:
    """Extracts comprehensive intrinsic properties from a local image manifestation.
    Includes size, dimensions, format, mode, DPI, and GIF frame count/animation status.
    """
    metadata: dict[str, Any] = {
        "file_path": str(file_path), # Store as string for JSON serialization
        "filename": file_path.name,
        "query_based_subdir_name": query_based_subdir_name,
        "file_size_bytes": None,
        "dimensions": None,
        "width": None,
        "height": None,
        "format": None,
        "mode": None,
        "dpi": None,
        "is_animated": False,
        "frame_count": None,
        "phash": None,
        "error": None
    }
    try:
        if not file_path.exists():
            metadata["error"] = "File does not exist at time of metadata extraction."
            logger.debug(f"File not found for metadata extraction: {metadata['filename']}")
            return metadata
        if not file_path.is_file():
             metadata["error"] = "Path is not a tangible file."
             logger.debug(f"Path is not a tangible file, skipping metadata: {metadata['filename']}")
             return metadata

        try:
            metadata["file_size_bytes"] = file_path.stat().st_size
        except OSError as size_err:
             metadata["error"] = f"OS error getting size: {size_err}"
             logger.warning(f"Could not discern size for {metadata['filename']}: {size_err}")

        if PIL_AVAILABLE and Image and ImageSequence and IMAGEHASH_AVAILABLE and imagehash:
            try:
                # Open image with Pillow
                with Image.open(file_path) as img: # type: ignore
                    img_pil: Image.Image = img
                    metadata["width"], metadata["height"] = img_pil.size
                    metadata["dimensions"] = f"{img_pil.width}x{img_pil.height}"
                    metadata["format"] = img_pil.format
                    metadata["mode"] = img_pil.mode
                    metadata["dpi"] = img_pil.info.get("dpi")

                    # Calculate perceptual hash
                    try:
                        # Convert to RGB for consistent hashing, handle transparency for PNGs
                        if img_pil.mode in ('RGBA', 'LA') or (img_pil.mode == 'P' and 'transparency' in img_pil.info):
                            # Create a white background if converting from RGBA/LA for pHash
                            bg = Image.new('RGB', img_pil.size, (255, 255, 255))
                            bg.paste(img_pil, mask=img_pil.split()[3] if img_pil.mode == 'RGBA' else None)
                            img_phash_source = bg
                        elif img_pil.mode != 'RGB':
                            img_phash_source = img_pil.convert('RGB')
                        else:
                            img_phash_source = img_pil

                        # Resize for consistent pHash calculation (8x8 recommended for pHash)
                        img_phash_resized = img_phash_source.resize((8, 8), Image.LANCZOS) # Use LANCZOS for quality
                        metadata["phash"] = str(imagehash.phash(img_phash_resized)) # type: ignore
                    except Exception as phash_err:
                        metadata["error"] = f"Error calculating pHash: {phash_err}"
                        logger.warning(f"Error calculating pHash for {metadata['filename']}: {phash_err}")

                    # Check for animation (primarily for GIFs)
                    if img_pil.format == "GIF":
                        try:
                            frame_count: int = 0
                            for _frame in ImageSequence.Iterator(img_pil): # type: ignore
                                frame_count += 1
                            metadata["frame_count"] = frame_count
                            metadata["is_animated"] = frame_count > 1
                        except Exception as gif_err:
                            metadata["error"] = f"GIF frame count error: {gif_err}"
                            logger.warning(f"Error counting GIF frames for {metadata['filename']}: {gif_err}")

            except UnidentifiedImageError: # type: ignore
                metadata["error"] = "Cannot identify image file (Pillow's gaze is clouded). Possibly corrupted or not an image."
                logger.warning(f"Unidentified image format for {metadata['filename']}.")
            except Exception as img_err:
                metadata["error"] = f"Error reading image properties with Pillow: {img_err}"
                logger.warning(f"Could not discern full image properties for {metadata['filename']}: {img_err}")
        else:
            # If Pillow or imagehash is not available, set a more specific error message
            if not PIL_AVAILABLE:
                metadata["error"] = "Pillow library not installed. Advanced image properties (dimensions, format, etc.) will remain a mystery."
            elif not IMAGEHASH_AVAILABLE:
                metadata["error"] = "Imagehash library not installed. Perceptual hash (pHash) will not be calculated."
            logger.debug(f"Pillow/Imagehash not available for {metadata['filename']}.")

    except OSError as e_os:
        metadata["error"] = f"OS error accessing file: {e_os}"
        print_error(f"Error accessing {metadata['filename']} for metadata: {e_os}")
        logger.debug(f"OS error during metadata extraction: {e_os}", exc_info=True)
    except Exception as e_gen:
        metadata["error"] = f"An unforeseen error occurred during metadata extraction: {e_gen}"
        print_error(f"Unexpected error processing {metadata['filename']}: {e_gen}")
        logger.debug(f"Unexpected error during metadata extraction: {e_gen}", exc_info=True)

    return metadata


def extract_metadata_parallel(image_paths: list[Path], query_based_subdir_name: str) -> list[dict[str, Any]]:
    """Extracts local file metadata for multiple images concurrently, harnessing parallel energies."""
    if not image_paths:
        return []

    if not PIL_AVAILABLE:
        print_warning("Pillow library not found. Image dimensions and other advanced properties will not be extracted.")
    if not IMAGEHASH_AVAILABLE:
        print_warning("Imagehash library not found. Perceptual hash (pHash) will not be calculated.")

    metadata_list: list[dict[str, Any]] = []
    max_workers: int = Config.MAX_METADATA_WORKERS

    logger.info(f"Extracting intrinsic properties from {len(image_paths)} local manifestations using up to {max_workers} parallel threads...")

    tqdm_instance = tqdm(
        total=len(image_paths),
        desc=f"{Fore.BLUE}📄 Extracting Metadata{Style.RESET_ALL}",
        unit="file",
        ncols=100,
        leave=False,
        disable=not TQDM_AVAILABLE
    )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures: dict[Future[dict[str, Any]], Path] = {
            executor.submit(get_local_file_metadata, path, query_based_subdir_name): path
            for path in image_paths
        }

        for future in futures: # Iterate over futures directly, tqdm is handled outside
            original_path: Path = futures[future]
            try:
                result: dict[str, Any] = future.result()
                metadata_list.append(result)
            except Exception as e:
                print_error(f"Error processing future result for {original_path.name}: {e}")
                logger.debug(f"Future result error traceback: {e}", exc_info=True)
                # Create a fallback metadata entry in case of error during future.result()
                error_metadata_entry: dict[str, Any] = {
                    "file_path": str(original_path),
                    "filename": original_path.name,
                    "query_based_subdir_name": query_based_subdir_name,
                    "file_size_bytes": None,
                    "dimensions": None, "width": None, "height": None,
                    "format": None, "mode": None, "dpi": None,
                    "is_animated": False, "frame_count": None, "phash": None,
                    "error": f"Future processing error: {e}"
                }
                metadata_list.append(error_metadata_entry)
            finally:
                tqdm_instance.update(1)
    tqdm_instance.close()

    print_success(f"Metadata extraction completed for {len(metadata_list)} manifestations.")
    return metadata_list


def save_metadata(metadata_list: list[dict[str, Any]], output_dir_base: Path, query: str) -> bool:
    """Records the collected metadata into a JSON scroll within the base output directory."""
    if not metadata_list:
        print_warning("No metadata collected to inscribe.")
        return False

    sanitized_query_str: str = sanitize_filename(query)
    if not sanitized_query_str:
        sanitized_query_str = "unknown_query"
    timestamp: str = datetime.now().strftime("%Y%m%d_%H%M%S")
    metadata_filename: str = f"{Config.METADATA_FILENAME_PREFIX}{sanitized_query_str}_{timestamp}.json"
    metadata_file_path: Path = output_dir_base / metadata_filename

    logger.info(f"Attempting to inscribe metadata to: {metadata_file_path}")
    try:
        if not create_directory(output_dir_base):
             print_error(f"Cannot inscribe metadata, base output directory '{output_dir_base}' does not exist and couldn't be forged.")
             return False

        with open(metadata_file_path, "w", encoding="utf-8") as f:
            json.dump(metadata_list, f, indent=4, ensure_ascii=False)
        print_success(f"Metadata inscribed successfully to: {metadata_file_path}")
        return True
    except OSError as e:
        print_error(f"Failed to inscribe metadata to {metadata_file_path}: {e}")
        logger.debug(f"Metadata save OSError traceback: {e}", exc_info=True)
        return False
    except Exception as e:
        print_error(f"An unexpected error occurred while inscribing metadata: {e}")
        logger.debug(f"Metadata save unexpected error traceback: {e}", exc_info=True)
        return False


def load_master_manifest(output_dir_base: Path) -> dict[str, dict[str, Any]]:
    """Loads the existing master manifest into a dictionary for quick lookup.
    The key is the resolved, absolute file path to ensure uniqueness.
    """
    master_manifest_file_path: Path = output_dir_base / Config.MASTER_MANIFEST_FILENAME
    existing_entries: dict[str, dict[str, Any]] = {}

    if master_manifest_file_path.exists():
        try:
            with open(master_manifest_file_path, encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for entry in data:
                        if isinstance(entry, dict) and "file_path" in entry and isinstance(entry["file_path"], str):
                            # Normalize path to ensure consistent keys (absolute path)
                            normalized_path: str = str(Path(entry["file_path"]).resolve())
                            existing_entries[normalized_path] = entry
                logger.debug(f"Loaded {len(existing_entries)} entries from existing master manifest.")
        except json.JSONDecodeError as e:
            print_error(f"Error decoding existing master manifest {master_manifest_file_path}: {e}. Manifest will be rebuilt.")
            logger.debug(f"Master manifest JSON decode error traceback: {e}", exc_info=True)
        except Exception as e:
            print_error(f"Error loading existing master manifest {master_manifest_file_path}: {e}. Manifest will be rebuilt.")
            logger.debug(f"Master manifest load unexpected error traceback: {e}", exc_info=True)
    return existing_entries


def generate_master_manifest(output_dir_base: Path, all_metadata_entries: dict[str, dict[str, Any]]) -> None:
    """Combines all unique image metadata entries into a single grand ledger (master manifest).
    This master ledger will be the key to the image_viewer.html's scrying pool.
    It filters out entries for files that no longer exist on disk.
    """
    print_header("✨ Forging the Master Image Manifest ✨")

    master_manifest_file_path: Path = output_dir_base / Config.MASTER_MANIFEST_FILENAME

    # Filter out entries for files that no longer exist on disk
    valid_manifest_entries: list[dict[str, Any]] = []
    # Using tqdm for potentially long operations if many files
    tqdm_instance = tqdm(
        all_metadata_entries.values(),
        desc=f"{Fore.BLUE}Validating Manifest Entries{Style.RESET_ALL}",
        unit="entry",
        ncols=100,
        leave=False,
        disable=not TQDM_AVAILABLE
    )
    for entry in tqdm_instance:
        if "file_path" in entry:
            entry_path = Path(entry["file_path"])
            if entry_path.exists() and entry_path.is_file():
                valid_manifest_entries.append(entry)
            else:
                logger.debug(f"Skipping non-existent file from master manifest: {entry['file_path']}")
        else:
            logger.debug(f"Skipping manifest entry without 'file_path': {entry}")
    tqdm_instance.close()

    try:
        with open(master_manifest_file_path, "w", encoding="utf-8") as f:
            json.dump(valid_manifest_entries, f, indent=4, ensure_ascii=False)
        print_success(f"Master manifest forged successfully: {master_manifest_file_path} (Contains {len(valid_manifest_entries)} unique entries).")
    except OSError as e:
        print_error(f"Failed to forge master manifest to {master_manifest_file_path}: {e}")
        logger.debug(f"Master manifest save OSError traceback: {e}", exc_info=True)
    except Exception as e:
        print_error(f"An unexpected error occurred while forging master manifest: {e}")
        logger.debug(f"Master manifest save unexpected error traceback: {e}", exc_info=True)


# --- Command-Line Argument Parsing ---
def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments for the image scrying process."""
    parser = argparse.ArgumentParser(
        description="Enhanced Bing Image Downloader Script",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        "query",
        type=str,
        nargs='?', # Make query optional
        default=None,
        help="The search query (e.g., 'red cars', 'mountain landscape')."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Base output directory for downloaded images. Images will be saved in a subfolder named after the query."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of images to manifest."
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help="Download timeout per image in seconds."
    )
    parser.add_argument(
        "--safe-search",
        dest="adult_filter_off",
        action="store_false",
        help="Enable adult content filter. By default, adult content is allowed."
    )
    parser.set_defaults(adult_filter_off=True)
    parser.add_argument(
        "--site",
        type=str,
        default=None,
        help="Filter results by a specific site (e.g., wikipedia.org, flickr.com)."
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)."
    )
    parser.add_argument(
        "--no-deduplicate",
        action="store_true",
        help="Disable perceptual hashing based duplicate detection and removal. Requires Pillow and Imagehash."
    )
    parser.add_argument(
        "--phash-threshold",
        type=int,
        default=None,
        help=f"Perceptual hash difference threshold for duplicate detection. Lower is stricter. (Default: {Config.PHASH_THRESHOLD})"
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enable interactive mode, prompting for missing arguments."
    )

    # Filter arguments
    filter_group = parser.add_argument_group("Ethereal Search Filters")
    filter_group.add_argument("--size", type=str, help="Image size (Small, Medium, Large, Wallpaper).")
    filter_group.add_argument("--color", type=str, help="Image color (ColorOnly, Monochrome, color name like Red, Blue).")
    filter_group.add_argument("--type", type=str, help="Image type (Photo, Clipart, Line, AnimatedGif, Transparent).")
    filter_group.add_argument("--layout", type=str, help="Image layout (Square, Wide, Tall).")
    filter_group.add_argument("--people", type=str, help="People filter (Face, Portrait).")
    filter_group.add_argument("--date", type=str, help="Date filter (PastDay, PastWeek, PastMonth, PastYear).")
    filter_group.add_argument("--license", type=str, help="License filter (Any, Public, Share, ShareCommercially, Modify, ModifyCommercially).")
    filter_group.add_argument("--gif-only", action="store_true", help="Only search for animated GIFs. This sets the 'type' filter to 'AnimatedGif'.")

    return parser.parse_args()


def get_interactive_input(args: argparse.Namespace) -> None:
    """Interactively prompts the user for missing arguments."""
    print_header("🔍 Articulating Your Intent (Interactive Mode)")

    if args.query is None:
        while True:
            query = input(f"{Fore.CYAN}⌨️  Enter your Search Query (e.g., 'red cars', 'mountain landscape'): {Fore.WHITE}").strip()
            if query:
                args.query = query
                break
            print_warning("Your search query cannot be an empty whisper.")

    if args.output_dir is None:
        output_dir_str = input(
            f"{Fore.CYAN}📂 Enter Base Output Directory [default: {Config.DEFAULT_OUTPUT_DIR}]: {Fore.WHITE}"
        ).strip() or str(Config.DEFAULT_OUTPUT_DIR)
        args.output_dir = Path(output_dir_str)

    if args.limit is None:
        while True:
            try:
                limit_str = input(f"{Fore.CYAN}🔢 Enter Max Images to Manifest [default: 50]: {Fore.WHITE}").strip() or "50"
                limit = int(limit_str)
                if limit > 0:
                    args.limit = limit
                    break
                print_warning("The number of images must be a positive integer.")
            except ValueError:
                print_error("Invalid input. Please enter a whole number.")

    if args.timeout is None:
        while True:
            try:
                timeout_str = input(f"{Fore.CYAN}⏳ Enter Download Timeout per image (seconds) [default: 60]: {Fore.WHITE}").strip() or "60"
                timeout = int(timeout_str)
                if timeout > 0:
                    args.timeout = timeout
                    break
                print_warning("Timeout duration must be positive.")
            except ValueError:
                print_error("Invalid input. Please enter a whole number.")

    if not args.adult_filter_off and args.adult_filter_off is None: # Check if it's not set and not explicitly false
        adult_filter_off_input = input(f"{Fore.CYAN}🔞 Disable the adult filter? (y/N) [default: N]: {Fore.WHITE}").strip().lower()
        args.adult_filter_off = (adult_filter_off_input == "y")

    if args.site is None:
        site_filter = input(f"{Fore.CYAN}🌐 Filter by specific site (e.g., wikipedia.org, flickr.com) [optional]: {Fore.WHITE}").strip()
        if site_filter: args.site = site_filter

    if args.phash_threshold is None:
        while True:
            try:
                phash_threshold_str = input(f"{Fore.CYAN}🧮 Perceptual hash difference threshold for duplicates [default: {Config.PHASH_THRESHOLD}]: {Fore.WHITE}").strip() or str(Config.PHASH_THRESHOLD)
                phash_threshold = int(phash_threshold_str)
                if phash_threshold >= 0:
                    args.phash_threshold = phash_threshold
                    break
                print_warning("pHash threshold must be a non-negative integer.")
            except ValueError:
                print_error("Invalid input. Please enter a whole number.")

    if not args.gif_only:
        gif_only_input = input(f"{Fore.CYAN}🎞️  Search for GIFs only? (y/N) [default: N]: {Fore.WHITE}").strip().lower()
        args.gif_only = (gif_only_input == "y")

    # Interactive filter inputs
    print_header("🎨 Ethereal Search Filters (Optional - Press Enter to skip)")
    print_info("Examples: Size:Large, Type:Photo, Layout:Wide, License:Share")

    filter_prompts = {
        "size": "📏 Size (Small, Medium, Large, Wallpaper)",
        "color": "🎨 Color (ColorOnly, Monochrome, color name like Red, Blue)",
        "type": "🖼️  Type (Photo, Clipart, Line, AnimatedGif, Transparent)",
        "layout": "📐 Layout (Square, Wide, Tall)",
        "people": "👥 People (Face, Portrait)",
        "date": "📅 Date (PastDay, PastWeek, PastMonth, PastYear)",
        "license": "📜 License (Any, Public, Share, ShareCommercially, Modify, ModifyCommercially)",
    }

    for filter_name, prompt_text in filter_prompts.items():
        current_value = getattr(args, filter_name)
        if current_value is None:
            user_input = input(f"{Fore.CYAN}{prompt_text}: {Fore.WHITE}").strip()
            if user_input: setattr(args, filter_name, user_input)


# --- Main Application: The Orchestration of the Ritual ---
def main() -> None:
    """Main function to orchestrate the image scrying and manifestation process."""
    start_time = datetime.now()
    print_header("🌟 Enhanced Bing Image Scrying & Manifestation 🌟")
    print_info("Dependencies: bing-image-downloader, colorama (optional), tqdm (optional), Pillow (optional), imagehash (optional)")

    args = parse_arguments()

    # If query is not provided via CLI or interactive flag is set, enter interactive mode
    if args.query is None or args.interactive:
        get_interactive_input(args)

    # If query is still None after interactive input, exit
    if args.query is None:
        print_error("No search query provided. Exiting.")
        sys.exit(1)

    # Apply gif-only filter if specified
    if args.gif_only:
        args.type = "AnimatedGif"

    # Apply default values if not set by CLI or interactive input
    if args.output_dir is None:
        args.output_dir = Config.DEFAULT_OUTPUT_DIR
    if args.limit is None:
        args.limit = 50
    if args.timeout is None:
        args.timeout = 60
    if args.phash_threshold is None:
        args.phash_threshold = Config.PHASH_THRESHOLD

    # Ensure adult filter is always off (safe search off)
    args.adult_filter_off = True

    logger.setLevel(getattr(logging, args.log_level.upper()))

    # Dependency checks
    if not PIL_AVAILABLE:
        print_warning("Pillow library not installed. Advanced image properties (dimensions, format, etc.) will not be extracted.")
        if not args.no_deduplicate:
            print_warning("Duplicate detection via pHash requires Pillow. It will be disabled.")
            args.no_deduplicate = True # Force disable deduplication

    if not IMAGEHASH_AVAILABLE:
        print_warning("Imagehash library not installed. Perceptual hashing for duplicate detection is unavailable.")
        if not args.no_deduplicate:
            print_warning("Duplicate detection via pHash requires Imagehash. It will be disabled.")
            args.no_deduplicate = True # Force disable deduplication

    # Prompt for installation if needed and not explicitly disabled
    if (not PIL_AVAILABLE or not IMAGEHASH_AVAILABLE) and (not args.no_deduplicate):
        print_info("To enable advanced image metadata and pHash-based deduplication, Pillow and Imagehash are required.")
        install_libs = input(f"{Fore.YELLOW}Would you like to attempt to install Pillow and Imagehash now? (y/N): {Style.RESET_ALL}").strip().lower()
        if install_libs == 'y':
            print_info("Attempting to install Pillow and Imagehash...")
            try:
                import subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "imagehash"])
                print_success("Pillow and Imagehash installed successfully. Please restart the script to enable these features.")
                sys.exit(0)
            except Exception as e:
                print_error(f"Failed to install Pillow/Imagehash: {e}. Please try installing them manually: pip install Pillow imagehash")
                sys.exit(1)
        else:
            print_info("Installation skipped. Proceeding without advanced image metadata extraction or pHash-based deduplication.")
            args.no_deduplicate = True

    # Re-check availability after potential installation attempt (though script exits)
    enable_deduplication: bool = not args.no_deduplicate and PIL_AVAILABLE and IMAGEHASH_AVAILABLE

    query: str = args.query
    output_dir_base_path: Path = args.output_dir
    limit_val: int = args.limit
    timeout_val: int = args.timeout
    adult_filter_off_bool: bool = args.adult_filter_off
    site_filter_str: str | None = args.site
    phash_threshold: int = args.phash_threshold

    filters_dict_map: dict[str, str | None] = {
        "size": args.size, "color": args.color, "type": args.type,
        "layout": args.layout, "people": args.people, "date": args.date,
        "license": args.license,
    }

    if not create_directory(output_dir_base_path):
        print_error(f"Cannot proceed without the base manifestation chamber: {output_dir_base_path}")
        sys.exit(1)

    all_known_images_metadata: dict[str, dict[str, Any]] = load_master_manifest(output_dir_base_path)
    existing_phashes_set: set[tuple[str, str]] = set() # Store (phash_str, normalized_file_path_str)

    if enable_deduplication:
        print_info(f"Loaded {len(all_known_images_metadata)} existing image records for duplicate checks.")
        # Populate the set of existing pHashes for live files
        for entry in all_known_images_metadata.values():
            if entry.get('phash') and entry.get('file_path'):
                current_path = Path(entry['file_path'])
                if current_path.exists() and current_path.is_file():
                    existing_phashes_set.add((str(entry['phash']), str(current_path.resolve())))
                else:
                    logger.debug(f"Skipping non-existent file's pHash from manifest: {entry['file_path']}")
    else:
        print_info("Duplicate detection is disabled.")

    filter_string: str = apply_filters(**filters_dict_map)

    print_header("🚀 Initiating the Scrying Process")

    downloaded_file_paths, query_based_subdir_name_for_metadata = download_images_with_bing(
        query, output_dir_base_path, limit_val, timeout_val, adult_filter_off_bool, filter_string, site_filter_str
    )

    if not downloaded_file_paths:
        print_warning("No images were manifested or discovered. Verify your query, filters, or permissions. Exiting gracefully.")
        generate_master_manifest(output_dir_base_path, all_known_images_metadata)
        return

    print_header("🔬 Analyzing New Manifestations")
    new_downloaded_metadata: list[dict[str, Any]] = extract_metadata_parallel(
        downloaded_file_paths, query_based_subdir_name_for_metadata
    )

    unique_files_for_processing: list[Path] = []
    duplicate_count: int = 0

    if enable_deduplication:
        print_header("🔍 Purging Duplicates")
        tqdm_instance = tqdm(
            new_downloaded_metadata,
            desc=f"{Fore.MAGENTA}Deduplicating{Style.RESET_ALL}",
            unit="image",
            ncols=100,
            leave=False,
            disable=not TQDM_AVAILABLE
        )
        for new_meta_entry in tqdm_instance:
            file_path = Path(new_meta_entry['file_path'])
            new_phash_str = new_meta_entry.get('phash')
            is_duplicate = False

            if not new_phash_str:
                logger.debug(f"Skipping pHash check for {file_path.name}: pHash not available. Treating as unique for now.")
                unique_files_for_processing.append(file_path)
                # Still add to all_known_images_metadata later, but won't be used for phash comparison if phash is missing.
                # However, if it's genuinely new, its metadata will be added based on its path.
                continue

            try:
                new_phash = imagehash.hex_to_hash(new_phash_str) # type: ignore
            except ValueError as ve:
                print_warning(f"Invalid pHash string for {file_path.name}: {new_phash_str}. Treating as unique. Error: {ve}")
                logger.debug(f"Invalid pHash string ValueError traceback: {ve}", exc_info=True)
                unique_files_for_processing.append(file_path)
                continue
            except Exception as e:
                print_warning(f"Error converting pHash for {file_path.name}: {e}. Treating as unique.")
                logger.debug(f"pHash conversion unexpected error traceback: {e}", exc_info=True)
                unique_files_for_processing.append(file_path)
                continue

            # Iterate through existing pHashes to find a close match
            for existing_phash_str, existing_file_path_raw in list(existing_phashes_set): # Iterate on a copy to allow modification
                existing_file_path = Path(existing_file_path_raw)
                try:
                    existing_phash = imagehash.hex_to_hash(existing_phash_str) # type: ignore
                    if existing_file_path.exists() and (new_phash - existing_phash) <= phash_threshold:
                        print_info(f"Duplicate detected: {file_path.name} (new) is similar to {existing_file_path.name} (existing, diff: {new_phash - existing_phash}).")
                        try:
                            file_path.unlink() # Delete the newly downloaded duplicate file
                            duplicate_count += 1
                            is_duplicate = True
                            break # Found a duplicate, no need to check further existing hashes
                        except OSError as e:
                            print_error(f"Failed to delete duplicate file {file_path.name}: {e}. Keeping it.")
                            logger.debug(f"Duplicate file deletion OSError traceback: {e}", exc_info=True)
                            # If deletion fails, we treat it as unique for now to avoid re-download loops
                            unique_files_for_processing.append(file_path)
                            is_duplicate = False # Treat as not deleted, so not a duplicate *for this run*
                            break # No point checking further as current file is retained
                except ValueError as ve:
                    print_warning(f"Invalid existing pHash string for {existing_file_path.name}: {existing_phash_str}. Skipping comparison. Error: {ve}")
                    logger.debug(f"Existing pHash ValueError traceback: {ve}", exc_info=True)
                    # Remove invalid pHash from set to avoid future issues
                    existing_phashes_set.discard((existing_phash_str, existing_file_path_raw))
                except Exception as e:
                    print_warning(f"Error comparing pHashes for {file_path.name} and {existing_file_path.name}: {e}. Skipping comparison.")
                    logger.debug(f"pHash comparison unexpected error traceback: {e}", exc_info=True)
                    # If comparison fails, it's safer to treat as unique to avoid accidental deletion

            if not is_duplicate:
                unique_files_for_processing.append(file_path)
                # Add the new unique file's pHash to the set for subsequent comparisons in this run
                if new_phash_str: # Only add if pHash was successfully calculated
                    existing_phashes_set.add((new_phash_str, str(file_path.resolve())))
                # Also update the running master manifest data
                normalized_new_path = str(file_path.resolve())
                all_known_images_metadata[normalized_new_path] = new_meta_entry
        tqdm_instance.close()

    else: # Deduplication is disabled
        unique_files_for_processing = downloaded_file_paths
        for new_meta_entry in new_downloaded_metadata:
            if 'file_path' in new_meta_entry:
                normalized_new_path = str(Path(new_meta_entry['file_path']).resolve())
                all_known_images_metadata[normalized_new_path] = new_meta_entry

    if duplicate_count > 0:
        print_success(f"Removed {duplicate_count} duplicate image(s).")
    if not unique_files_for_processing:
        print_warning("All downloaded images were duplicates or failed processing. No new unique images. Exiting gracefully.")
        generate_master_manifest(output_dir_base_path, all_known_images_metadata)
        return

    # --- Renaming Ritual for unique files ---
    print_header("📝 Renaming Unique Manifestations")
    renamed_paths: list[Path] = rename_files(unique_files_for_processing, query)

    # --- Extracting Metadata for Renamed Files ---
    # This ensures the metadata has the correct, final file paths and names.
    extracted_metadata_list: list[dict[str, Any]] = []
    if renamed_paths:
         print_header("✨ Re-extracting Metadata for Renamed Files")
         # Pass the original query-based subdir name, as the physical directory structure hasn't changed.
         extracted_metadata_list = extract_metadata_parallel(renamed_paths, query_based_subdir_name_for_metadata)

         # Update the master manifest with the metadata from renamed unique files
         # It's crucial to remove old entries and add new ones with the resolved path.
         # First, remove any old paths that might have been renamed
         paths_to_remove = []
         for key, value in all_known_images_metadata.items():
             # Check if the file_path in the manifest entry is one of the *original* downloaded paths
             # that got renamed. This is complex because the original path isn't directly passed here.
             # A simpler approach is to iterate over the 'old' `downloaded_file_paths` and remove them
             # from `all_known_images_metadata` if their new names are in `renamed_paths`.
             # However, this current logic (add new, overwrite old if key matches) usually works if
             # the old path from the manifest still exists as a key, but the *new* path (after rename)
             # is what we want as the key.

             # A more robust update: After renaming, the original file paths are gone.
             # We should update `all_known_images_metadata` by removing old paths and adding new ones.
             # For simplicity and correctness, we will rebuild the relevant part of the manifest.
             pass # Logic moved to final manifest generation or handled by new entries overwriting old

         for meta_entry in extracted_metadata_list:
             if 'file_path' in meta_entry:
                 normalized_path = str(Path(meta_entry['file_path']).resolve())
                 all_known_images_metadata[normalized_path] = meta_entry
    else:
        print_warning("No valid file paths remained after deduplication/renaming to extract final metadata from.")


    # --- Inscribing Metadata for this query's session ---
    if extracted_metadata_list:
        save_metadata(extracted_metadata_list, output_dir_base_path, query)
    else:
        print_warning("No new metadata was generated for inscription this session.")

    # --- Forging the Master Manifest (The Grand Ledger) ---
    generate_master_manifest(output_dir_base_path, all_known_images_metadata)

    # --- Final Revelation: Summary of the Ritual ---
    print_header("📊 Revelation Summary")
    total_downloaded_initial: int = len(downloaded_file_paths)
    total_duplicates_removed: int = duplicate_count
    total_unique_processed: int = len(unique_files_for_processing)
    total_renamed: int = len(renamed_paths)
    total_metadata_extracted_final: int = len(extracted_metadata_list)
    errors_in_metadata_final: int = sum(1 for item in extracted_metadata_list if item.get("error"))

    print_info(f"Initial manifestations scried: {total_downloaded_initial}")
    if enable_deduplication:
        print_info(f"Duplicates identified and removed: {total_duplicates_removed}")
    print_info(f"Unique manifestations processed (after deduplication): {total_unique_processed}")
    print_info(f"Manifestations successfully renamed: {total_renamed}")
    print_info(f"Final metadata records inscribed for this session: {total_metadata_extracted_final}")

    if errors_in_metadata_final > 0:
        print_warning(f"Encountered errors during final metadata extraction for {errors_in_metadata_final} manifestation(s). Consult the individual scroll: '{Config.METADATA_FILENAME_PREFIX}{sanitize_filename(query)}_*.json'.")

    if extracted_metadata_list:
        print_info("\nFirst few new metadata revelations:")
        for item_metadata in extracted_metadata_list[:min(5, len(extracted_metadata_list))]:
            filename = item_metadata.get('filename', 'N/A')
            size_str = f"{item_metadata.get('file_size_bytes', 'N/A')} bytes"
            dim_str = item_metadata.get("dimensions", "N/A")
            format_str = item_metadata.get("format", "N/A")
            mode_str = item_metadata.get("mode", "N/A")
            frames_str = f"Frames: {item_metadata.get('frame_count')}" if item_metadata.get("is_animated") else ""
            error_str = f"{Fore.RED}(Error: {item_metadata.get('error')}){Style.RESET_ALL}" if item_metadata.get("error") else ""
            print(f"  - {Fore.MAGENTA}{filename}{Style.RESET_ALL}: Dims: {dim_str}, Format: {format_str}, Mode: {mode_str} {frames_str} {error_str}")
        if len(extracted_metadata_list) > 5:
            print(f"  ... and {len(extracted_metadata_list) - 5} more secrets.")
    else:
        print_info("No new metadata was extracted or inscribed this session.")

    end_time: datetime = datetime.now()
    duration: timedelta = end_time - start_time
    print_success(f"\nOperation completed in {duration.total_seconds():.2f} seconds! The ritual is complete.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("\nOperation cancelled by the seeker's will (Ctrl+C detected). The ritual is halted.")
        sys.exit(1)
    except Exception as e:
        print_error(f"\nAn unexpected critical anomaly occurred during the ritual: {e}")
        logger.exception("Unhandled exception trace:")
        sys.exit(1)
