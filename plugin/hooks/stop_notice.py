#!/usr/bin/env python3
"""Stop hook (U2 · CMP-09 · US-05) — save-proposal NOTICE ONLY.

At end of turn, present a generic reminder that the user MAY save this work as a skill or
leave a nag. This is a NOTICE ONLY (BR-03):
  - written to STDERR (Q6=A) so it does NOT get injected into the conversation/model context
    and is NOT a direct save;
  - stdout is left empty and we exit 0 so the session is never blocked;
  - NO heuristic / NO LLM decides "worth saving" here (Q5=A) — that judgment happens when the
    user actually invokes /jansori:save or /jansori:nag.

NOTE (F-04): whether this stderr line is surfaced to the user in the Claude Code UI is a
runtime fact verified live at U4. If it is not visible, switch to a notice-only alternative
that keeps the same "notice, not conversation/direct-save" property.
"""
from __future__ import annotations

import json
import sys

NOTICE = (
    "[jansori] Turn complete. To keep useful changes: /jansori:save to register a new skill, "
    "or /jansori:nag to leave a correction on an existing one."
)


def run(stdin_text: str) -> int:
    # We don't need the payload to emit a generic notice, but parse defensively.
    try:
        json.loads(stdin_text) if stdin_text.strip() else {}
    except (ValueError, AttributeError):
        pass
    sys.stderr.write(NOTICE + "\n")
    # stdout stays empty; exit 0 (never block the stop, never inject).
    return 0


def _force_utf8_stdio() -> None:
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
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
