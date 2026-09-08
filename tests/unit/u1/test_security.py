"""U1 security unit tests: loopback bind, path containment, script no-auto-exec (SPEC 5)."""
from __future__ import annotations

import pytest

from server.domain.errors import ValidationError
from server.security import guard


def test_assert_loopback_accepts_127_and_localhost_and_ipv6():
    guard.assert_loopback("127.0.0.1")
    guard.assert_loopback("localhost")
    guard.assert_loopback("::1")
    guard.assert_loopback("[::1]")


def test_assert_loopback_rejects_routable():
    for host in ("0.0.0.0", "192.168.1.10", "10.0.0.1", "example.com"):
        with pytest.raises(ValidationError):
            guard.assert_loopback(host)


def test_contain_path_blocks_traversal(tmp_path):
    with pytest.raises(ValidationError):
        guard.contain_path(tmp_path, "../escape.txt")
    with pytest.raises(ValidationError):
        guard.contain_path(tmp_path, "../../etc/passwd")


def test_contain_path_allows_inside(tmp_path):
    result = guard.contain_path(tmp_path, "sub/ok.txt")
    assert str(result).startswith(str(tmp_path.resolve()))


def test_guard_script_returns_notice_and_never_executes():
    notice = guard.guard_script("run.sh", is_script=True)
    assert notice is not None
    assert notice.requires_consent is True
    assert guard.guard_script("data.md", is_script=False) is None
