import argparse

import ast

import configparser

import difflib

import hashlib

import json

import logging

import os

import re

import shutil

import signal

import subprocess

import sys

import tempfile

import time

from concurrent.futures import ThreadPoolExecutor, as_completed

from dataclasses import dataclass, field

from datetime import datetime

from pathlib import Path

import astor

import pathspec

import requests

import tqdm

from colorama import Fore, init, Style

from dotenv import load_dotenv

from colorama import init
init(autoreset=True)

DEFAULT_MODEL = 'gemini-1.5-flash'

DEFAULT_TEMPERATURE = 0.2

DEFAULT_MAX_JOBS = 5

DEFAULT_CONNECT_TIMEOUT = 20

DEFAULT_READ_TIMEOUT = 180

MAX_RETRIES = 3

RETRY_DELAY_SECONDS = 5

API_RATE_LIMIT_WAIT = 61

API_BASE_URL = 'https://generativelanguage.googleapis.com/v1beta/models'

from pathlib import Path

SCRIPT_NAME = Path(__file__).name

from pathlib import Path

CONFIG_DIR = Path.home() / '.config' / 'pyrmethus'

CONFIG_FILE = CONFIG_DIR / 'config.ini'

TIMESTAMP_FORMAT = '%Y%m%d_%H%M%S'

CHUNK_PREFIX = 'chunk_'

OUTPUT_CHUNK_PREFIX = 'output_chunk_'

CHECKPOINT_SUFFIX = '.gr.checkpoint'

BACKUP_SUFFIX = '.bak'

COST_DATA = {'gemini-1.5-pro': {'input': 3.5, 'output': 10.5},
             'gemini-1.5-flash': {'input': 0.35, 'output': 1.05}, 'default': {
                 'input': 3.5, 'output': 10.5}}

CHARS_PER_TOKEN = 4

logger = logging.getLogger('gemini_review')

log_level_map = {'DEBUG': logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING, 'ERROR': logging.ERROR, 'CRITICAL': logging.CRITICAL}

from dataclasses import dataclass, field
import argparse
import configparser
from pathlib import Path

@dataclass
class ScriptContext:
    """A container for script configuration and runtime state."""
    args: argparse.Namespace
    config: configparser.ConfigParser
    api_key: str = ''
    temp_dir: Path | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    files_to_process: list[tuple[Path, Path]] = field(default_factory=list)
    has_changes: bool = False

ctx: ScriptContext | None = None

class NeonFormatter(logging.Formatter):
    """A logging formatter with a vibrant neon theme."""
    FORMATS = {logging.DEBUG:
        f'{Fore.LIGHTMAGENTA_EX}[DBG]{Style.RESET_ALL} %(message)s',
        logging.INFO:
        f'{Fore.LIGHTCYAN_EX}[INFO]{Style.RESET_ALL} {Fore.LIGHTBLUE_EX}%(message)s{Style.RESET_ALL}'
        , logging.WARNING:
        f'{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}[WARN]{Style.RESET_ALL} {Fore.LIGHTYELLOW_EX}%(message)s{Style.RESET_ALL}'
        , logging.ERROR:
        f'{Fore.LIGHTRED_EX}{Style.BRIGHT}[ERROR]{Style.RESET_ALL} {Fore.LIGHTRED_EX}%(message)s{Style.RESET_ALL}'
        , logging.CRITICAL:
        f'{Fore.LIGHTWHITE_EX}{Style.BRIGHT}[CRIT]{Style.RESET_ALL} {Fore.LIGHTRED_EX}%(message)s{Style.RESET_ALL}'
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, '%(message)s')
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


import logging
import sys

def setup_logger(level: int):
    """Configures the global logger with the NeonFormatter."""
    logger = logging.getLogger()
    logger.setLevel(level)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(NeonFormatter())
    logger.addHandler(handler)

def log_info(message: str):
    logger.info(message)


def log_success(message: str):
    logger.info(f'{Fore.LIGHTGREEN_EX}{Style.BRIGHT}{message}{Style.RESET_ALL}'
        )


def log_warning(message: str):
    logger.warning(message)


def log_error(message: str):
    logger.error(message)


def log_debug(message: str):
    logger.debug(message)


def load_config() ->configparser.ConfigParser:
    """Loads configuration from the Pyrmethus config scroll."""
    config = configparser.ConfigParser()
    if CONFIG_FILE.is_file():
        log_debug(f'Loading configuration from {CONFIG_FILE}')
        try:
            config.read(CONFIG_FILE)
        except configparser.Error as e:
            log_error(f'Error reading config scroll {CONFIG_FILE}: {e}')
            return configparser.ConfigParser()
    return config


