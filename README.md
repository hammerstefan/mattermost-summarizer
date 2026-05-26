# Mattermost Summarizer

An agentic tool that summarizes Mattermost conversation threads using the OpenHands SDK.

## Installation

```bash
uv add mattermost-summarizer
```

## Configuration

Create a `mattermost-summarizer.toml` config file:

```toml
[mattermost]
url = "https://chat.canonical.com"
token = "your-mattermost-token"

[llm]
model = "openai/gpt-4o"
api_key = "your-llm-api-key"
base_url = "https://api.openai.com/v1"  # optional

[github]
token = "ghp_..."  # optional; raises GitHub API rate limit

[summarizer]
default_level = "normal"       # brief, normal, or detailed (default: normal)
max_reference_depth = 3        # max recursion depth for following referenced URLs (0=disabled, default: 3)
critic_enabled = true          # enable LLM critic for iterative refinement (default: true)
critic_threshold = 0.7         # quality threshold 0-1 for accepting summaries (default: 0.7)
critic_max_iterations = 2      # max critic revision rounds (default: 2)
max_sub_agents = 500           # max sub-agents spawned during reference following (default: 500)
```

**Security note**: Store tokens in environment variables rather than in TOML files when deploying on multi-user systems — TOML files contain plaintext secrets that require filesystem-level `0600` permissions to protect.

### Using GitHub Copilot

If you have a GitHub Copilot subscription, you can use it instead of a separate LLM provider. LiteLLM has native support via the `github_copilot/` provider prefix:

```toml
[mattermost]
url = "https://chat.canonical.com"
token = "your-mattermost-token"

[llm]
model   = "github_copilot/gpt-5-mini"
api_key = "ghp_your_github_personal_access_token"
```

Your GitHub PAT needs the `copilot` scope. No `base_url` is required — LiteLLM routes automatically.
**Note**: Only gpt models are supported at this time.

See [docs/gh-copilot.md](docs/gh-copilot.md) for more details.

### Environment Variables

You can use environment variables with `MM_` prefix instead of a config file. Environment variables are the recommended approach for production deployments to avoid plaintext secrets on disk.

```bash
export MM_MATTERMOST_URL=https://chat.canonical.com
export MM_MATTERMOST_TOKEN=your-token
export MM_LLM_MODEL=openai/gpt-4o
export MM_LLM_API_KEY=your-key
export MM_LLM_BASE_URL=https://api.openai.com/v1
export MM_GITHUB_TOKEN=ghp_...              # optional
export MM_SUMMARIZER_DEFAULT_LEVEL=detailed  # brief, normal, or detailed
export MM_SUMMARIZER_MAX_REFERENCE_DEPTH=3
export MM_SUMMARIZER_CRITIC_ENABLED=true
export MM_SUMMARIZER_CRITIC_THRESHOLD=0.7
export MM_SUMMARIZER_CRITIC_MAX_ITERATIONS=2
export MM_SUMMARIZER_MAX_SUB_AGENTS=500
```

## Usage

### Python API

```python
from mattermost_summarizer import MattermostSummarizer

summarizer = MattermostSummarizer.from_config("mattermost-summarizer.toml")
result = summarizer.summarize("https://chat.canonical.com/canonical/pl/abc123xyz")

print(result)  # Pretty formatted output
print(result.tldr)  # Just the TL;DR
```

### CLI

```bash
uv run python summarize.py https://chat.canonical.com/canonical/pl/post_id
```

Additional CLI options:

| Option | Description |
|--------|-------------|
| `--config`, `-c` | Path to TOML config file (default: mattermost-summarizer.toml) |
| `--output`, `-o` | Output format: `text` or `json` (default: text) |
| `--level`, `-l` | Summarization level: `brief`, `normal`, or `detailed` (overrides config default_level) |

## License

GPLv3
