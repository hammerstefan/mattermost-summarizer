[ ] Flatten the Architecture: Remove LLM Sub-Agents for Pure Data Fetching. Give the fetching tools directly to the Orchestrator agent to eliminate expensive LLM roundtrips per URL.
[ ] Exploit Native Parallel Tool Calling. Modern LLMs support parallel function calling. The orchestrator can emit multiple fetch_reference calls in a single generation step.
