# Architecture: mattermost-summarizer

---

## Architecture Evolution

```
 v1 (current)                      v2 (multi-agent)
┌──────────────────┐    ┌──────────────────────────────────────┐
│  Single Agent    │    │  Orchestrator + Sub-agents           │
│                  │    │                                      │
│  All 7 tools     │    │  Orchestrator: DelegateTool + finish │
│  in one agent    │    │  Sub-agents: domain tools only       │
│                  │    │                                      │
│  Sequential      │ ──► │  Parallel fetching via delegation  │
│  No recursion    │    │  Recursive reference following      │
│  No quality gate │    │  LLM-as-critic quality gate          │
│  Prompt in user  │    │  System prompt via AgentContext      │
│  message         │    │                                      │
└──────────────────┘    └──────────────────────────────────────┘
```

---

## v2: Overall Request Flow

```
┌──────────────┐
│  summarize.py│  CLI entry point
│  main()      │
└──────┬───────┘
       │ summarize(url)
       ▼
┌──────────────────────────────────────────────────────────────────────┐
│  MattermostSummarizer.summarize()  [summarizer.py]                  │
│                                                                      │
│  1. parse_permalink(url)  ──► post_id                               │
│  2. MattermostClient(base_url, token)                               │
│  3. load_config() ──► max_reference_depth, critic_*, level         │
│  4. register_subagents(client, github_token) ──► 4 agent types      │
│  5. build_orchestrator_agent(llm, level, critic) ──► Agent          │
│  6. LocalConversation(agent, workspace, visualizer)                  │
│  7. conversation.send_message("Summarize thread {url}")             │
│  8. conversation.run()  ◄──── blocking agent loop                   │
│  9. _extract_finish_action(conversation) ──► SummaryResult          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## v2: Multi-Agent Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR AGENT                              │
│                                                                         │
│  System prompt: AgentContext.system_message_suffix                      │
│  Tools: DelegateTool, finish (level-specific)                          │
│  Critic: SummarizationCritic (iterative refinement)                    │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Turn 1: Parse input, delegate root thread                       │ │
│  │                                                                   │ │
│  │  spawn ["thread_fetcher"]                                         │ │
│  │  delegate {"thread_fetcher": "Fetch thread abc123"}               │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                          │                                              │
│                          ▼ consolidated text result                     │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Turn 2: LLM scans fetched text, identifies references           │ │
│  │                                                                   │ │
│  │  Found:                                                           │ │
│  │    • bugs.launchpad.net/12345                                     │ │
│  │    • github.com/canonical/mattermost/pull/789                     │ │
│  │    • chat.canonical.com/canonical/pl/xyz789                       │ │
│  │    • file_id: abc (attachment)                                    │ │
│  │                                                                   │ │
│  │  spawn ["bug_researcher", "github_researcher",                    │ │
│  │         "thread_fetcher", "file_fetcher"]                         │ │
│  │  delegate {                    ← ALL FOUR RUN IN PARALLEL         │ │
│  │    "bug_researcher":    "Fetch Launchpad bug #12345",             │ │
│  │    "github_researcher": "Fetch github.com/.../pull/789",         │ │
│  │    "thread_fetcher":    "Fetch thread xyz789",                    │ │
│  │    "file_fetcher":      "Fetch file abc from thread abc123",      │ │
│  │  }                                                                │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                          │                                              │
│                          ▼ consolidated text results                     │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Turn 3: depth=2, thread xyz789 references another thread        │ │
│  │                                                                   │ │
│  │  delegate {"thread_fetcher": "Fetch thread def456"}               │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                          │                                              │
│                          ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Turn 4: All context gathered. Synthesize → call finish.         │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                          │                                              │
│                          ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  CRITIC EVALUATION                                               │ │
│  │                                                                   │ │
│  │  LLM reads: [original thread] + [fetched context] + [summary]   │ │
│  │                                                                   │ │
│  │  Score: 0.55 — below threshold (0.7)                             │ │
│  │  Feedback: "TL;DR misses key decision. Narrative too thin."     │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                          │                                              │
│                          ▼ feedback injected as new user message        │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  Turn 5: Agent revises summary → calls finish again             │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                          │                                              │
│                          ▼                                              │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  CRITIC EVALUATION                                               │ │
│  │  Score: 0.85 — above threshold ✓                                │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## v2: Sub-Agent Types

```
┌────────────────────────┐  ┌────────────────────────┐
│   thread_fetcher       │  │   bug_researcher        │
│                        │  │                        │
│   Tools:               │  │   Tools:               │
│   • FetchThread        │  │   • FetchLaunchpadBug   │
│   • GetUser            │  │                        │
│   • FetchChannel       │  │   System prompt:        │
│                        │  │   "You are a bug        │
│   System prompt:        │  │   researcher. Fetch     │
│   "You are a thread    │  │   Launchpad bugs and     │
│   researcher. Fetch    │  │   summarize findings."  │
│   Mattermost threads   │  │                        │
│   and extract key      │  │   Returns: bug title,   │
│   information including │  │   status, description,  │
│   any URLs found."     │  │   comments, impact       │
│                        │  │                        │
│   Returns: thread      │  │                        │
│   content + extracted  │  │                        │
│   URLs for next round  │  │                        │
└────────────────────────┘  └────────────────────────┘

