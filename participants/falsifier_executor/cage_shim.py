#!/usr/bin/env python3
"""cage_shim — runs IN THE CHILD, seals the process, then execs the target.

Independent implementation for the AIOS seam (spec/aios-seam-v0.md §3). Links
NONE of the aios_* code — the seam's whole test is that a foreign participant
can enforce the boundary from the kernel primitives and the written rule alone.

Sealing order (each step dies BEFORE exec on failure, so the target never runs
half-caged):
  1. rlimits            — CPU, address space, open files, file size, procs.
                          (The reference engine explicitly does NOT do this;
                          it is this implementation's own hardening, named
                          honestly in the receipt as part of the engine.)
  2. unshare(NEWUSER|NEWNET) — an EMPTY network namespace: no interfaces at
                          all, so every connect fails with ENETUNREACH. Needs
                          no capability, which is why it survives Ubuntu's
                          apparmor_restrict_unprivileged_userns=1.
  3. PR_SET_NO_NEW_PRIVS — required before Landlock; also blocks setuid escalation.
  4. Landlock ruleset   — filesystem allowlist; everything not allowlisted is
                          denied by the LSM (EACCES), and the restriction
                          survives execve so the target inherits the cage.
Exit 97 + "cage_shim:" marker on any setup failure.
"""
import ctypes
import json
import os
import resource
import stat
import sys

CLONE_NEWUSER = 0x10000000
CLONE_NEWNET = 0x40000000
PR_SET_NO_NEW_PRIVS = 38
SYS_landlock_create_ruleset = 444
SYS_landlock_add_rule = 445
SYS_landlock_restrict_self = 446
LANDLOCK_RULE_PATH_BENEATH = 1

libc = ctypes.CDLL(None, use_errno=True)
libc.syscall.restype = ctypes.c_long


def die(msg: str) -> None:
    sys.stderr.write("cage_shim: " + msg + "\n")
    sys.stderr.flush()
    os._exit(97)


class RulesetAttr(ctypes.Structure):
    _fields_ = [("handled_access_fs", ctypes.c_uint64),
                ("handled_access_net", ctypes.c_uint64),
                ("scoped", ctypes.c_uint64)]


class PathBeneath(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64),
                ("parent_fd", ctypes.c_int32)]


def set_rlimits(limits: dict) -> None:
    table = {
        "cpu": resource.RLIMIT_CPU, "as": resource.RLIMIT_AS,
        "nofile": resource.RLIMIT_NOFILE, "fsize": resource.RLIMIT_FSIZE,
        "nproc": resource.RLIMIT_NPROC,
    }
    for name, val in limits.items():
        r = table[name]
        try:
            resource.setrlimit(r, (val, val))
        except (ValueError, OSError) as exc:
            die(f"rlimit {name}={val} failed: {exc}")


def landlock_fs_allowlist(rules: list) -> None:
    abi = libc.syscall(SYS_landlock_create_ruleset, None, 0, 1)
    if abi < 1:
        die(f"landlock unavailable abi={abi} errno={ctypes.get_errno()}")
    fs_all = 0x1FFF if abi < 2 else (0x3FFF if abi < 3 else
                                     (0x7FFF if abi < 5 else 0xFFFF))
    file_ok = 0x7 | ((1 << 14) if abi >= 3 else 0) | ((1 << 15) if abi >= 5 else 0)
    read = (1 << 0) | (1 << 2) | (1 << 3)          # EXECUTE|READ_FILE|READ_DIR
    rwfile = (1 << 1) | (1 << 2)                    # WRITE_FILE|READ_FILE
    # size=8 => the kernel reads only handled_access_fs; network is handled by
    # the empty netns, so we do not declare handled_access_net here.
    attr = RulesetAttr(fs_all, 0, 0)
    rfd = libc.syscall(SYS_landlock_create_ruleset, ctypes.byref(attr), 8, 0)
    if rfd < 0:
        die(f"create_ruleset failed errno={ctypes.get_errno()}")
    for path, mode in rules:
        mask = fs_all if mode == "rw" else (rwfile if mode == "rwfile" else read)
        try:
            pfd = os.open(path, os.O_PATH | os.O_CLOEXEC)
        except OSError as exc:
            die(f"open rule path {path!r}: {exc}")
        if not stat.S_ISDIR(os.fstat(pfd).st_mode):
            mask &= file_ok
        rule = PathBeneath(mask, pfd)
        if libc.syscall(SYS_landlock_add_rule, rfd,
                        LANDLOCK_RULE_PATH_BENEATH, ctypes.byref(rule), 0) != 0:
            die(f"add_rule {path!r} errno={ctypes.get_errno()}")
        os.close(pfd)
    if libc.syscall(SYS_landlock_restrict_self, rfd, 0) != 0:
        die(f"restrict_self errno={ctypes.get_errno()}")
    os.close(rfd)


def main() -> None:
    spec = json.loads(sys.argv[1])
    set_rlimits(spec["rlimits"])
    if not spec["allow_net"]:
        if libc.unshare(CLONE_NEWUSER | CLONE_NEWNET) != 0:
            die(f"unshare(user+net) errno={ctypes.get_errno()}")
    if libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
        die(f"no_new_privs errno={ctypes.get_errno()}")
    landlock_fs_allowlist(spec["rules"])
    argv = spec["argv"]
    try:
        os.execvp(argv[0], argv)
    except OSError as exc:
        die(f"exec {argv[0]!r}: {exc}")


if __name__ == "__main__":
    main()
