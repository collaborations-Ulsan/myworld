"""Security-critical tests for scripts/aios_sandbox.py — enforcement, not mocks.

Where a real OS engine works (bwrap on stock kernels; unshare-netns + Landlock
on apparmor-restricted ones like this box), these tests ACTUALLY attempt the
exfiltration/escape and assert the KERNEL blocked it:

1. network egress denied by default (socket connect fails);
2. privacy-boundary / un-bound paths unreadable even on explicit open
   (ENOENT under bwrap's mount namespace, EACCES under Landlock);
3. explicit ro binds readable, explicit rw binds writable (and ro NOT
   writable);
4. timeout kills the whole sandboxed process group;
5. no working engine => fail CLOSED: sandboxed=False and the command is
   NEVER executed unsandboxed;
6. stdout/stderr/returncode/stdin captured faithfully.

Plus: the privacy bind-guard refuses forbidden binds BEFORE exec, host env
never leaks in, run_untrusted_code has no network path, receipts store
hashes only, and the legacy (2026-06-08) aios_smx surface still works.
Where no engine works, enforcement tests skip with the concrete reason —
never a silent pass — and the fail-closed + guard tests still run.
"""
from __future__ import annotations

import json
import socket
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_sandbox as sb  # noqa: E402

STATUS = sb.engine_status()
ENGINE = STATUS["engine"]
needs_engine = pytest.mark.skipif(
    ENGINE == "none",
    reason=f"no working sandbox engine on this box — enforcement unprovable here: {STATUS}")

# Path strings only — the private dirs are never opened, listed, or created.
PRIVACY_PROBE_PATH = str(sb.PRIVACY_ROOTS[1] / "x")   # .../dain/x
NOW = 1_800_000_000.0


def run(argv, **kw):
    kw.setdefault("receipt_log", None)   # tests never write the repo audit log
    return sb.run_sandboxed(argv, **kw)


# ---------------------------------------------------------------------------
# 1 — network egress denied by default (OS-enforced, not advisory)
# ---------------------------------------------------------------------------

@needs_engine
def test_network_denied_by_default():
    code = (
        "import socket\n"
        "s = socket.socket(); s.settimeout(5)\n"
        "try:\n"
        "    s.connect(('1.1.1.1', 80)); print('CONNECTED')\n"
        "except OSError as e:\n"
        "    print('BLOCKED errno', e.errno); raise SystemExit(42)\n"
    )
    r = run(["python3", "-c", code], timeout=30)
    assert r.sandboxed is True
    assert r.returncode == 42, (r.stdout, r.stderr)
    assert "BLOCKED" in r.stdout
    assert "CONNECTED" not in r.stdout


@needs_engine
def test_allow_net_is_differential():
    """Hermetic differential proof: a host-localhost listener is unreachable
    from the default sandbox but reachable with allow_net=True — the deny is
    the sandbox, not a broken network."""
    with socket.socket() as srv:
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]
        code = (
            "import socket\n"
            "s = socket.socket(); s.settimeout(5)\n"
            f"s.connect(('127.0.0.1', {port})); print('REACHED')\n"
        )
        denied = run(["python3", "-c", code], timeout=30)
        assert denied.returncode != 0
        assert "REACHED" not in denied.stdout
        allowed = run(["python3", "-c", code], allow_net=True, timeout=30)
        assert allowed.ok, (allowed.reason, allowed.stderr)
        assert "REACHED" in allowed.stdout


# ---------------------------------------------------------------------------
# 2 — privacy-boundary / un-bound paths are INVISIBLE, even on explicit read
# ---------------------------------------------------------------------------

@needs_engine
def test_privacy_path_unreadable_even_explicitly():
    code = (
        f"paths = [{PRIVACY_PROBE_PATH!r}, '/etc/hostname']\n"
        "denied = 0\n"
        "for p in paths:\n"
        "    try:\n"
        "        open(p); print('OPENED', p)\n"
        "    except OSError as e:\n"
        "        denied += 1; print('DENIED', type(e).__name__, e.errno)\n"
        "raise SystemExit(43 if denied == len(paths) else 1)\n"
    )
    r = run(["python3", "-c", code], timeout=30)
    assert r.sandboxed is True
    assert r.returncode == 43, (r.stdout, r.stderr)
    assert "OPENED" not in r.stdout
    # ENOENT (bwrap mount ns) or EACCES (Landlock) both mean: not visible.
    assert "DENIED" in r.stdout