┌────────────────────────┐  ┌────────────────────────┐
│  github_researcher      │  │   file_fetcher          │
│                        │  │                        │
│   Tools:               │  │   Tools:               │
│   • FetchGitHubIssue   │  │   • FetchFile           │
│                        │  │                        │
│   System prompt:        │  │   System prompt:        │
│   "You are a GitHub    │  │   "You are a file       │
│   researcher. Fetch     │  │   researcher. Fetch     │
│   GitHub issues/PRs     │  │   Mattermost files and  │
│   and summarize         │  │   report contents."     │
│   findings."            │  │                        │
│                        │  │   Returns: file content │
│   Returns: issue/PR    │  │   or "not readable"    │
│   title, body, state,  │  │   signal for binary     │
│   comments, reviews    │  │                        │
└────────────────────────┘  └────────────────────────┘
```

### Sub-Agent Registration Pattern

Each sub-agent is registered via the SDK's `register_agent()` with a factory function:

```python
def create_thread_fetcher(llm: LLM) -> Agent:
    return Agent(
        llm=llm,
        tools=[
            Tool(name="fetch_thread", params={}),
            Tool(name="get_user", params={}),
            Tool(name="fetch_channel", params={}),
        ],
        agent_context=AgentContext(
            system_message_suffix=(
                "You are a thread researcher. Fetch Mattermost threads "
                "and extract key information including any URLs or "
                "references found in the thread content."
            ),
        ),
    )

register_agent(
    name="thread_fetcher",
    factory_func=create_thread_fetcher,
    description="Fetches Mattermost threads and extracts key information and references.",
)
```

Sub-agents use the SDK's built-in `FinishAction` to return formatted text to the orchestrator.

---

## v2: Recursive Reference Following

```
Depth 0 (user input)
  │
  ▼
Depth 1: orchestrator delegates thread_fetcher for root thread
  │
  │  thread contains: LP bug URL, GitHub PR URL, Mattermost permalink
  ▼
Depth 2: orchestrator delegates bug_researcher, github_researcher, thread_fetcher
  │        (all three run in parallel)
  │
  │  fetched thread (from permalink) contains: another Mattermost permalink
  ▼
Depth 3: orchestrator delegates thread_fetcher for the new thread
  │
  │  fetched thread contains: no new references (or depth = max_reference_depth)
  ▼
Stop: synthesizing all gathered context → finish


Cycle prevention:
  ┌──────────────────────────────────────────────────┐
  │  followed_urls: set[str] = set()                  │
  │                                                  │
  │  Each time orchestrator delegates a sub-agent    │
  │  for a URL, that URL is added to followed_urls.  │
  │  Before delegating, check: URL in followed_urls? │
  │  → skip (already fetched)                        │
  └──────────────────────────────────────────────────┘


URL classification routing:
  ┌────────────────────────────────────────────────────────┐
  │  URL pattern                         │ Sub-agent       │
  │  ────────────────────────────────────│─────────────    │
  │  chat.{server}/{team}/pl/{post_id}   │ thread_fetcher  │
  │  bugs.launchpad.net/.../+bug/{id}   │ bug_researcher  │
  │  github.com/{o}/{r}/issues/{id}      │ github_researcher│
  │  github.com/{o}/{r}/pull/{id}        │ github_researcher│
  │  Mattermost file IDs                 │ file_fetcher     │
  └────────────────────────────────────────────────────────┘
