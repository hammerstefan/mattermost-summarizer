"""Tests for URL parsing utility."""

import pytest

from mattermost_summarizer.utils import PermalinkError, parse_permalink


class TestParsePermalink:
    def test_valid_permalink_with_team(self) -> None:
        url = "https://chat.canonical.com/canonical/pl/injbzc9x1igkmk6icenahhj7ho"
        result = parse_permalink(url)
        assert result == "injbzc9x1igkmk6icenahhj7ho"

    def test_valid_permalink_case_insensitive_pl(self) -> None:
        url = "https://example.com/team/PL/ABC123"
        result = parse_permalink(url)
        assert result == "ABC123"

    def test_valid_permalink_uppercase_post_id(self) -> None:
        url = "https://example.com/team/pl/ABC123XYZ"
        result = parse_permalink(url)
        assert result == "ABC123XYZ"

    def test_empty_url_raises_error(self) -> None:
        with pytest.raises(PermalinkError, match="Empty URL"):
            parse_permalink("")

    def test_invalid_format_raises_error(self) -> None:
        url = "https://chat.canonical.com/canonical/channels/general/123"
        with pytest.raises(PermalinkError, match="Not a valid Mattermost permalink"):
            parse_permalink(url)

    def test_url_without_pl_path_raises_error(self) -> None:
        url = "https://example.com/team/threads/abc123"
        with pytest.raises(PermalinkError, match="Not a valid Mattermost permalink"):
            parse_permalink(url)

    def test_url_without_path_raises_error(self) -> None:
        url = "https://chat.canonical.com"
        with pytest.raises(PermalinkError, match="Not a valid Mattermost permalink"):
            parse_permalink(url)

    def test_invalid_url_format_raises_error(self) -> None:
        url = "not-a-url-at-all"
        with pytest.raises(PermalinkError, match="Invalid URL format"):
            parse_permalink(url)
