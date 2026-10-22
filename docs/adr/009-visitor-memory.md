# ADR-009: Visitor memory on the same browser, with consent-friendly limits

**Status:** Accepted · **Date:** 2026-10-22 · **Deciders:** Chandru Ganeshan

## Context
The chat "remembered" returning visitors by accident. The browser's random session ID was reused across visits, so the bot resumed the old thread verbatim, with no sense of elapsed time. The LangGraph checkpoints holding that history were never purged, which broke the 30-day retention promise in the requirements (E4).

## Decision
1. **Two IDs.** A `visitor_id` (random UUID in localStorage, per browser) and a `conversation_id` (one per visit). A new conversation starts after `conversation_gap_min` (30 min) of silence.
2. **Profile, not transcript.** Each finished conversation is summarised (cheap LLM, plus a code filter for sensitive topics) into a small encrypted profile: the name/company/role the visitor shared, up to 8 topics, a one-line note, whether a lead was saved, the visit count, and when they were last seen. A scheduler job does this every 5 min for quiet conversations, with a fallback on return.
3. **Returning visitor.** A fresh conversation whose prompt carries a MEMORY note, used only for the first reply: greet them lightly, never quote old messages, don't resume the old thread unless they do. A known name skips "who's this?". A saved lead isn't captured again.
4. **Recognition basis:** the browser ID only. **Never** a claimed name (anyone can type "I'm Priya"), IP address or fingerprint. Cross-device continuity is deferred to a verified-email link (see revisit).
5. **Limits:**
   - Everything is forgotten after `retention_days` (30) of inactivity, including LangGraph checkpoints (the bug fix).
   - "Forget me" (button, or typing it) erases the visitor, conversations, transcripts, logs, leads, bookings and checkpoints, and rotates the browser ID.
   - The UI shows: "Chats are saved for 30 days so I remember you on this device."

## Options considered
| Option | Recognises | Risk | Verdict |
|---|---|---|---|
| **Browser ID + profile (chosen)** | same browser | low; no PII needed | chosen |
| Resume full transcript (previous behaviour) | same browser | stale threads, unbounded retention | rejected |
| Claimed name links visits | anyone typing the name | leaks one visitor's history to another | rejected |
| IP / fingerprint | rough, shared networks | invasive, legally risky (DPDP Act 2023, GDPR), unreliable | rejected |
| Verified email link | across devices | needs working email | later |

## Consequences
- \+ Feels like a person who remembers you, not one replaying a log; old threads don't leak into new ones.
- \+ Retention is real (checkpoints purged), and erasure works on request.
- − Incognito, cleared storage or another device means a stranger again. That's acceptable and honest.
- − The profile summary costs one cheap LLM call per finished conversation (~$0.0001).

## Revisit when
Lead emails send (Google connected): add a signed "continue this chat" link to the confirmation email for cross-device continuity.
