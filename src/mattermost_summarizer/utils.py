"""Utility functions for mattermost-summarizer."""

import re
from urllib.parse import urlparse

from mattermost_summarizer.exceptions import PermalinkError

__all__ = ["PermalinkError", "parse_permalink"]


def parse_permalink(url: str) -> str:
    """Extract the post ID from a Mattermost permalink URL.

    Mattermost permalinks follow the format:
        https://{server}/{team}/pl/{post_id}

    Args:
        url: A Mattermost permalink URL

    Returns:
        The post ID extracted from the URL

    Raises:
        PermalinkError: If the URL is not a valid Mattermost permalink

    Examples:
        >>> parse_permalink("https://chat.canonical.com/canonical/pl/abc123xyz")
        'abc123xyz'
    """
    if not url:
        raise PermalinkError("Empty URL provided")

    # Parse the URL to validate its structure
    parsed = urlparse(url)

    if not parsed.scheme or not parsed.netloc:
        raise PermalinkError(f"Invalid URL format: {url}")

    # Mattermost permalinks have /pl/{post_id} in the path
    # The post_id is a alphanumeric string
    match = re.search(r"/pl/([a-z0-9]+)", url, re.IGNORECASE)

    if not match:
        raise PermalinkError(
            f"Not a valid Mattermost permalink: {url}\n"
            "Expected format: https://{{server}}/{{team}}/pl/{{post_id}}"
        )

    return match.group(1)
