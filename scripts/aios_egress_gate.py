#!/usr/bin/env python3
"""AIOS Egress Gate — the single enforced choke-point for every off-box send.

Today the privacy boundary (DNA invariant 7: ``_from_desktop/``, ``dain/``,
``minyoung/``, secrets, ``.env``, raw exports) is a prompt-level convention —
exactly the layer the 2026 threat evidence proves worthless (Grok Build CLI
bulk-uploading whole repos 2026-07-12; GitLost prompt-injected repo exfil
2026-07-06 — transport exfiltrates regardless of instructions). This module is
the enforcement point: Sovereign Coordination Stack Pillar 2, "EGRESS GATE
(build — THE keystone)" — see docs/AIOS_SOVEREIGN_COORDINATION_STACK_2026-07-22.md.

It generalizes the network-address denylist pattern of ``aios_tools.py``
(``_WEB_BLOCKED_HOSTS`` guarding web.fetch/web.scrape) from ADDRESS-space
("never talk TO private addresses") to DATA-space ("never send private DATA
anywhere"). Every off-box byte — provider prompt, dispatch packet, web POST,
peer message — is meant to pass through ``egress_check`` first.

Four layers, in order (each appends findings; the decision aggregates):

1. Path/secret denylist (HARD)  — privacy-boundary path references in the
   payload, the destination, or any source; plus secret VALUE patterns
   (API keys, bearer tokens, AKIA AWS keys, PEM private-key blocks, sk-…).
2. PII scrub (redact)           — emails, phone numbers, credit-card-like digit
   runs (Luhn-annotated), a configurable literal token denylist; pluggable
   backend: stdlib-regex floor that ALWAYS runs + optional GLiNER2 hook,
   imported lazily and degraded honestly ("pii_backend": "gliner2" means
   GLiNER ran ON TOP of the regex floor; "regex-fallback" means floor only).
3. Taint/provenance (CaMeL-style) — data whose sources are private-tainted
   cannot cross without an explicit ``Grant`` matching that exact scope, bound
   to this exact destination (audience), and unexpired at caller-supplied
   ``now``.
4. Append-only egress receipt   — every decision (allow AND block) appends one
   JSONL line (default ``.aios/egress_receipts.jsonl``) carrying hashes and
   summaries only — NEVER raw private content. If the receipt cannot be
   written, the gate FAILS CLOSED (no unaudited egress).

Grant policy — two deny classes, deliberately asymmetric:

* private-class (``_from_desktop``, ``dain``, ``minyoung``, ``raw_exports``):
  the sovereign owner's own data — MAY cross with an explicit matching Grant
  (that is the entire point of grants: deliberate, audited sharing).
* secret-class (``.env``/``secrets`` path refs + every secret VALUE pattern):
  NEVER crosses. No grant can authorize a secret ("never scrub-and-send
  secrets" — there is no legitimate egress for credential material).

Purity: ``evaluate()`` is pure and deterministic — no clock, no filesystem, no
network; timestamps/now are passed IN by the caller (the CLI supplies
``time.time()`` at the edge). The one optional impure path is the lazy GLiNER2
hook (model load); with GLiNER absent or ``pii_backend="regex"`` the function
is referentially transparent. ``egress_check()`` = ``evaluate()`` + the single
receipt append.

This module only MATCHES the privacy-boundary directory NAMES as deny tokens;
it never reads or touches the private directories themselves.

Stdlib-only core (GLiNER2 optional). Schema: aios.egress_gate.v1 /
aios.egress_receipt.v1.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECEIPT_LOG = ROOT / ".aios" / "egress_receipts.jsonl"

GATE_SCHEMA = "aios.egress_gate.v1"
RECEIPT_SCHEMA = "aios.egress_receipt.v1"

# ---------------------------------------------------------------------------
# Layer 1 — path/secret denylist
# ---------------------------------------------------------------------------

# Privacy-boundary path tokens (DNA invariant 7), generalized from the scattered
# per-script denylists (aios_address.PRIVATE_PATH_RE, aios_capture_args
# _PRIVATE_MARKERS, aios_tools fs-scope guards) into ONE canonical detector.
# klass drives the grant policy: "private" is grant-able, "secret" never is.
#   scope           klass      detector
PRIVATE_PATH_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    # unique token — plain substring is safe (no English word contains it)
    ("_from_desktop", "private", re.compile(r"_from_desktop", re.IGNORECASE)),
    # word-delimited so "disdain"/"dainty"/"mundane prose" never trip the gate
    ("dain", "private", re.compile(r"(?<![A-Za-z0-9])dain(?![A-Za-z0-9])", re.IGNORECASE)),
    ("minyoung", "private", re.compile(r"(?<![A-Za-z0-9])minyoung(?![A-Za-z0-9])", re.IGNORECASE)),
    ("raw_exports", "private", re.compile(r"(?<![A-Za-z0-9])raw[_-]exports?(?![A-Za-z0-9])", re.IGNORECASE)),
    # .env / .env.local / v2.env — the literal dot delimits; "environment" never matches
    (".env", "secret", re.compile(r"\.env(?:\.[A-Za-z0-9_-]+)?(?![A-Za-z0-9])", re.IGNORECASE)),
    # secrets as a PATH SEGMENT only (".aios/secrets/", "secrets/api.json");
    # the bare English word "secrets" in prose is NOT a path hit — actual
    # secret VALUES are what SECRET_VALUE_PATTERNS below catches.
    ("secrets", "secret", re.compile(
        r"(?:(?<![A-Za-z0-9])secrets?[/\\]|[/\\]secrets?(?![A-Za-z0-9]))", re.IGNORECASE)),
)

# Secret VALUE patterns (payload + destination). Superset style of
# aios_capture_args._SECRET_VALUE_RE, kept as named patterns so findings and
# receipts can say WHICH kind fired without ever quoting the match.
SECRET_VALUE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key_block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
    # AWS access key id: AKIA + 16 uppercase alphanumerics
    ("aws_access_key", re.compile(r"(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![A-Za-z0-9])")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{16,}=*")),
    # sk-… provider keys; require >=8 chars incl. a digit so "sk-learn" never matches
    ("sk_token", re.compile(r"(?<![A-Za-z0-9])sk-(?=[A-Za-z0-9_-]*\d)[A-Za-z0-9_-]{8,}(?![A-Za-z0-9_-])")),
    ("jwt_token", re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("generic_api_key", re.compile(
        r"(?i)\b(?:api[_-]?key|apikey|access[_-]?token|auth[_-]?token|client[_-]?secret"
        r"|secret[_-]?key|password|passwd)\b\s*[:=]\s*[\"']?[A-Za-z0-9_\-./+]{8,}[\"']?")),
)

# ---------------------------------------------------------------------------
# Layer 2 — PII scrub
# ---------------------------------------------------------------------------

PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    # separator-required phone shapes (010-1234-5678, +82 10 1234 5678,
    # (02) 312-4567) — plain digit runs / dates / IPs do not match
    ("phone", re.compile(
        r"(?<![0-9A-Za-z])(?:\+\d{1,3}[\s.-]?)?(?:\(\d{2,4}\)|\d{2,4})[\s.-]\d{3,4}[\s.-]\d{4}(?![0-9])")),
    # 13–16 digit card-shaped runs in 4-groups; Luhn result annotated in the
    # finding but redaction is unconditional (false-positive redaction is
    # cheap, a leaked PAN is not)
    ("credit_card", re.compile(r"(?<![0-9])(?:\d{4}[ -]?){3}\d{1,4}(?![0-9])")),
)

# Entity labels asked of the optional GLiNER2 backend.
DEFAULT_GLINER_LABELS: tuple[str, ...] = (
    "person name", "physical address", "phone number", "email address",
    "national id number", "credit card number", "date of birth",
)

# Hub id for the optional GLiNER2 model. UNVERIFIED offline — override with
# AIOS_GLINER_MODEL. A wrong id simply degrades to the regex floor (and the
# decision says so honestly via pii_backend="regex-fallback").
DEFAULT_GLINER_MODEL = "fastino/gliner2-base"

_GLINER_STATE: dict[str, object] = {}  # process-lifetime model cache


def _hash16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d = d * 2 - 9 if d * 2 > 9 else d * 2
        total += d
    return total % 10 == 0


def _normalize_gliner(raw: object, text: str) -> list[tuple[int, int, str, str]]:
    """Normalize whatever entity shape the backend returned into spans.

    Tolerates: list[dict] with start/end/label, list[dict] with text/label,
    or {"entities": [...]}. Anything unrecognizable contributes nothing.
    """
    if isinstance(raw, dict):
        raw = raw.get("entities", [])
    spans: list[tuple[int, int, str, str]] = []
    if not isinstance(raw, (list, tuple)):
        return spans
    for ent in raw:
        if not isinstance(ent, dict):
            continue
        label = str(ent.get("label") or ent.get("type") or "entity")
        start, end = ent.get("start"), ent.get("end")
        if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(text):
            spans.append((start, end, f"gliner:{label}", text[start:end]))
            continue
        ent_text = ent.get("text")
        if isinstance(ent_text, str) and ent_text:
            pos = text.find(ent_text)
            while pos != -1:
                spans.append((pos, pos + len(ent_text), f"gliner:{label}", ent_text))
                pos = text.find(ent_text, pos + len(ent_text))
    return spans


def _gliner_spans(text: str) -> list[tuple[int, int, str, str]] | None:
    """Best-effort GLiNER2 pass. Returns None whenever the backend is
    unavailable in ANY way (not installed, model load fails, API mismatch) —
    the caller then reports pii_backend="regex-fallback" honestly."""
    try:
        import gliner2  # noqa: PLC0415 — optional dep, lazy on purpose
    except Exception:  # noqa: BLE001 — absence in any form degrades to regex
        return None
    try:
        model = _GLINER_STATE.get("model")
        if model is None:
            cls = getattr(gliner2, "GLiNER2", None)
            if cls is None or not hasattr(cls, "from_pretrained"):
                return None
            model_id = os.environ.get("AIOS_GLINER_MODEL", DEFAULT_GLINER_MODEL)
            model = cls.from_pretrained(model_id)
            _GLINER_STATE["model"] = model
        extract = getattr(model, "extract_entities", None) or getattr(model, "predict_entities", None)
        if extract is None:
            return None
        return _normalize_gliner(extract(text, list(DEFAULT_GLINER_LABELS)), text)
    except Exception:  # noqa: BLE001 — a broken model must never block the floor
        return None


def _scrub_pii(payload: str, redact_tokens: tuple[str, ...],
               pii_backend: str) -> tuple[str, list[dict], str]:
    """Redact PII from payload. Returns (scrubbed, findings, backend_used).

    The regex floor always runs; GLiNER2 (pii_backend="auto") adds spans on
    top when available. Deterministic given a fixed backend outcome.
    """
    spans: list[tuple[int, int, str, str]] = []
    extras: dict[tuple[int, int, str], dict] = {}
    for kind, rx in PII_PATTERNS:
        for m in rx.finditer(payload):
            spans.append((m.start(), m.end(), kind, m.group(0)))
            if kind == "credit_card":
                extras[(m.start(), m.end(), kind)] = {
                    "luhn_valid": _luhn_ok(re.sub(r"[^0-9]", "", m.group(0)))}
    for tok in redact_tokens:
        if not tok:
            continue
        for m in re.finditer(re.escape(tok), payload):
            spans.append((m.start(), m.end(), "token", m.group(0)))

    backend = "regex-fallback"
    if pii_backend == "auto":
        gl = _gliner_spans(payload)
        if gl is not None:
            backend = "gliner2"
            spans.extend(gl)

    # merge: earliest-start wins, overlapping later spans dropped
    spans.sort(key=lambda s: (s[0], -(s[1])))
    merged: list[tuple[int, int, str, str]] = []
    last_end = -1
    for start, end, kind, text in spans:
        if start >= last_end:
            merged.append((start, end, kind, text))
            last_end = end

    findings: list[dict] = []
    pieces: list[str] = []
    cursor = 0
    for start, end, kind, text in merged:
        pieces.append(payload[cursor:start])
        pieces.append(f"[REDACTED:{kind}]")
        cursor = end
        finding = {"layer": "pii", "kind": kind, "where": "payload",
                   "start": start, "end": end, "sha256_16": _hash16(text)}
        finding.update(extras.get((start, end, kind), {}))
        findings.append(finding)
    pieces.append(payload[cursor:])
    return "".join(pieces), findings, backend


# ---------------------------------------------------------------------------
# Layer 3 — taint/provenance grants
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class Grant:
    """Explicit authorization for private-scoped data to cross to ONE audience.

    scope       — exact private scope(s) covered ("dain", "raw_exports", or an
                  explicit taint label like "memory/graph/node-77")
    audience    — the exact destination this grant is bound to (RFC 8707 spirit)
    expires_at  — absolute unix timestamp; compared against caller-supplied
                  ``now`` (the gate never reads the clock itself). A grant that
                  carries an expiry but is checked without ``now`` is treated
                  as unverifiable and therefore INVALID (fail closed).
    note        — free-text audit note, echoed into the receipt.
    """
    scope: str | tuple[str, ...]
    audience: str
    expires_at: float | None = None
    note: str = ""

    def scopes(self) -> frozenset[str]:
        if isinstance(self.scope, str):
            return frozenset({self.scope})
        return frozenset(self.scope)


def _grant_covers(grant: Grant | None, needed: set[str], destination: str,
                  now: float | None) -> tuple[bool, str]:
    if grant is None:
        return False, "no grant supplied"
    missing = needed - grant.scopes()
    if missing:
        return False, f"grant scope mismatch (uncovered: {', '.join(sorted(missing))})"
    if grant.audience != destination:
        return False, "grant audience mismatch"
    if grant.expires_at is not None:
        if now is None:
            return False, "grant carries expiry but caller supplied no `now` (unverifiable => invalid)"
        if now >= grant.expires_at:
            return False, "grant expired"
    return True, "grant valid for all needed scopes"


# ---------------------------------------------------------------------------
# Decision core
# ---------------------------------------------------------------------------

@dataclasses.dataclass(frozen=True)
class EgressDecision:
    allowed: bool
    scrubbed_payload: str   # "" whenever allowed=False — a blocked send has NO sendable form
    findings: list[dict]
    receipt: dict
    reason: str


def _scan_denylist(text: str, where: str, hash_whole: bool = False) -> list[dict]:
    """Layer-1 path-token scan of one string. hash_whole hashes the entire
    string (used for sources — a path TO a private dir is itself sensitive)."""
    findings: list[dict] = []
    for scope, klass, rx in PRIVATE_PATH_PATTERNS:
        for m in rx.finditer(text):
            findings.append({
                "layer": "denylist", "class": klass, "scope": scope,
                "kind": "private_path_ref" if klass == "private" else "secret_path_ref",
                "where": where, "start": m.start(), "end": m.end(),
                "sha256_16": _hash16(text if hash_whole else m.group(0)),
            })
            if hash_whole:
                break  # one finding per source per token is enough
    return findings


def _scan_secret_values(text: str, where: str) -> list[dict]:
    findings: list[dict] = []
    for kind, rx in SECRET_VALUE_PATTERNS:
        for m in rx.finditer(text):
            findings.append({
                "layer": "denylist", "class": "secret", "kind": kind,
                "where": where, "start": m.start(), "end": m.end(),
                "sha256_16": _hash16(m.group(0)),
            })
    return findings


def _receipt_safe(text: str) -> str:
    """Make a string safe to store in the receipt: secret values and PII
    redacted (path tokens may remain — they are public deny-list constants)."""
    out = text
    for kind, rx in SECRET_VALUE_PATTERNS:
        out = rx.sub(f"[REDACTED:{kind}]", out)
    for kind, rx in PII_PATTERNS:
        out = rx.sub(f"[REDACTED:{kind}]", out)
    return out


def _taint_scope_of(source: str) -> str | None:
    """Explicit CaMeL-style taint labels: 'private:<scope>' or
    'taint:private:<scope>' mark a source as private-tainted."""
    label = source
    if label.startswith("taint:"):
        label = label[len("taint:"):]
    if label.startswith("private:"):
        scope = label[len("private:"):].strip()
        return scope or "private"
    return None


def evaluate(payload: str, destination: str, *, grant: Grant | None = None,
             sources: list[str] | None = None, now: float | None = None,
             redact_tokens: tuple[str, ...] | list[str] = (),
             pii_backend: str = "auto") -> EgressDecision:
    """PURE decision core — no clock, no filesystem, no receipt append.

    See module docstring for the four layers. ``egress_check`` wraps this with
    the append-only receipt write.
    """
    payload = str(payload)
    destination = str(destination)
    src_list = [str(s) for s in (sources or [])]
    redact_tokens = tuple(redact_tokens)
    findings: list[dict] = []

    # -- layer 1: denylist (payload, destination, sources) -------------------
    findings += _scan_denylist(payload, "payload")
    findings += _scan_secret_values(payload, "payload")
    findings += _scan_denylist(destination, "destination")
    findings += _scan_secret_values(destination, "destination")
    for i, src in enumerate(src_list):
        findings += _scan_denylist(src, f"sources[{i}]", hash_whole=True)

    # -- layer 2: PII scrub --------------------------------------------------
    scrubbed, pii_findings, backend = _scrub_pii(payload, redact_tokens, pii_backend)
    findings += pii_findings

    # -- layer 3: taint/provenance -------------------------------------------
    for i, src in enumerate(src_list):
        scope = _taint_scope_of(src)
        if scope is not None:
            findings.append({
                "layer": "taint", "class": "private", "kind": "tainted_source",
                "scope": scope, "where": f"sources[{i}]", "sha256_16": _hash16(src),
            })

    secret_kinds = sorted({f["kind"] for f in findings if f.get("class") == "secret"})
    needed_scopes = {f["scope"] for f in findings if f.get("class") == "private"}

    granted = False
    if secret_kinds:
        allowed = False
        reason = (f"blocked: secret material detected ({', '.join(secret_kinds)}) — "
                  "secrets never egress; no grant can authorize them")
    elif needed_scopes:
        granted, why = _grant_covers(grant, needed_scopes, destination, now)
        findings.append({"layer": "taint", "kind": "grant_check", "granted": granted,
                         "scopes": sorted(needed_scopes), "detail": why})
        if granted:
            allowed = True
            reason = (f"allowed: private scope(s) {', '.join(sorted(needed_scopes))} "
                      f"authorized by grant; {len(pii_findings)} PII finding(s) redacted")
        else:
            allowed = False
            reason = (f"blocked: private-tainted (scope(s): "
                      f"{', '.join(sorted(needed_scopes))}); {why}")
    else:
        allowed = True
        reason = (f"allowed: {len(pii_findings)} PII finding(s) redacted"
                  if pii_findings else "allowed: clean")

    scrubbed_payload = scrubbed if allowed else ""
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "ts": now,
        "destination": _receipt_safe(destination),
        "allowed": allowed,
        "reason": reason,
        "payload_sha256": hashlib.sha256(payload.encode("utf-8", errors="replace")).hexdigest(),
        "payload_len": len(payload),
        "scrubbed_sha256": (hashlib.sha256(scrubbed_payload.encode("utf-8", errors="replace")).hexdigest()
                            if allowed else None),
        "pii_backend": backend,
        "findings": findings,
        "sources": [{"sha256_16": _hash16(s)} for s in src_list],
        "grant": (None if grant is None else {
            "scope": sorted(grant.scopes()), "audience": grant.audience,
            "expires_at": grant.expires_at, "note": grant.note, "matched": granted}),
    }
    return EgressDecision(allowed=allowed, scrubbed_payload=scrubbed_payload,
                          findings=findings, receipt=receipt, reason=reason)


def append_receipt(receipt: dict, log_path: Path | str = DEFAULT_RECEIPT_LOG) -> Path:
    """Append ONE JSONL line. Append-only by construction (mode 'a'); this
    module never rewrites or truncates the log."""
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(receipt, ensure_ascii=False, sort_keys=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return path


def egress_check(payload: str, destination: str, *, grant: Grant | None = None,
                 sources: list[str] | None = None, now: float | None = None,
                 redact_tokens: tuple[str, ...] | list[str] = (),
                 pii_backend: str = "auto",
                 receipt_log: Path | str | None = DEFAULT_RECEIPT_LOG) -> EgressDecision:
    """THE choke-point API: evaluate + append the egress receipt.

    ``receipt_log=None`` skips the append (pure dry-run — equivalent to
    calling ``evaluate`` directly). If the receipt append FAILS, the decision
    is downgraded to blocked: an egress that cannot be audited does not happen
    (fail closed — DNA invariant 4, no silent failure).
    """
    decision = evaluate(payload, destination, grant=grant, sources=sources,
                        now=now, redact_tokens=redact_tokens, pii_backend=pii_backend)
    if receipt_log is None:
        return decision
    try:
        append_receipt(decision.receipt, receipt_log)
    except OSError as exc:
        return EgressDecision(
            allowed=False, scrubbed_payload="", findings=decision.findings,
            receipt=decision.receipt,
            reason=f"blocked: egress receipt append failed ({exc.__class__.__name__}) — "
                   "unauditable egress is not allowed (fail closed)")
    return decision


# ---------------------------------------------------------------------------
# CLI — the impure edge: supplies the real clock, always writes a receipt
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AIOS egress gate — check a payload before ANY off-box send")
    sub = parser.add_subparsers(dest="cmd", required=True)
    chk = sub.add_parser("check", help="run the four-layer egress check (always writes a receipt)")
    chk.add_argument("--dest", required=True, help="destination (URL/host/channel) of the send")
    grp = chk.add_mutually_exclusive_group(required=True)
    grp.add_argument("--payload", help="payload text")
    grp.add_argument("--payload-file", help="read payload from file")
    chk.add_argument("--source", action="append", default=[],
                     help="provenance of the payload (path or private:<scope> taint label); repeatable")
    chk.add_argument("--grant-scope", action="append", default=[],
                     help="scope a grant authorizes; repeatable")
    chk.add_argument("--grant-audience", help="destination the grant is bound to (required with --grant-scope)")
    chk.add_argument("--grant-expires-at", type=float, help="absolute unix expiry of the grant")
    chk.add_argument("--redact-token", action="append", default=[],
                     help="extra literal token to redact; repeatable")
    chk.add_argument("--receipt-log", default=str(DEFAULT_RECEIPT_LOG),
                     help=f"receipt JSONL path (default {DEFAULT_RECEIPT_LOG})")
    chk.add_argument("--now", type=float, default=None,
                     help="unix timestamp for grant expiry + receipt (default: real time)")
    args = parser.parse_args(argv)

    if args.payload_file is not None:
        payload = Path(args.payload_file).read_text(encoding="utf-8", errors="replace")
    else:
        payload = args.payload

    grant = None
    if args.grant_scope:
        if not args.grant_audience:
            parser.error("--grant-audience is required when --grant-scope is given")
        grant = Grant(scope=tuple(args.grant_scope), audience=args.grant_audience,
                      expires_at=args.grant_expires_at)

    now = args.now
    if now is None:
        import time  # noqa: PLC0415 — the clock lives at the CLI edge only
        now = time.time()

    decision = egress_check(payload, args.dest, grant=grant, sources=args.source,
                            now=now, redact_tokens=tuple(args.redact_token),
                            receipt_log=args.receipt_log)
    print(json.dumps({
        "schema": GATE_SCHEMA,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "findings": len(decision.findings),
        "pii_backend": decision.receipt["pii_backend"],
        "scrubbed_payload": decision.scrubbed_payload,
        "receipt_log": args.receipt_log,
    }, ensure_ascii=False, indent=2))
    return 0 if decision.allowed else 2


if __name__ == "__main__":
    sys.exit(main())
