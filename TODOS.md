[ ] Channel detail lookup doesn't work
    - the thread details don't return a channel_id, so we only have a channel_name, and you can't do an individual channel lookup without an id `/v4/channels/{id}`. If you try to do a name lookup `/v4/channels?name={name}` you will get a permission denied with the default user permisisions
[ ] Add / fix stuck loop detection
    - a recent run had the agent looping for a long time and was never killed, fix it
[ ] Flatten the Architecture: Remove LLM Sub-Agents for Pure Data Fetching. Give the fetching tools directly to the Orchestrator agent to eliminate expensive LLM roundtrips per URL.
[ ] Exploit Native Parallel Tool Calling. Modern LLMs support parallel function calling. The orchestrator can emit multiple fetch_reference calls in a single generation step.