```

---

## v2: LLM-as-Critic with Iterative Refinement

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│  SummarizationCritic(CriticBase)                                │
│                                                                  │
│  iterative_refinement:                                           │
│    success_threshold = 0.7  (configurable)                      │
│    max_iterations = 2       (configurable)                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  evaluate(events, git_patch=None) → CriticResult           │ │
│  │                                                            │ │
│  │  1. _extract_gathered_context(events)                      │ │
│  │     → original thread + all delegation results             │ │
│  │                                                            │ │
│  │  2. _extract_finish_action(events)                         │ │
│  │     → the produced summary (TL;DR, narrative, etc.)        │ │
│  │                                                            │ │
│  │  3. _build_rubric(level)                                   │ │
│  │     → level-specific evaluation prompt                     │ │
│  │                                                            │ │
│  │  4. _call_critic_llm(context, summary, rubric)             │ │
│  │     → LLM evaluates: score (0-1) + feedback                │ │
│  │                                                            │ │
│  │  5. return CriticResult(score, message)                    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Level-specific rubrics:                                         │
│  ┌──────────────┬──────────────────────────────────────────┐    │
│  │ Brief        │ Terseness, key points, no fluff         │    │
│  │ Normal       │ Completeness, accuracy, action items    │    │
│  │ Detailed     │ + open questions, sources, nuance       │    │
│  └──────────────┴──────────────────────────────────────────┘    │
│                                                                  │
│  Iterative refinement loop:                                      │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  iteration 1: agent calls finish → critic score 0.55       │ │
│  │    → below 0.7 threshold → feedback injected               │ │
│  │    → "TL;DR misses key decision. Narrative too thin."      │ │
│  │                                                            │ │
│  │  iteration 2: agent revises → calls finish → score 0.85   │ │
│  │    → above 0.7 threshold ✓ → summary accepted              │ │
│  │                                                            │ │
│  │  (if max_iterations reached without passing threshold,     │ │
│  │   return best-effort summary)                              │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## v2: System Prompt via AgentContext

```
BEFORE (v1 — system prompt in user message):
═════════════════════════════════════════════════

  Turn 1 user message:
    "Summarize this thread: https://...
     The post ID is: abc123

     You are a Mattermost conversation summarizer.
     Your job is to read conversation threads and
     produce structured summaries...
     [full 50-line system prompt repeated]"

  Turn 2 user message:
    (agent calls FetchThread, gets observation)
    [system prompt NOT repeated here — but it was
     already in the first user message, so it's
     still in context as a user message]

  Problem: system prompt sent in user turn, no
  provider-side caching benefit.


AFTER (v2 — system prompt via AgentContext):
═════════════════════════════════════════════════

  System message (sent once, cached by provider):
    "You are a Mattermost conversation summarizer.
     Your job is to read conversation threads and
     produce structured summaries..."

  Turn 1 user message:
    "Summarize this Mattermost thread:
     https://chat.example.com/team/pl/abc123
     The post ID is: abc123"

  Turn 2 user message:
    (delegation results returned as tool observation)

  Benefit: system message is cached (Anthropic,
  Gemini), user messages are small, clean
  separation of identity (system) vs task (user).
