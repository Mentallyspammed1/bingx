#!/bin/bash

# Ritual of Preparation: Attuning Termux for Enhanced Image Scrying and Manifestation

# --- Ethereal Hues for Clarity ---
# Pyrmethus's chosen palette
RED='\033[0;31m'    # Fiery Red for Errors
GREEN='\033[0;32m'  # Verdant Green for Success
YELLOW='\033[0;33m' # Golden Yellow for Warnings/Headers
BLUE='\033[0;34m'   # Deep Blue for Informational Whispers
MAGENTA='\033[0;35m' # Mystical Magenta for Key Elements
CYAN='\033[0;36m'   # Luminous Cyan for Prompts/Guidance
NC='\033[0m'        # The Void's Reset

# --- Header Sigil Function ---
print_header() {
    echo -e "${YELLOW}====================================================${NC}"
    echo -e "${YELLOW}  $1${NC}"
    echo -e "${YELLOW}====================================================${NC}"
}

# --- Main Setup Ritual ---
print_header "Initiating the Enhanced Bing Image Scrying Setup"
echo -e "${CYAN}This ritual will summon Python dependencies and forge the necessary scripts and viewing portal.${NC}"
echo -e "${CYAN}Ensure you are within the sacred Termux chamber or a compatible Linux realm.${NC}"
echo

# 1. Attune Package Lists
print_header "Attuning Termux/System Package Repositories"
if command -v pkg &> /dev/null; then
    echo -e "${BLUE}Whispering to the 'pkg' spirits for updates and upgrades...${NC}"
    pkg update && pkg upgrade -y
elif command -v apt &> /dev/null; then
    echo -e "${BLUE}Invoking 'apt' to refresh the knowledge scrolls...${NC}"
    sudo apt update && sudo apt upgrade -y
else
    echo -e "${RED}Warning: Neither 'pkg' nor 'apt' responde. Please manually update your package manager, seeker.${NC}"
fi
echo -e "${GREEN}Package attunement complete.${NC}"
echo

# 2. Verify Python and Pip Presence
print_header "Verifying Python and Pip Enchantments"
if ! command -v python &> /dev/null; then
    echo -e "${BLUE}Python's essence not detected. Invoking Python's spirit...${NC}"
    if command -v pkg &> /dev/null; then
        pkg install python -y
    elif command -v apt &> /dev/null; then
        sudo apt install python3 python3-pip -y
    else
        echo -e "${RED}Error: Cannot bind Python's spirit. Please install it manually, seeker.${NC}"
        exit 1
    fi
    echo -e "${GREEN}Python's spirit is now bound.${NC}"
else
    echo -e "${CYAN}Python's essence already resonates within this realm.${NC}"
fi

# Ensure pip, the package conduit, is installed and empowered
if ! command -v pip &> /dev/null; then
    echo -e "${BLUE}Pip, the conduit, not found. Attempting to forge its connection...${NC}"
    if command -v pkg &> /dev/null; then
        pkg install python-pip -y # Termux specific for older pip versions
    else
        python -m ensurepip --upgrade --default-pip
    fi
    echo -e "${GREEN}Pip conduit established.${NC}"
fi

echo -e "${BLUE}Empowering pip to its latest form...${NC}"
python -m pip install --upgrade pip
echo -e "${GREEN}Pip conduit fully empowered.${NC}"
echo

# 3. Install Python Dependencies
print_header "Summoning Python Libraries from the PyPI Aether"
# Ensure Pillow is explicitly mentioned and installed for advanced image analysis
REQUIRED_LIBS="bing-image-downloader colorama tqdm Pillow"

echo -e "${BLUE}Chanting the installation spell for: ${REQUIRED_LIBS}...${NC}"
python -m pip install $REQUIRED_LIBS
if [ $? -eq 0 ]; then
    echo -e "${GREEN}All Python libraries have manifested successfully!${NC}"
else
    echo -e "${RED}Error: One or more Python libraries resisted the summoning. Inspect the ethereal echoes above.${NC}"
    exit 1
fi
echo

