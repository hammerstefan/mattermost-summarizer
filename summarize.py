#!/usr/bin/env python3
"""CLI script to summarize a Mattermost thread."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from mattermost_summarizer.config import MattermostSummarizerConfig
from mattermost_summarizer.summarizer import MattermostSummarizer


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a Mattermost thread")
    parser.add_argument(
        "url",
        help="Mattermost thread URL (e.g., https://chat.canonical.com/canonical/pl/post_id)",
    )
    parser.add_argument(
        "--config",
        "-c",
        default="mattermost-summarizer.toml",
        help="Path to TOML config file (default: mattermost-summarizer.toml)",
    )
    parser.add_argument(
        "--output",
        "-o",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}", file=sys.stderr)
        return 1

    try:
        config = MattermostSummarizerConfig.from_config(config_path)
    except Exception as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        return 1

    try:
        summarizer = MattermostSummarizer(config)
        result = summarizer.summarize(args.url)
    except Exception as e:
        print(f"Error summarizing thread: {e}", file=sys.stderr)
        return 1

    if args.output == "json":
        print(result.model_dump_json(indent=2))
    else:
        print(str(result))

    return 0


if __name__ == "__main__":
    sys.exit(main())