```

---

## v2: Full Sequence: URL → SummaryResult

```
summarize(url)
  │
  ├─ parse_permalink(url) → post_id
  ├─ MattermostClient(base_url, token)
  │
  ├─ register_subagents(client, github_token)
  │    register_agent("thread_fetcher", create_thread_fetcher)
  │    register_agent("bug_researcher", create_bug_researcher)
  │    register_agent("github_researcher", create_github_researcher)
  │    register_agent("file_fetcher", create_file_fetcher)
  │
  ├─ build_orchestrator_agent(llm, level, critic)
  │    Agent(llm=LLM(...),
  │           tools=[Tool(name=DelegateTool.name),
  │                  Tool(name="finish", params={...})],
  │           agent_context=AgentContext(
  │               system_message_suffix=SYSTEM_PROMPT),
  │           critic=SummarizationCritic(llm=..., level=...))
  │
  ├─ LocalConversation(agent, workspace=tmpdir, visualizer)
  ├─ send_message("Summarize this Mattermost thread: {url}")
  │
  └─ run()
       │
       │  ┌─ Orchestrator Turn 1 ─────────────────────────┐
       │  │  LLM → spawn + delegate thread_fetcher         │
       │  │  thread_fetcher:                                │
       │  │    fetch_thread(abc123) → thread text           │
       │  │    get_user(uid1), get_user(uid2) → names       │
       │  │    fetch_channel(ch1) → channel info             │
       │  │    finish("Thread abc123: [content + URLs]")    │
       │  │  → consolidated result back to orchestrator     │
       │  └────────────────────────────────────────────────┘
       │
       │  ┌─ Orchestrator Turn 2 ─────────────────────────┐
       │  │  LLM scans result, identifies:                 │
       │  │    - bugs.launchpad.net/12345                  │
       │  │    - github.com/o/r/pull/789                    │
       │  │    - chat.example.com/team/pl/xyz789           │
       │  │                                                │
       │  │  spawn + delegate (PARALLEL):                  │
       │  │    bug_researcher → "Fetch LP bug #12345"     │
       │  │    github_researcher → "Fetch PR #789"         │
       │  │    thread_fetcher → "Fetch thread xyz789"     │
       │  │  → all three run in parallel, return results   │
       │  └────────────────────────────────────────────────┘
       │
       │  ┌─ Orchestrator Turn 3 (depth=2) ──────────────┐
       │  │  thread xyz789 references thread def456        │
       │  │  delegate thread_fetcher → "Fetch def456"      │
       │  └────────────────────────────────────────────────┘
       │
       │  ┌─ Orchestrator Turn 4 ─────────────────────────┐
       │  │  LLM synthesizes all gathered context           │
       │  │  finish(tldr=..., narrative=..., ...)            │
       │  └────────────────────────────────────────────────┘
       │
       │  ┌─ Critic Evaluation ────────────────────────────┐
       │  │  score=0.55, below threshold → revision       │
       │  │  feedback injected as new user message          │
       │  │                                                │
       │  │  LLM revises → finish(improved summary)         │
       │  │  score=0.85, above threshold ✓                  │
       │  └────────────────────────────────────────────────┘
       │
       └─ _extract_finish_action(conversation)
            scan state.events reversed
            find SummarizerFinishAction
            → SummaryResult(tldr, key_findings, narrative,
                           action_items, participants, metadata)
```

---

## v2: Tool Distribution (Agent vs Sub-agent)

```
v1: ALL tools in one agent
═══════════════════════════

  ┌───────────────────────────────────────────┐
  │            Single Agent                    │
  │                                           │
  │  FetchThread, GetUser, FetchChannel,      │
  │  FetchFile, FetchLaunchpadBug,            │
  │  FetchGitHubIssue, finish                 │
  └───────────────────────────────────────────┘


v2: Tools distributed by specialty
═══════════════════════════════════

  ┌─────────────────────┐
  │   Orchestrator       │
  │   DelegateTool       │
  │   finish (level)     │
  └────────┬────────────┘
           │ delegates
           │
  ┌────────┼──────────────────────────────┐
  │        │                              │
  ▼        ▼              ▼               ▼
┌──────┐ ┌──────┐   ┌──────────┐   ┌──────────┐
│Thread│ │ Bug  │   │ GitHub    │   │ File     │
│Fetchr│ │Rsrchr│   │ Researchr│   │ Fetcher  │
│      │ │      │   │          │   │          │
│Fetch │ │Fetch │   │FetchGH   │   │FetchFile │
│Thread│ │LPBug │   │Issue     │   │          │
│GetUsr│ │      │   │          │   │          │
│Fetch │ │      │   │          │   │          │
│Chanl │ │      │   │          │   │          │
└──────┘ └──────┘   └──────────┘   └──────────┘
```

---

## v2: Class Hierarchy (new components)

```
mattermost_summarizer
├── agent.py
│   ├── build_orchestrator_agent()    ← NEW: builds orchestrator with
│   │                                    DelegateTool, finish, AgentContext
│   ├── build_summarizer_agent()      ← existing (kept for rollback)
│   └── register_subagents()          ← NEW: registers 4 sub-agent types
│
├── subagents/                         ← NEW package
│   ├── __init__.py
│   ├── thread_fetcher.py              ← NEW: create_thread_fetcher()
│   ├── bug_researcher.py             ← NEW: create_bug_researcher()
│   ├── github_researcher.py          ← NEW: create_github_researcher()
│   └── file_fetcher.py               ← NEW: create_file_fetcher()
│
├── critic.py                         ← NEW module
│   └── SummarizationCritic(CriticBase)
│        ├── evaluate()
│        ├── _extract_gathered_context()
│        ├── _extract_finish_action()
│        ├── _build_rubric()
│        └── _call_critic_llm()
│
├── config.py
│   └── MattermostSummarizerConfig
│        ├── max_reference_depth: int = 3    ← NEW
│        ├── critic_enabled: bool = True      ← NEW
│        ├── critic_threshold: float = 0.7    ← NEW
│        └── critic_max_iterations: int = 2   ← NEW
│
├── summarizer.py
│   └── MattermostSummarizer.summarize()  ← MODIFIED: orchestrator loop
│
└── tools/                               ← UNCHANGED (tool code stays)
    ├── fetch_thread/impl.py
    ├── fetch_channel/impl.py
    ├── get_user/impl.py
    ├── fetch_file/impl.py
    ├── fetch_launchpad_bug/impl.py
    ├── fetch_github_issue/impl.py
    └── finish/definition.py
