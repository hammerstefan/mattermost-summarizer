"""Agent factory for mattermost-summarizer."""

from collections.abc import Sequence

from openhands.sdk import LLM, Agent, Tool
from pydantic import SecretStr

SYSTEM_PROMPT = """You are a Mattermost conversation summarizer. Your job is to read
conversation threads and produce structured summaries.

When given a Mattermost permalink:
1. Fetch the thread to get all posts
2. Fetch channel context if the thread is unclear without it
3. Produce a summary with:
   - TL;DR: 3-5 bullet points capturing the key outcomes
   - Key Findings: Important insights, discoveries, or noteworthy points from the discussion
   - Narrative: Chronological walkthrough of the conversation, noting who said
     what and how the discussion evolved
   - Action items: Any decisions, follow-ups, or assignments mentioned
   - Participants: List of people who contributed
4. Call the finish tool with your summary

IMPORTANT: After calling the finish tool, do NOT output any additional text.
The finish tool call IS your final output. Do not write markdown, summaries,
or any other text after calling it.

Be concise but thorough. Focus on substance, not procedural messages
("thanks!", "agreed", etc.).

IMPORTANT: Always fetch the thread first using the FetchThread tool before
attempting to summarize. The thread data will include user information. Only call
GetUser if you need additional details about a specific user."""


def build_summarizer_agent(
    llm_model: str,
    llm_api_key: str,
    llm_base_url: str | None,
    tools: Sequence[Tool],
) -> Agent:
    """Build a Mattermost summarizer agent.

    Args:
        llm_model: LLM model name (LiteLLM format: provider/model-name)
        llm_api_key: API key for the LLM
        llm_base_url: Base URL for the LLM API (None = provider default)
        tools: List of Tool spec instances for Mattermost operations

    Returns:
        Configured Agent instance ready for Conversation
    """
    llm = LLM(
        model=llm_model,
        api_key=SecretStr(llm_api_key),
        base_url=llm_base_url,
    )

    agent = Agent(llm=llm, tools=list(tools), include_default_tools=[])

    return agent


__all__ = ["build_summarizer_agent", "SYSTEM_PROMPT"]
