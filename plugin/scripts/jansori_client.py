#!/usr/bin/env python3
"""Jansori common client (U2 · CMP-11 common action path).

Single entry point shared by hooks, the `load` Skill, and the `/jansori:*` commands
(BR-04). Talks to the U1 loopback server over HTTP using ONLY the Python standard
library (urllib) so it runs on Windows without extra dependencies (Q2=A).

Design values (Q1..Q12=A):
  - Server base URL: env JANSORI_URL (default http://127.0.0.1:8765). loopback only (BR-11.1).
  - Timeout: --timeout-ms, else env JANSORI_HOOK_TIMEOUT_MS (default 2000).
  - request_id: caller passes --request-id for retries (idempotent, I-05); else a UUID
    is generated. One request_id binds to one skill_id (D-08) — the CALLER must reuse the
    SAME id on retry and NOT reuse it across skills.
  - Structured errors: the server returns {"error": {"code","message","detail?}}. We parse
    it and NEVER conflate SERVER_ERROR (outage/timeout/5xx) with SKILL_ABSENT (I-07 / BR-08).

Output contract: every subcommand prints a single JSON object to stdout:
  {"ok": true,  "status": <int>, "data": <server json>}
  {"ok": false, "status": <int|0>, "code": <ERROR_CODE>, "message": <str>, "detail": <any?>}
`status` 0 + code SERVER_ERROR means the request never got an HTTP reply (connect/timeout).

This module is pure client plumbing. All state, invariants, atomicity, and refs/version
logic live in the U1 server; the client only calls, classifies, and reports.

Terminology: "normalize" here = Capsule Normalization (SPEC "compaction"), NOT Claude
Code context (transcript) compaction. This client never sends transcripts (SPEC 5).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

DEFAULT_URL = "http://127.0.0.1:8765"
DEFAULT_TIMEOUT_MS = 2000

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1", "[::1]"}


def base_url() -> str:
    return os.environ.get("JANSORI_URL", DEFAULT_URL).rstrip("/")


def default_timeout_ms() -> int:
    raw = os.environ.get("JANSORI_HOOK_TIMEOUT_MS", str(DEFAULT_TIMEOUT_MS))
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return DEFAULT_TIMEOUT_MS


def _assert_loopback(url: str) -> None:
    """BR-11.1: refuse to talk to a non-loopback address (client-side defense)."""
    host = urllib.parse.urlsplit(url).hostname or ""
    if host not in _LOOPBACK_HOSTS:
        raise ValueError(f"JANSORI_URL host must be loopback, got {host!r}")


def _ok(status: int, data) -> dict:
    return {"ok": True, "status": status, "data": data}


def _err(status: int, code: str, message: str, detail=None) -> dict:
    out = {"ok": False, "status": status, "code": code, "message": message}
    if detail is not None:
        out["detail"] = detail
    return out


def _parse_error_body(status: int, body: bytes) -> dict:
    """Map a non-2xx HTTP response to our standardized error dict (BR-08)."""
    try:
        parsed = json.loads(body.decode("utf-8"))
        env = parsed.get("error") if isinstance(parsed, dict) else None
        if isinstance(env, dict) and "code" in env:
            return _err(status, str(env.get("code")), str(env.get("message", "")), env.get("detail"))
    except (ValueError, AttributeError):
        pass
    # Unstructured non-2xx: classify by status. 404 -> SKILL_ABSENT, else SERVER_ERROR.
    code = "SKILL_ABSENT" if status == 404 else "SERVER_ERROR"
    return _err(status, code, f"HTTP {status}")


def request(method: str, path: str, *, params: dict | None = None,
            body: dict | None = None, timeout_ms: int | None = None) -> dict:
    """Perform one HTTP call and return the standardized dict. Never raises for
    network/HTTP errors — they become SERVER_ERROR/SKILL_ABSENT (fail-open friendly)."""
    url = base_url()
    _assert_loopback(url)
    if params:
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        path = f"{path}?{query}" if query else path
    full = f"{url}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(full, data=data, headers=headers, method=method)
    timeout_s = (timeout_ms if timeout_ms is not None else default_timeout_ms()) / 1000.0
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310 (loopback only)
            payload = resp.read()
            status = resp.status
            try:
                return _ok(status, json.loads(payload.decode("utf-8")) if payload else None)
            except ValueError:
                return _ok(status, {"raw": payload.decode("utf-8", "replace")})
    except urllib.error.HTTPError as e:  # non-2xx with a body
        return _parse_error_body(e.code, e.read() or b"")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        # connect refused / DNS / timeout — the request got no HTTP reply. NOT absence (I-07).
        return _err(0, "SERVER_ERROR", f"server unreachable: {e}")


# ----------------------------- actions -------------------------------------

def act_index(session_id: str | None, timeout_ms: int | None) -> dict:
    return request("GET", "/skills/index", params={"session_id": session_id}, timeout_ms=timeout_ms)


def act_get(skill_id: str, timeout_ms: int | None) -> dict:
    return request("GET", f"/skills/{urllib.parse.quote(skill_id)}", timeout_ms=timeout_ms)


def act_load(skill_id: str, session_id: str, timeout_ms: int | None) -> dict:
    return request("POST", f"/skills/{urllib.parse.quote(skill_id)}/load",
                   body={"session_id": session_id}, timeout_ms=timeout_ms)


def act_resolve_target(hint: str | None, session_id: str, timeout_ms: int | None) -> dict:
    return request("GET", "/skills/resolve-target",
                   params={"hint": hint, "session_id": session_id}, timeout_ms=timeout_ms)


def act_nag(skill_id: str, correction_text: str, request_id: str,
            base_version: int | None, timeout_ms: int | None) -> dict:
    # nag needs base_version (I-04). If not supplied, read current latest first.
    if base_version is None:
        current = act_get(skill_id, timeout_ms)
        if not current["ok"]:
            return current  # propagate SKILL_ABSENT / SERVER_ERROR unchanged (I-07)
        base_version = int(current["data"].get("version", 0))
    return request("POST", f"/skills/{urllib.parse.quote(skill_id)}/nag",
                   body={"correction_text": correction_text, "base_version": base_version,
                         "request_id": request_id}, timeout_ms=timeout_ms)


def act_register(skill_id: str, request_id: str, *, name: str, description: str, body: str,
                 refs_children: list[str], timeout_ms: int | None) -> dict:
    return request("POST", "/skills/register",
                   body={"skill_id": skill_id, "name": name, "description": description,
                         "body": body, "refs_children": refs_children, "request_id": request_id},
                   timeout_ms=timeout_ms)


def act_protected_change(skill_id: str, field: str, new_value, request_id: str,
                         approval_flag: bool, base_version: int | None,
                         timeout_ms: int | None) -> dict:
    if base_version is None:
        current = act_get(skill_id, timeout_ms)
        if not current["ok"]:
            return current
        base_version = int(current["data"].get("version", 0))
    return request("POST", f"/skills/{urllib.parse.quote(skill_id)}/protected-change",
                   body={"field": field, "new_value": new_value, "base_version": base_version,
                         "approval_flag": approval_flag, "request_id": request_id},
                   timeout_ms=timeout_ms)


def act_normalize(skill_id: str, base_version: int, new_body: str,
                  merged_correction_ids: "list[str]", request_id: str,
                  timeout_ms: int | None) -> dict:
    # Used by the U3 capsule-normalizer subagent to submit a merged (condensed/paraphrased)
    # body. Server validates preservation by the merged_correction_ids DECLARATION + length
    # (NOT verbatim substring), and removes only the declared corrections. STALE_BASE_VERSION
    # => caller restarts from latest (I-04). Loopback-only like all actions.
    return request("POST", f"/skills/{urllib.parse.quote(skill_id)}/normalize",
                   body={"base_version": base_version, "new_body": new_body,
                         "request_id": request_id,
                         "merged_correction_ids": list(merged_correction_ids)},
                   timeout_ms=timeout_ms)


# ----------------------------- CLI -----------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Jansori common client (U2 -> U1 loopback).")
    p.add_argument("--timeout-ms", type=int, default=None)
    p.add_argument("--request-id", default=None, help="reuse the SAME id on retry (I-05).")
    sub = p.add_subparsers(dest="action", required=True)

    s = sub.add_parser("index"); s.add_argument("--session", default=None)
    s = sub.add_parser("get"); s.add_argument("--id", required=True)
    s = sub.add_parser("load"); s.add_argument("--id", required=True); s.add_argument("--session", required=True)
    s = sub.add_parser("resolve-target"); s.add_argument("--hint", default=None); s.add_argument("--session", required=True)
    s = sub.add_parser("nag")
    s.add_argument("--id", required=True); s.add_argument("--text", required=True); s.add_argument("--base-version", type=int, default=None)
    s = sub.add_parser("register")
    s.add_argument("--id", required=True); s.add_argument("--name", default=""); s.add_argument("--description", default="")
    s.add_argument("--body", default=""); s.add_argument("--ref", action="append", default=[], dest="refs")
    s = sub.add_parser("protected-change")
    s.add_argument("--id", required=True); s.add_argument("--field", required=True); s.add_argument("--value", default=None)
    s.add_argument("--approve", action="store_true"); s.add_argument("--base-version", type=int, default=None)
    s = sub.add_parser("normalize")
    s.add_argument("--id", required=True); s.add_argument("--base-version", type=int, required=True)
    body_src = s.add_mutually_exclusive_group(required=True)
    body_src.add_argument("--new-body", default=None)
    body_src.add_argument("--new-body-stdin", action="store_true",
                          help="read new_body from stdin (for large/multiline merged bodies).")
    s.add_argument("--merged-id", action="append", default=[], dest="merged_ids", required=True,
                   help="a correction id merged into new_body; repeat for each (1+).")
    return p


def dispatch(args: argparse.Namespace) -> dict:
    rid = args.request_id or str(uuid.uuid4())
    t = args.timeout_ms
    if args.action == "index":
        return act_index(args.session, t)
    if args.action == "get":
        return act_get(args.id, t)
    if args.action == "load":
        return act_load(args.id, args.session, t)
    if args.action == "resolve-target":
        return act_resolve_target(args.hint, args.session, t)
    if args.action == "nag":
        return act_nag(args.id, args.text, rid, args.base_version, t)
    if args.action == "register":
        return act_register(args.id, rid, name=args.name, description=args.description,
                            body=args.body, refs_children=args.refs, timeout_ms=t)
    if args.action == "protected-change":
        return act_protected_change(args.id, args.field, args.value, rid, args.approve,
                                    args.base_version, t)
    if args.action == "normalize":
        new_body = sys.stdin.read() if getattr(args, "new_body_stdin", False) else args.new_body
        return act_normalize(args.id, args.base_version, new_body, args.merged_ids, rid, t)
    return _err(0, "VALIDATION_ERROR", f"unknown action {args.action!r}")


def _force_utf8_stdio() -> None:
    # Windows consoles default to a locale codec (e.g. cp949); capsule content can be
    # non-ASCII (Korean skill names/descriptions). Force UTF-8 so output never crashes.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdio()
    args = _build_parser().parse_args(argv)
    result = dispatch(args)
    print(json.dumps(result, ensure_ascii=False))
    # Exit 0 even on server errors: callers (model/hooks) decide, and hooks must fail-open.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