def get_api_key():
    """Summons the Gemini API key and stores it in the context."""
    if ctx.args.key:
        ctx.api_key = ctx.args.key
        log_debug('API key summoned from command-line arguments.')
        return
    load_dotenv()
    if 'GEMINI_API_KEY' in os.environ:
        ctx.api_key = os.environ['GEMINI_API_KEY']
        log_debug("API key summoned from .env file or environment's ether.")
        return
    if ctx.config.has_section('Gemini') and 'api_key' in ctx.config['Gemini']:
        ctx.api_key = ctx.config['Gemini']['api_key']
        log_debug('API key summoned from config scroll.')
        return
    try:
        api_key_input = input(
            f'{Fore.LIGHTBLUE_EX}{Style.BRIGHT}Enter your Gemini API key: {Style.RESET_ALL}'
            ).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        log_error(
            'API key input cancelled. The ritual cannot proceed without the key.'
            )
        sys.exit(1)
    if not api_key_input:
        log_error(
            'The API key is the heart of this ritual. It cannot be absent!')
        sys.exit(1)
    ctx.api_key = api_key_input
    if len(ctx.api_key) < 30:
        log_warning(
            'API Key seems unusually short. Please verify its authenticity.')
    try:
        save_key = input(
            f'{Fore.LIGHTYELLOW_EX}Inscribe this key to {CONFIG_FILE} for future rituals? (y/N): {Style.RESET_ALL}'
            ).lower()
        if save_key == 'y':
            save_api_key_to_config()
    except (EOFError, KeyboardInterrupt):
        print()
        log_info('Skipping key inscription.')


def save_api_key_to_config():
    """Inscribes the Gemini API key from context to the config scroll."""
    if not CONFIG_DIR.exists():
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            log_debug(f'Created config directory: {CONFIG_DIR}')
        except OSError as e:
            log_error(f'Could not create config directory {CONFIG_DIR}: {e}')
            return
    if not ctx.config.has_section('Gemini'):
        ctx.config.add_section('Gemini')
    ctx.config['Gemini']['api_key'] = ctx.api_key
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            ctx.config.write(f)
        log_success(f'API key inscribed in {CONFIG_FILE}')
    except OSError as e:
        log_error(
            f'Failed to inscribe API key to config scroll {CONFIG_FILE}: {e}')


def check_dependencies():
    """Ensures the presence of optional arcane tools for pre-flight checks."""
    log_info(
        f'{Fore.LIGHTMAGENTA_EX}Inspecting the arcane arsenal for optional tools...{Style.RESET_ALL}'
        )
    deps = {'ruff': 'Python linter & formatter', 'shellcheck':
        'Shell script linter'}
    missing = []
    for dep, desc in deps.items():
        if not shutil.which(dep):
            missing.append(dep)
            log_debug(f'Missing optional tool: {dep} ({desc})')
    if missing:
        log_warning(
            f"Optional tools not found: {', '.join(missing)}. Pre-check functionality will be limited."
            )
    else:
        log_success('All optional arcane tools found.')


def create_temp_dir() ->bool:
    """Conjures a secure temporary sanctum for chunk sorcery."""
    try:
        base_tmp_dir = ctx.args.temp_dir
        if not base_tmp_dir:
            termux_tmp_path = Path('/data/data/com.termux/files/usr/tmp')
            if termux_tmp_path.is_dir() and os.access(termux_tmp_path, os.W_OK
                ):
                base_tmp_dir = termux_tmp_path
        if base_tmp_dir and not Path(base_tmp_dir).is_dir():
            log_warning(
                f'Custom temp dir {base_tmp_dir} does not exist, using system default.'
                )
            base_tmp_dir = None
        ctx.temp_dir = Path(tempfile.mkdtemp(prefix='gemini_review_', dir=
            base_tmp_dir))
        log_debug(f'Temporary sanctum created at: {ctx.temp_dir}')
        return True
    except Exception as e:
        log_error(f'Failed to conjure temporary sanctum: {e}')
        return False


def cleanup_temp_dir():
    """Dissolves the temporary sanctum, banishing its remnants."""
    if ctx and ctx.temp_dir and ctx.temp_dir.exists():
        try:
            shutil.rmtree(ctx.temp_dir)
            log_debug(f"Sanctum '{ctx.temp_dir}' dissolved into the void.")
        except OSError as e:
            log_warning(
                f"Could not banish temporary sanctum '{ctx.temp_dir}': {e}")


def handle_exit(signum=None, frame=None):
    """Guides the script to a graceful exit, ensuring no trace is left behind."""
    print()
    log_info(
        f'{Fore.LIGHTMAGENTA_EX}A signal from the beyond... initiating graceful dissolution of the ritual.{Style.RESET_ALL}'
        )
    cleanup_temp_dir()
    sys.exit(0)


def backup_file(file_path: Path) ->bool:
    """Creates a backup of a file. Used for --in-place and --force."""
    if not file_path.exists():
        return True
    timestamp = datetime.now().strftime(TIMESTAMP_FORMAT)
    backup_path = file_path.with_name(
        f'{file_path.name}.{timestamp}{BACKUP_SUFFIX}')
    try:
        shutil.copy2(file_path, backup_path)
        log_info(f"Original file preserved as '{backup_path.name}'.")
        return True
    except OSError as e:
        log_error(f"Failed to preserve original file '{file_path.name}': {e}")
        return False


