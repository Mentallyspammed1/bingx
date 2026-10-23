#!/usr/bin/env python3
"""AI code review via NVIDIA NIM (OpenAI-compatible API).

Reads a unified diff (file path arg or stdin), sends it to NIM chat
completions, and prints a Markdown review to stdout.
Review-only: never edits code, never pushes.

Env:
  NVIDIA_API_KEY    required (GitHub secret) - if unset, prints a skip notice
  NVIDIA_NIM_MODEL  optional, default meta/llama-3.3-70b-instruct
  NIM_BASE_URL      optional, default https://integrate.api.nvidia.com/v1
"""
import json
import os
import sys
import urllib.request

MAX_DIFF_CHARS = 120_000

SYSTEM = (
    "You are a strict, practical code reviewer. Review the unified diff for "
    "bugs, security issues, error handling, and performance problems. "
    "Be specific: cite file and change. Skip style nitpicks unless they hide a bug. "
    "Output Markdown with sections: ## Summary, ## Issues (numbered, severity-tagged), "
    "## Suggestions. If the diff is clean, say so plainly."
)


def main() -> int:
    api_key = os.environ.get("NVIDIA_API_KEY", "").strip()
    if not api_key:
        print("## NVIDIA NIM review skipped\n\n`NVIDIA_API_KEY` secret is not set in this repository.")
        return 0

    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8", errors="replace") as fh:
            diff = fh.read()
    else:
        diff = sys.stdin.read()

    diff = diff.strip()
    if not diff:
        print("## NVIDIA NIM review\n\nNo diff to review.")
        return 0
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + "\n\n[diff truncated]\n"

    model = os.environ.get("NVIDIA_NIM_MODEL", "meta/llama-3.3-70b-instruct")
    base = os.environ.get("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1").rstrip("/")
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Review this diff:\n\n```diff\n{diff}\n```"},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.load(resp)
    text = data["choices"][0]["message"]["content"].strip()
    print(f"## NVIDIA NIM review ({model})\n\n{text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
