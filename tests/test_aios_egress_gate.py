"""Security-critical tests for scripts/aios_egress_gate.py — every layer probed.

Layer 1: privacy-boundary path refs + secret value patterns => hard block
Layer 2: PII scrub (regex floor always; GLiNER2 optional, absence => honest fallback)
Layer 3: CaMeL-style taint — private sources blocked without a matching grant
Layer 4: append-only receipt, one line per decision, NO raw private content
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, (Path(__file__).resolve().parents[1] / "scripts").as_posix())

import aios_egress_gate as gate  # noqa: E402

DEST = "https://peer.example.com/inbox"
NOW = 1_800_000_000.0


def check(payload: str, dest: str = DEST, **kw) -> gate.EgressDecision:
    """evaluate() = the pure core (no receipt IO) — used for layer 1-3 tests."""
    return gate.evaluate(payload, dest, **kw)


# ---------------------------------------------------------------------------
# Layer 1 — privacy-boundary path references
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("payload", [
    "summary of _from_desktop/family_notes.md attached",
    "met dain today at school",
    "photos in minyoung/photos/2026 folder",
    "attaching raw_exports/kakaotalk_dump.json",
])
def test_private_dir_reference_in_payload_blocks(payload):
    d = check(payload)
    assert d.allowed is False
    assert d.scrubbed_payload == ""          # blocked send has NO sendable form
    assert any(f["layer"] == "denylist" and f["class"] == "private" for f in d.findings)


def test_private_dir_in_sources_blocks():
    d = check("weekly report, nothing sensitive here",
              sources=["/home/user/workspaces/jaewon/dain/diary.md"])
    assert d.allowed is False
    assert "dain" in d.reason
    src_findings = [f for f in d.findings if f.get("where") == "sources[0]"]
    assert src_findings and src_findings[0]["scope"] == "dain"


@pytest.mark.parametrize("payload", [
    "the .env file has the connection string",
    "loading config/.env.local for staging",
    "copied .aios/secrets/api_key.json to the build",
])
def test_env_and_secrets_path_refs_block(payload):
    d = check(payload)
    assert d.allowed is False
    assert any(f["kind"] == "secret_path_ref" for f in d.findings)


def test_env_secrets_path_refs_never_grantable():
    g = gate.Grant(scope=(".env", "secrets"), audience=DEST, expires_at=NOW + 3600)
    d = check("please read .env and secrets/token.json", grant=g, now=NOW)
    assert d.allowed is False
    assert "secrets never egress" in d.reason


def test_lookalike_words_pass():
    # disdain / environment / dainty / "secretive" (no path context) are NOT hits
    d = check("I disdain long meetings about the environment; dainty secretive plans.")
    assert d.allowed is True
    assert d.findings == []
    assert d.reason == "allowed: clean"
    assert d.scrubbed_payload == "I disdain long meetings about the environment; dainty secretive plans."


# ---------------------------------------------------------------------------
# Layer 1 — secret value patterns (each one must block)
# ---------------------------------------------------------------------------

SECRET_SAMPLES = {
    "aws_access_key": "deploy creds AKIAABCDEFGHIJKLMNOP configured",
    "bearer_token": "Authorization: Bearer abcdef0123456789TOKEN",
    "private_key_block": "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA...",
    "sk_token": "use key sk-live-4f9a8b7c6d5e for the call",
    "generic_api_key": 'settings: api_key = "zz88yy77xx66ww55"',
    "jwt_token": ("session eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
                  "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJVadQssw5c"),
}


@pytest.mark.parametrize("kind,payload", sorted(SECRET_SAMPLES.items()))
def test_secret_patterns_block(kind, payload):
    d = check(payload)
    assert d.allowed is False, f"{kind} sample was NOT blocked"
    assert kind in {f["kind"] for f in d.findings if f.get("class") == "secret"}
    assert d.scrubbed_payload == ""


def test_secret_with_grant_still_blocked():
    # grants authorize PRIVATE scopes, never secret material
    g = gate.Grant(scope="dain", audience=DEST, expires_at=NOW + 3600)
    d = check("for dain: token sk-live-4f9a8b7c6d5e", grant=g, now=NOW)
    assert d.allowed is False
    assert "no grant can authorize" in d.reason


def test_sk_learn_is_not_a_secret():
    d = check("we trained the model with sk-learn pipelines")
    assert d.allowed is True


# ---------------------------------------------------------------------------
# Layer 2 — PII scrub (regex floor)
# ---------------------------------------------------------------------------

def test_email_phone_cc_redacted():
    payload = "Contact alice@example.com or 010-1234-5678, card 4111 1111 1111 1111."
    d = check(payload)
    assert d.allowed is True
    for raw in ("alice@example.com", "010-1234-5678", "4111 1111 1111 1111"):
        assert raw not in d.scrubbed_payload
    for marker in ("[REDACTED:email]", "[REDACTED:phone]", "[REDACTED:credit_card]"):
        assert marker in d.scrubbed_payload
    kinds = {f["kind"] for f in d.findings if f["layer"] == "pii"}
    assert {"email", "phone", "credit_card"} <= kinds
    cc = next(f for f in d.findings if f["kind"] == "credit_card")
    assert cc["luhn_valid"] is True          # 4111... is the Luhn-valid Visa test PAN


def test_custom_token_denylist_redacted():
    d = check("codename PROJECT-KRAKEN ships Friday", redact_tokens=("PROJECT-KRAKEN",))
    assert d.allowed is True
    assert "PROJECT-KRAKEN" not in d.scrubbed_payload
    assert "[REDACTED:token]" in d.scrubbed_payload


def test_findings_carry_hashes_not_raw_text():
    d = check("mail bob@corp.example now")
    blob = json.dumps(d.findings)
    assert "bob@corp.example" not in blob
    f = next(f for f in d.findings if f["kind"] == "email")
    assert f["sha256_16"] == hashlib.sha256(b"bob@corp.example").hexdigest()[:16]


# ---------------------------------------------------------------------------
# Layer 2 — pluggable backend: GLiNER absent => regex fallback; present => used
# ---------------------------------------------------------------------------

def test_gliner_absent_regex_fallback(monkeypatch):
    monkeypatch.setattr(gate, "_GLINER_STATE", {})
    monkeypatch.setitem(sys.modules, "gliner2", None)   # forces ImportError on import
    d = check("reach me at carol@example.org", pii_backend="auto")
    assert d.receipt["pii_backend"] == "regex-fallback"
    assert d.allowed is True
    assert "carol@example.org" not in d.scrubbed_payload   # floor still works


def test_gliner_present_is_used(monkeypatch):
    fake = types.ModuleType("gliner2")

    class _FakeModel:
        def extract_entities(self, text, labels):
            out, needle, i = [], "Jaewon Choi", 0
            while (i := text.find(needle, i)) != -1:
                out.append({"start": i, "end": i + len(needle), "label": "person"})
                i += len(needle)
            return out

    class GLiNER2:
        @classmethod
        def from_pretrained(cls, model_id):
            return _FakeModel()

    fake.GLiNER2 = GLiNER2
    monkeypatch.setattr(gate, "_GLINER_STATE", {})
    monkeypatch.setitem(sys.modules, "gliner2", fake)
    d = check("Ask Jaewon Choi (jw@corp.example) about the launch", pii_backend="auto")
    assert d.receipt["pii_backend"] == "gliner2"
    assert "Jaewon Choi" not in d.scrubbed_payload
    assert "[REDACTED:gliner:person]" in d.scrubbed_payload
    assert "jw@corp.example" not in d.scrubbed_payload     # regex floor ALSO applied


# ---------------------------------------------------------------------------
# Layer 3 — taint/provenance grants
# ---------------------------------------------------------------------------

def test_tainted_source_blocked_without_grant():
    d = check("her drawing from art class", sources=["private:dain"])
    assert d.allowed is False
    assert "no grant supplied" in d.reason


def test_tainted_source_allowed_with_matching_grant():
    g = gate.Grant(scope="dain", audience=DEST, expires_at=NOW + 3600, note="school share")
    d = check("her drawing from art class", sources=["private:dain"], grant=g, now=NOW)
    assert d.allowed is True
    assert "authorized by grant" in d.reason
    assert d.receipt["grant"]["matched"] is True
    assert d.scrubbed_payload == "her drawing from art class"


def test_grant_audience_mismatch_blocks():
    g = gate.Grant(scope="dain", audience="https://other.example/webhook")
    d = check("x", sources=["private:dain"], grant=g, now=NOW)
    assert d.allowed is False
    assert "audience mismatch" in d.reason


def test_grant_expired_blocks():
    g = gate.Grant(scope="dain", audience=DEST, expires_at=NOW - 1)
    d = check("x", sources=["private:dain"], grant=g, now=NOW)
    assert d.allowed is False
    assert "expired" in d.reason


def test_grant_expiry_without_now_blocks():
    g = gate.Grant(scope="dain", audience=DEST, expires_at=NOW + 3600)
    d = check("x", sources=["private:dain"], grant=g, now=None)
    assert d.allowed is False
    assert "unverifiable" in d.reason


def test_grant_scope_mismatch_blocks():
    g = gate.Grant(scope="minyoung", audience=DEST)
    d = check("x", sources=["private:dain"], grant=g, now=NOW)
    assert d.allowed is False
    assert "scope mismatch" in d.reason


def test_multi_scope_grant_must_cover_all():
    srcs = ["private:dain", "private:minyoung"]
    partial = gate.Grant(scope="dain", audience=DEST)
    d = check("x", sources=srcs, grant=partial, now=NOW)
    assert d.allowed is False
    assert "minyoung" in d.reason
    full = gate.Grant(scope=("dain", "minyoung"), audience=DEST)
    d2 = check("x", sources=srcs, grant=full, now=NOW)
    assert d2.allowed is True


def test_payload_private_ref_covered_by_grant():
    # a grant lifts the layer-1 PRIVATE path block too (deliberate sharing)
    g = gate.Grant(scope="dain", audience=DEST, expires_at=NOW + 60)
    d = check("dain's schedule for tomorrow", grant=g, now=NOW)
    assert d.allowed is True
    assert d.scrubbed_payload == "dain's schedule for tomorrow"


def test_destination_private_ref_blocked_without_grant():
    d = check("hello", "https://drop.example/dain/upload")
    assert d.allowed is False
    assert any(f["where"] == "destination" for f in d.findings)


# ---------------------------------------------------------------------------
# Layer 4 — append-only receipt
# ---------------------------------------------------------------------------

def test_receipt_appends_one_line_per_call(tmp_path):
    log = tmp_path / "receipts.jsonl"
    gate.egress_check("clean note", DEST, now=NOW, receipt_log=log)              # allow
    first = log.read_text(encoding="utf-8")
    assert len(first.splitlines()) == 1
    gate.egress_check("see dain today", DEST, now=NOW + 1, receipt_log=log)      # block
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0] == first.splitlines()[0]        # append-only: line 1 untouched
    recs = [json.loads(ln) for ln in lines]
    assert [r["allowed"] for r in recs] == [True, False]
    assert [r["ts"] for r in recs] == [NOW, NOW + 1]


def test_receipt_contains_no_raw_private_content(tmp_path):
    log = tmp_path / "receipts.jsonl"
    payload = "Send bob@corp.example the family dinner plan from dain"
    d = gate.egress_check(payload, DEST, now=NOW, receipt_log=log)
    assert d.allowed is False
    line = log.read_text(encoding="utf-8")
    assert "bob@corp.example" not in line           # PII never in the receipt
    assert "family dinner" not in line              # payload text never in the receipt
    rec = json.loads(line)
    assert rec["payload_sha256"] == hashlib.sha256(payload.encode()).hexdigest()
    assert rec["scrubbed_sha256"] is None
    email = next(f for f in rec["findings"] if f["kind"] == "email")
    assert email["sha256_16"] == hashlib.sha256(b"bob@corp.example").hexdigest()[:16]


def test_receipt_destination_secret_redacted(tmp_path):
    # GitLost-style URL exfil: secret riding the destination itself
    log = tmp_path / "receipts.jsonl"
    d = gate.egress_check("hi", "https://evil.example/?k=sk-live-12345678",
                          now=NOW, receipt_log=log)
    assert d.allowed is False
    line = log.read_text(encoding="utf-8")
    assert "sk-live-12345678" not in line
    assert "[REDACTED:sk_token]" in json.loads(line)["destination"]


def test_default_receipt_log_location():
    assert str(gate.DEFAULT_RECEIPT_LOG).endswith(".aios/egress_receipts.jsonl")


def test_receipt_write_failure_fails_closed(tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file, not a directory")
    d = gate.egress_check("perfectly clean text", DEST, now=NOW,
                          receipt_log=blocker / "log.jsonl")   # parent is a file => OSError
    assert d.allowed is False
    assert "fail closed" in d.reason


# ---------------------------------------------------------------------------
# Core properties + CLI
# ---------------------------------------------------------------------------

def test_clean_payload_allowed_unchanged():
    d = check("quarterly OKR summary: shipped the egress gate")
    assert d.allowed is True
    assert d.scrubbed_payload == "quarterly OKR summary: shipped the egress gate"
    assert d.receipt["allowed"] is True and d.receipt["ts"] is None


def test_evaluate_is_deterministic():
    kw = dict(sources=["private:dain"],
              grant=gate.Grant(scope="dain", audience=DEST, expires_at=NOW + 9),
              now=NOW, pii_backend="regex")
    d1 = gate.evaluate("call 010-1234-5678 re dain", DEST, **kw)
    d2 = gate.evaluate("call 010-1234-5678 re dain", DEST, **kw)
    assert dataclasses.asdict(d1) == dataclasses.asdict(d2)


def test_cli_check_allow_and_block(tmp_path, capsys):
    log = tmp_path / "cli.jsonl"
    rc_allow = gate.main(["check", "--dest", DEST, "--payload",
                          "hello world from the CLI", "--receipt-log", str(log),
                          "--now", str(NOW)])
    out_allow = json.loads(capsys.readouterr().out)
    rc_block = gate.main(["check", "--dest", DEST, "--payload",
                          "leak _from_desktop/notes.md", "--receipt-log", str(log),
                          "--now", str(NOW)])
    out_block = json.loads(capsys.readouterr().out)
    assert (rc_allow, rc_block) == (0, 2)
    assert out_allow["allowed"] is True and out_block["allowed"] is False
    assert len(log.read_text(encoding="utf-8").splitlines()) == 2   # both decisions logged