# 4. Forging scrapey.py, the Scrying Script
print_header "Forging 'scrapey.py', the Enhanced Scrying Script"
cat << 'EOF' > scrapey.py
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
    """Renames downloaded files sequentially, imbuing them with a query-based prefix."""
    renamed_paths: List[str] = []
    if not file_paths:
        print_warning("No file paths provided for the renaming ritual.")
        return []

    sanitized_query = sanitize_filename(base_query)
    if not sanitized_query:
        sanitized_query = "image"  # Fallback if the query is too ethereal
        print_warning(f"Query '{base_query}' yielded an empty name, using fallback 'image'.")

    # Ascertaining the sacred directory from the first path
    if not os.path.dirname(file_paths[0]):
         print_error("Cannot discern the directory for renaming files.")
         return []
    dir_name = os.path.dirname(file_paths[0])

    print_info(f"Imbuing {len(file_paths)} files in '{dir_name}' with the prefix '{sanitized_query}'...")

    file_paths.sort()  # For consistent ordering in the renaming sequence

    for idx, old_path in enumerate(
        tqdm(file_paths, desc=Fore.BLUE + "🔄 Renaming Files", unit="file", ncols=100, leave=False), start=1
    ):
        try:
            if not os.path.exists(old_path):
                print_warning(f"File not found for renaming (already transformed or vanished?): {old_path}")
                continue
            if not os.path.isfile(old_path):
                 print_warning(f"Path is not a tangible file, skipping rename: {old_path}")
                 continue

            _, ext = os.path.splitext(old_path)
            # Crafting the new name within the same sacred directory
            new_name = f"{sanitized_query}_{idx}{ext}"
            new_path = os.path.join(dir_name, new_name)

            # Addressing potential name collisions (a rare but possible anomaly)
            counter = 1
            while os.path.exists(new_path):
                # If it's the same file, no actual collision, just a redundant rename
                if os.path.samefile(old_path, new_path):
                    logger.debug(f"Skipping rename for {os.path.basename(old_path)} as target name is identical.")
                    renamed_paths.append(old_path)  # Keep its track
                    break  # Break the collision loop for this file

                # If a different file exists, append a counter sigil
                new_name = f"{sanitized_query}_{idx}_{counter}{ext}"
                new_path = os.path.join(dir_name, new_name)
                counter += 1
                if counter > 100:  # A safety ward against infinite loops
                    print_error(f"Could not find a unique name for {os.path.basename(old_path)} after 100 attempts. Skipping.")
                    new_path = None  # Mark as failed
                    break
            else:  # This block executes if no 'break' occurred in the while loop
                try:
                    os.rename(old_path, new_path)
                    renamed_paths.append(new_path)
                except OSError as e:
                    print_error(f"Error transforming {os.path.basename(old_path)} to {os.path.basename(new_path)}: {e}")
                except Exception as e:
                    print_error(f"An unforeseen error occurred during renaming {os.path.basename(old_path)}: {e}")

        except Exception as e:
            print_error(f"An unexpected anomaly occurred while processing {os.path.basename(old_path)} for renaming: {e}")

    if renamed_paths:
        print_success(f"Successfully processed {len(renamed_paths)} files for renaming (check warnings for minor disturbances).")
    else:
        print_warning("No files were successfully renamed in this ritual phase.")
    return renamed_paths


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
            formatted_value = value.strip().capitalize() # Capitalize for Bing's preference
            # Specific adjustments for certain filter values if Bing is particular
            if key == "color" and formatted_value.lower() == "monochrome":
                formatted_value = "Monochrome"
            elif key == "color" and formatted_value.lower() == "coloronly":
                 formatted_value = "ColorOnly"

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

    # The downloader creates a sub-chamber named after the raw 'query' within the base directory.
    query_based_subdir_name = query
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

        # The downloader creates a sub-chamber based on the raw query.
        query_based_subdir_name_for_metadata = query

        # --- Renaming Ritual ---
        # The renaming happens in-place, transforming the filenames.
        renamed_paths = rename_files(downloaded_file_paths, query)

        # Deciding which paths to use for metadata extraction
        if not renamed_paths:
            print_warning("Renaming ritual failed or yielded no results. Attempting metadata extraction on original downloaded paths.")
            paths_for_metadata = downloaded_file_paths
        else:
            paths_for_metadata = renamed_paths

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
EOF
echo -e "${GREEN}The 'scrapey.py' enhanced scrying script has been forged!${NC}"
echo

