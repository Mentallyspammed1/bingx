```json
[
  {
    "suggestion": "Refactor Global State into a Context Class",
    "description": "Encapsulate configuration and runtime state into a single data class. This reduces the number of global variables, making the code easier to read, test, and maintain by passing a single context object to functions that need it, improving overall structure.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before ---\n# --- Global State Runes ---\n# temp_dir: Path | None = None\n# gemini_api_key: str = \"\"\n# raw_api_output_mode: bool = False\n# total_input_tokens: int = 0\n# total_output_tokens: int = 0\n# \n# def cleanup_temp_dir():\n#     if temp_dir and temp_dir.exists():\n#         ...\n\n# --- suggestion: after ---\nfrom dataclasses import dataclass, field\n\n@dataclass\nclass ScriptContext:\n    \"\"\"A container for script configuration and runtime state.\"\"\"\n    args: argparse.Namespace\n    config: configparser.ConfigParser\n    temp_dir: Path | None = None\n    api_key: str = \"\"\n    raw_api_output_mode: bool = False\n    total_input_tokens: int = 0\n    total_output_tokens: int = 0\n    # Use a list to be mutable within the dataclass instance\n    files_to_process: list[tuple[Path, Path]] = field(default_factory=list)\n\ndef cleanup_temp_dir(context: ScriptContext):\n    \"\"\"Dissolves the temporary sanctum, banishing its remnants.\"\"\"\n    if context.temp_dir and context.temp_dir.exists():\n        try:\n            shutil.rmtree(context.temp_dir)\n            log_debug(f\"Sanctum '{context.temp_dir}' dissolved into the void.\")\n        except OSError as e:\n            log_warning(f\"Could not banish temporary sanctum '{context.temp_dir}': {e}\")\n"
    }
  },
  {
    "suggestion": "Use a Custom Logging Formatter for Colors",
    "description": "Instead of manually prepending color codes in helper functions like `log_message`, create a custom `logging.Formatter`. This is a more idiomatic and robust way to handle logging, separating the message content from its presentation.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before ---\n# def log_message(level: int, message: str, color: str = Fore.RESET, style: str = Style.RESET_ALL):\n#     \"\"\"Logs a message with specified level and color.\"\"\"\n#     level_name = logging.getLevelName(level)\n#     # Using LIGHT variants for a brighter, more \"neon\" feel\n#     if level == logging.INFO:\n#         prefix = f\"{Fore.LIGHTCYAN_EX}[INFO]{Style.RESET_ALL}\"\n#     # ... more elifs ...\n#     logger.log(level, f\"{prefix} {color}{message}{style}\")\n\n# --- suggestion: after ---\nclass NeonFormatter(logging.Formatter):\n    \"\"\"A logging formatter with a vibrant neon theme.\"\"\"\n    FORMATS = {\n        logging.DEBUG: f\"{Fore.LIGHTMAGENTA_EX}[DEBUG]{Style.RESET_ALL} %(message)s\",\n        logging.INFO: f\"{Fore.LIGHTCYAN_EX}[INFO]{Style.RESET_ALL} {Fore.LIGHTBLUE_EX}%(message)s{Style.RESET_ALL}\",\n        logging.WARNING: f\"{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}[WARNING]{Style.RESET_ALL} {Fore.LIGHTYELLOW_EX}%(message)s{Style.RESET_ALL}\",\n        logging.ERROR: f\"{Fore.LIGHTRED_EX}{Style.BRIGHT}[ERROR]{Style.RESET_ALL} {Fore.LIGHTRED_EX}%(message)s{Style.RESET_ALL}\",\n        logging.CRITICAL: f\"{Fore.LIGHTWHITE_EX}{Style.BRIGHT}[CRITICAL]{Style.RESET_ALL} {Fore.LIGHTRED_EX}%(message)s{Style.RESET_ALL}\",\n    }\n\n    def format(self, record):\n        log_fmt = self.FORMATS.get(record.levelno)\n        formatter = logging.Formatter(log_fmt)\n        return formatter.format(record)\n\n# In main setup:\nhandler = logging.StreamHandler(sys.stdout)\n# formatter = logging.Formatter(\"%(message)s\") # old\nhandler.setFormatter(NeonFormatter()) # new\nlogger.addHandler(handler)\n"
    }
  },
  {
    "suggestion": "Implement Model-Aware Cost Estimation",
    "description": "API costs vary between models. Instead of hardcoding costs for one model, use a dictionary to store rates for different models. This allows for more accurate cost estimation when the user selects a model other than the default.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before ---\n# COST_PER_MILLION_INPUT_TOKENS = 3.50\n# COST_PER_MILLION_OUTPUT_TOKENS = 10.50\n# \n# def display_final_summary(...):\n#     input_cost = (total_input_tokens / 1_000_000) * COST_PER_MILLION_INPUT_TOKENS\n#     output_cost = (total_output_tokens / 1_000_000) * COST_PER_MILLION_OUTPUT_TOKENS\n\n# --- suggestion: after ---\nCOST_DATA = {\n    \"gemini-1.5-pro\": {\"input\": 3.50, \"output\": 10.50},\n    \"gemini-1.5-flash\": {\"input\": 0.35, \"output\": 1.05}, # Example rates\n    \"default\": {\"input\": 3.50, \"output\": 10.50} # Fallback\n}\n\ndef display_final_summary(files_processed_count: int, dry_run: bool, model_name: str):\n    #...\n    model_key = next((key for key in COST_DATA if key in model_name), \"default\")\n    rates = COST_DATA[model_key]\n    input_cost = (total_input_tokens / 1_000_000) * rates[\"input\"]\n    output_cost = (total_output_tokens / 1_000_000) * rates[\"output\"]\n    #...\n"
    }
  },
  {
    "suggestion": "Add Support for `.gitignore` Rules",
    "description": "When processing a directory, automatically discover and respect `.gitignore` files. This prevents the script from processing files that are intentionally ignored by the user's version control, such as build artifacts or local configurations. This requires the `pathspec` library.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before ---\n# In get_files_from_input_dir:\n# for root_str, _, files in os.walk(input_dir):\n#     # ... checks for script name, backup suffix, etc.\n\n# --- suggestion: after ---\n# import pathspec # Add this import\n\ndef get_files_from_input_dir(...):\n    # ...\n    gitignore_path = input_dir / '.gitignore'\n    spec = None\n    if gitignore_path.is_file():\n        try:\n            with open(gitignore_path, 'r') as f:\n                spec = pathspec.PathSpec.from_lines('gitwildmatch', f)\n            log_debug(\"Loaded .gitignore rules.\")\n        except Exception as e:\n            log_warning(f\"Could not parse .gitignore file: {e}\")\n\n    for root_str, _, files in os.walk(input_dir):\n        # ...\n        for file_name in files:\n            file_path = root / file_name\n            if spec and spec.match_file(str(file_path.relative_to(input_dir))):\n                log_debug(f\"Skipping gitignored file: {file_path.name}\")\n                continue\n            # ... rest of the checks\n"
    }
  },
  {
    "suggestion": "Improve Python Chunking with `ast` Module",
    "description": "The current Python chunking logic is based on indentation, which can fail with multi-line strings or complex layouts. Use Python's built-in `ast` (Abstract Syntax Tree) module to parse the code and split it based on top-level nodes (functions, classes, etc.) for much more reliable and accurate chunking.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before ---\n# if lang_hint == \"python\":\n#     log_debug(\"Using Python-aware splitting strategy (zero-indentation blocks).\")\n#     current_chunk_lines = []\n#     for line in lines:\n#         stripped_line = line.lstrip()\n#         if stripped_line and not stripped_line.startswith(\"#\") and (len(line) - len(stripped_line)) == 0:\n#             # ... complex line-based logic ...\n\n# --- suggestion: after ---\n# import ast\n# import astor # external library: pip install astor\n#\n# if lang_hint == \"python\":\n#     log_debug(\"Using Python AST splitting strategy.\")\n#     try:\n#         tree = ast.parse(content)\n#         for node in tree.body:\n#             # astor.to_source correctly reconstructs the source from the node\n#             chunk_content = astor.to_source(node)\n#             chunks_raw.append(chunk_content)\n#         if not chunks_raw and content.strip(): # Fallback for non-node content\n#             chunks_raw = [content]\n#     except SyntaxError as e:\n#         log_warning(f\"Could not parse Python with AST due to syntax error: {e}. Falling back to default split.\")\n#         # ... fallback logic ...\n"
    }
  },
  {
    "suggestion": "Load Prompts From an External File",
    "description": "Allow users to manage complex prompts by loading them from a file. This is more convenient than passing a long, multi-line string as a command-line argument and encourages reusable, version-controlled prompt templates.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before (in main) ---\n# parser.add_argument(\"--custom-prompt-template\", help=\"Custom prompt template. ...\")\n# # ...\n# # in process_chunk_with_api:\n# if args.custom_prompt_template:\n#     prompt_text = args.custom_prompt_template.replace(\"{original_code}\", original_content)\n\n# --- suggestion: after (in main) ---\nparser.add_argument(\"--custom-prompt-template\", help=\"Custom prompt template string...\")\nparser.add_argument(\"--prompt-file\", type=Path, help=\"Path to a file containing the prompt template.\")\n\n# In main, after parsing args:\nif args.prompt_file:\n    if not args.prompt_file.is_file():\n        log_error(f\"Prompt file not found: {args.prompt_file}\")\n        sys.exit(1)\n    try:\n        args.custom_prompt_template = args.prompt_file.read_text(encoding='utf-8')\n        log_debug(f\"Loaded prompt from {args.prompt_file}\")\n    except OSError as e:\n        log_error(f\"Could not read prompt file: {e}\")\n        sys.exit(1)\n"
    }
  },
  {
    "suggestion": "Allow In-Place File Modification",
    "description": "Add an `--in-place` flag to modify files directly, similar to tools like `sed` or `black`. This is a common and convenient workflow. The script should automatically create a backup of the original file before writing changes.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before (in main) ---\n# output_group.add_argument(\"-o\", \"--output-file\", type=Path, help=\"Output file path...\")\n# ...\n# if args.input_dir:\n#    if not args.output_dir:\n#        log_error(\"--output-dir is required when using --input-dir.\")\n\n# --- suggestion: after (in main) ---\nparser.add_argument(\"--in-place\", action=\"store_true\", help=\"Modify files in-place (creates backups).\")\n\n# After parsing args:\nif args.in_place and args.output_dir:\n    parser.error(\"argument --in-place: not allowed with argument --output-dir\")\n\n# When setting up files_to_process:\nif args.input_file and args.in_place:\n    # Set output path to be same as input for in-place editing\n    output_path_for_file = args.input_file\n    if not backup_output_file(output_path_for_file, True, args.dry_run):\n        sys.exit(1)\n    files_to_process.append((args.input_file, output_path_for_file))\n"
    }
  },
  {
    "suggestion": "Add a `--diff-only` Mode for CI/CD",
    "description": "Implement a `--diff-only` or `--check` mode that computes all changes and prints a unified diff to the console, then exits with a non-zero status code if changes were found. This is extremely useful for integration into CI/CD pipelines to check for style or syntax issues without modifying files.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before (in main) ---\n# parser.add_argument(\"--dry-run\", action=\"store_true\", help=\"Perform all operations but do not write any files...\")\n\n# --- suggestion: after (in main) ---\n# Add a new global or context variable: `changes_found = False`\nparser.add_argument(\"--diff-only\", action=\"store_true\", help=\"Show a diff of changes and exit with a status code. Implies --dry-run.\")\n\n# In reassemble_output:\nglobal changes_found\nif dry_run and original_content != new_content:\n    # This part already exists and is perfect for diff-only\n    print(f\"\\n{Style.BRIGHT}{Fore.LIGHTYELLOW_EX}--- Dry Run: Changes for fragment: {original_chunk_file.name} ---\")\n    display_diff(original_content, new_content, original_chunk_file.name)\n    changes_found = True\n    final_content_parts.append(new_content)\n\n# In main, before exiting:\nif args.diff_only:\n    log_info(\"Diff-only mode finished.\")\n    if changes_found:\n        log_warning(\"Changes were found.\")\n        sys.exit(1)\n    else:\n        log_success(\"No changes needed.\")\n        sys.exit(0)\n"
    }
  },
  {
    "suggestion": "Cache API Responses to Reduce Cost",
    "description": "Implement a simple file-based cache for API responses. Before calling the API, generate a hash of the prompt and chunk content. If a cached response exists for that hash, use it instead. This can save significant time and money when re-running the script on files with unchanged sections.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before (in process_chunk_with_api) ---\n# # The function immediately builds the prompt and calls the API\n# prompt_text = ...\n# json_payload = ...\n# for attempt in range(1, args.retries + 1):\n#     response = requests.post(...)\n\n# --- suggestion: after (in process_chunk_with_api) ---\n# import hashlib # Add this import\n\n# ... inside process_chunk_with_api ...\nprompt_text = ...\n\n# Caching logic\ncache_dir = temp_dir.parent / \"pyrmethus_cache\"\ncache_dir.mkdir(exist_ok=True)\ncache_key = hashlib.sha256((prompt_text + original_content).encode('utf-8')).hexdigest()\ncache_file = cache_dir / cache_key\n\nif not args.force and cache_file.exists():\n    log_debug(f\"Found cached response for chunk {chunk_name}\")\n    final_content = cache_file.read_text(encoding='utf-8')\n    # ... (write output chunk and return) ...\n\n# ... (existing API call logic) ...\n\n# After getting a successful response:\nfinal_content = extract_code_block(text_content)\ncache_file.write_text(final_content, encoding='utf-8') # Save to cache\n# ... (rest of the function)\n"
    }
  },
  {
    "suggestion": "Use a Real Tokenizer for Accurate Costing",
    "description": "The current `CHARS_PER_TOKEN` heuristic is a very rough approximation. For more accurate cost estimation, integrate a proper tokenizer library like `tiktoken` (used by OpenAI, but generally good for other models too) or a library specific to Gemini if available. This provides precise token counts.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before ---\n# CHARS_PER_TOKEN = 4\n# def process_chunk_with_api(...):\n#     # ...\n#     input_tokens = len(prompt_text) // CHARS_PER_TOKEN\n#     # ...\n#     output_tokens = len(final_content) // CHARS_PER_TOKEN\n#     return ..., input_tokens, output_tokens\n\n# --- suggestion: after ---\n# import tiktoken # Requires: pip install tiktoken\n# try:\n#     TOKENIZER = tiktoken.get_encoding(\"cl100k_base\")\n# except ImportError:\n#     TOKENIZER = None\n#     log_warning(\"tiktoken not found, falling back to character-based token estimation.\")\n#\n# def estimate_tokens(text: str) -> int:\n#     if TOKENIZER:\n#         return len(TOKENIZER.encode(text))\n#     return len(text) // 4 # Fallback\n#\n# def process_chunk_with_api(...):\n#     # ...\n#     input_tokens = estimate_tokens(prompt_text)\n#     # ...\n#     output_tokens = estimate_tokens(final_content)\n#     return ..., input_tokens, output_tokens\n"
    }
  },
  {
    "suggestion": "Validate API Responses with `pydantic`",
    "description": "The current method of extracting data from the API response involves multiple `.get()` calls, which is verbose and error-prone. Use `pydantic` to define a model of the expected response structure. This provides automatic data validation, conversion, and cleaner access to nested data.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before ---\n# # in process_chunk_with_api\n# response_data = response.json()\n# text_content = response_data.get(\"candidates\", [{}])[0].get(\"content\", {}).get(\"parts\", [{}])[0].get(\"text\")\n# if not text_content:\n#     log_warning(...)\n\n# --- suggestion: after ---\n# from pydantic import BaseModel, Field # Requires: pip install pydantic\n# from typing import List, Optional\n#\n# class Part(BaseModel):\n#     text: str\n# \n# class Content(BaseModel):\n#     parts: List[Part]\n#     role: Optional[str] = None\n#\n# class Candidate(BaseModel):\n#     content: Content\n#\n# class GeminiResponse(BaseModel):\n#     candidates: List[Candidate]\n#\n# # in process_chunk_with_api\n# try:\n#     response_model = GeminiResponse.parse_obj(response.json())\n#     text_content = response_model.candidates[0].content.parts[0].text\n# except (ValidationError, IndexError) as e:\n#     log_error(f\"Invalid API response structure: {e}\")\n#     # ... handle error ...\n"
    }
  },
  {
    "suggestion": "Retry on 5xx Server Errors",
    "description": "The current retry logic handles 429 (Rate Limit) errors but not 5xx server errors (e.g., 500, 503). These are often transient and should trigger a retry attempt, making the script more resilient to temporary API provider issues.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before ---\n#         except requests.exceptions.HTTPError as e:\n#             error_details = e.response.text if e.response else \"No response text\"\n#             if e.response and e.response.status_code == 429:\n#                 log_warning(f\"Rate limit reached...)\n#                 time.sleep(API_RATE_LIMIT_WAIT)\n#             elif e.response and e.response.status_code in [400, 401, 403]:\n#                 log_error(f\"API Error {e.response.status_code}...)\n\n# --- suggestion: after ---\n        except requests.exceptions.HTTPError as e:\n            error_details = e.response.text if e.response else \"No response text\"\n            if e.response:\n                status = e.response.status_code\n                if status == 429:\n                    log_warning(f\"Rate limit reached...)\n                    time.sleep(API_RATE_LIMIT_WAIT)\n                elif status >= 500: # Is it a server error?\n                    log_warning(f\"API server error ({status}). Retrying... Details: {error_details[:200]}\")\n                    time.sleep(args.retry_delay)\n                elif status in [400, 401, 403]: # Unrecoverable client error\n                    log_error(f\"API Error {status}...)\n                    return None, original_content, original_chunk_path, input_tokens, 0\n            else:\n                log_error(f\"API failed... Retrying...\")\n                time.sleep(args.retry_delay)\n"
    }
  },
  {
    "suggestion": "Add a `--list-models` Action",
    "description": "Implement a command to query the Gemini API and list all available models. This helps users discover new or more suitable models (e.g., `gemini-1.5-pro-latest`) without having to check the Google Cloud documentation.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before (in main) ---\n# # No such feature exists\n# parser = argparse.ArgumentParser(...)\n# input_group = parser.add_mutually_exclusive_group(required=True)\n\n# --- suggestion: after (in main) ---\n# Add argument\nparser.add_argument(\"--list-models\", action=\"store_true\", help=\"List available Gemini models and exit.\")\n# Make input group not required if --list-models is present\ninput_group = parser.add_mutually_exclusive_group(required=not any(x in sys.argv for x in ['--list-models', '-h', '--help']))\n\n# After parsing args\nif args.list_models:\n    list_available_models(gemini_api_key)\n    sys.exit(0)\n\n# New function\ndef list_available_models(api_key):\n    log_info(\"Fetching available models...\")\n    try:\n        response = requests.get(f\"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}\")\n        response.raise_for_status()\n        models = response.json().get('models', [])\n        for model in models:\n            print(f\"- {model.get('name')}\")\n    except Exception as e:\n        log_error(f\"Failed to fetch models: {e}\")\n"
    }
  },
  {
    "suggestion": "Refactor Chunk Splitting to be Pluggable",
    "description": "The `split_file_into_chunks` function uses a large `if/elif/else` block to select a splitting strategy. Refactor this to use a dictionary mapping language hints to strategy functions. This makes the code cleaner and easier to extend with new language-specific splitters.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before (in split_file_into_chunks) ---\n# if lang_hint == \"python\":\n#     # python logic\n# elif lang_hint in [\"bash\", \"sh\", \"zsh\"]:\n#     # shell logic\n# else:\n#     # default logic\n\n# --- suggestion: after ---\ndef _split_python(content):\n    # ... python splitting logic ...\n    return chunks\n\ndef _split_shell(content):\n    # ... shell splitting logic ...\n    return chunks\n\ndef _split_default(content):\n    # ... default splitting logic ...\n    return chunks\n\nSPLITTING_STRATEGIES = {\n    \"python\": _split_python,\n    \"bash\": _split_shell,\n    \"sh\": _split_shell,\n    \"zsh\": _split_shell,\n}\n\ndef split_file_into_chunks(...):\n    # ...\n    log_debug(f\"Looking for splitter for lang_hint: {lang_hint}\")\n    splitter_func = SPLITTING_STRATEGIES.get(lang_hint, _split_default)\n    chunks_raw = splitter_func(content)\n    # ...\n"
    }
  },
  {
    "suggestion": "Use `tqdm` for a Better Progress Bar",
    "description": "Replace the manual progress bar implementation with the `tqdm` library. It's easy to use and provides richer features out-of-the-box, such as a cleaner look, transfer rate (chunks/s), and an estimated time of arrival (ETA), improving user experience during long-running jobs.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before (in process_single_file_workflow) ---\n# for future in as_completed(future_to_chunk_info):\n#     # ...\n#     progress = int(100 * completed_count / total_chunks) if total_chunks > 0 else 100\n#     bar = \"█\" * filled_length + \"-\" * (bar_length - filled_length)\n#     sys.stderr.write(f\"\\r[PROGRESS] [{bar}] {progress}% ...\")\n# sys.stderr.write(\"\\n\")\n\n# --- suggestion: after (in process_single_file_workflow) ---\n# from tqdm import tqdm # Requires: pip install tqdm\n# # ...\n# with ThreadPoolExecutor(max_workers=args.jobs) as executor:\n#     # ... setup futures ...\n#     # Use tqdm to wrap the as_completed iterator\n#     progress_bar = tqdm(as_completed(future_to_chunk_info), total=len(chunks_to_process_info), desc=f\"Processing {original_file_path.name}\", unit=\"chunk\", file=sys.stderr)\n#     for future in progress_bar:\n#         # ... existing logic to process future.result() ...\n#         # The progress bar updates automatically\n#         pass\n"
    }
  },
  {
    "suggestion": "Centralize Configuration Resolution",
    "description": "The logic for resolving settings from CLI arguments, environment variables, and the config file is repeated for each setting. Centralize this into a helper function to reduce code duplication and make it easier to add new configurable options.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before (in main) ---\n# args.model = args.model if args.model is not None else os.getenv(\"GEMINI_MODEL\") or config.get(\"Gemini\", \"model\", fallback=DEFAULT_MODEL)\n# args.temperature = args.temperature if args.temperature is not None else float(os.getenv(\"GEMINI_TEMPERATURE\", config.get(\"Gemini\", \"temperature\", fallback=str(DEFAULT_TEMPERATURE))))\n# args.jobs = args.jobs if args.jobs is not None else int(os.getenv(\"PYRMETHUS_JOBS\", config.get(\"Pyrmethus\", \"jobs\", fallback=str(DEFAULT_MAX_JOBS))))\n\n# --- suggestion: after (in main) ---\ndef resolve_setting(cli_val, env_key, config_tuple, default, type_cast=str):\n    \"\"\"Resolves a setting from CLI, environment, or config file.\"\"\"\n    if cli_val is not None:\n        return cli_val\n    val = os.getenv(env_key)\n    if val is not None:\n        return type_cast(val)\n    section, key = config_tuple\n    return type_cast(config.get(section, key, fallback=str(default)))\n\n# In main, after loading config:\nargs.model = resolve_setting(args.model, \"GEMINI_MODEL\", (\"Gemini\", \"model\"), DEFAULT_MODEL)\nargs.temperature = resolve_setting(args.temperature, \"GEMINI_TEMPERATURE\", (\"Gemini\", \"temperature\"), DEFAULT_TEMPERATURE, float)\nargs.jobs = resolve_setting(args.jobs, \"PYRMETHUS_JOBS\", (\"Pyrmethus\", \"jobs\"), DEFAULT_MAX_JOBS, int)\n"
    }
  },
  {
    "suggestion": "Respect `XDG_CONFIG_HOME` Standard",
    "description": "The configuration file path is hardcoded to `~/.config/pyrmethus`. For better cross-platform compatibility and adherence to Linux standards, the script should respect the `XDG_CONFIG_HOME` environment variable if it is set.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before ---\n# SCRIPT_NAME = Path(__file__).name\n# CONFIG_DIR = Path.home() / \".config\" / \"pyrmethus\"\n# CONFIG_FILE = CONFIG_DIR / \"config.ini\"\n\n# --- suggestion: after ---\nSCRIPT_NAME = Path(__file__).name\n\n# Respect XDG_CONFIG_HOME if set, otherwise default to ~/.config\nXDG_CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME')\nif XDG_CONFIG_HOME:\n    CONFIG_DIR = Path(XDG_CONFIG_HOME) / \"pyrmethus\"\nelse:\n    CONFIG_DIR = Path.home() / \".config\" / \"pyrmethus\"\n\nCONFIG_FILE = CONFIG_DIR / \"config.ini\"\n"
    }
  },
  {
    "suggestion": "Add a `--no-color` Flag",
    "description": "Provide an option to disable all colorized output. This is essential for environments that do not support ANSI color codes, such as certain CI/CD logs, or when redirecting the script's output to a file.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before ---\n# import colorama\n# colorama.init(autoreset=True)\n#\n# parser.add_argument(\"--dry-run\", ...)\n\n# --- suggestion: after ---\n# import colorama\n# \n# parser.add_argument(\"--no-color\", action=\"store_true\", help=\"Disable colorized output.\")\n# ...\n# args = parser.parse_args()\n# \n# # Initialize colorama based on the flag\n# colorama.init(autoreset=True, strip=args.no_color)\n"
    }
  },
  {
    "suggestion": "Make `get_api_key` a Pure Function",
    "description": "Refactor `get_api_key` so it returns the discovered key instead of setting a global variable. This removes side effects, makes the function's behavior more predictable, and improves testability.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before ---\n# def get_api_key(args_key: str, config: configparser.ConfigParser):\n#     \"\"\"Summons the Gemini API key...\"\"\"\n#     global gemini_api_key\n#     if args_key:\n#         gemini_api_key = args_key\n#         return\n#     # ... sets global gemini_api_key in other branches\n\n# --- suggestion: after ---\ndef get_api_key(args_key: str, config: configparser.ConfigParser) -> str | None:\n    \"\"\"Summons the Gemini API key and returns it.\"\"\"\n    # 1. Command-line argument\n    if args_key:\n        log_debug(\"API key summoned from command-line arguments.\")\n        return args_key\n\n    # 2. .env file or environment\n    load_dotenv()\n    if \"GEMINI_API_KEY\" in os.environ:\n        log_debug(\"API key summoned from .env file or environment's ether.\")\n        return os.environ[\"GEMINI_API_KEY\"]\n    \n    # ... other branches return the key or None\n    return None\n\n# In main:\ngemini_api_key = get_api_key(args.key, config)\nif not gemini_api_key:\n    # ... handle missing key ...\n"
    }
  },
  {
    "suggestion": "Validate Custom Prompt Template",
    "description": "If a user provides a custom prompt via `--custom-prompt-template` or `--prompt-file`, validate that it contains the necessary placeholder (e.g., `{original_code}`). This provides early feedback on a malformed template instead of failing later with a confusing API error.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before (in main) ---\n# if args.prompt_file:\n#     # ... loads prompt from file\n#     args.custom_prompt_template = ...\n\n# --- suggestion: after (in main) ---\n# After resolving the prompt template string\nif args.custom_prompt_template and \"{original_code}\" not in args.custom_prompt_template:\n    log_error(\"Custom prompt template must include the '{original_code}' placeholder.\")\n    sys.exit(1)\n"
    }
  },
  {
    "suggestion": "Improve Stdin Workflow for Empty Input",
    "description": "Currently, the script exits immediately if stdin is empty, bypassing the final summary. A better approach is to let the workflow continue. This will result in processing zero chunks and then printing a consistent final summary, such as '0 files processed', which is more informative.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before ---\n#             stdin_content = sys.stdin.read()\n#             if not stdin_content.strip():\n#                 log_warning(\"Input from stdin is empty. Nothing to process.\")\n#                 sys.exit(0) # Exits abruptly\n\n# --- suggestion: after ---\n            stdin_content = sys.stdin.read()\n            # Do not exit. Let the empty content be processed.\n            # The downstream logic will handle it gracefully (0 chunks).\n            if not stdin_content.strip():\n                log_warning(\"Input from stdin is empty. The ritual will complete with no changes.\")\n\n            stdin_tmp_path = temp_dir / \"stdin.tmp\"\n            # ... continue as normal ...\n"
    }
  },
  {
    "suggestion": "Use `argparse.FileType` for Cleaner File Handling",
    "description": "Instead of manually handling file paths and checking for stdin with a string comparison ('-'), use `argparse.FileType`. This allows argparse to handle opening files and stdin/stdout streams, leading to cleaner, more idiomatic code for I/O operations.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before ---\n# input_group.add_argument(\"-i\", \"--input-file\", type=Path, help=\"Input file path or '-' for stdin.\")\n# ...\n# is_stdin = str(args.input_file) == \"-\"\n# if is_stdin:\n#     stdin_content = sys.stdin.read()\n#     stdin_tmp_path.write_text(stdin_content)\n#     input_path = stdin_tmp_path\n# else:\n#     input_path = args.input_file\n\n# --- suggestion: after ---\nimport tempfile\n# \n# input_group.add_argument(\"-i\", \"--input-file\", type=argparse.FileType('r', encoding='UTF-8'), default=sys.stdin, help=\"Input file path (default: stdin).\")\n# output_group.add_argument(\"-o\", \"--output-file\", type=argparse.FileType('w', encoding='UTF-8'), default=sys.stdout, help=\"Output file path (default: stdout).\")\n\n# In main:\n# if args.input_file is sys.stdin:\n#    if sys.stdin.isatty():\n#        # ... error out ...\n#    log_info(\"Reading from stdin...\")\n# # Read content and write to a temporary file for chunking\n# with tempfile.NamedTemporaryFile(mode='w', delete=False, dir=temp_dir, suffix='.tmp') as f:\n#     f.write(args.input_file.read())\n#     input_path = Path(f.name)\n# args.input_file.close()\n"
    }
  },
  {
    "suggestion": "Define Constants for Magic Values",
    "description": "The script uses a magic number (30) to check the length of an API key. Replace this with a named constant, like `MIN_API_KEY_LENGTH`. This improves readability and makes the value's purpose self-documenting and easier to change.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before (in get_api_key) ---\n#     if len(gemini_api_key) < 30:  # Gemini keys are typically long\n#         log_warning(\"API Key seems unusually short. Please verify its authenticity.\")\n\n# --- suggestion: after ---\n# At top of file:\nMIN_API_KEY_LENGTH = 35 # Typical length of Gemini API keys is 39\n\n# In get_api_key:\n    if len(gemini_api_key) < MIN_API_KEY_LENGTH:\n        log_warning(f\"API Key is shorter than {MIN_API_KEY_LENGTH} characters. Please verify its authenticity.\")\n"
    }
  },
  {
    "suggestion": "Enhance Interactive Edit with Context",
    "description": "When a user chooses to 'edit' a chunk in interactive mode, the context of the surrounding code is lost. To help them make better edits, show a few lines from the previous and next chunks (if they exist) as read-only context around the editable chunk.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before (in reassemble_output) ---\n# if response == \"e\":\n#     # ... writes new_content to a temp file and opens in editor ...\n#     temp_edit_file.write_text(new_content, encoding=\"utf-8\")\n\n# --- suggestion: after (in reassemble_output) ---\nif response == \"e\":\n    # ...\n    # Get context from previous chunk if available\n    prev_chunk_content = final_content_parts[-1] if final_content_parts else \"\"\n    prev_context = \"\\n\".join(prev_chunk_content.splitlines()[-3:])\n\n    # (This requires a lookahead to the next chunk, which complicates the loop)\n    # A simpler implementation would be to just show previous context.\n\n    editable_content = (\n        f\"# --- CONTEXT (PREVIOUS CHUNK, READ-ONLY) ---\\n\"\n        f\"{prev_context}\\n\"\n        f\"# --- END CONTEXT ---\n\\n\"\n        f\"# --- EDIT THIS CHUNK ---\\n\"\n        f\"{new_content}\"\n    )\n    temp_edit_file.write_text(editable_content, encoding=\"utf-8\")\n    # ... open editor, then parse the edited content back out ...\n"
    }
  },
  {
    "suggestion": "Add a `--version` Action",
    "description": "Implement a `--version` flag to print the script's version number and exit. This is a standard CLI feature that is helpful for debugging, bug reporting, and managing different versions of the tool.",
    "code_snippet": {
      "file": "gr.py",
      "code": "\n# --- suggestion: before (at top of file) ---\n# SCRIPT_NAME = Path(__file__).name\n#\n# parser.add_argument(\"-v\", \"--verbose\", ...)\n\n# --- suggestion: after (at top of file) ---\n__version__ = \"1.0.0\" # Define a version\nSCRIPT_NAME = Path(__file__).name\n\n# In main, add argument:\nparser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')\n# `argparse` handles the rest automatically.\n"
    }
  }
]
```
