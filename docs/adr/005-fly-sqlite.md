# ADR-005: Single Fly.io machine with SQLite on a volume

**Status:** Proposed · **Date:** 2026-10-21

## Context
Expected load is 1–50 concurrent chats. WebSockets need a long-lived process. The frontend is static on GitHub Pages, so the backend must be a separate host with TLS (`wss://`). Chandru chose Fly.io/Railway.

## Decision
Deploy one Fly.io machine (shared CPU, `min_machines_running = 1` to avoid cold starts) in region **`sin` (Singapore)**: good RTT to India and SEA, with Qdrant Cloud in the nearest region, with a 1 GB volume holding SQLite (WAL) for sessions, messages, leads, bookings, turn logs and LangGraph checkpoints (`AsyncSqliteSaver`). Secrets in Fly secrets. Scheduled jobs (news ingest, keepalive, purge, email outbox) run in-process on APScheduler.

## Options considered
| Option | Pros | Cons |
|---|---|---|
| **Fly.io + SQLite volume (chosen)** | WebSockets native, near-Asia regions, simple, cheap | single-machine state |
| Railway | very simple deploys | fewer Asia regions, volumes less mature |
| Cloud Run | scale-to-zero, GCP familiarity | WebSocket timeouts, cold starts, stateless (needs external DB) |
| Fly + Postgres | multi-machine ready | extra service for no current need |

## Consequences
- \+ Zero external DB; backups via volume snapshots.
- − Can't scale horizontally without moving to Postgres + Redis; revisit at > 1 machine.