@needs_engine
def test_workspace_root_not_listable():
    code = (
        "import os\n"
        "try:\n"
        f"    os.listdir({str(sb.ROOT.parent)!r}); print('LISTED')\n"
        "except OSError as e:\n"
        "    print('DENIED', e.errno); raise SystemExit(44)\n"
    )
    r = run(["python3", "-c", code], timeout=30)
    assert r.returncode == 44, (r.stdout, r.stderr)
    assert "LISTED" not in r.stdout


# ---------------------------------------------------------------------------
# 2b — the bind-guard refuses forbidden binds BEFORE anything executes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    str(sb.PRIVACY_ROOTS[0]),                # _from_desktop
    str(sb.PRIVACY_ROOTS[1]),                # dain
    str(sb.PRIVACY_ROOTS[2] / "photos"),     # inside minyoung
    str(sb.ROOT.parent),                     # ancestor of all privacy roots
    "/home",                                 # broader ancestor
    "/somewhere/project/.env",               # secret-class token
    "/data/secrets/api.json",                # secrets path segment
])
def test_privacy_bind_refused_pre_exec(tmp_path, bad):
    sentinel = tmp_path / "executed.txt"
    for kwargs in ({"ro_paths": (bad,)}, {"rw_paths": (bad,)}):
        r = run(["touch", str(sentinel)], **kwargs)
        assert r.ok is False
        assert r.sandboxed is False
        assert r.returncode is None          # nothing executed
        assert r.engine == "none"
        assert "refused" in r.reason and (
            "privacy" in r.reason or "boundary" in r.reason)
    assert not sentinel.exists()             # command truly never ran


def test_symlink_into_privacy_dir_refused(tmp_path):
    link = tmp_path / "innocent-name"
    link.symlink_to(sb.PRIVACY_ROOTS[1])     # points into dain/ (never opened)
    r = run(["true"], ro_paths=(str(link),))
    assert r.sandboxed is False and r.returncode is None
    assert "privacy" in r.reason or "boundary" in r.reason


def test_nonexistent_bind_refused(tmp_path):
    r = run(["true"], ro_paths=(str(tmp_path / "missing"),))
    assert r.sandboxed is False and r.returncode is None
    assert "does not exist" in r.reason


# ---------------------------------------------------------------------------
# 3 — explicit ro binds readable; explicit rw binds writable; ro not writable
# ---------------------------------------------------------------------------

@needs_engine
def test_ro_bind_readable_and_rw_bind_writable(tmp_path):
    ro_dir = tmp_path / "ro_src"
    rw_dir = tmp_path / "rw_dst"
    ro_dir.mkdir()
    rw_dir.mkdir()
    (ro_dir / "data.txt").write_text("ro-bind-content-7391", encoding="utf-8")
    code = (
        f"print(open({str(ro_dir / 'data.txt')!r}).read().strip())\n"
        f"open({str(rw_dir / 'out.txt')!r}, 'w').write('rw-bind-write-7392')\n"
    )
    r = run(["python3", "-c", code],
            ro_paths=(str(ro_dir),), rw_paths=(str(rw_dir),), timeout=30)
    assert r.ok, (r.reason, r.stderr)
    assert "ro-bind-content-7391" in r.stdout
    # the write is visible ON THE HOST afterwards — a real bind, not a copy
    assert (rw_dir / "out.txt").read_text(encoding="utf-8") == "rw-bind-write-7392"


@needs_engine
def test_ro_bind_not_writable(tmp_path):
    ro_dir = tmp_path / "ro_only"
    ro_dir.mkdir()
    code = (
        "try:\n"
        f"    open({str(ro_dir / 'x.txt')!r}, 'w'); print('WROTE')\n"
        "except OSError as e:\n"
        "    print('DENIED', e.errno); raise SystemExit(45)\n"
    )
    r = run(["python3", "-c", code], ro_paths=(str(ro_dir),), timeout=30)
    assert r.returncode == 45, (r.stdout, r.stderr)
    assert "WROTE" not in r.stdout
    assert not (ro_dir / "x.txt").exists()


