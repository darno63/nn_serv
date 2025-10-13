#!/usr/bin/env python3
"""Download a Hugging Face model snapshot into a target directory."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from huggingface_hub import snapshot_download
except ImportError as exc:  # pragma: no cover - dependency hint
    raise SystemExit(
        "huggingface-hub is required. Install with `pip install huggingface-hub`."
    ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a Hugging Face repository (model) into persistent storage",
    )
    parser.add_argument("repo_id", help="Hugging Face repo id, e.g. Wan-AI/Wan2.2-T2V-A14B")
    parser.add_argument(
        "destination",
        help="Directory where the snapshot should be stored (e.g. /lambda/nfs/fs-name/Wan-AI)",
    )
    parser.add_argument("--revision", help="Optional branch/tag/commit to download")
    parser.add_argument(
        "--token",
        help="Hugging Face access token (defaults to HF_TOKEN environment variable)",
    )
    parser.add_argument(
        "--ignore-pattern",
        action="append",
        dest="ignore_patterns",
        help="Glob pattern(s) to skip during download (repeatable)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    token = args.token or os.getenv("HF_TOKEN")
    dest = Path(args.destination).expanduser().resolve()
    dest.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {args.repo_id} to {dest}...")
    snapshot_download(
        repo_id=args.repo_id,
        revision=args.revision,
        local_dir=str(dest),
        local_dir_use_symlinks=False,
        resume_download=True,
        token=token,
        allow_patterns=None,
        ignore_patterns=args.ignore_patterns or None,
    )
    print("Download complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
