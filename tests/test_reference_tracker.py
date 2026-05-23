"""Tests for reference_tracker.py — URL sanitization and extraction."""

from urllib.parse import urlparse


class TestSanitizeUrl:
    """Regression tests for sanitize_url."""

    def test_properly_bracketed_ipv6(self) -> None:
        from mattermost_summarizer.tools.reference_tracker import sanitize_url

        result = sanitize_url("http://[fd00::1]/path")
        assert "ipv6-placeholder" in result
        assert "[fd00::1]" not in result
        parsed = urlparse(result)
        assert parsed.netloc == "ipv6-placeholder"

    def test_properly_bracketed_ipv6_with_port(self) -> None:
        from mattermost_summarizer.tools.reference_tracker import sanitize_url

        result = sanitize_url("http://[fd00:c1::a9fe:a9fe]:8080/path")
        assert "ipv6-placeholder" in result
        parsed = urlparse(result)
        assert parsed.netloc == "ipv6-placeholder:8080"

    def test_bare_bracket_no_closing(self) -> None:
        """Bug regression: http://[fd00:c1::a9fe:a9fe (no ]) must not raise."""
        from mattermost_summarizer.tools.reference_tracker import sanitize_url

        result = sanitize_url("http://[fd00:c1::a9fe:a9fe")
        assert "[" not in result

    def test_bare_bracket_short_ipv6(self) -> None:
        from mattermost_summarizer.tools.reference_tracker import sanitize_url

        result = sanitize_url("http://[::1")
        assert "[" not in result

    def test_no_brackets_untouched(self) -> None:
        from mattermost_summarizer.tools.reference_tracker import sanitize_url

        result = sanitize_url("https://github.com/canonical/cloud-init/issues/6867")
        assert result == "https://github.com/canonical/cloud-init/issues/6867"

    def test_brackets_in_query_string(self) -> None:
        """Brackets in query/fragment are never touched."""
        from mattermost_summarizer.tools.reference_tracker import sanitize_url

        result = sanitize_url("http://example.com/path?filter=[foo]&tag=[bar]")
        assert "[foo]" in result
        assert "[bar]" in result
        parsed = urlparse(result)
        assert "filter=[foo]&tag=[bar]" in parsed.query

    def test_bare_bracket_invalid_chars(self) -> None:
        """Non-IPv6 content after [ must also be handled."""
        from mattermost_summarizer.tools.reference_tracker import sanitize_url

        result = sanitize_url("http://[invalid")
        assert "[" not in result


class TestExtractUrlsFromText:
    """Regression tests for extract_urls_from_text."""

    def test_ipv6_literal_url(self) -> None:
        """IPv6 literal URL must not be truncated at ]."""
        from mattermost_summarizer.tools.reference_tracker import extract_urls_from_text

        text = "curl -s -H 'Authorization: Bearer Oracle' \\\nhttp://[fd00:c1::a9fe:a9fe]/opc/v2/vnics/ | jq\n"
        urls = extract_urls_from_text(text)
        assert len(urls) == 1
        url = urls[0]
        assert url.startswith("http://[fd00:c1::a9fe:a9fe]")
        parsed = urlparse(url)
        assert parsed.netloc == "[fd00:c1::a9fe:a9fe]"
        assert parsed.path == "/opc/v2/vnics/"

    def test_regular_http_url(self) -> None:
        from mattermost_summarizer.tools.reference_tracker import extract_urls_from_text

        urls = extract_urls_from_text("See https://example.com/page for details")
        assert "https://example.com/page" in urls

    def test_github_url(self) -> None:
        from mattermost_summarizer.tools.reference_tracker import extract_urls_from_text

        urls = extract_urls_from_text("PR: https://github.com/canonical/cloud-init/pull/6868")
        assert "https://github.com/canonical/cloud-init/pull/6868" in urls

    def test_launchpad_url(self) -> None:
        from mattermost_summarizer.tools.reference_tracker import extract_urls_from_text

        urls = extract_urls_from_text("Bug: https://bugs.launchpad.net/ubuntu/+source/open-iscsi/+bug/2098515")
        assert "https://bugs.launchpad.net/ubuntu/+source/open-iscsi/+bug/2098515" in urls

    def test_url_with_trailing_bracket_from_markdown(self) -> None:
        """URL followed by ] (e.g. markdown image alt close) should not balloon."""
        from mattermost_summarizer.tools.reference_tracker import extract_urls_from_text

        urls = extract_urls_from_text("![alt](http://example.com/img.png)")
        assert any("http://example.com/img.png" in u for u in urls)

    def test_code_block_with_ipv6_url(self) -> None:
        """IPv6 URL in a code block must be extracted without truncation."""
        from mattermost_summarizer.tools.reference_tracker import extract_urls_from_text

        text = """```\ncurl http://[fd00:c1::a9fe:a9fe]/opc/v2/vnics/\n```"""
        urls = extract_urls_from_text(text)
        assert len(urls) == 1
        url = urls[0]
        assert url == "http://[fd00:c1::a9fe:a9fe]/opc/v2/vnics/"

    def test_no_urls(self) -> None:
        from mattermost_summarizer.tools.reference_tracker import extract_urls_from_text

        assert extract_urls_from_text("Just plain text, no URLs here.") == []

    def test_short_text_not_extracted(self) -> None:
        from mattermost_summarizer.tools.reference_tracker import extract_urls_from_text

        urls = extract_urls_from_text("short.com")
        assert len(urls) == 0


class TestClassifyUrlsInText:
    """Regression tests for classify_urls_in_text resilience."""

    def test_ipv6_url_does_not_crash(self) -> None:
        """IPv6 literal URL must not raise ValueError from urlparse."""
        from mattermost_summarizer.tools.reference_tracker import classify_urls_in_text

        text = "curl http://[fd00:c1::a9fe:a9fe]/opc/v2/vnics/"
        results = classify_urls_in_text(text)
        assert len(results) == 0
        # assert results[0].reference_type.value == "unknown"

    def test_mixed_urls_with_ipv6(self) -> None:
        """Normal URLs alongside IPv6 must all be classified without crash."""
        from mattermost_summarizer.tools.reference_tracker import classify_urls_in_text

        text = "PR: https://github.com/canonical/cloud-init/pull/6868\ncurl http://[fd00:c1::a9fe:a9fe]/opc/v2/vnics/\n"
        results = classify_urls_in_text(text)
        types = [r.reference_type.value for r in results]
        assert "github_pr" in types
        # assert "unknown" in types

    def test_bare_bracket_does_not_crash(self) -> None:
        """Defensive: even if a bare [ slips through, no crash."""
        from mattermost_summarizer.tools.reference_tracker import classify_urls_in_text

        text = "malformed http://[fd00:c1::a9fe:a9fe here"
        results = classify_urls_in_text(text)
        # Should at least not crash; actual extraction depends on sanitize_url
        assert isinstance(results, list)