def get_file_type_from_extension(file_path: Path) ->(str | None):
    """Infers a language hint from a file's extension."""
    ext_map = {'.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.sh': 'bash', '.bash': 'bash', '.zsh': 'bash', '.html': 'html',
        '.css': 'css', '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
        '.xml': 'xml', '.md': 'markdown', '.txt': 'text', '.go': 'go', '.c':
        'c', '.cpp': 'cpp', '.java': 'java', '.rs': 'rust', '.rb': 'ruby',
        '.php': 'php', '.swift': 'swift', '.kt': 'kotlin', '.cs': 'csharp',
        '.vue': 'vue', '.ipynb': 'json'}
    return ext_map.get(file_path.suffix.lower())


def _split_python(content: str) ->list[str]:
    """Splits Python code into chunks based on top-level AST nodes."""
    try:
        tree = ast.parse(content)
        if not tree.body:
            return [content] if content.strip() else []
        chunks_raw = [astor.to_source(node) for node in tree.body]
        return [c for c in chunks_raw if c.strip()]
    except (SyntaxError, ValueError) as e:
        log_warning(
            f'AST parsing failed: {e}. Falling back to paragraph split.')
        return _split_default(content)


def _split_shell(content: str) ->list[str]:
    """Splits shell script into chunks based on functions and control blocks."""
    chunks_raw = re.split(
        '(?m)(^\\s*(?:function\\s|if\\s|for\\s|while\\s|case\\s|until\\s|select\\s) | ^\\s*$)'
        , content)
    recombined = []
    for i in range(1, len(chunks_raw), 2):
        recombined.append(chunks_raw[i] + chunks_raw[i + 1])
    if chunks_raw[0].strip():
        recombined.insert(0, chunks_raw[0])
    return [c for c in recombined if c.strip()] or ([content] if content.
        strip() else [])


def _split_default(content: str) ->list[str]:
    """Splits content into chunks based on paragraph-like breaks (two or more newlines)."""
    chunks_raw = re.split('\\n\\s*\\n', content)
    return [c.strip() for c in chunks_raw if c.strip()]


SPLITTING_STRATEGIES = {'python': _split_python, 'bash': _split_shell, 'sh':
    _split_shell, 'zsh': _split_shell}


def split_file_into_chunks(input_path: Path, lang_hint: (str | None)) ->list[
    Path]:
    """Divides the input tome into content-aware fragments."""
    log_info(f"Dividing '{input_path.name}' into fragments...")
    try:
        content = input_path.read_text(encoding='utf-8')
    except OSError as e:
        log_error(f"Could not read input tome '{input_path.name}': {e}")
        return []
    if not content.strip():
        log_warning(f"Input tome '{input_path.name}' is empty.")
        return []
    splitter_func = SPLITTING_STRATEGIES.get(lang_hint, _split_default)
    chunks_raw = splitter_func(content)
    final_chunks_content = []
    max_tokens = ctx.args.max_chunk_tokens
    for chunk_content in chunks_raw:
        if max_tokens and len(chunk_content) // CHARS_PER_TOKEN > max_tokens:
            log_debug(f'Fragment too large, subdividing by line.')
            lines = chunk_content.splitlines(keepends=True)
            sub_chunk_lines = []
            sub_chunk_tokens = 0
            for line in lines:
                line_tokens = len(line) // CHARS_PER_TOKEN
                if (sub_chunk_tokens + line_tokens > max_tokens and
                    sub_chunk_lines):
                    final_chunks_content.append(''.join(sub_chunk_lines))
                    sub_chunk_lines = [line]
                    sub_chunk_tokens = line_tokens
                else:
                    sub_chunk_lines.append(line)
                    sub_chunk_tokens += line_tokens
            if sub_chunk_lines:
                final_chunks_content.append(''.join(sub_chunk_lines))
        else:
            final_chunks_content.append(chunk_content)
    chunk_files = []
    for i, chunk_text in enumerate(final_chunks_content):
        chunk_path = ctx.temp_dir / f'{CHUNK_PREFIX}{i:04d}'
        try:
            chunk_path.write_text(chunk_text, encoding='utf-8')
            chunk_files.append(chunk_path)
        except OSError as e:
            log_error(f"Could not write fragment file '{chunk_path.name}': {e}"
                )
    log_success(f'Tome successfully divided into {len(chunk_files)} fragments.'
        )
    return chunk_files


