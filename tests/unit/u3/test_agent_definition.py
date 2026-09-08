"""Structural validation of the capsule-normalizer subagent definition (STEP 3 artifact).

This checks the STATIC CONTRACT of the definition file (frontmatter validity + required
instruction content). It does NOT — and cannot — verify runtime behavior: that Claude Code
actually launches the subagent on `normalize_due`, or that the model's merge is good. Those
are host-runtime facts recorded as UNVERIFIED U4 residuals (F-04) in README-u3.
"""
import os

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
AGENT = os.path.join(ROOT, "plugin", "agents", "capsule-normalizer.md")


def _split_frontmatter(text):
    assert text.startswith("---"), "definition must start with YAML frontmatter"
    parts = text.split("---", 2)
    assert len(parts) == 3, "frontmatter must be delimited by two --- lines"
    return parts[1], parts[2]  # (frontmatter, body)


def test_definition_file_exists():
    assert os.path.isfile(AGENT), f"missing subagent definition: {AGENT}"


def test_frontmatter_is_valid_yaml_with_name_and_minimal_tools():
    yaml = pytest.importorskip("yaml")
    fm_text, _ = _split_frontmatter(open(AGENT, encoding="utf-8").read())
    fm = yaml.safe_load(fm_text)
    assert fm["name"] == "capsule-normalizer"
    assert "description" in fm and fm["description"].strip()
    # minimal tools (BR-U3-01): only Bash, needed to run the loopback client.
    assert str(fm.get("tools", "")).strip() == "Bash"


def test_body_encodes_isolation_and_terminology():
    _, body = _split_frontmatter(open(AGENT, encoding="utf-8").read())
    low = body.lower()
    # terminology non-conflation with Claude Code context compaction
    assert "context" in low and "compaction" in low
    # isolation: must forbid reading the conversation/transcript/prompts
    assert "transcript" in low
    assert "do not read" in low or "never read" in low or "do not read, request" in low


def test_body_encodes_id_declaration_and_bounds():
    _, body = _split_frontmatter(open(AGENT, encoding="utf-8").read())
    low = body.lower()
    assert "merged-id" in low or "merged_correction_ids" in low  # id declaration
    assert "normalize" in low and "base-version" in low          # submit contract
    assert "stale_base_version" in low                           # stale handling
    assert "at most 3 restarts" in low                           # restart bound (BR-U3-08)
    assert "at most 3 merge attempts" in low                     # merge bound (BR-U3-07)


def test_body_encodes_no_change_honesty_and_nonblocking():
    _, body = _split_frontmatter(open(AGENT, encoding="utf-8").read())
    low = body.lower()
    assert "unchanged" in low                       # no-change safety (I-11)
    assert "do not fabricate success" in low        # honesty (F-04)
    assert "block" in low                           # non-blocking (I-10)


def test_uses_bundled_client_not_ad_hoc_http():
    _, body = _split_frontmatter(open(AGENT, encoding="utf-8").read())
    assert "jansori_client.py" in body
    assert "${CLAUDE_PLUGIN_ROOT}" in body
