#!/usr/bin/env python3
"""AIOS Sandbox — the OS-ENFORCED execution boundary (privacy: advisory → non-bypassable).

Why this exists: ``aios_egress_gate.egress_check`` is a Python function. A
compromised or prompt-injected agent can simply NOT CALL it, monkey-patch it,
or open a raw socket around it — "Python cannot secure Python". The 2026
threat evidence (Grok Build CLI bulk .env exfil 2026-07-12; GitLost
prompt-injected repo exfil 2026-07-06) defeated exactly this class of
in-process convention. This module moves enforcement to the OS: a sandboxed
process CANNOT open an off-box socket and CANNOT see the privacy-boundary
directories, no matter what its code says — the kernel refuses, not a check
the code could have skipped.

Composition with the egress gate (the two halves of "advisory → enforced"):

* ``aios_egress_gate``  decides + scrubs the PAYLOAD of a deliberate off-box
  send (denylist, PII scrub, taint grants, receipt).
* ``aios_sandbox``      enforces that code EXECUTION cannot exfiltrate AROUND
  that gate: no network by default, no view of the private dirs, no inherited
  environment (secret env vars never enter the sandbox).
* Rule of composition: anything a sandboxed run PRODUCES (stdout, files in
  rw_paths) is still on-box data — it must STILL pass ``egress_check`` before
  any off-box send. ``allow_net=True`` is the explicit opt-in for runs that
  legitimately need the network; their payloads go through the gate first.
* The privacy-path detector is shared: this module imports the gate's
  ``PRIVATE_PATH_PATTERNS`` (one canonical detector, not a second copy).

Enforcement engines (probed at runtime, strongest first; fail CLOSED):

1. ``bwrap``  — bubblewrap: ``--unshare-all`` (user/pid/ipc/uts/net
   namespaces), ``--disable-userns``, ``--die-with-parent``,
   ``--new-session``, ``--clearenv``, minimal ro binds for the interpreter,
   tmpfs elsewhere. Un-bound paths do not EXIST in the mount namespace
   (ENOENT). Preferred engine on stock kernels.
2. ``native`` — direct kernel enforcement, no helper binary:
   ``unshare(CLONE_NEWUSER|CLONE_NEWNET)`` puts the process in an EMPTY
   network namespace (no interfaces at all), and a Landlock LSM ruleset
   allowlists the filesystem (non-allowlisted paths → EACCES; with Landlock
   ABI ≥ 4 all TCP bind/connect is ALSO denied at the LSM layer — two
   independent kernel denials of the network). Unprivileged by design.
3. ``none``   — neither engine works: ``run_sandboxed`` REFUSES to execute
   (``sandboxed=False``, command NOT run). Untrusted code never runs
   unsandboxed — honest degradation is refusal, not silent fallback.

Measured on THIS box (2026-07-22): Ubuntu ships
``kernel.apparmor_restrict_unprivileged_userns=1`` with the
``unprivileged_userns`` apparmor profile (``audit deny capability``), which
NEUTERS unprivileged bwrap end-to-end — uid_map write (CAP_SETUID), loopback
setup (CAP_NET_ADMIN) and mount population (CAP_SYS_ADMIN) are all denied
inside the userns, for every flag combination, and nested namespaces stack
the same profile. "bwrap binary present" therefore does NOT mean "bwrap
works" — the probe runs it for real. The native engine is immune: living in
an empty netns needs no capability, and Landlock is not capability-gated
(verified live: Landlock ABI 7; unshare(user+net) rc=0; denied open →
EACCES/ENOENT; denied connect → EACCES).

The privacy boundary is structural in BOTH engines: the privacy dirs
(``_from_desktop/``, ``dain/``, ``minyoung/``, ``.env``/secrets, raw exports)
are never bound / never allowlisted, and ``bind_violation`` REFUSES any
attempt to bind them, a parent of them (which would expose them
transitively), or any path matching the gate's canonical privacy tokens —
before anything executes.

Supersedes the 2026-06-08 version of this file, whose ``--ro-bind / /``
design left the ENTIRE filesystem — privacy dirs included — readable inside
the sandbox, and which was in any case fail-closed-dead on this box (see the
apparmor finding above). The legacy surface (``SandboxUnavailable``,
``sandbox_self_test``, ``run_sandboxed(argv, workspace=...)``) is kept as a
thin shim for existing callers (aios_smx), now running on the new engines
with the tightened read posture.

What this does NOT stop (honest limitations — do not oversell):

* Exfiltration THROUGH THE CALLER: stdout/rw_paths return data to the
  calling agent; if the caller then sends it off-box ungated, the sandbox
  cannot help. The gate remains mandatory at every egress point.
* ``allow_net=True`` is a binary switch, not a firewall: an opted-in run has
  the full host network. Payload control stays with the egress gate.
* Kernel 0-days / LSM bypass bugs; side channels (timing); /proc kernel info
  (bwrap mounts a namespaced /proc; native denies /proc reads outright).
* Resource exhaustion beyond the timeout: no CPU/RSS rlimits or cgroup caps
  in v1 (bwrap's tmpfs is size-capped; the timeout kill is the backstop).
  cgroup v2 + a seccomp filter (libseccomp is present) are the v2 hardening.
* The native engine has no PID-namespace isolation and no private /tmp mount
  (it uses a fresh 0700 per-run directory instead); bwrap has both.
* DAC still applies inside: the sandboxed uid is the caller's uid. The
  sandbox only ever REMOVES access relative to DAC; binding a broad
  directory read-only exposes whatever it contains — bind narrowly.

Audit: every decision (refusal AND execution) appends one JSONL receipt via
``aios_egress_gate.append_receipt`` — hashes/lengths/reasons only, NEVER raw
command text or output (command lines and stdout routinely contain exactly
the material the privacy boundary protects). If the receipt log cannot be
opened for append, the run is REFUSED before exec (unaudited execution is
not allowed — DNA #4). ``now`` is caller-supplied (the CLI passes
``time.time()``); the library never reads the wall clock for decisions.

Stdlib-only. Schema: aios.sandbox.v1 / aios.sandbox_receipt.v1.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import aios_egress_gate as egress_gate  # noqa: E402 — canonical privacy detector + receipt appender

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT_LOG = ROOT / ".aios" / "sandbox_receipts.jsonl"

SANDBOX_SCHEMA = "aios.sandbox.v1"
RECEIPT_SCHEMA = "aios.sandbox_receipt.v1"

# Privacy-boundary roots (DNA invariant 7) relative to the workspace root —
# refused as binds in BOTH directions (a bind inside them, or a bind of any
# ancestor that would expose them transitively). Token-level matches for
# .env / secrets / raw exports come from the gate's PRIVATE_PATH_PATTERNS.
PRIVACY_ROOTS: tuple[Path, ...] = tuple(
    ROOT.parent / name for name in ("_from_desktop", "dain", "minyoung"))

WORKDIR = "/sandbox/work"  # cwd inside the bwrap engine

# The ONLY environment a sandboxed process sees (--clearenv / env=): the host
# environment — which routinely carries API keys — is never inherited.
_SANDBOX_ENV: dict[str, str] = {
    "PATH": "/usr/local/bin:/usr/bin:/bin",
    "HOME": "/sandbox/home",
    "TMPDIR": "/tmp",
    "LANG": "C.UTF-8",
    "PYTHONDONTWRITEBYTECODE": "1",
}

# /etc pieces exposed only when the caller explicitly opts into the network.
_NET_ETC: tuple[str, ...] = (
    "/etc/resolv.conf", "/etc/hosts", "/etc/nsswitch.conf",
    "/etc/ssl", "/etc/ca-certificates", "/etc/pki",
)

_SHIM_MARK = "aios-sandbox-shim:"
_PROBE: dict[str, bool] = {}  # process-lifetime engine probe cache


class SandboxUnavailable(RuntimeError):
    """Legacy-compat exception (2026-06-08 API): OS isolation cannot be
    established — the caller must refuse to run. The new API expresses the
    same fail-closed outcome as ``SandboxResult(sandboxed=False)``."""


@dataclasses.dataclass(frozen=True)
class SandboxResult:
    """Outcome of one sandboxed run.

    ok         — sandboxed execution happened, exit 0, no timeout.
    returncode — child exit code; None when nothing was executed (refusal).
    sandboxed  — True only if the command actually ran under OS enforcement.
                 False means the command did NOT run enforced — and with this
                 module it then did not run AT ALL (fail closed).
    engine     — "bwrap" | "native" | "none" (what enforced the run; "none"
                 when nothing executed).
    """
    ok: bool
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    sandboxed: bool
    reason: str
    engine: str = "none"


# ---------------------------------------------------------------------------
# Privacy guard — refuse forbidden binds BEFORE anything executes
# ---------------------------------------------------------------------------

def bind_violation(path: str | Path) -> str | None:
    """Reason this path must NOT be bound into a sandbox, or None if clean.

    Checks, in order: the gate's canonical privacy tokens against both the
    raw and the symlink-resolved path (a symlink into dain/ does not slip
    through); containment inside a privacy root; ancestry OVER a privacy
    root (binding /home/user would expose dain/ transitively — bind
    narrower); existence (a nonexistent bind is refused loudly, not silently
    skipped). Privacy checks run before the existence check on purpose: the
    guard never needs the private dirs to exist, and never opens them.
    """
    raw = str(path)
    if not raw.strip():
        return "empty bind path"
    resolved = Path(raw).expanduser().resolve()
    for cand in {raw, str(resolved)}:
        for scope, klass, rx in egress_gate.PRIVATE_PATH_PATTERNS:
            if rx.search(cand):
                return (f"bind path matches privacy boundary "
                        f"(scope: {scope}, class: {klass})")
    for priv in PRIVACY_ROOTS:
        if resolved.is_relative_to(priv):
            return f"bind path inside privacy boundary ({priv.name})"
        if priv.is_relative_to(resolved):
            return (f"bind path is an ancestor of privacy boundary "
                    f"({priv.name}) — bind narrower paths")
    if not resolved.exists():
        return f"bind path does not exist: {resolved}"
    return None


# ---------------------------------------------------------------------------
# Engine 1 — bubblewrap
# ---------------------------------------------------------------------------

def bwrap_path() -> str | None:
    return shutil.which("bwrap")


def _bwrap_flags(allow_net: bool, ro_paths: tuple[str, ...],
                 rw_paths: tuple[str, ...], workdir: str = WORKDIR) -> list[str]:
    """The enforcement IS these flags — the kernel applies them, the payload
    cannot opt out. Order matters: the /tmp tmpfs precedes caller binds so a
    caller rw bind under /tmp lands on top of the fresh tmpfs."""
    flags = [
        "--unshare-all",        # user+pid+ipc+uts+net(+cgroup) namespaces
        "--unshare-user",       # explicit, so --disable-userns is accepted
        "--disable-userns",     # no NESTED user namespaces inside the sandbox
        "--die-with-parent",
        "--new-session",        # detach from the controlling terminal
        "--clearenv",           # host env (API keys!) never crosses
    ]
    for key, val in _SANDBOX_ENV.items():
        flags += ["--setenv", key, val]
    if allow_net:
        flags += ["--share-net"]  # explicit opt-in; payloads still gate-checked
    flags += [
        "--proc", "/proc",       # namespaced procfs (own PID ns only)
        "--dev", "/dev",         # minimal devtmpfs (null/zero/random/urandom/tty)
        "--size", "268435456", "--tmpfs", "/tmp",
        "--dir", "/sandbox/home", "--dir", WORKDIR,
    ]
    # Interpreter closure, read-only. Merged-usr symlinks are recreated as
    # symlinks; real directories are ro-bound.
    flags += ["--ro-bind", "/usr", "/usr"]
    for top in ("/bin", "/sbin", "/lib", "/lib32", "/lib64"):
        if os.path.islink(top):
            flags += ["--symlink", os.readlink(top), top]
        elif os.path.isdir(top):
            flags += ["--ro-bind", top, top]
    for etc in ("/etc/ld.so.cache", "/etc/alternatives"):
        flags += ["--ro-bind-try", etc, etc]
    if allow_net:
        for etc in _NET_ETC:
            flags += ["--ro-bind-try", etc, etc]
    # Caller binds LAST (already privacy-guarded), identity-mapped.
    for p in ro_paths:
        rp = str(Path(p).resolve())
        flags += ["--ro-bind", rp, rp]
    for p in rw_paths:
        rp = str(Path(p).resolve())
        flags += ["--bind", rp, rp]
    flags += ["--chdir", workdir]
    return flags


def _probe_bwrap() -> bool:
    """Does bwrap WORK here (not merely exist)? Runs /bin/true under the real
    flag set. On Ubuntu with apparmor_restrict_unprivileged_userns=1 the
    binary exists but every setup step is capability-denied — presence alone
    would be a lie."""
    if "bwrap" in _PROBE:
        return _PROBE["bwrap"]
    bw = bwrap_path()
    works = False
    if bw is not None:
        try:
            rc, _, _, timed_out = _run_capture(
                [bw, *_bwrap_flags(False, (), ()), "--", "/bin/true"],
                stdin_text="", timeout=10.0)
            works = (rc == 0 and not timed_out)
        except (OSError, ValueError):
            works = False
    _PROBE["bwrap"] = works
    return works


# ---------------------------------------------------------------------------
# Engine 2 — native kernel enforcement (unshare netns + Landlock LSM)
# ---------------------------------------------------------------------------

# The shim runs IN THE CHILD before exec: it seals the process with
# unshare(user+net) and a Landlock ruleset, then execs the target. Landlock
# survives execve (under no_new_privs), so the target inherits the cage and
# cannot shed it. Any setup failure dies BEFORE exec (exit 97 + marker) —
# the target never runs half-caged. Plain %-formatting only; runs on the
# system python3.
_SHIM_SRC = r'''
import ctypes, json, os, stat, sys
spec = json.loads(sys.argv[1])
libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long

def die(msg):
    sys.stderr.write("aios-sandbox-shim: " + msg + "\n")
    sys.stderr.flush()
    os._exit(97)

if not spec["allow_net"]:
    # Empty network namespace: no interfaces at all (loopback stays down).
    # Needs no capability — which is why this works even where apparmor
    # denies every capability inside unprivileged userns.
    if libc.unshare(0x10000000 | 0x40000000) != 0:  # CLONE_NEWUSER|CLONE_NEWNET
        die("unshare(user+net) failed errno=%d" % ctypes.get_errno())

if libc.prctl(38, 1, 0, 0, 0) != 0:                 # PR_SET_NO_NEW_PRIVS
    die("prctl(no_new_privs) failed errno=%d" % ctypes.get_errno())

SYS_CREATE, SYS_ADD, SYS_RESTRICT = 444, 445, 446
abi = libc.syscall(SYS_CREATE, None, 0, 1)          # LANDLOCK_CREATE_RULESET_VERSION
if abi < 1:
    die("landlock unavailable abi=%d errno=%d" % (abi, ctypes.get_errno()))

FS_ALL = 0x1FFF if abi < 2 else (0x3FFF if abi < 3 else (0x7FFF if abi < 5 else 0xFFFF))
FILE_OK = 0x7 | ((1 << 14) if abi >= 3 else 0) | ((1 << 15) if abi >= 5 else 0)
READ = (1 << 0) | (1 << 2) | (1 << 3)               # EXECUTE|READ_FILE|READ_DIR
RWFILE = (1 << 1) | (1 << 2)                        # WRITE_FILE|READ_FILE

class RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64),
                ("handled_access_net", ctypes.c_uint64),
                ("scoped", ctypes.c_uint64)]

class PathBeneath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]

net_handled = 0 if spec["allow_net"] else (0x3 if abi >= 4 else 0)  # BIND|CONNECT_TCP
scoped = 0x3 if abi >= 6 else 0                     # abstract-unix sockets + signals
attr = RulesetAttr(FS_ALL, net_handled, scoped)
size = 8 if abi < 4 else (16 if abi < 6 else 24)
rfd = libc.syscall(SYS_CREATE, ctypes.byref(attr), size, 0)
if rfd < 0:
    die("landlock_create_ruleset failed errno=%d" % ctypes.get_errno())

for path, mode in spec["rules"]:
    mask = FS_ALL if mode == "rw" else (RWFILE if mode == "rwfile" else READ)
    try:
        pfd = os.open(path, os.O_PATH | os.O_CLOEXEC)
    except OSError as exc:
        die("open rule path %r failed: %s" % (path, exc))
    if not stat.S_ISDIR(os.fstat(pfd).st_mode):
        mask &= FILE_OK                             # dir-only rights are EINVAL on files
    rule = PathBeneath(mask, pfd)
    if libc.syscall(SYS_ADD, rfd, 1, ctypes.byref(rule), 0) != 0:  # ..._RULE_PATH_BENEATH
        die("landlock_add_rule %r failed errno=%d" % (path, ctypes.get_errno()))
    os.close(pfd)

if libc.syscall(SYS_RESTRICT, rfd, 0) != 0:
    die("landlock_restrict_self failed errno=%d" % ctypes.get_errno())
os.close(rfd)

argv = spec["argv"]
try:
    os.execvp(argv[0], argv)
except OSError as exc:
    die("exec %r failed: %s" % (argv[0], exc))
'''


def _shim_python() -> str:
    return "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable


def _native_rules(allow_net: bool, ro_paths: tuple[str, ...],
                  rw_paths: tuple[str, ...], sandbox_dir: str) -> list[list[str]]:
    """Landlock allowlist: interpreter closure ro, standard /dev nodes as
    read/write FILES only, caller paths, and the per-run scratch dir rw.
    Everything else on the filesystem is DENIED by the kernel."""
    rules: list[list[str]] = [["/usr", "ro"]]
    for etc in ("/etc/ld.so.cache", "/etc/alternatives"):
        if os.path.exists(etc):
            rules.append([etc, "ro"])
    for dev in ("/dev/null", "/dev/zero", "/dev/full", "/dev/random", "/dev/urandom"):
        if os.path.exists(dev):
            rules.append([dev, "rwfile"])
    if allow_net:
        for etc in _NET_ETC:
            if os.path.exists(etc):
                rules.append([etc, "ro"])
    for p in ro_paths:
        rules.append([str(Path(p).resolve()), "ro"])
    for p in rw_paths:
        rules.append([str(Path(p).resolve()), "rw"])
    rules.append([sandbox_dir, "rw"])
    return rules


def _native_run(argv: list[str], *, allow_net: bool, ro_paths: tuple[str, ...],
                rw_paths: tuple[str, ...], stdin_text: str, timeout: float,
                workdir: str | None = None) -> tuple[int, str, str, bool, bool]:
    """Returns (returncode, stdout, stderr, timed_out, setup_failed)."""
    sandbox_dir = tempfile.mkdtemp(prefix="aios-sbx-")   # 0700 by mkdtemp
    try:
        home = os.path.join(sandbox_dir, "home")
        tmpd = os.path.join(sandbox_dir, "tmp")
        work = os.path.join(sandbox_dir, "work")
        for d in (home, tmpd, work):
            os.mkdir(d)
        spec = {"allow_net": allow_net, "argv": list(argv),
                "rules": _native_rules(allow_net, ro_paths, rw_paths, sandbox_dir)}
        env = dict(_SANDBOX_ENV)
        env["HOME"] = home
        env["TMPDIR"] = tmpd
        rc, out, err, timed_out = _run_capture(
            [_shim_python(), "-c", _SHIM_SRC, json.dumps(spec)],
            stdin_text=stdin_text, timeout=timeout, env=env,
            cwd=workdir or work)
        setup_failed = (rc == 97 and err.lstrip().startswith(_SHIM_MARK))
        return rc, out, err, timed_out, setup_failed
    finally:
        shutil.rmtree(sandbox_dir, ignore_errors=True)


def _probe_native() -> bool:
    if "native" in _PROBE:
        return _PROBE["native"]
    try:
        rc, _, _, timed_out, setup_failed = _native_run(
            ["/bin/true"], allow_net=False, ro_paths=(), rw_paths=(),
            stdin_text="", timeout=10.0)
        works = (rc == 0 and not timed_out and not setup_failed)
    except (OSError, ValueError):
        works = False
    _PROBE["native"] = works
    return works


# ---------------------------------------------------------------------------
# Shared runner + engine selection
# ---------------------------------------------------------------------------

def _run_capture(cmd: list[str], *, stdin_text: str, timeout: float,
                 env: dict[str, str] | None = None,
                 cwd: str | None = None) -> tuple[int, str, str, bool]:
    """Popen in its own session; on timeout SIGKILL the whole process group
    (bwrap additionally --die-with-parent's its child)."""
    proc = subprocess.Popen(
        cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, errors="replace",
        env=env, cwd=cwd, start_new_session=True)
    try:
        out, err = proc.communicate(stdin_text, timeout=timeout)
        return proc.returncode, out or "", err or "", False
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        try:
            out, err = proc.communicate(timeout=5)
        except (subprocess.TimeoutExpired, ValueError):
            out, err = "", ""
        rc = proc.returncode if proc.returncode is not None else -9
        return rc, out or "", err or "", True


def pick_engine() -> str:
    """Strongest working engine, or "none" (=> refuse to execute). The
    AIOS_SANDBOX_ENGINE env var can force auto|bwrap|native|none; a forced
    engine that does not work degrades to "none", NEVER silently to the
    other engine — a forced choice is a policy, not a preference."""
    forced = os.environ.get("AIOS_SANDBOX_ENGINE", "auto").strip().lower()
    if forced == "none":
        return "none"
    if forced == "bwrap":
        return "bwrap" if _probe_bwrap() else "none"
    if forced == "native":
        return "native" if _probe_native() else "none"
    if _probe_bwrap():
        return "bwrap"
    if _probe_native():
        return "native"
    return "none"


def _landlock_abi() -> int:
    try:
        import ctypes  # noqa: PLC0415 — diagnostics only
        libc = ctypes.CDLL(None, use_errno=True)
        libc.syscall.restype = ctypes.c_long
        return int(libc.syscall(444, None, 0, 1))
    except Exception:  # noqa: BLE001 — diagnostics must never raise
        return -1


def engine_status() -> dict:
    """Probe + report what actually enforces on this box (CLI: selftest)."""
    return {
        "schema": SANDBOX_SCHEMA,
        "bwrap_path": bwrap_path(),
        "bwrap_works": _probe_bwrap(),
        "landlock_abi": _landlock_abi(),
        "native_works": _probe_native(),
        "forced": os.environ.get("AIOS_SANDBOX_ENGINE", "auto"),
        "engine": pick_engine(),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _hash16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _receipt(result: SandboxResult, *, now: float | None, allow_net: bool,
             argv: list[str], ro_paths: tuple[str, ...],
             rw_paths: tuple[str, ...], duration_s: float) -> dict:
    argv0 = argv[0] if argv else ""
    if any(rx.search(argv0) for _, _, rx in egress_gate.PRIVATE_PATH_PATTERNS):
        argv0 = "[redacted-argv0]"
    return {
        "schema": RECEIPT_SCHEMA,
        "ts": now,
        "engine": result.engine,
        "argv0": argv0,
        "argv_sha256_16": _hash16(json.dumps(argv, ensure_ascii=False)),
        "argv_items": len(argv),
        "allow_net": allow_net,
        "ro_paths": [str(p) for p in ro_paths],
        "rw_paths": [str(p) for p in rw_paths],
        "ok": result.ok,
        "sandboxed": result.sandboxed,
        "returncode": result.returncode,
        "timed_out": result.timed_out,
        "duration_s": round(duration_s, 3),
        "stdout_len": len(result.stdout), "stdout_sha256_16": _hash16(result.stdout),
        "stderr_len": len(result.stderr), "stderr_sha256_16": _hash16(result.stderr),
        "reason": result.reason,
    }


def run_sandboxed(argv: list[str], *, allow_net: bool = False,
                  ro_paths=(), rw_paths=(), stdin_text: str = "",
                  timeout: float = 30.0, now: float | None = None,
                  receipt_log: Path | str | None = DEFAULT_RECEIPT_LOG,
                  _workdir: str | None = None, **legacy) -> SandboxResult:
    """Execute ``argv`` under OS enforcement. THE fail-closed invariant: if
    this returns ``sandboxed=False``, the command DID NOT RUN.

    allow_net   — False (default): the process cannot open any off-box
                  socket (kernel-denied). True: explicit opt-in; the payload
                  of any send still belongs to the egress gate.
    ro_paths    — extra host paths visible read-only (identity-mapped).
    rw_paths    — the ONLY writable host paths.
    stdin_text  — piped to the child's stdin.
    timeout     — seconds; on expiry the whole process group is SIGKILLed.
    now         — caller-supplied timestamp for the audit receipt (the
                  library never reads the clock for decisions).
    receipt_log — append-only JSONL audit line per decision; None skips.
                  If the log cannot be opened, the run is REFUSED.
    _workdir    — internal (legacy shim): cwd inside the sandbox; must be a
                  guarded rw path. Default: an ephemeral sandbox workdir.

    Legacy (2026-06-08) keyword ``workspace=`` switches to the old contract:
    tuple return, ``SandboxUnavailable`` on refusal — see
    ``_legacy_run_sandboxed``.
    """
    if legacy:
        if "workspace" not in legacy:
            raise TypeError(f"unexpected keyword arguments: {sorted(legacy)}")
        return _legacy_run_sandboxed(list(argv), timeout=timeout, **legacy)

    argv = [str(a) for a in argv]
    ro_paths = tuple(str(p) for p in ro_paths)
    rw_paths = tuple(str(p) for p in rw_paths)
    t0 = time.monotonic()

    def finish(result: SandboxResult) -> SandboxResult:
        if receipt_log is None:
            return result
        try:
            egress_gate.append_receipt(
                _receipt(result, now=now, allow_net=allow_net, argv=argv,
                         ro_paths=ro_paths, rw_paths=rw_paths,
                         duration_s=time.monotonic() - t0),
                receipt_log)
        except OSError as exc:
            result = dataclasses.replace(
                result, reason=result.reason +
                f" [receipt append failed: {exc.__class__.__name__}]")
        return result

    def refused(reason: str) -> SandboxResult:
        return finish(SandboxResult(ok=False, returncode=None, stdout="",
                                    stderr="", timed_out=False,
                                    sandboxed=False, reason=reason,
                                    engine="none"))

    if not argv:
        return refused("refused: empty argv")
    if timeout <= 0:
        return refused("refused: timeout must be > 0")
    for p in (*ro_paths, *rw_paths, *((_workdir,) if _workdir else ())):
        violation = bind_violation(p)
        if violation is not None:
            return refused(f"refused: {violation}")

    engine = pick_engine()
    if engine == "none":
        return refused(
            "refused: no working sandbox engine (bwrap "
            f"{'present but non-functional' if bwrap_path() else 'absent'}, "
            f"landlock abi {_landlock_abi()}) — untrusted code never runs "
            "unsandboxed (fail closed)")

    if receipt_log is not None:
        try:
            path = Path(receipt_log)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8"):
                pass  # pre-flight: unauditable execution is refused up front
        except OSError as exc:
            return refused(f"refused: sandbox receipt log unwritable "
                           f"({exc.__class__.__name__}) — unaudited execution "
                           "is not allowed (fail closed)")

    net_note = "net=allowed" if allow_net else "net=denied"
    try:
        if engine == "bwrap":
            cmd = [bwrap_path(),
                   *_bwrap_flags(allow_net, ro_paths, rw_paths,
                                 workdir=_workdir or WORKDIR),
                   "--", *argv]
            rc, out, err, timed_out = _run_capture(
                cmd, stdin_text=stdin_text, timeout=timeout)
            setup_failed = (not timed_out and rc != 0
                            and err.lstrip().startswith("bwrap:"))
        else:
            rc, out, err, timed_out, setup_failed = _native_run(
                argv, allow_net=allow_net, ro_paths=ro_paths,
                rw_paths=rw_paths, stdin_text=stdin_text, timeout=timeout,
                workdir=_workdir)
    except (OSError, ValueError) as exc:
        return refused(f"refused: sandbox launch failed ({exc})")

    if setup_failed:
        first = (err.strip().splitlines() or ["(no detail)"])[0]
        return finish(SandboxResult(
            ok=False, returncode=rc, stdout=out, stderr=err, timed_out=False,
            sandboxed=False, engine=engine,
            reason=f"sandbox setup failed via {engine} — command did not run "
                   f"(fail closed): {first[:160]}"))

    if timed_out:
        return finish(SandboxResult(
            ok=False, returncode=rc, stdout=out, stderr=err, timed_out=True,
            sandboxed=True, engine=engine,
            reason=f"timed out after {timeout}s — process group killed "
                   f"(via {engine}, {net_note})"))

    detail = f"via {engine} ({net_note}, ro={len(ro_paths)}, rw={len(rw_paths)})"
    if rc == 0:
        return finish(SandboxResult(
            ok=True, returncode=0, stdout=out, stderr=err, timed_out=False,
            sandboxed=True, engine=engine, reason=f"ok: exit 0 {detail}"))
    return finish(SandboxResult(
        ok=False, returncode=rc, stdout=out, stderr=err, timed_out=False,
        sandboxed=True, engine=engine,
        reason=f"command failed: exit {rc} {detail}"))


_LANG_INTERP = {"python": ("python3", ".py"), "bash": ("bash", ".sh"),
                "sh": ("sh", ".sh")}


def run_untrusted_code(code: str, lang: str = "python", **kw) -> SandboxResult:
    """Convenience: write ``code`` to a file in a fresh 0700 rw tmpdir and
    run it sandboxed with NO NETWORK — the default posture for code whose
    intent is unverified (LLM-generated, web-sourced, peer-sent).

    ``allow_net`` is deliberately NOT accepted here: untrusted code never
    gets the network through the convenience path. A caller who has decided
    (and gate-audited) that a run needs the network must say so explicitly
    via ``run_sandboxed(argv, allow_net=True, ...)``.
    """
    if "allow_net" in kw:
        raise ValueError(
            "run_untrusted_code never allows the network; use run_sandboxed "
            "explicitly (with an egress_check-audited payload) if a run "
            "genuinely needs it")
    if lang not in _LANG_INTERP:
        raise ValueError(f"unsupported lang {lang!r} "
                         f"(supported: {', '.join(sorted(_LANG_INTERP))})")
    interp, suffix = _LANG_INTERP[lang]
    tmpdir = tempfile.mkdtemp(prefix="aios-untrusted-")  # 0700 by mkdtemp
    try:
        code_file = os.path.join(tmpdir, "code" + suffix)
        with open(code_file, "w", encoding="utf-8") as fh:
            fh.write(code)
        rw_paths = (tmpdir, *tuple(kw.pop("rw_paths", ())))
        return run_sandboxed([interp, code_file], allow_net=False,
                             rw_paths=rw_paths, **kw)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Legacy compat (2026-06-08 API) — kept for aios_smx; new code uses the
# SandboxResult API above.
# ---------------------------------------------------------------------------

def _legacy_run_sandboxed(argv: list[str], *, workspace, allow_network=False,
                          allow_write=None, timeout: float = 30.0,
                          bwrap_bin=None, which=None) -> tuple[int, str, str]:
    """Old contract: (returncode, stdout, stderr), SandboxUnavailable on any
    refusal, 124 on timeout. Now runs on the new engines with the tightened
    read posture (interpreter closure + workspace, NOT the whole root — the
    old ``--ro-bind / /`` exposed the privacy dirs and is the very design
    this module supersedes)."""
    if bwrap_bin is not None or which is not None:
        raise SandboxUnavailable(
            "legacy bwrap_bin/which knobs were superseded 2026-07-22 — "
            "engine probing is internal now (see engine_status())")
    ws = str(Path(str(workspace)).expanduser().resolve())
    rw = (ws, *(str(Path(str(p)).resolve()) for p in (allow_write or [])))
    result = run_sandboxed(argv, allow_net=bool(allow_network), rw_paths=rw,
                           timeout=float(timeout), _workdir=ws)
    if result.timed_out:
        return 124, result.stdout, f"timeout after {timeout}s"
    if not result.sandboxed:
        raise SandboxUnavailable(result.reason)
    return int(result.returncode), result.stdout, result.stderr


def sandbox_self_test(which=None) -> dict:  # noqa: ARG001 — legacy signature
    """Legacy probe shape ({"isolated": bool, "reason": str}); the ``which``
    parameter is accepted and ignored (bwrap is no longer the only engine)."""
    status = engine_status()
    isolated = status["engine"] != "none"
    return {"isolated": isolated,
            "reason": "ok" if isolated else
            f"no working engine (bwrap_works={status['bwrap_works']}, "
            f"landlock_abi={status['landlock_abi']})",
            "engine": status["engine"]}


# ---------------------------------------------------------------------------
# CLI — the impure edge: supplies the real clock
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AIOS sandbox — OS-enforced execution (no net, no "
                    "privacy dirs, fail closed)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run", help="run a command sandboxed")
    run.add_argument("--allow-net", action="store_true",
                     help="explicit network opt-in (payloads still go "
                          "through the egress gate)")
    run.add_argument("--ro", action="append", default=[],
                     help="host path visible read-only; repeatable")
    run.add_argument("--rw", action="append", default=[],
                     help="host path writable; repeatable")
    run.add_argument("--timeout", type=float, default=30.0)
    run.add_argument("--stdin-text", default="")
    run.add_argument("--receipt-log", default=str(DEFAULT_RECEIPT_LOG))
    run.add_argument("command", nargs=argparse.REMAINDER,
                     help="command to run (prefix with -- )")
    sub.add_parser("selftest",
                   help="probe which enforcement engine works here")
    args = parser.parse_args(argv)

    if args.cmd == "selftest":
        status = engine_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return 0 if status["engine"] != "none" else 2

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        parser.error("no command given (use: run [flags] -- cmd args...)")
    result = run_sandboxed(command, allow_net=args.allow_net,
                           ro_paths=tuple(args.ro), rw_paths=tuple(args.rw),
                           stdin_text=args.stdin_text, timeout=args.timeout,
                           now=time.time(), receipt_log=args.receipt_log)
    print(json.dumps({
        "schema": SANDBOX_SCHEMA, "engine": result.engine, "ok": result.ok,
        "sandboxed": result.sandboxed, "returncode": result.returncode,
        "timed_out": result.timed_out, "reason": result.reason,
        "stdout": result.stdout, "stderr": result.stderr,
    }, ensure_ascii=False, indent=2))
    return 0 if result.ok else 2


if __name__ == "__main__":
    sys.exit(main())