def extract_code_block(text: str) ->str:
    """Extracts the first code block from Gemini's response."""
    if ctx.args.raw:
        return text.strip()
    match = re.search('```(?:\\S*\\n)?(.*?)\\n?```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    log_debug('No code fences found in response. Using entire text.')
    return text.strip()


def run_pre_check(content: str, lang_hint: str) ->bool:
    """Runs language-specific linting. Returns True if check passes or is skipped."""
    log_info(f"Running pre-check for {lang_hint or 'unknown'}...")
    if lang_hint == 'python' and shutil.which('ruff'):
        cmd = ['ruff', 'check', '--quiet', '--stdin-filename', 'stdin.py', '-']
        proc = subprocess.run(cmd, input=content.encode('utf-8'),
            capture_output=True, check=False)
        if proc.returncode != 0:
            log_warning(
                f"Ruff check found issues:\n{proc.stdout.decode('utf-8')}")
            return False
        log_info('Ruff pre-check passed.')
        return True
    elif lang_hint in ['bash', 'sh', 'zsh'] and shutil.which('shellcheck'):
        cmd = ['shellcheck', '-s', lang_hint, '-']
        proc = subprocess.run(cmd, input=content.encode('utf-8'),
            capture_output=True, check=False)
        if proc.returncode != 0:
            log_warning(
                f"ShellCheck found issues:\n{proc.stdout.decode('utf-8')}")
            return False
        log_info('Shell pre-check passed.')
        return True
    log_debug(f"No pre-check available for language '{lang_hint}'. Skipping.")
    return True


def process_chunk_with_api(original_chunk_path: Path, output_chunk_path:
    Path, file_info: str) ->(tuple[str, str, Path, int, int] | None):
    """Channels a single fragment through the Gemini API for enhancement."""
    chunk_name = original_chunk_path.name
    log_debug(f'Channeling fragment: {chunk_name}')
    try:
        original_content = original_chunk_path.read_text(encoding='utf-8')
    except OSError as e:
        log_error(f"Could not read fragment '{chunk_name}': {e}")
        return None
    if not original_content.strip():
        output_chunk_path.write_text('', encoding='utf-8')
        return '', original_content, original_chunk_path, 0, 0
    current_lang_hint = ctx.args.lang or get_file_type_from_extension(Path(
        file_info))
    if ctx.args.pre_check and run_pre_check(original_content, current_lang_hint
        ):
        log_info(f"Pre-check passed for '{chunk_name}'. Skipping API call.")
        output_chunk_path.write_text(original_content, encoding='utf-8')
        return original_content, original_content, original_chunk_path, 0, 0
    prompt_text = ctx.args.custom_prompt_template.replace('{original_code}',
        original_content).replace('{lang_hint}', current_lang_hint or 'text')
    cache_dir = ctx.temp_dir.parent / 'pyrmethus_cache'
    cache_dir.mkdir(exist_ok=True)
    cache_key_str = prompt_text + original_content + ctx.args.model + str(ctx
        .args.temperature)
    cache_key = hashlib.sha256(cache_key_str.encode('utf-8')).hexdigest()
    cache_file = cache_dir / cache_key
    if not ctx.args.force and cache_file.exists():
        log_debug(f'Found cached response for chunk {chunk_name}')
        final_content = cache_file.read_text(encoding='utf-8')
        output_chunk_path.write_text(final_content, encoding='utf-8')
        output_tokens = len(final_content) // CHARS_PER_TOKEN
        return (final_content, original_content, original_chunk_path, 0,
            output_tokens)
    json_payload = {'contents': [{'parts': [{'text': prompt_text}]}],
        'generationConfig': {'temperature': ctx.args.temperature,
        'maxOutputTokens': 8192}}
    input_tokens = len(prompt_text) // CHARS_PER_TOKEN
    api_url = (
        f'{API_BASE_URL}/{ctx.args.model}:generateContent?key={ctx.api_key}')
    for attempt in range(1, ctx.args.retries + 1):
        try:
            response = requests.post(url=api_url, headers={'Content-Type':
                'application/json'}, json=json_payload, timeout=(ctx.args.
                connect_timeout, ctx.args.read_timeout))
            response.raise_for_status()
            response_data = response.json()
            text_content = response_data['candidates'][0]['content']['parts'][0
                ]['text']
            final_content = extract_code_block(text_content)
            output_tokens = len(final_content) // CHARS_PER_TOKEN
            cache_file.write_text(final_content, encoding='utf-8')
            if ctx.args.pre_check and final_content.strip(
                ) != original_content.strip():
                log_info(f"Running post-API check for '{chunk_name}'...")
                if not run_pre_check(final_content, current_lang_hint):
                    log_warning(
                        f"Post-API check failed for '{chunk_name}'. Reverting to original."
                        )
                    final_content = original_content
                    output_tokens = len(final_content) // CHARS_PER_TOKEN
            output_chunk_path.write_text(final_content, encoding='utf-8')
            return (final_content, original_content, original_chunk_path,
                input_tokens, output_tokens)
        except requests.exceptions.Timeout:
            log_warning(
                f"Timeout for '{chunk_name}'. Retrying in {ctx.args.retry_delay}s..."
                )
            time.sleep(ctx.args.retry_delay)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                log_warning(
                    f'Rate limit reached. Waiting {API_RATE_LIMIT_WAIT}s...')
                time.sleep(API_RATE_LIMIT_WAIT)
            elif e.response.status_code >= 500:
                log_warning(
                    f'API server error ({e.response.status_code}). Retrying...'
                    )
                time.sleep(ctx.args.retry_delay)
            else:
                log_error(
                    f"API Error {e.response.status_code} for '{chunk_name}'. Not retryable. Details: {e.response.text[:200]}"
                    )
                return None
        except (ValueError, json.JSONDecodeError, IndexError, KeyError) as e:
            log_error(
                f"Error parsing API response for '{chunk_name}': {e}. Retrying..."
                )
            time.sleep(ctx.args.retry_delay)
        except Exception as e:
            log_error(f"Unexpected error for '{chunk_name}': {e}. Retrying...")
            time.sleep(ctx.args.retry_delay)
    log_error(
        f"Failed to enhance fragment '{chunk_name}' after {ctx.args.retries} attempts. Using original."
        )
    output_chunk_path.write_text(original_content, encoding='utf-8')
    return (original_content, original_content, original_chunk_path,
        input_tokens, len(original_content) // CHARS_PER_TOKEN)


def display_diff(original_content: str, new_content: str,
    file_path_for_display: str):
    """Displays a colorized diff between original and new content."""
    diff = difflib.unified_diff(original_content.splitlines(keepends=True),
        new_content.splitlines(keepends=True), fromfile=
        f'a/{file_path_for_display}', tofile=f'b/{file_path_for_display}')
    diff_lines = list(diff)
    if not diff_lines:
        return
    ctx.has_changes = True
    for line in diff_lines:
        line = line.rstrip()
        if line.startswith('+++') or line.startswith('---'):
            print(f'{Fore.LIGHTBLUE_EX}{Style.BRIGHT}{line}{Style.RESET_ALL}')
        elif line.startswith('+'):
            print(f'{Fore.LIGHTGREEN_EX}{line}{Style.RESET_ALL}')
        elif line.startswith('-'):
            print(f'{Fore.LIGHTRED_EX}{line}{Style.RESET_ALL}')
        elif line.startswith('@@'):
            print(f'{Fore.LIGHTMAGENTA_EX}{line}{Style.RESET_ALL}')
        else:
            print(line)


def reassemble_output(all_original_chunks: list[Path], file_path: Path,
    to_stdout: bool) ->str:
    """Weaves processed fragments into the final enhanced tome."""
    log_info(f"Weaving enhanced fragments for '{file_path.name}'...")
    final_content_parts = []
    accept_all = False
    for original_chunk_file in all_original_chunks:
        chunk_basename = original_chunk_file.name
        chunk_num = chunk_basename.split('_')[-1]
        output_chunk_file = ctx.temp_dir / f'{OUTPUT_CHUNK_PREFIX}{chunk_num}'
        try:
            original_content = original_chunk_file.read_text(encoding='utf-8')
            new_content = output_chunk_file.read_text(encoding='utf-8'
                ) if output_chunk_file.exists() else original_content
        except OSError as e:
            log_error(
                f'Error reading fragments for {chunk_basename}: {e}. Using original.'
                )
            final_content_parts.append(original_content)
            continue
        if ctx.args.interactive and not accept_all and original_content.strip(
            ) != new_content.strip() and not ctx.args.dry_run:
            print(
                f"""
{Style.BRIGHT}{Fore.LIGHTYELLOW_EX}--- Reviewing fragment: {chunk_basename} for {file_path.name} ---{Style.RESET_ALL}"""
                )
            display_diff(original_content, new_content, chunk_basename)
            while True:
                try:
                    resp = input(
                        f'{Fore.LIGHTGREEN_EX}Accept? {Style.BRIGHT}(y/n/e[dit]/a[ccept all]): {Style.RESET_ALL}'
                        ).lower().strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    resp = 'n'
                if resp == 'y':
                    final_content_parts.append(new_content)
                    break
                elif resp == 'n':
                    final_content_parts.append(original_content)
                    break
                elif resp == 'e':
                    editor = os.environ.get('EDITOR', 'nano')
                    temp_edit_file = ctx.temp_dir / f'edit_{chunk_basename}'
                    temp_edit_file.write_text(new_content, encoding='utf-8')
                    subprocess.run([editor, str(temp_edit_file)], check=False)
                    final_content_parts.append(temp_edit_file.read_text(
                        encoding='utf-8'))
                    break
                elif resp == 'a':
                    accept_all = True
                    final_content_parts.append(new_content)
                    break
        else:
            final_content_parts.append(new_content)
    final_output = '\n\n'.join(final_content_parts)
    if final_output and not final_output.endswith('\n'):
        final_output += '\n'
    return final_output


def display_final_summary():
    """Displays a summary of the ritual's cost and completion."""
    print(f"\n{Fore.LIGHTBLUE_EX}{Style.BRIGHT}{'=' * 50}{Style.RESET_ALL}")
    if ctx.args.dry_run:
        log_info(
            f'{Fore.LIGHTMAGENTA_EX}Dry Run Complete. No files were modified.{Style.RESET_ALL}'
            )
    else:
        log_success('Ritual Complete. Final Summary:')
    log_info(f'  Files Processed: {len(ctx.files_to_process)}')
    model_costs = COST_DATA.get(ctx.args.model, COST_DATA['default'])
    input_cost = ctx.total_input_tokens / 1000000 * model_costs['input']
    output_cost = ctx.total_output_tokens / 1000000 * model_costs['output']
    total_cost = input_cost + output_cost
    log_info(f'  Estimated Input Tokens:  ~{ctx.total_input_tokens:,}')
    log_info(f'  Estimated Output Tokens: ~{ctx.total_output_tokens:,}')
    log_success(f'  Estimated Total Cost:    ${total_cost:.4f}')
    print(f"{Fore.LIGHTBLUE_EX}{Style.BRIGHT}{'=' * 50}{Style.RESET_ALL}")


def get_files_from_input_dir() ->list[tuple[Path, Path]]:
    """Collects file paths from an input directory, respecting .gitignore."""
    input_dir, output_dir = ctx.args.input_dir, ctx.args.output_dir
    log_info(f"Scanning directory '{input_dir}' for files to process...")
    gitignore_path = input_dir / '.gitignore'
    spec = None
    if gitignore_path.is_file():
        log_info(f'Applying ignore patterns from {gitignore_path}')
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            spec = pathspec.PathSpec.from_lines('gitwildmatch', f)
    default_skip_ext = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.zip',
        '.tar', '.gz', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.sqlite3',
        '.db', '.lock', '.log', '.tmp', '.bak', '.pyc', '.o', '.a', '.so',
        '.dll'}
    all_skip_ext = set(ext.lower() for ext in ctx.args.skip_ext
        ) | default_skip_ext
    files_to_process_list = []
    for root_str, _, files in os.walk(input_dir):
        root = Path(root_str)
        if spec and spec.match_file(str(root.relative_to(input_dir))):
            log_debug(f'Skipping ignored directory: {root.name}')
            continue
        for file_name in files:
            file_path = root / file_name
            rel_path = file_path.relative_to(input_dir)
            if spec and spec.match_file(str(rel_path)):
                log_debug(f'Skipping ignored file: {file_path.name}')
                continue
            if file_path.suffix.lower() in [BACKUP_SUFFIX, CHECKPOINT_SUFFIX
                ] or file_path.suffix.lower() in all_skip_ext:
                log_debug(f'Skipping backup/excluded file: {file_path.name}')
                continue
            if file_path.stat().st_size == 0:
                log_warning(
                    f"Input file '{file_path.name}' is empty. Skipping.")
                continue
            output_file_path = (output_dir / rel_path if output_dir else
                file_path)
            if (not ctx.args.force and not ctx.args.in_place and
                output_file_path.exists()):
                log_warning(
                    f"Output '{output_file_path.name}' exists. Skipping. Use --force."
                    )
                continue
            files_to_process_list.append((file_path, output_file_path))
    if not files_to_process_list:
        log_warning(f"No processable files found in '{input_dir}'.")
    return files_to_process_list


def process_single_file_workflow(original_file_path: Path, output_file_path:
    Path):
    """Manages the workflow for processing a single file."""
    log_info(
        f"""
{Style.BRIGHT}{Fore.LIGHTMAGENTA_EX}--- Processing Tome: {original_file_path.name} ---{Style.RESET_ALL}"""
        )
    try:
        original_content = original_file_path.read_text(encoding='utf-8'
            ) if str(original_file_path) != 'stdin.tmp' else (ctx.temp_dir /
            'stdin.tmp').read_text(encoding='utf-8')
    except OSError as e:
        log_error(f'Cannot read original file {original_file_path}: {e}')
        return
    is_stdout = str(output_file_path) == '-'
    if not is_stdout and not ctx.args.dry_run:
        if not backup_file(output_file_path):
            return
    file_lang_hint = ctx.args.lang or get_file_type_from_extension(
        original_file_path)
    if not file_lang_hint:
        log_warning(
            f"Could not infer language for '{original_file_path.name}'.")
    all_chunks_raw_paths = split_file_into_chunks(original_file_path,
        file_lang_hint)
    if not all_chunks_raw_paths:
        if original_content.strip():
            log_error(
                f"Division of text for '{original_file_path.name}' failed. Skipping file."
                )
        else:
            final_content = ''
            if not ctx.args.dry_run:
                if is_stdout:
                    sys.stdout.write(final_content)
                else:
                    output_file_path.write_text(final_content, encoding='utf-8'
                        )
        return
    log_info(
        f"Total fragments for '{original_file_path.name}': {len(all_chunks_raw_paths)}."
        )
    with ThreadPoolExecutor(max_workers=ctx.args.jobs) as executor:
        future_to_chunk_info = {executor.submit(process_chunk_with_api,
            orig_c, ctx.temp_dir /
            f"{OUTPUT_CHUNK_PREFIX}{orig_c.name.split('_')[-1]}", str(
            original_file_path)): orig_c for orig_c in all_chunks_raw_paths}
        progress_bar = tqdm.tqdm(as_completed(future_to_chunk_info), total=
            len(all_chunks_raw_paths), desc=
            f'Enhancing {original_file_path.name}', unit='frag', file=sys.
            stderr, dynamic_ncols=True, colour='cyan')
        for future in progress_bar:
            try:
                result = future.result()
                if result:
                    _, _, _, in_tokens, out_tokens = result
                    ctx.total_input_tokens += in_tokens
                    ctx.total_output_tokens += out_tokens
            except Exception as exc:
                chunk_path = future_to_chunk_info[future]
                log_error(f"Fragment '{chunk_path.name}' failed: {exc}")
    sys.stderr.write('\n')
    final_content = reassemble_output(all_chunks_raw_paths,
        original_file_path, is_stdout)
    if ctx.args.dry_run:
        log_info(f'Dry run for {original_file_path.name}:')
        display_diff(original_content, final_content, str(original_file_path))
    elif is_stdout:
        sys.stdout.write(final_content)
        sys.stdout.flush()
    else:
        try:
            output_file_path.parent.mkdir(parents=True, exist_ok=True)
            output_file_path.write_text(final_content, encoding='utf-8')
            log_success(
                f"Tome woven successfully. Saved to '{output_file_path}'.")
        except OSError as e:
            log_error(
                f"Failed to write final tome to '{output_file_path}': {e}")


def list_available_models():
    """Lists available Gemini models from the API."""
    log_info('Fetching available models...')
    get_api_key()
    if not ctx.api_key:
        log_error('API key is required to list models.')
        return
    try:
        response = requests.get(
            f'https://generativelanguage.googleapis.com/v1beta/models?key={ctx.api_key}'
            )
        response.raise_for_status()
        models = response.json().get('models', [])
        print(
            f'{Fore.LIGHTCYAN_EX}{Style.BRIGHT}--- Available Gemini Models ---{Style.RESET_ALL}'
            )
        for model in sorted(models, key=lambda m: m['name']):
            model_name = model['name'].replace('models/', '')
            cost_info = COST_DATA.get(model_name)
            cost_str = (
                f" (Input: ${cost_info['input']}/M, Output: ${cost_info['output']}/M)"
                 if cost_info else '')
            print(
                f'  - {Fore.LIGHTGREEN_EX}{model_name}{Style.RESET_ALL}{cost_str}'
                )
    except requests.exceptions.RequestException as e:
        log_error(f'Failed to fetch models: {e}')
    except (json.JSONDecodeError, KeyError):
        log_error(f'Failed to parse model list from API response.')


def main():
    """Orchestrates the grand ritual of text enhancement."""
    global ctx
    parser = argparse.ArgumentParser(description=
        f"{Fore.LIGHTCYAN_EX}{Style.BRIGHT}Pyrmethus's Grand Gemini File Review Spell{Style.RESET_ALL}"
        , formatter_class=argparse.RawTextHelpFormatter, epilog=
        f"""
{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}Configuration Priority:{Style.RESET_ALL}
  Command-line args > .env file > Environment variables > Config File ({CONFIG_FILE}) > Defaults.

{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}Examples:{Style.RESET_ALL}
  # Review a single file and output to another
  {SCRIPT_NAME} -i script.py -o enhanced.py
  # Review and modify a file in-place (creates .bak)
  {SCRIPT_NAME} --in-place script.py --interactive
  # Read from stdin, specify language, write to stdout
  cat script.sh | {SCRIPT_NAME} -l bash --pre-check
  # Process a whole directory, modifying files in-place
  {SCRIPT_NAME} --input-dir ./project --in-place -j 8
  # Show a diff of potential changes without writing files
  {SCRIPT_NAME} --input-dir ./project --diff-only
  # Use a custom prompt from a file
  {SCRIPT_NAME} -i doc.md --prompt-file my_prompt.txt
  # List available models and their estimated costs
  {SCRIPT_NAME} --list-models

{Fore.LIGHTYELLOW_EX}{Style.BRIGHT}Dependencies:{Style.RESET_ALL}
  pip install colorama requests python-dotenv astor pathspec tqdm
  Optional: ruff (for Python), shellcheck (for Shell)
"""
        )
    is_processing_run = not any(x in sys.argv for x in ['--list-models',
        '-h', '--help'])
    parser.add_argument('--list-models', action='store_true', help=
        'List available Gemini models and exit.')
    input_group = parser.add_mutually_exclusive_group(required=
        is_processing_run)
    input_group.add_argument('-i', '--input-file', type=Path, help=
        "Input file path or '-' for stdin.")
    input_group.add_argument('--input-dir', type=Path, help=
        'Input directory to process files within.')
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument('-o', '--output-file', type=Path, help=
        'Output file path. Default: stdout for single file.')
    output_group.add_argument('--output-dir', type=Path, help=
        'Output directory. Required if not using --in-place.')
    output_group.add_argument('--in-place', action='store_true', help=
        'Modify files in-place (creates backups).')
    parser.add_argument('--stdout', action='store_true', help=
        'Force all output to stdout, overriding file-based output.')
    parser.add_argument('-k', '--key', help='Gemini API Key.')
    parser.add_argument('-m', '--model', default=DEFAULT_MODEL, help=
        f'Gemini model (default: {DEFAULT_MODEL}).')
    parser.add_argument('-t', '--temperature', type=float, default=
        DEFAULT_TEMPERATURE, help=
        f'API temperature (default: {DEFAULT_TEMPERATURE}).')
    parser.add_argument('-l', '--lang', help=
        'Language hint (e.g., python, bash). Overrides auto-detection.')
    prompt_group = parser.add_mutually_exclusive_group()
    prompt_group.add_argument('--custom-prompt-template', help=
        'Custom prompt string. Use {original_code} and {lang_hint}.')
    prompt_group.add_argument('--prompt-file', type=Path, help=
        'Path to a file containing the prompt template.')
    parser.add_argument('-j', '--jobs', type=int, default=DEFAULT_MAX_JOBS,
        help=f'Max parallel API requests (default: {DEFAULT_MAX_JOBS}).')
    parser.add_argument('-f', '--force', action='store_true', help=
        'Force overwrite of existing output files.')
    parser.add_argument('--raw', action='store_true', help=
        'Output raw API response, bypassing code extraction.')
    parser.add_argument('--log-level', choices=log_level_map.keys(),
        default='INFO', help='Set logging level.')
    parser.add_argument('-v', '--verbose', action='store_true', help=
        'Enable verbose logging (alias for --log-level DEBUG).')
    parser.add_argument('--interactive', action='store_true', help=
        'Interactively review changes for each fragment.')
    parser.add_argument('--pre-check', action='store_true', help=
        'Run pre-API checks (e.g., ruff, shellcheck). Skips API call if original code is valid.'
        )
    parser.add_argument('--max-chunk-tokens', type=int, help=
        'Max estimated tokens per chunk for splitting.')
    parser.add_argument('--connect-timeout', type=int, default=
        DEFAULT_CONNECT_TIMEOUT, help=
        f'Connection timeout (default: {DEFAULT_CONNECT_TIMEOUT}s).')
    parser.add_argument('--read-timeout', type=int, default=
        DEFAULT_READ_TIMEOUT, help=
        f'Read timeout (default: {DEFAULT_READ_TIMEOUT}s).')
    parser.add_argument('--retries', type=int, default=MAX_RETRIES, help=
        f'API retry attempts (default: {MAX_RETRIES}).')
    parser.add_argument('--retry-delay', type=int, default=
        RETRY_DELAY_SECONDS, help=
        f'Delay between retries (default: {RETRY_DELAY_SECONDS}s).')
    parser.add_argument('--skip-ext', nargs='*', default=[], help=
        'File extensions to skip (e.g., .log .txt).')
    parser.add_argument('--dry-run', action='store_true', help=
        'Show changes but do not write files. Use with --diff-only to get a patch-like output.'
        )
    parser.add_argument('--diff-only', action='store_true', help=
        'Show a diff of changes and exit with status 0 (no changes) or 1 (changes). Implies --dry-run.'
        )
    parser.add_argument('--temp-dir', type=Path, help=
        'Custom directory for temporary files.')
    args = parser.parse_args()
    log_level = logging.DEBUG if args.verbose else log_level_map[args.log_level
        ]
    setup_logger(log_level)
    ctx = ScriptContext(args=args, config=load_config())
    if args.list_models:
        list_available_models()
        sys.exit(0)
    if args.diff_only:
        args.dry_run = True
    if args.prompt_file:
        try:
            args.custom_prompt_template = args.prompt_file.read_text(encoding
                ='utf-8')
        except OSError as e:
            log_error(f"Could not read prompt file '{args.prompt_file}': {e}")
            sys.exit(1)
    elif not args.custom_prompt_template:
        args.custom_prompt_template = """You are an expert software engineer. Review and provide syntax corrections for the following code chunk from '{file_info}'.
**CRITICAL INSTRUCTIONS:**
1.  **If the code is correct, return it unchanged.**
2.  **Correct ONLY syntax errors.** Do not make stylistic changes, rename anything, or alter logic.
3.  **Respond ONLY with the complete, corrected code chunk inside a code block.**

Original Code Chunk:
```{lang_hint}
{original_code}
```"""
    if args.input_dir and not (args.output_dir or args.in_place):
        log_error(
            '--output-dir or --in-place is required when using --input-dir.')
        sys.exit(1)
    if args.input_dir and args.output_dir and args.output_dir.resolve(
        ) == args.input_dir.resolve():
        log_error('Input and output directories cannot be the same.')
        sys.exit(1)
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    check_dependencies()
    get_api_key()
    if not ctx.api_key:
        log_error('A valid Gemini API key is required to proceed.')
        sys.exit(1)
    if not create_temp_dir():
        sys.exit(1)
    if args.input_file:
        is_stdin = str(args.input_file) == '-'
        if is_stdin:
            if sys.stdin.isatty():
                log_error('Cannot read from TTY. Pipe input or use -i <file>.')
                sys.exit(1)
            stdin_content = sys.stdin.read()
            stdin_tmp_path = ctx.temp_dir / 'stdin.tmp'
            stdin_tmp_path.write_text(stdin_content, encoding='utf-8')
            input_path = stdin_tmp_path
        else:
            if not args.input_file.is_file():
                log_error(f"Input file '{args.input_file}' not found.")
                sys.exit(1)
            input_path = args.input_file
        output_path = args.output_file or (Path('-') if not args.in_place else
            input_path)
        if args.stdout:
            output_path = Path('-')
        ctx.files_to_process.append((input_path, output_path))
    elif args.input_dir:
        ctx.files_to_process = get_files_from_input_dir()
    if not ctx.files_to_process:
        log_warning('No files to process.')
        sys.exit(0)
    files_processed_count = 0
    try:
        for original_path, output_path in ctx.files_to_process:
            process_single_file_workflow(original_path, output_path)
            files_processed_count += 1
    finally:
        cleanup_temp_dir()
        if files_processed_count > 0:
            display_final_summary()
        if args.diff_only:
            log_info(f'Exiting with status {1 if ctx.has_changes else 0}.')
            sys.exit(1 if ctx.has_changes else 0)


if __name__ == '__main__':
    main()