# ---------------------------------------------------------------------------
# 4 — timeout kills the sandboxed process group
# ---------------------------------------------------------------------------

@needs_engine
def test_timeout_kills_sleep():
    t0 = time.monotonic()
    r = run(["sleep", "999"], timeout=1.5)
    elapsed = time.monotonic() - t0
    assert r.timed_out is True
    assert r.ok is False
    assert r.sandboxed is True
    assert elapsed < 20, f"kill took {elapsed:.1f}s"


# ---------------------------------------------------------------------------
# 5 — no engine => fail CLOSED (command NEVER executed unsandboxed)
# ---------------------------------------------------------------------------

def test_no_engine_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(sb, "_probe_bwrap", lambda: False)
    monkeypatch.setattr(sb, "_probe_native", lambda: False)
    sentinel = tmp_path / "must_not_exist.txt"
    r = run(["touch", str(sentinel)])
    assert r.sandboxed is False
    assert r.ok is False
    assert r.returncode is None
    assert r.engine == "none"
    assert "fail closed" in r.reason
    assert not sentinel.exists()             # the whole point


def test_forced_engine_none_env(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOS_SANDBOX_ENGINE", "none")
    sentinel = tmp_path / "forced_none.txt"
    r = run(["touch", str(sentinel)])
    assert r.sandboxed is False and r.returncode is None
    assert not sentinel.exists()


@pytest.mark.skipif(not STATUS["native_works"],
                    reason="native engine unavailable — ladder test needs it")
def test_engine_ladder_bwrap_absent_falls_to_native(monkeypatch):
    monkeypatch.setattr(sb, "bwrap_path", lambda: None)
    monkeypatch.setattr(sb, "_PROBE", {})    # fresh probe cache
    assert sb.pick_engine() == "native"


# ---------------------------------------------------------------------------
# 6 — faithful capture: stdout / stderr / returncode / stdin
# ---------------------------------------------------------------------------

@needs_engine
def test_capture_stdout_stderr_returncode():
    code = ("import sys\n"
            "sys.stdout.write('out-marker-91')\n"
            "sys.stderr.write('err-marker-92')\n"
            "sys.exit(7)\n")
    r = run(["python3", "-c", code], timeout=30)
    assert r.sandboxed is True
    assert r.returncode == 7
    assert r.ok is False                      # nonzero exit is not ok
    assert "out-marker-91" in r.stdout
    assert "err-marker-92" in r.stderr

    ok = run(["echo", "plain-echo-93"])
    assert ok.ok and ok.returncode == 0
    assert "plain-echo-93" in ok.stdout


@needs_engine
def test_stdin_piped():
    r = run(["cat"], stdin_text="stdin-marker-94")
    assert r.ok
    assert r.stdout == "stdin-marker-94"


@needs_engine
def test_host_env_never_inherited(monkeypatch):
    monkeypatch.setenv("AIOS_SBX_CANARY", "canary-value-123")
    r = run(["python3", "-c",
             "import os; print(os.environ.get('AIOS_SBX_CANARY', 'ABSENT'))"])
    assert r.ok
    assert r.stdout.strip() == "ABSENT"
    assert "canary-value-123" not in r.stdout


# ---------------------------------------------------------------------------
# run_untrusted_code — no-net convenience over the same enforcement
# ---------------------------------------------------------------------------

@needs_engine
def test_untrusted_code_runs_and_computes():
    r = sb.run_untrusted_code("print(6 * 7)", receipt_log=None)
    assert r.ok, (r.reason, r.stderr)
    assert r.stdout.strip() == "42"


@needs_engine
def test_untrusted_code_cannot_reach_network():
    code = (
        "import socket\n"
        "s = socket.socket(); s.settimeout(5)\n"
        "try:\n"
        "    s.connect(('1.1.1.1', 80)); print('CONNECTED')\n"
        "except OSError as e:\n"
        "    print('BLOCKED', e.errno); raise SystemExit(42)\n"
    )
    r = sb.run_untrusted_code(code, receipt_log=None)
    assert r.returncode == 42
    assert "CONNECTED" not in r.stdout


@needs_engine
def test_untrusted_code_bash_lang():
    r = sb.run_untrusted_code("echo bash-ok-95", lang="bash", receipt_log=None)
    assert r.ok and "bash-ok-95" in r.stdout


def test_untrusted_code_rejects_allow_net():
    with pytest.raises(ValueError, match="never allows the network"):
        sb.run_untrusted_code("print(1)", allow_net=True)
    with pytest.raises(ValueError, match="unsupported lang"):
        sb.run_untrusted_code("print(1)", lang="ruby")


# ---------------------------------------------------------------------------
# Receipts — append-only audit, hashes/lengths only, never raw content
# ---------------------------------------------------------------------------

@needs_engine
def test_receipt_written_without_raw_content(tmp_path):
    log = tmp_path / "receipts.jsonl"
    r = sb.run_sandboxed(["echo", "receipt-probe-string-96"],
                         receipt_log=log, now=NOW)
    assert r.ok
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["schema"] == sb.RECEIPT_SCHEMA
    assert obj["ts"] == NOW
    assert obj["engine"] in ("bwrap", "native")
    assert obj["ok"] is True and obj["returncode"] == 0
    # argv text and stdout are NEVER stored raw — hashes/lengths only
    assert "receipt-probe-string-96" not in log.read_text(encoding="utf-8")
    assert obj["stdout_len"] == len(r.stdout)


def test_refusal_also_writes_receipt(tmp_path):
    log = tmp_path / "receipts.jsonl"
    r = sb.run_sandboxed(["true"], ro_paths=(str(sb.PRIVACY_ROOTS[1]),),
                         receipt_log=log, now=NOW)
    assert r.sandboxed is False
    obj = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    assert obj["sandboxed"] is False and obj["returncode"] is None
    assert "refused" in obj["reason"]


# ---------------------------------------------------------------------------
# bwrap policy encoding — correct even where bwrap cannot execute here
# ---------------------------------------------------------------------------

def test_bwrap_flags_encode_the_policy():
    flags = sb._bwrap_flags(False, (), ())
    for required in ("--unshare-all", "--disable-userns", "--die-with-parent",
                     "--new-session", "--clearenv", "--proc", "--tmpfs"):
        assert required in flags
    assert "--share-net" not in flags        # default: no network
    net_flags = sb._bwrap_flags(True, (), ())
    assert "--share-net" in net_flags        # explicit opt-in only
    # no privacy token ever appears in the constructed command
    joined = " ".join(flags)
    for scope, _klass, rx in sb.egress_gate.PRIVATE_PATH_PATTERNS:
        assert not rx.search(joined), f"privacy token {scope} in bwrap flags"


def test_tmpfs_precedes_caller_binds(tmp_path):
    d = tmp_path / "under_tmp"
    d.mkdir()
    flags = sb._bwrap_flags(False, (), (str(d),))
    assert flags.index("--tmpfs") < flags.index("--bind"), \
        "caller binds must land ON TOP of the /tmp tmpfs"


# ---------------------------------------------------------------------------
# Legacy (2026-06-08) surface — aios_smx keeps working
# ---------------------------------------------------------------------------

def test_legacy_self_test_shape():
    st = sb.sandbox_self_test()
    assert isinstance(st.get("isolated"), bool)
    assert st["isolated"] == (ENGINE != "none")


@needs_engine
def test_legacy_workspace_call(tmp_path):
    code, out, err = sb.run_sandboxed(["sh", "-c", "echo legacy-ok-97 > f.txt && cat f.txt"],
                                      workspace=str(tmp_path))
    assert code == 0, err
    assert "legacy-ok-97" in out
    assert (tmp_path / "f.txt").read_text(encoding="utf-8").strip() == "legacy-ok-97"


def test_legacy_privacy_workspace_refused():
    with pytest.raises(sb.SandboxUnavailable):
        sb.run_sandboxed(["true"], workspace=str(sb.PRIVACY_ROOTS[1]))


def test_legacy_missing_workspace_refused(tmp_path):
    with pytest.raises(sb.SandboxUnavailable):
        sb.run_sandboxed(["true"], workspace=str(tmp_path / "nope"))


def test_legacy_no_engine_raises(monkeypatch, tmp_path):
    monkeypatch.setattr(sb, "_probe_bwrap", lambda: False)
    monkeypatch.setattr(sb, "_probe_native", lambda: False)
    with pytest.raises(sb.SandboxUnavailable):
        sb.run_sandboxed(["sh", "-c", "echo x"], workspace=str(tmp_path))
