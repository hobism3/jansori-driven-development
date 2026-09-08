"""Hook CONTRACT tests (US-01/05/13, I-08, BR-01/02/03).

We run the hooks as REAL subprocesses with real stdin JSON — exactly the shape Claude Code
uses — so we verify the parts we author: fail-open, exit codes (NEVER 2), output channel,
and the injected additionalContext shape. (Whether Claude Code actually fires the hook and
injects the context is a runtime fact verified live at U4 — see README-u2 residual checklist.)
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
HOOK_UPS = os.path.join(ROOT, "plugin", "hooks", "user_prompt_submit.py")
HOOK_STOP = os.path.join(ROOT, "plugin", "hooks", "stop_notice.py")

# A port nothing listens on -> connection refused -> server "down" (fail-open path).
DOWN_URL = "http://127.0.0.1:9"


def _run(script, stdin_obj, env_extra=None):
    env = dict(os.environ)
    env["JANSORI_HOOK_TIMEOUT_MS"] = "800"
    if env_extra:
        env.update(env_extra)
    stdin = json.dumps(stdin_obj) if stdin_obj is not None else ""
    return subprocess.run([sys.executable, script], input=stdin, capture_output=True,
                          text=True, encoding="utf-8", env=env, timeout=30)


def test_user_prompt_submit_failopen_when_server_down():
    p = _run(HOOK_UPS, {"session_id": "s1", "prompt": "hi"}, {"JANSORI_URL": DOWN_URL})
    assert p.returncode == 0            # never blocks
    assert p.stdout.strip() == ""       # no injection on outage (fail-open, I-08)
    assert p.returncode != 2            # NEVER exit 2 (would erase the prompt)


def test_user_prompt_submit_failopen_on_malformed_stdin():
    env = dict(os.environ); env["JANSORI_HOOK_TIMEOUT_MS"] = "800"; env["JANSORI_URL"] = DOWN_URL
    p = subprocess.run([sys.executable, HOOK_UPS], input="{not json",
                       capture_output=True, text=True, encoding="utf-8", env=env, timeout=30)
    assert p.returncode == 0
    assert p.stdout.strip() == ""


def test_user_prompt_submit_never_exits_2_even_empty_stdin():
    p = _run(HOOK_UPS, None, {"JANSORI_URL": DOWN_URL})
    assert p.returncode == 0


def test_stop_notice_writes_stderr_only_and_exits_0():
    p = _run(HOOK_STOP, {"session_id": "s1", "last_assistant_message": "done"})
    assert p.returncode == 0
    assert p.stdout.strip() == ""        # notice-only: nothing injected into conversation
    assert "jansori" in p.stderr.lower() # user-visible notice goes to stderr (BR-03)


def test_user_prompt_submit_success_shape_inprocess(monkeypatch):
    """Success-path additionalContext shape, via import + patched client (no server needed)."""
    import user_prompt_submit as ups

    monkeypatch.setattr(ups.jansori_client, "act_index",
                        lambda sid, t: {"ok": True, "status": 200,
                                        "data": {"entries": [{"skill_id": "fmt", "name": "Formatter", "description": "code style"}]}})
    ctx = ups.build_additional_context("s1", 2000)
    assert ctx is not None
    assert "jansori" in ctx.lower()
    assert "/jansori:nag" in ctx          # behavior preamble present (BR-02.3, auto-detect)
    assert "Formatter" in ctx and "fmt" in ctx  # index entry present


def test_user_prompt_submit_no_context_when_index_fails(monkeypatch):
    import user_prompt_submit as ups
    monkeypatch.setattr(ups.jansori_client, "act_index",
                        lambda sid, t: {"ok": False, "status": 0, "code": "SERVER_ERROR", "message": "down"})
    assert ups.build_additional_context("s1", 2000) is None  # no preamble on failure (BR-02.4)