```

---

## v2: Configuration

```toml
[mattermost]
url = "https://chat.canonical.com"
token = "..."

[llm]
model = "openai/gpt-4o"
api_key = "..."
base_url = "..."

[github]
token = "ghp_..."

[summarizer]                             ← NEW section
default_level = "normal"                  ← from summarization-levels change
max_reference_depth = 3                  ← NEW
critic_enabled = true                     ← NEW
critic_threshold = 0.7                    ← NEW
critic_max_iterations = 2                ← NEW
```

Environment variable overrides:

| TOML field | Env var |
|-----------|---------|
| `max_reference_depth` | `MM_SUMMARIZER_MAX_REFERENCE_DEPTH` |
| `critic_enabled` | `MM_CRITIC_ENABLED` |
| `critic_threshold` | `MM_CRITIC_THRESHOLD` |
| `critic_max_iterations` | `MM_CRITIC_MAX_ITERATIONS` |

---

## SDK Internals: Agent Loop (unchanged, for reference)

### Setup (lazy, one-time)

```
LocalConversation.__init__()          local_conversation.py:96
  └─ stores agent, workspace, visualizer — no I/O yet

first run() or send_message() calls:
LocalConversation._ensure_agent_ready()   local_conversation.py:592
  ├─ _ensure_plugins_loaded()   loads MCP config, hooks, skills
  ├─ registers file-based agents
  └─ agent.init_state(state, on_event)    agent.py:350
       └─ emits SystemPromptEvent(system_prompt, tools, dynamic_context)
            → appended to state.events as event[0]
```

---

### send_message() — Inject the Task

```
LocalConversation.send_message(text)      local_conversation.py:702
  └─ emits MessageEvent(source="user", content=text)
       → appended to state.events
```

---

### run() — The Main Loop

```
LocalConversation.run()                   local_conversation.py:768

┌─────────────────────────────────────────────────────────────────┐
│  while True:                                                    │
│    ① check status                                               │
│       PAUSED/STUCK       → break                                │
│       FINISHED           → run stop-hooks, break               │
│       WAITING_FOR_CONFIRM→ reset to RUNNING                     │
│                                                                 │
│    ② stuck_detector.is_stuck()  (scans last 20 events)         │
│       → if stuck: set status = STUCK, break                     │
│                                                                 │
│    ③ agent.step(conversation, on_event, on_token)              │
│                                                                 │
│    ④ check WAITING_FOR_CONFIRMATION → break                     │
│    ⑤ check max_iteration_per_run   → error + break             │
└─────────────────────────────────────────────────────────────────┘
```

---

### agent.step() — One Iteration

```
Agent.step()                              agent.py:554

  ① pending actions?   unmatched ActionEvents → execute & return

  ② blocked message?   hook blocked last user msg → FINISHED & return

  ③ Build LLM message history
       prepare_llm_messages(state.events, condenser, llm)
       ┌─────────────────────────────────────────────────┐
       │  SystemPromptEvent   → system message            │
       │  MessageEvent(user)  → user message              │
       │  MessageEvent(agent) → assistant message         │
       │  ActionEvent         → assistant + tool_calls    │
       │  ObservationEvent    → tool result message       │
       │  AgentErrorEvent     → tool error message        │
       └─────────────────────────────────────────────────┘
       context too long + condenser? → emit CondensationRequest, return

  ④ LLM call
       make_llm_completion(llm, messages, tools=schemas)
       → calls LiteLLM → returns LLMResponse(message)

  ⑤ classify_response(message)           response_dispatch.py:53
       TOOL_CALLS     → has message.tool_calls
       CONTENT        → non-blank text content
       REASONING_ONLY → thinking blocks only
       EMPTY          → nothing
