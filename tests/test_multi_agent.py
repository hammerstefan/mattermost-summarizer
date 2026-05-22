"""Tests for multi-agent orchestration."""

from __future__ import annotations


class TestSubagentRegistration:
    """Test sub-agent registration."""

    def test_register_subagents_does_not_raise(self) -> None:
        """Test that register_subagents completes without error."""
        from unittest.mock import MagicMock

        from mattermost_summarizer.subagents import register_subagents

        mock_client = MagicMock()
        register_subagents(mock_client)


class TestOrchestratorAgent:
    """Test orchestrator agent building."""

    def test_build_orchestrator_agent_returns_agent(self) -> None:
        """Test that build_orchestrator_agent returns an Agent instance."""
        from mattermost_summarizer.agent import build_orchestrator_agent
        from mattermost_summarizer.levels import SummaryLevel

        agent = build_orchestrator_agent(
            llm_model="openai/gpt-4o",
            llm_api_key="test-key",
            llm_base_url=None,
            level=SummaryLevel.NORMAL,
        )

        assert agent is not None
        assert hasattr(agent, "llm")
        assert hasattr(agent, "tools")

    def test_orchestrator_has_delegate_and_finish_tools(self) -> None:
        """Test that orchestrator has delegate and finish tools."""
        from mattermost_summarizer.agent import build_orchestrator_agent
        from mattermost_summarizer.levels import SummaryLevel

        agent = build_orchestrator_agent(
            llm_model="openai/gpt-4o",
            llm_api_key="test-key",
            llm_base_url=None,
            level=SummaryLevel.NORMAL,
        )

        tool_names = [t.name for t in agent.tools]
        assert "delegate" in tool_names
        assert "finish" in tool_names

    def test_orchestrator_has_agent_context(self) -> None:
        """Test that orchestrator uses AgentContext with system_message_suffix."""
        from mattermost_summarizer.agent import build_orchestrator_agent
        from mattermost_summarizer.levels import SummaryLevel

        agent = build_orchestrator_agent(
            llm_model="openai/gpt-4o",
            llm_api_key="test-key",
            llm_base_url=None,
            level=SummaryLevel.NORMAL,
        )

        assert hasattr(agent, "agent_context")
        assert agent.agent_context is not None
        assert agent.agent_context.system_message_suffix is not None
        assert len(agent.agent_context.system_message_suffix) > 0


class TestDelegateTool:
    """Test DelegateTool creation."""

    def test_delegate_tool_creation(self) -> None:
        """Test that DelegateTool.create() returns valid tool definitions."""
        from mattermost_summarizer.subagents.delegate_tool import DelegateTool

        tools = DelegateTool.create()
        assert len(tools) == 1
        tool = tools[0]
        assert tool.name == "delegate"
        assert tool.description is not None
        assert "delegate" in tool.description.lower()


class TestSubagentPrompts:
    """Test sub-agent system prompts."""

    def test_thread_fetcher_prompt_contains_instructions(self) -> None:
        """Test that thread_fetcher prompt contains key instructions."""
        from mattermost_summarizer.subagents import THREAD_FETCHER_PROMPT

        assert "thread researcher" in THREAD_FETCHER_PROMPT.lower()
        assert "FetchThread" in THREAD_FETCHER_PROMPT
        assert "finish" in THREAD_FETCHER_PROMPT.lower()

    def test_bug_researcher_prompt_contains_instructions(self) -> None:
        """Test that bug_researcher prompt contains key instructions."""
        from mattermost_summarizer.subagents import BUG_RESEARCHER_PROMPT

        assert "bug researcher" in BUG_RESEARCHER_PROMPT.lower()
        assert "FetchLaunchpadBug" in BUG_RESEARCHER_PROMPT
        assert "finish" in BUG_RESEARCHER_PROMPT.lower()

    def test_github_researcher_prompt_contains_instructions(self) -> None:
        """Test that github_researcher prompt contains key instructions."""
        from mattermost_summarizer.subagents import GITHUB_RESEARCHER_PROMPT

        assert "github researcher" in GITHUB_RESEARCHER_PROMPT.lower()
        assert "FetchGitHubIssue" in GITHUB_RESEARCHER_PROMPT
        assert "finish" in GITHUB_RESEARCHER_PROMPT.lower()

    def test_file_fetcher_prompt_contains_instructions(self) -> None:
        """Test that file_fetcher prompt contains key instructions."""
        from mattermost_summarizer.subagents import FILE_FETCHER_PROMPT

        assert "file researcher" in FILE_FETCHER_PROMPT.lower()
        assert "FetchFile" in FILE_FETCHER_PROMPT
        assert "finish" in FILE_FETCHER_PROMPT.lower()


class TestOrchestratorPrompt:
    """Test orchestrator system prompt."""

    def test_orchestrator_prompt_contains_coordination_flow(self) -> None:
        """Test that orchestrator prompt contains coordination instructions."""
        from mattermost_summarizer.agent import ORCHESTRATOR_PROMPT

        assert "orchestrator" in ORCHESTRATOR_PROMPT.lower()
        assert "delegate" in ORCHESTRATOR_PROMPT.lower()
        assert "thread_fetcher" in ORCHESTRATOR_PROMPT
        assert "bug_researcher" in ORCHESTRATOR_PROMPT
        assert "github_researcher" in ORCHESTRATOR_PROMPT
        assert "file_fetcher" in ORCHESTRATOR_PROMPT

    def test_orchestrator_prompt_explains_different_reference_types(self) -> None:
        """Test that orchestrator prompt explains how to route different reference types."""
        from mattermost_summarizer.agent import ORCHESTRATOR_PROMPT

        assert "Mattermost" in ORCHESTRATOR_PROMPT
        assert "Launchpad" in ORCHESTRATOR_PROMPT
        assert "GitHub" in ORCHESTRATOR_PROMPT

    def test_orchestrator_prompt_includes_delegation_example(self) -> None:
        """Test that orchestrator prompt includes example delegation call."""
        from mattermost_summarizer.agent import ORCHESTRATOR_PROMPT

        assert "delegate(" in ORCHESTRATOR_PROMPT
        assert "agent_types" in ORCHESTRATOR_PROMPT
        assert "tasks" in ORCHESTRATOR_PROMPT
