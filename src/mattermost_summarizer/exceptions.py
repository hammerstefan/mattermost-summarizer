"""Custom exceptions for mattermost-summarizer."""


class PermalinkError(ValueError):
    """Raised when a Mattermost permalink URL is invalid."""


class AuthenticationError(Exception):
    """Raised when Mattermost API returns 401 Unauthorized."""


class NotFoundError(Exception):
    """Raised when a requested resource is not found (404)."""


class ThreadNotFoundError(NotFoundError):
    """Raised when the specified thread/post is not found (404)."""


class UserNotFoundError(NotFoundError):
    """Raised when a requested user is not found (404)."""


class ChannelNotFoundError(NotFoundError):
    """Raised when a requested channel is not found (404)."""


class FileNotFoundError(NotFoundError):
    """Raised when a requested file is not found (404)."""


class AgentStuckError(Exception):
    """Raised when the OpenHands agent gets stuck and cannot complete."""


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""