# 5. Crafting image_viewer.html, the Scrying Pool
print_header "Crafting 'image_viewer.html', the Enhanced Scrying Pool"
cat << 'EOF' > image_viewer.html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pyrmethus's Scrying Pool: Local Image Manifestations</title>
    <style>
        /* Pyrmethus's Mystical CSS Enchantments */
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0d1117; /* The deep void of Termux */
            color: #c9d1d9; /* Whispers of light */
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            min-height: 100vh; /* Ensure body takes full height */
        }
        .container {
            width: 100%;
            max-width: 1200px;
        }
        h1 {
            color: #56F000; /* Verdant glow for headers */
            text-align: center;
            margin-bottom: 30px;
            text-shadow: 0 0 10px #56F000, 0 0 20px #56F000; /* Aura of power */
        }
        .controls-container {
            margin-bottom: 30px;
            width: 100%;
            display: flex;
            flex-wrap: wrap; /* Allow wrapping on smaller screens */
            justify-content: center;
            gap: 15px; /* Increased gap for better spacing */
            padding: 10px;
            background-color: #161b22;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 255, 255, 0.2);
        }
        .control-group {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            gap: 5px;
        }
        .control-group label {
            font-size: 0.9em;
            color: #00FFFF; /* Luminous cyan for labels */
            font-weight: bold;
        }
        #searchInput, #typeFilter, #sortSelect {
            padding: 10px 12px;
            border: 1px solid #00FFFF; /* Luminous cyan border */
            border-radius: 8px;
            background-color: #1e242b; /* Slightly lighter dark for contrast */
            color: #c9d1d9;
            font-size: 0.95em;
            box-shadow: 0 0 8px rgba(0, 255, 255, 0.3); /* Subtle glow */
            transition: all 0.3s ease;
            min-width: 180px; /* Ensure inputs have a minimum width */
        }
        #searchInput:focus, #typeFilter:focus, #sortSelect:focus {
            outline: none;
            border-color: #FF00FF; /* Mystical magenta on focus */
            box-shadow: 0 0 12px rgba(255, 0, 255, 0.7); /* Enhanced glow */
        }
        .image-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 20px;
            padding: 20px 0;
            justify-items: center;
        }
        .image-item {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
            width: 100%;
            max-width: 300px;
            cursor: pointer; /* Indicate clickable */
        }
        .image-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 20px rgba(0, 255, 255, 0.6); /* Luminous cyan glow on hover */
        }
        .image-item img {
            width: 100%;
            height: 200px;
            object-fit: cover;
            display: block;
            border-bottom: 1px solid #30363d;
        }
        .image-info {
            padding: 15px;
            text-align: center;
        }
        .image-info p {
            margin: 5px 0;
            font-size: 0.9em;
            color: #b0b0b0;
            word-wrap: break-word;
        }
        .image-info .filename {
            font-weight: bold;
            color: #00FFFF; /* Luminous cyan for filename */
        }
        .image-info .query-folder {
            font-style: italic;
            color: #FF00FF; /* Mystical magenta for query folder */
            font-size: 0.85em;
        }
        .image-info .metadata-line {
            font-size: 0.8em;
            color: #888;
        }
        .no-results, #loadingMessage, #errorMessage {
            text-align: center;
            color: #FF6600; /* Fiery orange for no results */
            font-size: 1.2em;
            margin-top: 50px;
        }
        #errorMessage {
            color: #FF0000; /* Fiery red for errors */
        }

        /* Lightbox/Modal Styles */
        .modal {
            display: none; /* Hidden by default */
            position: fixed; /* Stay in place */
            z-index: 1000; /* Sit on top */
            left: 0;
            top: 0;
            width: 100%; /* Full width */
            height: 100%; /* Full height */
            overflow: auto; /* Enable scroll if needed */
            background-color: rgba(0,0,0,0.9); /* Black w/ opacity */
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s forwards;
        }
        .modal-content {
            margin: auto;
            display: block;
            max-width: 90%;
            max-height: 90%;
            object-fit: contain; /* Ensure image fits within bounds */
        }
        .modal-caption {
            margin: 15px auto;
            display: block;
            width: 80%;
            max-width: 700px;
            text-align: center;
            color: #ccc;
            padding: 10px 0;
            font-size: 1.2em;
        }
        .modal-close {
            position: absolute;
            top: 15px;
            right: 35px;
            color: #f1f1f1;
            font-size: 40px;
            font-weight: bold;
            transition: 0.3s;
            cursor: pointer;
        }
        .modal-close:hover,
        .modal-close:focus {
            color: #bbb;
            text-decoration: none;
            cursor: pointer;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        @keyframes fadeOut {
            from { opacity: 1; }
            to { opacity: 0; }
        }
        .modal.fade-out {
            animation: fadeOut 0.3s forwards;
        }

        /* Basic Dark Mode Scrollbar */
        ::-webkit-scrollbar {
            width: 12px;
        }
        ::-webkit-scrollbar-track {
            background: #161b22;
        }
        ::-webkit-scrollbar-thumb {
            background-color: #00FFFF; /* Luminous cyan thumb */
            border-radius: 6px;
            border: 3px solid #161b22;
        }
        ::-webkit-scrollbar-thumb:hover {
            background-color: #FF00FF; /* Mystical magenta thumb on hover */
        }

        /* Responsive adjustments */
        @media (max-width: 768px) {
            .controls-container {
                flex-direction: column;
                align-items: center;
            }
            #searchInput, #typeFilter, #sortSelect {
                width: 80%;
                max-width: none;
            }
            .image-grid {
                grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            }
            .image-item {
                max-width: none; /* Allow items to stretch more */
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Pyrmethus's Scrying Pool 👁️‍🗨️</h1>
        <div class="controls-container">
            <div class="control-group">
                <label for="searchInput">Scry by Name/Folder:</label>
                <input type="text" id="searchInput" onkeyup="applyFiltersAndSort()" placeholder="Search...">
            </div>
            <div class="control-group">
                <label for="typeFilter">Filter by Type:</label>
                <select id="typeFilter" onchange="applyFiltersAndSort()">
                    <option value="all">All Types</option>
                    <option value="GIF">GIF (Animated)</option>
                    <option value="JPEG">JPEG</option>
                    <option value="PNG">PNG</option>
                    <option value="WEBP">WEBP</option>
                    <option value="BMP">BMP</option>
                    <option value="TIFF">TIFF</option>
                    <!-- Add more as needed based on common formats -->
                </select>
            </div>
            <div class="control-group">
                <label for="sortSelect">Sort By:</label>
                <select id="sortSelect" onchange="applyFiltersAndSort()">
                    <option value="filename-asc">Filename (A-Z)</option>
                    <option value="filename-desc">Filename (Z-A)</option>
                    <option value="size-asc">Size (Smallest First)</option>
                    <option value="size-desc">Size (Largest First)</option>
                    <option value="width-asc">Width (Smallest First)</option>
                    <option value="width-desc">Width (Largest First)</option>
                    <option value="height-asc">Height (Smallest First)</option>
                    <option value="height-desc">Height (Largest First)</option>
                </select>
            </div>
        </div>
        <div id="imageGrid" class="image-grid">
            </div>
        <div id="noResults" class="no-results" style="display: none;">
            No images found matching your scrying query.
        </div>
        <div id="loadingMessage" class="no-results" style="display: block;">
            Loading manifestations...
        </div>
        <div id="errorMessage" class="no-results" style="display: none;">
            Error loading the master image manifest. Ensure `scrapey.py` has completed its ritual and forged `master_image_manifest.json`, and that your local server is active.
        </div>
    </div>

    <!-- The Lightbox Modal -->
    <div id="imageModal" class="modal">
        <span class="modal-close" onclick="closeModal()">×</span>
        <img class="modal-content" id="modalImage">
        <div id="modalCaption" class="modal-caption"></div>
    </div>

    <script>
        // Constants: Echoes from the Python script
        const DEFAULT_OUTPUT_DIR = "downloads";
        const MASTER_MANIFEST_FILENAME = "master_image_manifest.json";

        const imageGrid = document.getElementById('imageGrid');
        const searchInput = document.getElementById('searchInput');
        const typeFilter = document.getElementById('typeFilter');
        const sortSelect = document.getElementById('sortSelect');
        const noResultsMessage = document.getElementById('noResults');
        const loadingMessage = document.getElementById('loadingMessage');
        const errorMessage = document.getElementById('errorMessage');

        const imageModal = document.getElementById('imageModal');
        const modalImage = document.getElementById('modalImage');
        const modalCaption = document.getElementById('modalCaption');

        let allImages = []; // To hold all image data for filtering and sorting
        let displayedImages = []; // Images currently visible after filtering/sorting

        const IMAGES_PER_LOAD = 30; // Number of images to load at a time for lazy loading
        let currentImageIndex = 0; // Tracks how many images have been rendered

        /**
         * Loads the master image manifest and prepares images for rendering.
         */
        async function loadImages() {
            imageGrid.innerHTML = ''; // Clear existing visions
            allImages = []; // Reset the pool's memory
            displayedImages = [];
            currentImageIndex = 0;
            loadingMessage.style.display = 'block'; // Reveal loading message
            noResultsMessage.style.display = 'none'; // Conceal no results
            errorMessage.style.display = 'none'; // Conceal error message

            const manifestPath = `${DEFAULT_OUTPUT_DIR}/${MASTER_MANIFEST_FILENAME}`;
            console.log(`Attempting to fetch master manifest from: ${manifestPath}`);

            try {
                const response = await fetch(manifestPath);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const manifestData = await response.json();

                if (!Array.isArray(manifestData)) {
                    throw new Error("Master manifest is not a valid array. Its structure is corrupted.");
                }

                allImages = manifestData.map(item => {
                    const relativePath = `${DEFAULT_OUTPUT_DIR}/${item.query_based_subdir_name}/${item.filename}`;
                    return {
                        src: relativePath,
                        filename: item.filename,
                        queryFolder: item.query_based_subdir_name,
                        dimensions: item.dimensions,
                        width: item.width,
                        height: item.height,
                        size: item.file_size_bytes,
                        format: item.format,
                        mode: item.mode,
                        dpi: item.dpi,
                        isAnimated: item.is_animated,
                        frameCount: item.frame_count,
                        error: item.error,
                        element: null // Placeholder for the actual DOM element
                    };
                });

                if (allImages.length === 0) {
                    imageGrid.innerHTML = '<p class="no-results">No images found in the master manifest. Please run `scrapey.py` to download images and forge the manifest.</p>';
                    loadingMessage.style.display = 'none';
                    return;
                }

                loadingMessage.style.display = 'none'; // Conceal loading message
                applyFiltersAndSort(); // Apply initial filters and sorting, then render first batch
            } catch (e) {
                console.error("Failed to load master image manifest:", e);
                loadingMessage.style.display = 'none';
                errorMessage.style.display = 'block'; // Reveal error
                imageGrid.innerHTML = ''; // Clear grid if error
            }
        }

        /**
         * Applies current search, type filters, and sorting, then triggers rendering.
         */
        function applyFiltersAndSort() {
            const searchTerm = searchInput.value.toLowerCase();
            const selectedType = typeFilter.value;
            const sortOption = sortSelect.value;

            // 1. Filter
            let filtered = allImages.filter(imageData => {
                const filenameMatch = imageData.filename.toLowerCase().includes(searchTerm);
                const folderMatch = imageData.queryFolder.toLowerCase().includes(searchTerm);
                const typeMatch = selectedType === 'all' || (imageData.format && imageData.format.toLowerCase() === selectedType.toLowerCase());

                return (filenameMatch || folderMatch) && typeMatch;
            });

            // 2. Sort
            filtered.sort((a, b) => {
                switch (sortOption) {
                    case 'filename-asc': return a.filename.localeCompare(b.filename);
                    case 'filename-desc': return b.filename.localeCompare(a.filename);
                    case 'size-asc': return (a.size || 0) - (b.size || 0);
                    case 'size-desc': return (b.size || 0) - (a.size || 0);
                    case 'width-asc': return (a.width || 0) - (b.width || 0);
                    case 'width-desc': return (b.width || 0) - (a.width || 0);
                    case 'height-asc': return (a.height || 0) - (b.height || 0);
                    case 'height-desc': return (b.height || 0) - (a.height || 0);
                    default: return 0;
                }
            });

            displayedImages = filtered;
            currentImageIndex = 0; // Reset for lazy loading
            imageGrid.innerHTML = ''; // Clear grid for new filtered/sorted set
            renderNextBatch(); // Render the first batch
        }

        /**
         * Renders the next batch of images into the grid.
         */
        function renderNextBatch() {
            const batch = displayedImages.slice(currentImageIndex, currentImageIndex + IMAGES_PER_LOAD);

            if (batch.length === 0 && currentImageIndex === 0) {
                noResultsMessage.style.display = 'block';
            } else {
                noResultsMessage.style.display = 'none';
            }

            batch.forEach(imageData => {
                const item = document.createElement('div');
                item.className = 'image-item';
                item.onclick = () => openModal(imageData); // Attach click handler for modal

                const img = document.createElement('img');
                img.src = imageData.src;
                img.alt = imageData.filename;
                img.loading = 'lazy'; // Native lazy loading
                // Fallback for broken images: a mystical broken file icon
                img.onerror = function() {
                    this.onerror = null; // Prevent infinite loops
                    this.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiB2aWV3Qm94PSIwIDAgMjQgMjQiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTE4LjUgMThINC41QzMuNjcgMTggMyAxNy4zMyAzIDE2LjVWNi41QzMgNS42NyAzLjY3IDUgNC41IDVIOC41TDEwLjUzIDcuNDdIMjEuNDdDMjIuMzMgNy40NyAyMyA4LjEzIDIzIDguOTZWMTcuOTRDMjMgMTguNzcgMjIuMzMgMTkuNDcgMjEuNDcgMTkuNDdIMTUuNDdMMTMuNTIgMTguNDdIMTguNVYxOFoiIGZpbGw9IiM2NjY2NjYiLz48cGF0aCBkPSJNNiAxMi44TDMuNzMgMTUuMDcgNiAxNy4zNFYxMi44WiIgc3Ryb2tlPSIjZmZmZmZmIiBzdHJva2Utd2lkdGg9IjEuNSIvPjxwYXRoIGQ9Ik0xOC40NyAxMC45N0wxNS4yIDE0LjI0IDE2Ljg1IDE1LjkgMjAuMTIgMTIuNjNIMjIuMTlWMTEuNTdIMTguNDdaIiBzdHJva2U9IiNmZmZmZmZmIiBzdHJva2Utd2lkdGg9IjEuNSIvPj4=';
                    this.style.filter = 'grayscale(100%) opacity(50%)'; // Dim the broken image
                };

                const info = document.createElement('div');
                info.className = 'image-info';

                let sizeStr = imageData.size ? (imageData.size / 1024).toFixed(2) + ' KB' : 'Unknown';
                if (imageData.size && imageData.size > 1024 * 1024) {
                    sizeStr = (imageData.size / (1024 * 1024)).toFixed(2) + ' MB';
                }

                let dpiStr = imageData.dpi ? `DPI: ${imageData.dpi[0]}x${imageData.dpi[1]}` : '';
                let animatedStr = imageData.isAnimated ? `Frames: ${imageData.frameCount}` : '';
                let errorHtml = imageData.error ? `<p style="color: #FF0000; font-size: 0.7em;">Error: ${imageData.error}</p>` : '';

                info.innerHTML = `
                    <p class="filename">${imageData.filename}</p>
                    <p class="query-folder">Folder: ${imageData.queryFolder}</p>
                    <p class="metadata-line">Dims: ${imageData.dimensions || 'Unknown'}</p>
                    <p class="metadata-line">Size: ${sizeStr}</p>
                    <p class="metadata-line">Format: ${imageData.format || 'Unknown'}</p>
                    <p class="metadata-line">Mode: ${imageData.mode || 'Unknown'}</p>
                    ${dpiStr ? `<p class="metadata-line">${dpiStr}</p>` : ''}
                    ${animatedStr ? `<p class="metadata-line">${animatedStr}</p>` : ''}
                    ${errorHtml}
                `;

                item.appendChild(img);
                item.appendChild(info);
                imageGrid.appendChild(item);
                imageData.element = item; // Store reference to the DOM element
            });
            currentImageIndex += batch.length;
        }

        /**
         * Opens the modal with the clicked image and its details.
         * @param {Object} imageData - The data object for the clicked image.
         */
        function openModal(imageData) {
            modalImage.src = imageData.src;
            modalImage.alt = imageData.filename;

            let sizeStr = imageData.size ? (imageData.size / 1024).toFixed(2) + ' KB' : 'Unknown';
            if (imageData.size && imageData.size > 1024 * 1024) {
                sizeStr = (imageData.size / (1024 * 1024)).toFixed(2) + ' MB';
            }
            let dpiStr = imageData.dpi ? `DPI: ${imageData.dpi[0]}x${imageData.dpi[1]}` : '';
            let animatedStr = imageData.isAnimated ? `Frames: ${imageData.frameCount}` : '';
            let errorHtml = imageData.error ? `<span style="color: #FF0000; font-size: 0.9em;">Error: ${imageData.error}</span>` : '';

            modalCaption.innerHTML = `
                <strong>${imageData.filename}</strong><br>
                Folder: ${imageData.queryFolder}<br>
                Dimensions: ${imageData.dimensions || 'Unknown'}<br>
                Size: ${sizeStr}<br>
                Format: ${imageData.format || 'Unknown'}<br>
                Mode: ${imageData.mode || 'Unknown'}<br>
                ${dpiStr ? `${dpiStr}<br>` : ''}
                ${animatedStr ? `${animatedStr}<br>` : ''}
                ${errorHtml}
            `;
            imageModal.style.display = 'flex';
        }

        /**
         * Closes the modal.
         */
        function closeModal() {
            imageModal.classList.add('fade-out');
            imageModal.addEventListener('animationend', function handler() {
                imageModal.classList.remove('fade-out');
                imageModal.style.display = 'none';
                imageModal.removeEventListener('animationend', handler);
            });
        }

        // Lazy loading / Infinite scroll
        window.addEventListener('scroll', () => {
            if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 500) { // 500px from bottom
                if (currentImageIndex < displayedImages.length) {
                    renderNextBatch();
                }
            }
        });

        // Initiate the loading of images when the scrying pool is ready
        document.addEventListener('DOMContentLoaded', loadImages);
    </script>
</body>
</html>
EOF
echo -e "${GREEN}The 'image_viewer.html' enhanced scrying pool has been crafted!${NC}"
echo

print_header "Setup Ritual Complete!"
echo -e "${GREEN}All components for your Enhanced Bing Image Scrying and Viewing system are now in place.${NC}"
echo -e "${MAGENTA}To summon images, invoke the scrying script:${NC}"
echo -e "${CYAN}  python scrapey.py${NC}"
echo
echo -e "${MAGENTA}To view your manifested images in the enhanced scrying pool:${NC}"
echo -e "${CYAN}1. Ensure you have a local web server. In Termux, you can install lighttpd:${NC}"
echo -e "${CYAN}   pkg install lighttpd${NC}"
echo -e "${CYAN}2. Start the server from your current directory (where 'downloads' folder and 'image_viewer.html' reside):${NC}"
echo -e "${CYAN}   lighttpd -f .lighttpd.conf   (If you have a config, or use python's simple server)${NC}"
echo -e "${CYAN}   OR, simpler: python -m http.server 8000${NC}"
echo -e "${CYAN}3. Open your browser and navigate to: http://localhost:8000/image_viewer.html${NC}"
echo
echo -e "${YELLOW}May your digital visions be clear and abundant, seeker!${NC}"
