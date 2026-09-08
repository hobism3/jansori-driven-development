#!/usr/bin/env python3
"""UserPromptSubmit hook (U2 · CMP-09 · US-01, US-13, I-08).

Injects, once per turn, a short BEHAVIOR PREAMBLE + the skill name/description index into
the model's context via stdout JSON `additionalContext` (Q1=A). The preamble makes the
model auto-detect natural-language corrections and route them to /jansori:nag (user
decision 2026-09-08, "항상 자동 판별", BR-02.3).

FAIL-OPEN (I-08 / BR-01):
  - The server call is bounded by JANSORI_HOOK_TIMEOUT_MS (default 2000ms).
  - On ANY failure (timeout, server down, bad data) we print NOTHING and exit 0 — the
    user's prompt is never blocked.
  - We NEVER exit 2 (exit 2 would block and erase the prompt).
  - No LLM call happens here (US-01 AC3): pure HTTP GET + text formatting.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
import jansori_client  # noqa: E402

PREAMBLE = (
    "[jansori] A local skill store is active. When the user's message corrects or refines "
    "how a task should be done (a 'nag'), route it through /jansori:nag (it resolves the "
    "target skill; if the target is ambiguous, ask the user before applying). To save a NEW "
    "reusable rule as a skill, use /jansori:save. When a nag response has normalize_due=true, "
    "launch the background capsule-normalizer subagent (does not block your work). If the "
    "jansori server is unavailable, continue the task anyway (fail-open)."
)


def _format_index(entries: list[dict]) -> str:
    if not entries:
        return "[jansori] Skill index: (empty — no skills registered yet.)"
    lines = ["[jansori] Available skills (name — description):"]
    for e in entries:
        name = e.get("name") or e.get("skill_id", "")
        desc = e.get("description", "")
        lines.append(f"  - {name} ({e.get('skill_id','')}): {desc}")
    return "\n".join(lines)


def build_additional_context(session_id: str | None, timeout_ms: int) -> str | None:
    """Return the text to inject, or None to inject nothing (fail-open)."""
    result = jansori_client.act_index(session_id, timeout_ms)
    if not result.get("ok"):
        return None  # server failure -> no injection, no preamble (BR-02.4)
    data = result.get("data") or {}
    entries = data.get("entries", []) if isinstance(data, dict) else []
    return f"{PREAMBLE}\n\n{_format_index(entries)}"


def run(stdin_text: str) -> int:
    # Parse hook stdin; tolerate malformed input (still fail-open).
    session_id = None
    try:
        payload = json.loads(stdin_text) if stdin_text.strip() else {}
        session_id = payload.get("session_id") or os.environ.get("CLAUDE_SESSION_ID")
    except (ValueError, AttributeError):
        session_id = os.environ.get("CLAUDE_SESSION_ID")

    try:
        ctx = build_additional_context(session_id, jansori_client.default_timeout_ms())
    except Exception:
        ctx = None  # absolute fail-open guard

    if ctx:
        out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}
        sys.stdout.write(json.dumps(out, ensure_ascii=False))
    # else: print nothing (fail-open). Always exit 0 — NEVER exit 2.
    return 0


def _force_utf8_stdio() -> None:
    # Windows consoles default to a locale codec (e.g. cp949) that cannot encode the em-dash
    # / non-ASCII in the injected context. Force UTF-8 so the success path never dies (which
    # would look like a silent fail-open and drop injection).
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def main() -> int:
    _force_utf8_stdio()
    try:
        return run(sys.stdin.read())
    except Exception:
        return 0  # any unexpected error must still fail-open


if __name__ == "__main__":
    raise SystemExit(main())
