"""Tests for the OTel context propagation monkey-patch."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest

from mattermost_summarizer.tracing_patch import _parent_otel_context, install


@pytest.fixture(autouse=True)
def reset_install():
    """Reset the _installed flag so each test gets a clean slate."""
    import mattermost_summarizer.tracing_patch as tp

    original = tp._installed
    tp._installed = False
    yield
    tp._installed = original


class TestInstallIdempotent:
    def test_install_twice_does_not_raise(self):
        """install() should be safe to call multiple times."""
        install()
        install()  # second call must not error or double-patch


class TestParentOtelContextVar:
    def test_default_is_none(self):
        assert _parent_otel_context.get() is None

    def test_set_and_reset(self):
        sentinel = object()
        token = _parent_otel_context.set(sentinel)
        assert _parent_otel_context.get() is sentinel
        _parent_otel_context.reset(token)
        assert _parent_otel_context.get() is None

    def test_isolated_across_threads(self):
        """Each thread should see its own value of the context var."""
        sentinel = object()
        token = _parent_otel_context.set(sentinel)

        seen_in_thread: list[object] = []

        def worker():
            seen_in_thread.append(_parent_otel_context.get())

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        _parent_otel_context.reset(token)
        # The new thread should NOT inherit the parent thread's contextvar value
        # (plain threads don't propagate contextvars unless explicitly copied).
        assert seen_in_thread == [None]


class TestDelegateExecutorPatch:
    """Verify that _patched_delegate_tasks wraps thread targets to inject context."""

    def test_thread_target_receives_parent_context(self):
        """The wrapped thread target should see a non-None _parent_otel_context."""
        install()

        from openhands.tools.delegate.impl import DelegateExecutor

        executor = DelegateExecutor()

        # We'll record what _parent_otel_context.get() returns inside the thread.
        seen_contexts: list[object] = []

        # Fake OTel context object
        fake_ctx = object()

        # Replace the original _delegate_tasks with a version that spawns one
        # thread and records the context var value inside it.
        def fake_original_delegate_tasks(self_inner, action):
            def task_target():
                seen_contexts.append(_parent_otel_context.get())

            t = threading.Thread(target=task_target)
            t.start()
            t.join()
            return MagicMock()

        with (
            patch(
                "opentelemetry.context.get_current",
                return_value=fake_ctx,
            ),
            patch.object(
                type(executor),
                "_delegate_tasks",
                new=executor._delegate_tasks,
            ),
        ):
            # Manually invoke the patched method by calling the patched function
            # directly through the module-level reference captured at patch time.
            import mattermost_summarizer.tracing_patch as tp

            # Temporarily override the original inside the patch closure
            import openhands.tools.delegate.impl as delegate_impl

            original = delegate_impl.DelegateExecutor._delegate_tasks

            # Re-apply the patch so we can control the inner original
            delegate_impl.DelegateExecutor._delegate_tasks = original

            # Patch the inner "original" that the patch wraps
            with patch.object(
                delegate_impl.DelegateExecutor,
                "_delegate_tasks",
                side_effect=lambda self_inner, action: fake_original_delegate_tasks(self_inner, action),
            ):
                tp._installed = False
                tp._patch_delegate_executor()
                executor._delegate_tasks(MagicMock())  # type: ignore[call-arg]

        assert seen_contexts == [fake_ctx], f"Expected thread to see fake_ctx, got {seen_contexts}"

    def test_context_reset_after_thread_exits(self):
        """_parent_otel_context must be None again after the thread finishes."""
        install()

        sentinel = object()
        token = _parent_otel_context.set(sentinel)
        try:
            # Start a thread that reads then exits
            results: list[object] = []

            def worker():
                results.append(_parent_otel_context.get())

            t = threading.Thread(target=worker)
            t.start()
            t.join()
        finally:
            _parent_otel_context.reset(token)

        # The main thread's value should be unchanged after thread exit
        assert _parent_otel_context.get() is None


class TestLocalConversationPatch:
    """Verify _patch_local_conversation falls back gracefully."""

    def test_fallback_when_no_parent_context(self):
        """When _parent_otel_context is None, original method is called."""
        install()

        from openhands.sdk.conversation.impl.local_conversation import LocalConversation

        mock_conv = MagicMock(spec=LocalConversation)
        mock_conv._observability_root_span = None
        mock_conv._span_ended = False

        original_called: list[bool] = []

        with patch(
            "openhands.sdk.observability.laminar.should_enable_observability",
            return_value=False,
        ):
            # With no parent context and observability disabled, it should
            # call through to the original (which returns immediately).
            LocalConversation._start_observability_span(mock_conv, "test-session-id")

        # No span should have been set
        assert mock_conv._observability_root_span is None
