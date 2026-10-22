# ADR-010: Actions through Composio MCP; "Ask the real me" human-in-the-loop

**Status:** Accepted (live Composio check pending Chandru's API key) · **Date:** 2026-10-22

## Context
Booking calls and alert emails depended on a hand-rolled Google OAuth client and refresh token (`app/tools/google.py`), which was never set up. Chandru wanted MCP-based actions through Composio. He also chose a showcase feature that keeps the chat human: when the twin doesn't know something, the real Chandru answers later.

## Decision
1. **Composio over MCP for Google Calendar and Gmail** (`app/integrations/composio_mcp.py`).
   - One Composio session for Chandru's own account, connected once via auth links (`scripts/composio_connect.py`).
   - The session's hosted MCP endpoint is opened with the official `mcp` client (streamable HTTP).
   - Tools are called **deterministically from code** after Jev J4 confirmation; no LLM agent picks them. That's why there's no `langchain-mcp-adapters` agent layer.
   - Composio's docs disagree on slugs and parameter names, so tools are resolved by name pattern from `list_tools()`, and arguments are mapped onto each tool's real input schema (`pick_args`).
   - If the endpoint exposes only meta tools, calls fall back to the SDK's `session.execute(slug, ...)`.
   - Slot selection (working hours, buffer, spread across days) and idempotency stay in our code and database.
2. **Gmail via the same session** sends lead, booking and question emails through the existing outbox, which keeps exactly-once delivery and retries.
3. **"Ask the real me"**:
   - The LLM offers "lemme check and get back to u?"; on yes it calls `ask_chandru`, which Jev J8 verifies.
   - The question is stored encrypted and emailed to Chandru, and its Gmail thread ID is kept.
   - A 5-minute job reads replies; Jev J9 accepts only real answers.
   - On the visitor's next visit the bot **texts first** in Chandru's voice, using only his answer, and it joins the conversation history.
   - Answers are exported as draft cards (`admin.py learned`), so the knowledge base grows from real questions.
4. **Persona safety found by the targeted golden run:** the LLM once narrated its own tool call as a bubble ("start_connect call with kind lead…"). Lines mentioning tool names or prompt mechanics are now dropped, and the eval's leak check covers them.

## Consequences
- \+ No Google Cloud console or OAuth client: one Composio account plus two auth links.
- \+ MCP keeps the action layer swappable (Outlook or Cal.com later are another toolkit).
- \+ Questions the twin can't answer become real conversations and new knowledge, with a human in the loop.
- − An external dependency on the action path. If Composio is down, the bot falls back to lead capture (`calendar_down`), and the outbox retries emails.
- − The exact slugs and arguments are only verified once connected; `scripts/composio_connect.py` prints what was resolved.
- − Removed: `app/tools/google.py`, `scripts/google_auth.py` and the google-api/google-auth packages.