```

---

### Tool Call Dispatch (TOOL_CALLS path)

```
_handle_tool_calls()                      response_dispatch.py:187

  for each tool_call in message.tool_calls:

    _get_action_event()                   agent.py:971
      ├─ parse JSON arguments
      ├─ normalize tool name
      ├─ validate args against tool.action_type (Pydantic)
      ├─ action = tool.action_from_arguments(args)
      └─ emit ActionEvent(action, tool_name, tool_call_id, thought)

    requires confirmation? → WAITING_FOR_CONFIRMATION, return

  _execute_actions()                      agent.py:491
    └─ ParallelToolExecutor.execute_batch()
         ThreadPoolExecutor — runs all tool calls in parallel
         ┌───────────────────────────────────────────────────┐
         │  tool.__call__(action, conversation)              │
         │    = ToolExecutor.__call__(action, conversation)  │
         │    returns Observation                            │
         │  → emit ObservationEvent  (or AgentErrorEvent)   │
         └───────────────────────────────────────────────────┘
    └─ batch.finalize()
         if SummarizerFinishTool called → set status = FINISHED
```

---

### Critic Integration (v2 addition to the loop)

```
After agent.step() completes with a finish action:

┌────────────────────────────────────────────────────────────────┐
│  Critic Evaluation (if critic attached and finish detected)     │
│                                                                │
│  critic.evaluate(events, git_patch)                            │
│    → CriticResult(score, message)                             │
│                                                                │
│  if critic.should_refine(result):                              │
│    → inject feedback as new user message                       │
│    → loop continues (agent revises)                           │
│  else:                                                         │
│    → summary accepted, conversation ends                        │
│                                                                │
│  max_iterations reached without passing?                       │
│    → return best-effort summary (no more revisions)           │
└────────────────────────────────────────────────────────────────┘
```

---

### Event Callback Chain (every emitted event)

```
emit(event)
  ├─ visualizer.on_event(event)
  │    DelegationVisualizer → writes delegation trace
  │    FileConversationVisualizer → writes to agent-trace.log
  │
  ├─ user_callbacks(event)         (optional user-supplied)
  │
  ├─ _default_callback(event)
  │    state.events.append(event)
  │    tracks last_user_message_id
  │
  └─ hook_processor(event)
       runs session / stop / action hooks if configured
```

---

### Stuck Detector

```
StuckDetector.is_stuck()                  stuck_detector.py:62
  scans last 20 events since last user message
  checks 4 patterns:

  ┌──────────────────────────────────────────────────────────┐
  │ repeating_action_observation                             │
  │   same action + same observation  ≥ 4 times             │
  │                                                          │
  │ repeating_action_error                                   │
  │   same action + all errors        ≥ 4 times             │
  │                                                          │
  │ monologue                                                │
  │   N consecutive agent MessageEvents with no user input  │
  │                                                          │
  │ alternating_action_observation                           │
  │   A/B/A/B pattern in event pairs                        │
  └──────────────────────────────────────────────────────────┘
  equality ignores IDs — compares action, thought, tool_name,
  observation, error content
```

---

## v1 Reference: Original Single-Agent Flow (preserved for rollback context)

```
  URL: https://mattermost.example.com/team/pl/abc123
       │
       ▼ parse_permalink()
  post_id = "abc123"
       │
       ▼ LLM prompt: "Summarize... post_id=abc123" + SYSTEM_PROMPT
       │
       │  LLM calls fetch_thread(post_id="abc123")
       ▼
  FetchThreadExecutor
    → client.get_post_thread("abc123")
    → resolves user IDs → usernames
    → FetchThreadObservation(root_post, replies, channel_id, ...)
       │
       │  LLM (optionally) calls fetch_channel(channel_id=...)
       ▼
  FetchChannelExecutor
    → client.get_channel(channel_id)
    → FetchChannelObservation(name, purpose, ...)
       │
       │  LLM calls finish(tldr=..., key_findings=..., narrative=...,
       ▼                    action_items=..., participants=...)
  SummarizerFinishExecutor → SummarizerFinishObservation(success=True)
       │
       │  conversation ends
       ▼
  _extract_finish_action() scans conversation.state.events
    → finds SummarizerFinishAction
    → SummaryResult(tldr, key_findings, narrative, action_items, participants)
       │
       ▼
  printed to stdout as Markdown
```