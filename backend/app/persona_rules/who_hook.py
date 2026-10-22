"""A10: casually ask "who's this?" once, early, if the visitor hasn't said."""

from __future__ import annotations

NO_HOOK_ROUTES = {"tools", "identity", "deflect", "personal", "reject", "clarify"}


def should_ask(*, visitor_name: str | None, asked: bool, visitor_msgs: int, route: str,
               ask_after: list[int]) -> bool:
    return (
        not visitor_name
        and not asked
        and visitor_msgs in ask_after
        and route not in NO_HOOK_ROUTES
    )
