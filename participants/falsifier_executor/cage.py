#!/usr/bin/env python3
"""cage — orchestrates cage_shim and produces the attempt-and-refused evidence
that spec §3 requires. Foreign implementation: imports NOTHING from aios_*.

engine name (recorded in the sandbox receipt, a mechanism not an intention):
    "userns-netns+landlock+rlimits"
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHIM = str(HERE / "cage_shim.py")
ENGINE = "userns-netns+landlock+rlimits"

DEFAULT_RLIMITS = {"cpu": 10, "as": 512 * 1024 * 1024, "nofile": 64,
                   "fsize": 16 * 1024 * 1024, "nproc": 64}
SANDBOX_ENV = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8",
               "PYTHONDONTWRITEBYTECODE": "1"}


@dataclass
class CageResult:
    ran: bool           # did the target execute under the cage?
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool
    engine: str
    reason: str


def _fs_rules(scratch: str, ro_paths: tuple[str, ...]) -> list:
    rules = [["/usr", "ro"]]
    for etc in ("/etc/ld.so.cache", "/etc/alternatives"):
        if os.path.exists(etc):
            rules.append([etc, "ro"])
    for dev in ("/dev/null", "/dev/zero", "/dev/urandom", "/dev/random"):
        if os.path.exists(dev):
            rules.append([dev, "rwfile"])
    for p in ro_paths:
        rules.append([str(Path(p).resolve()), "ro"])
    rules.append([scratch, "rw"])
    return rules


def run_in_cage(argv: list[str], *, ro_paths: tuple[str, ...] = (),
                stdin_text: str = "", timeout: float = 15.0,
                allow_net: bool = False, env_extra: dict | None = None
                ) -> CageResult:
    scratch = tempfile.mkdtemp(prefix="fe-cage-")     # 0700
    try:
        spec = {"argv": [str(a) for a in argv], "allow_net": allow_net,
                "rlimits": DEFAULT_RLIMITS,
                "rules": _fs_rules(scratch, ro_paths)}
        env = dict(SANDBOX_ENV)
        env["HOME"] = scratch
        env["TMPDIR"] = scratch
        if env_extra:
            env.update(env_extra)
        proc = subprocess.Popen(
            ["/usr/bin/python3", SHIM, json.dumps(spec)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, errors="replace",
            env=env, cwd=scratch, start_new_session=True)
        try:
            out, err = proc.communicate(stdin_text, timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                proc.kill()
            out, err = proc.communicate()
            timed_out = True
        rc = proc.returncode
        setup_failed = (rc == 97 and err.lstrip().startswith("cage_shim:"))
        if setup_failed:
            first = (err.strip().splitlines() or ["(no detail)"])[0]
            return CageResult(False, rc, out, err, False, ENGINE,
                              f"cage setup failed — target did not run: {first}")
        if timed_out:
            return CageResult(True, rc, out, err, True, ENGINE,
                              f"timed out after {timeout}s (killed)")
        return CageResult(True, rc, out, err, False, ENGINE,
                          f"ran under {ENGINE}, exit {rc}")
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


# --------------------------------------------------------------------------
# Attempt-and-refused probes (spec §3: a "denied" claim MUST be backed by an
# actual attempt that observed refusal). Both use a POSITIVE CONTROL so the
# denial is attributed to the CAGE, not to an already-offline host.
# --------------------------------------------------------------------------

def _loopback_listener() -> tuple[socket.socket, int]:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(8)
    port = srv.getsockname()[1]

    def serve():
        srv.settimeout(20)
        try:
            while True:
                c, _ = srv.accept()
                c.close()
        except OSError:
            pass
    threading.Thread(target=serve, daemon=True).start()
    return srv, port


_PROBE_SRC = (
    "import socket,sys\n"
    "s=socket.socket(socket.AF_INET,socket.SOCK_STREAM); s.settimeout(3)\n"
    "try:\n"
    "    s.connect(('127.0.0.1', {port})); s.close(); print('OPEN')\n"
    "except OSError as e:\n"
    "    print('REFUSED', e.errno)\n")


def network_probe() -> dict:
    """Positive control: a host loopback listener that an UNCAGED child reaches
    (OPEN) and a CAGED child cannot (REFUSED). 'denied' is asserted only when
    control=OPEN and cage=REFUSED — otherwise the environment, not the cage,
    is doing the blocking and we say so."""
    srv, port = _loopback_listener()
    try:
        code = _PROBE_SRC.format(port=port)
        control = subprocess.run(["/usr/bin/python3", "-c", code],
                                 capture_output=True, text=True, timeout=15)
        control_out = control.stdout.strip()
        caged = run_in_cage(["/usr/bin/python3", "-c", code], timeout=15)
        cage_out = caged.stdout.strip()
    finally:
        srv.close()
    control_open = control_out.startswith("OPEN")
    cage_refused = cage_out.startswith("REFUSED")
    denied = control_open and cage_refused
    return {
        "network": "denied" if denied else "inconclusive",
        "control_uncaged": control_out,          # expect OPEN
        "cage_result": cage_out,                 # expect REFUSED <errno>
        "attributable_to_cage": denied,
        "note": ("positive control: uncaged child reached the loopback "
                 "listener, caged child was refused — denial is the cage's"),
    }


def path_denial_probe(paths: list[str]) -> dict:
    """For each path: an UNCAGED read of a decoy file succeeds, the CAGED read
    of the same path is refused (EACCES/ENOENT). Uses a decoy file we create
    outside the allowlist — never a real privacy-boundary file (we never open
    those; the probe proves the cage would refuse them)."""
    results = []
    for p in paths:
        code = (f"import sys\n"
                f"try:\n"
                f"    open({p!r},'rb').read(1); print('READ')\n"
                f"except OSError as e:\n"
                f"    print('DENIED', e.errno)\n")
        control = subprocess.run(["/usr/bin/python3", "-c", code],
                                 capture_output=True, text=True, timeout=10)
        caged = run_in_cage(["/usr/bin/python3", "-c", code], timeout=10)
        results.append({
            "path": p,
            "control_uncaged": control.stdout.strip(),
            "cage_result": caged.stdout.strip(),
            "denied_by_cage": (control.stdout.strip().startswith("READ")
                               and caged.stdout.strip().startswith("DENIED")),
        })
    return {"paths_denied": [r["path"] for r in results if r["denied_by_cage"]],
            "probes": results}


if __name__ == "__main__":
    import sys
    print(json.dumps({"engine": ENGINE, "network": network_probe()},
                     indent=1))
    # decoy path denial demo
    decoy = tempfile.NamedTemporaryFile(prefix="fe-decoy-", delete=False)
    decoy.write(b"secret-decoy-byte")
    decoy.close()
    print(json.dumps(path_denial_probe([decoy.name]), indent=1))
    os.unlink(decoy.name)
    sys.exit(0)
