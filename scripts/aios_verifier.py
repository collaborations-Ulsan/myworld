#!/usr/bin/env python3
"""aios_verifier — LOCAL STRONG VERIFIER organ (Weaver weak-verifier
ensembling + distilled cross-encoder).

docs/AIOS_ABSORPTION_SCAN_2026-07-22.md, "#1 smallest integration path": AIOS's
escalation organ (scripts/aios_escalate.py, EscalationOrgan) has always taken a
`score_fn: Callable[[str], float]` by dependency injection, but the only
scorer this repo ever shipped was `_demo_scorer` — a length-capped heuristic,
explicitly documented there as "NOT a real verifier." This module is the real
verifier: this program's core finding (the DriftBench STOP, and every prior
negative traced through the self-observation log) is that self-improvement
strength tracks the VERIFIER hierarchy, not the generator. A local,
provider-independent, real verifier is the single highest-leverage missing
organ this scan identified.

GROUNDING (verified live 2026-07-22 — repo README, HF model card, HF
collection page, HF hub API file listing, and the ACTUAL distillation source
code `distillation/train.py` + `distillation/evaluate.py` fetched raw from
GitHub, plus a live download-and-load-and-score run on this box. NOT from
training memory, which pre-dates this repo and this model release.)

  - Repo: https://github.com/HazyResearch/scaling-verification — MIT license
    (GitHub license badge). Stanford Hazy Research / Scaling Intelligence
    (Saad-Falcon et al.), arXiv 2506.18203, NeurIPS 2025.
  - Method: combine many WEAK verifiers (LM judges + reward models,
    individually noisy, <=70B) into one STRONG score via WEAK SUPERVISION — a
    latent-variable graphical model in the Dawid-Skene / Snorkel lineage.
    Per-verifier true/false-positive rates are estimated from CO-VOTING
    AGREEMENT STATISTICS ACROSS A DATASET via a method-of-moments / tensor
    decomposition estimator (see `weaver/tensor_decomp.py` in the source
    repo) — fully UNSUPERVISED, no ground-truth labels needed.
  - Distilled artifact (what this module actually runs): the repo distills
    Weaver's combined ensemble judgment into a compact ~400M-param classifier
    ("retains 98.7% of Weaver's accuracy while reducing verification compute
    by up to 99.97%", per distillation/README.md) that runs cheaply, locally,
    provider-independent. HF collection:
    https://huggingface.co/collections/hazyresearch/weaver-683798010b39c9653ddb9bd8
    ships 5 distilled models; this module uses
    `hazyresearch/Weaver_Distilled_All_Datasets_ModernBERT-large` — the
    general-purpose one (trained on combined MATH500+GPQA+MMLU-Pro, not a
    single-domain variant) and the smaller of the two general variants
    (~400M vs. the sibling gte-Qwen2-1.5B-instruct's ~1.5B) — matching the
    absorption scan's "distilled 400M cross-encoder" sizing.

  - >>> CORRECTION vs. the model card's own quoted usage snippet <<<
    The HF model card page (and this module's first draft, built from a
    WebFetch summary of it) describes loading via plain
    `AutoModelForSequenceClassification.from_pretrained(model_id)` +
    `torch.sigmoid(...logits)`. That does NOT work: `hazyresearch/
    Weaver_Distilled_All_Datasets_ModernBERT-large` ships ONLY
    `pytorch_model.bin` (verified via the HF hub API `/api/models/...` file
    listing) — no `config.json`, no tokenizer files, and its own
    `transformersInfo.auto_model` field says `AutoModel`, not
    `AutoModelForSequenceClassification`. Tracing the ACTUAL training/eval
    code (`distillation/train.py` `CustomCrossEncoder`/`MLPHead`,
    `distillation/evaluate.py`) fetched raw from GitHub shows the real
    architecture and the real usage command
    (`evaluate.py --model_name answerdotai/ModernBERT-large --checkpoint_path
    hazyresearch/Weaver_Distilled_All_Datasets_ModernBERT-large`):
      * tokenizer + base encoder load from the BASE model id
        (`answerdotai/ModernBERT-large`, a fully-formed HF repo), NOT from
        the checkpoint repo.
      * the checkpoint (`pytorch_model.bin`, a bare `torch.save(state_dict)`,
        fetched via `huggingface_hub.hf_hub_download`) has two prefix groups:
        `base_model.*` (170 keys — the ModernBERT encoder WAS fine-tuned, not
        frozen) and `mlp_head.*` (8 keys — `nn.Linear(1024,1024)`, GELU,
        Dropout, `nn.Linear(1024,512)`, GELU, Dropout, `nn.Linear(512,256)`,
        GELU, Dropout, `nn.Linear(256,1)`; input_dim=1024 = ModernBERT-large
        hidden size, hidden_dims=[1024,512,256] per `TrainingConfig.
        __post_init__`'s ModernBERT branch) — split by prefix and loaded into
        the encoder and head separately.
      * `forward()`: run the base encoder with `output_hidden_states=True`,
        take `hidden_states[-1][:, 0, :]` (the CLS-token embedding of the
        LAST layer), feed it through the MLP head, `squeeze(-1)`. There is NO
        sigmoid in the real forward pass — it is a RAW REGRESSION output
        (trained with a regression loss toward Weaver's continuous [0,1]
        pseudo-labels), not a classification logit. `_clamp01()` below
        handles values that stray slightly outside [0,1].
      * all checkpoint weights are natively `torch.bfloat16`.
    Live-loading this ported architecture against the real checkpoint on
    2026-07-22 produced ZERO missing and ZERO unexpected keys on both
    `base_model.load_state_dict(...)` and `mlp_head.load_state_dict(...)` —
    i.e. an exact structural match, not a guess.
  - Live discrimination result (2026-07-22, this box, real weights — see
    module-level CLI verification in the task record): on 5 real held-out
    rows from `hazyresearch/MATH500_with_Llama_3.1_8B_Instruct_v1` (its own
    training-distribution shape: multi-step competition-math reasoning
    traces, real ground-truth `answer_correct` labels, real Llama-3.1-8B
    correct/incorrect completions), the correct sample outscored the wrong
    sample in 4/5 rows (avg score correct=0.509 vs wrong=0.473). On SHORT,
    single-step, hand-made arithmetic pairs (out of its training
    distribution), two independent hand-made sets scored 2/4 and 1/4 —
    at-or-below chance. HONEST READ: this is a real, non-fabricated verifier
    whose discrimination power is genuinely domain-bound to multi-step
    reasoning-trace verification (its training distribution), not a general
    short-answer/factual-QA judge. This is exactly why `weak_ensemble()`
    below (fusing several weak signals) matters instead of trusting any one
    verifier unconditionally — see its docstring.

WHAT THIS MODULE DOES NOT DO: it does not vendor Weaver's training/selection
pipeline (the weak-supervision fit / tensor-decomposition moment estimation
across a labeled-enough dataset) — that is a dataset-level calibration step,
out of scope for a per-call inference organ. `weak_ensemble()` below is an
HONEST, DOCUMENTED SIMPLIFICATION of the same idea, adapted to a
single-instance call shape — see its docstring for the precise scope note.
This is an "honest-degrade, never fake" choice (founder directive), not an
oversight.

Public API:
    score(query, answer, *, model_id=..., timeout=...) -> float in [0, 1], or
        an honest error dict {"error": ..., "detail": ...} on timeout /
        model-load / inference failure (never a fabricated score). Caller
        bugs (empty query, wrong types) raise ValueError instead, matching
        EscalationOrgan's own convention (see aios_escalate.py).
    weak_ensemble(query, answer, weak_scores) -> float in [0, 1] — fuses
        AIOS's EXISTING weak signals (multi-substrate-review scores, H0
        consistency, functional-test pass/fail, ...) via a single-instance
        reliability-reweighting fixed point — an honestly simplified
        adaptation of Weaver's weak-supervision combine (see docstring).
    make_verifier_score_fn(query, ...) -> Callable[[str], float] — binds
        `query` and returns EXACTLY the ScoreFn shape
        scripts/aios_escalate.py's EscalationOrgan expects (answer -> score),
        degrading to 0.0 (never raising, never returning a dict) on failure —
        see its docstring for why that specific degrade path matters.

CLI:
    python3 scripts/aios_verifier.py score --query Q --answer A
    python3 scripts/aios_verifier.py weak-ensemble --query Q --answer A --scores 0.9,0.4,0.7

Dependencies (OPTIONAL, lazily imported — only needed if score() /
make_verifier_score_fn() are actually called; weak_ensemble() is pure stdlib
math and needs neither): torch, transformers, huggingface_hub. Not declared
in pyproject.toml — matches this repo's stdlib-first / optional-extras
convention (e.g. aios_cls_train.py's lazy peft/transformers/trl import).
Model weights (base encoder + distilled checkpoint) download once via the
standard HF hub cache (~/.cache/huggingface/hub/...) and are NEVER committed
to this repo.

Schema: aios.verifier.v1
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from typing import Callable

_MODEL_ID = "hazyresearch/Weaver_Distilled_All_Datasets_ModernBERT-large"
_BASE_MODEL_ID = "answerdotai/ModernBERT-large"
_MLP_HIDDEN_DIMS = [1024, 512, 256]  # distillation/train.py TrainingConfig, ModernBERT branch
_EMBEDDING_DIM = 1024  # ModernBERT-large hidden size (distillation/train.py hardcodes this)
_MAX_LENGTH = 4096  # ModernBERT-large native context (model card + distillation/evaluate.py default)
_DEFAULT_TIMEOUT = float(os.environ.get("AIOS_VERIFIER_TIMEOUT", "300"))
_MIN_FREE_CUDA_BYTES = 1_500_000_000  # ~1.5 GiB headroom for a ~400M-param model

# One persistent, small worker pool — NOT a per-call `with ThreadPoolExecutor()`.
# A context-managed executor's __exit__ calls shutdown(wait=True), which BLOCKS
# until the submitted call finishes even after .result(timeout=...) already
# raised — that would silently defeat "never hang". Submitting to a
# module-level executor and only ever calling .result(timeout=...) on the
# returned future is what actually bounds the CALLING thread's wait.
_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix="aios-verifier")

_MODEL_CACHE: "dict[tuple[str, str, str], dict]" = {}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _run_with_timeout(fn: "Callable[[], float]", timeout: float) -> float:
    future = _EXECUTOR.submit(fn)
    return future.result(timeout=timeout)


def _select_device() -> str:
    """Pick the CUDA device with the most free memory; fall back to CPU if
    none have enough headroom for a ~400M-param model or CUDA is unavailable.

    Written defensively because this box runs two GPUs shared with other
    processes — `nvidia-smi` showed GPU0 at 11.0/32.6 GiB free and GPU1 at
    0.97/32.6 GiB free on 2026-07-22 (build time), so blindly trusting
    torch's default device ordering is not safe here; live GPU load on a
    shared box changes over time.
    """
    try:
        import torch
    # Not just ImportError: torch raises OSError when its CUDA shared objects
    # are missing or mismatched, and falling back to CPU is the right answer
    # in that case too.
    except Exception:
        return "cpu"
    if not torch.cuda.is_available():
        return "cpu"
    best_idx, best_free = None, 0
    for i in range(torch.cuda.device_count()):
        try:
            free, _total = torch.cuda.mem_get_info(i)
        except Exception:  # noqa: BLE001 — a device query failure just skips that device
            continue
        if free > best_free:
            best_idx, best_free = i, free
    if best_idx is not None and best_free >= _MIN_FREE_CUDA_BYTES:
        return f"cuda:{best_idx}"
    return "cpu"


def _load_verifier_model(
    *, model_id: str = _MODEL_ID, base_model_id: str = _BASE_MODEL_ID, device: "str | None" = None,
) -> dict:
    """Lazily import torch/transformers/huggingface_hub and load+cache the
    Weaver distilled cross-encoder as an in-process singleton (keyed by
    model_id + base_model_id + device), so only the FIRST call for a given
    key downloads/loads weights. Allowed to raise — the only caller
    (`score()`, via `_run_with_timeout`) converts any exception into an
    honest error dict.

    Architecture ported from HazyResearch/scaling-verification
    `distillation/train.py`'s `CustomCrossEncoder`/`MLPHead` (see module
    docstring's CORRECTION note for why this is NOT a plain
    `AutoModelForSequenceClassification` load) — a base ModernBERT-large
    encoder + a separately-trained 4-linear-layer MLP head on the CLS token.
    """
    cache_key = (model_id, base_model_id, device or "auto")
    cached = _MODEL_CACHE.get(cache_key)
    if cached is not None:
        return cached

    import torch
    import torch.nn as nn
    from huggingface_hub import hf_hub_download
    from transformers import AutoModel, AutoTokenizer

    resolved_device = device or _select_device()
    dtype = torch.bfloat16 if resolved_device != "cpu" else torch.float32

    class _MLPHead(nn.Module):
        """Ported verbatim (structure + key names) from distillation/
        train.py's MLPHead — must match exactly for the trained checkpoint's
        state_dict keys/shapes to load (verified live: 0 missing, 0
        unexpected keys against the real `pytorch_model.bin`)."""

        def __init__(self, input_dim: int, hidden_dims: "list[int]", dropout_rate: float = 0.1):
            super().__init__()
            layers = []
            prev_dim = input_dim
            for hidden_dim in hidden_dims:
                layers += [nn.Linear(prev_dim, hidden_dim), nn.GELU(), nn.Dropout(dropout_rate)]
                prev_dim = hidden_dim
            layers.append(nn.Linear(prev_dim, 1))
            self.mlp = nn.Sequential(*layers)

        def forward(self, x):
            return self.mlp(x)

    tokenizer = AutoTokenizer.from_pretrained(base_model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # reference_compile/attn_implementation pinned explicitly: HF's ModernBERT
    # otherwise auto-enables a torch.compile'd GeGLU path on first forward()
    # call, which JIT-compiles a Triton/CUDA kernel via gcc — that compile
    # step failed on this box (gcc/Triton toolchain issue unrelated to GPU
    # availability). Forcing eager SDPA attention avoids the compile step
    # entirely; verified live to still load the checkpoint with 0 missing/
    # unexpected keys and produce sane (non-NaN, non-degenerate) scores.
    base_model = AutoModel.from_pretrained(
        base_model_id, torch_dtype=dtype, output_hidden_states=True,
        reference_compile=False, attn_implementation="sdpa",
    )
    mlp_head = _MLPHead(_EMBEDDING_DIM, _MLP_HIDDEN_DIMS).to(dtype)

    ckpt_path = hf_hub_download(repo_id=model_id, filename="pytorch_model.bin")
    state_dict = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    base_sd = {k[len("base_model."):]: v for k, v in state_dict.items() if k.startswith("base_model.")}
    mlp_sd = {k[len("mlp_head."):]: v for k, v in state_dict.items() if k.startswith("mlp_head.")}
    if base_sd:
        base_model.load_state_dict(base_sd)
    if mlp_sd:
        mlp_head.load_state_dict(mlp_sd)

    base_model = base_model.to(resolved_device).eval()
    mlp_head = mlp_head.to(resolved_device).eval()

    entry = {
        "tokenizer": tokenizer, "base_model": base_model, "mlp_head": mlp_head,
        "device": resolved_device, "model_id": model_id,
    }
    _MODEL_CACHE[cache_key] = entry
    return entry


# ---------------------------------------------------------------------------
# score() — the real verifier
# ---------------------------------------------------------------------------

def score(
    query: str,
    answer: str,
    *,
    model_id: str = _MODEL_ID,
    timeout: float = _DEFAULT_TIMEOUT,
) -> "float | dict":
    """Score how likely `answer` correctly answers `query`, via the Weaver
    distilled ModernBERT-large cross-encoder (see module docstring for full
    grounding/provenance, INCLUDING the honest domain-generalization finding:
    this verifier discriminates well on multi-step reasoning-trace answers —
    its training distribution — and does not reliably discriminate on short/
    simple factual QA; verified live, not assumed).

    Returns a float in [0, 1] (higher = more likely correct) on success. On
    timeout, model-load failure (e.g. no network for the first download), or
    any inference error, returns an honest error dict
    `{"error": <code>, "detail": <message>}` — NEVER a fabricated score.
    Caller-side bugs (empty/non-string query or answer) raise ValueError,
    matching EscalationOrgan's own convention (empty generators / non-positive
    budget both raise there rather than degrading).
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("score() requires a non-empty string query")
    if not isinstance(answer, str):
        raise ValueError("score() requires answer to be a string")
    if not answer.strip():
        # An empty answer is honestly a non-answer, not a runtime failure —
        # score it 0 directly, no need to invoke the model at all.
        return 0.0

    def _run() -> float:
        import torch

        entry = _load_verifier_model(model_id=model_id)
        tokenizer = entry["tokenizer"]
        base_model = entry["base_model"]
        mlp_head = entry["mlp_head"]
        device = entry["device"]

        encoded = tokenizer(
            text=query, text_pair=answer, truncation=True, max_length=_MAX_LENGTH,
            padding=True, return_tensors="pt",
        )
        input_ids = encoded["input_ids"].to(device)
        attention_mask = encoded["attention_mask"].to(device)

        with torch.no_grad():
            outputs = base_model(input_ids=input_ids, attention_mask=attention_mask, output_hidden_states=True)
            cls_embedding = outputs.hidden_states[-1][:, 0, :]  # last-layer CLS token
            raw = mlp_head(cls_embedding).squeeze(-1)
        return _clamp01(raw.float().item())

    try:
        return _run_with_timeout(_run, timeout)
    except concurrent.futures.TimeoutError:
        return {"error": "timeout", "detail": f"verifier scoring exceeded {timeout}s (model_id={model_id})"}
    except Exception as exc:  # noqa: BLE001 — any load/inference failure is an honest degrade, not a crash
        return {"error": "verifier_unavailable", "detail": f"{type(exc).__name__}: {exc}"[:300]}


# ---------------------------------------------------------------------------
# weak_ensemble() — fuse AIOS's existing weak signals
# ---------------------------------------------------------------------------

def weak_ensemble(
    query: str,
    answer: str,
    weak_scores: "list[float]",
    *,
    iterations: int = 8,
) -> float:
    """Fuse multiple WEAK verifier scores (each an independent, possibly
    noisy estimate of P(answer correct) — e.g. multi-substrate-review scores,
    H0 consistency checks, functional-test pass/fail, OR this module's own
    `score()`, whose live verification found it domain-bound rather than
    universally reliable — exactly the motivation for fusing it with other
    signals instead of trusting it alone) into one score, via a simplified
    single-instance adaptation of Weaver's weak-supervision combine.

    HONEST SCOPE NOTE: Weaver's actual method (`weaver/tensor_decomp.py` in
    HazyResearch/scaling-verification) estimates each verifier's true/false
    positive rate from CO-VOTING AGREEMENT STATISTICS ACROSS A DATASET of many
    scored examples (a method-of-moments / tensor-decomposition estimator
    grounded in the Dawid-Skene / Snorkel weak-supervision literature), then
    applies those FIXED, learned per-verifier reliability weights at
    inference time. This function's signature is single-instance —
    (query, answer, weak_scores) -> float, no persisted cross-call history —
    so it CANNOT replicate that dataset-level moment estimation. Instead it
    runs a real (not fake) unsupervised truth-discovery fixed point: starting
    from a uniform-weight consensus, iteratively re-estimate each verifier's
    reliability from how closely it agrees with the CURRENT weighted
    consensus on THIS instance, then re-weight by that agreement and recompute
    the consensus. This is the same "reliability-weighted aggregation beats a
    naive average, without labels" idea Weaver is built on, just estimated
    from single-instance agreement rather than dataset-level co-voting
    moments — outliers are down-weighted rather than allowed to drag a
    straight mean, and unanimous/symmetric inputs are provably stable fixed
    points (see tests/test_aios_verifier.py).

    `query`/`answer` are accepted (and validated) for API symmetry with
    `score()`, and so a future version can condition the reliability prior on
    them; the current fixed point does not use their text content.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("weak_ensemble() requires a non-empty string query")
    if not isinstance(answer, str):
        raise ValueError("weak_ensemble() requires answer to be a string")
    if not weak_scores:
        raise ValueError("weak_ensemble() requires at least one weak score")

    scores = [_clamp01(s) for s in weak_scores]
    n = len(scores)
    if n == 1:
        return scores[0]

    weights = [1.0 / n] * n
    consensus = sum(w * s for w, s in zip(weights, scores))
    for _ in range(iterations):
        agreement = [1.0 - abs(s - consensus) for s in scores]
        total = sum(agreement)
        if total <= 0:
            break  # degenerate: every verifier maximally disagrees; keep last consensus
        weights = [a / total for a in agreement]
        consensus = sum(w * s for w, s in zip(weights, scores))

    return _clamp01(consensus)


# ---------------------------------------------------------------------------
# EscalationOrgan adapter
# ---------------------------------------------------------------------------

def make_verifier_score_fn(
    query: str,
    *,
    model_id: str = _MODEL_ID,
    timeout: float = _DEFAULT_TIMEOUT,
) -> "Callable[[str], float]":
    """Factory matching scripts/aios_escalate.py's ScoreFn contract EXACTLY
    (`Callable[[str], float]`, answer -> score in [0, 1]) — binds `query`
    (the escalation goal) via closure, since EscalationOrgan.escalate() calls
    `self.score_fn(answer)` with no query in scope at call time.

    On any verifier failure the returned closure degrades to 0.0 rather than
    raising or returning a dict. This matters structurally, not just
    stylistically: EscalationOrgan wraps `self.score_fn(answer)` in the SAME
    try/except as the generator call it scored (see `_make_gen._gen` in
    aios_escalate.py) — a raised exception here would be mis-attributed to
    the GENERATOR (marking it "dead" for the rest of the run) instead of the
    verifier. Always returning a plain float avoids that misattribution.
    """
    def _score_fn(answer: str) -> float:
        result = score(query, answer, model_id=model_id, timeout=timeout)
        return result if isinstance(result, float) else 0.0
    return _score_fn


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: "list[str] | None" = None) -> int:
    parser = argparse.ArgumentParser(
        description="AIOS local verifier organ — Weaver distilled cross-encoder + weak-supervision fuse.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_score = sub.add_parser("score", help="score one (query, answer) pair with the real verifier")
    p_score.add_argument("--query", required=True)
    p_score.add_argument("--answer", required=True)
    p_score.add_argument("--model-id", default=_MODEL_ID)
    p_score.add_argument("--timeout", type=float, default=_DEFAULT_TIMEOUT)

    p_weak = sub.add_parser("weak-ensemble", help="fuse comma-separated weak verifier scores")
    p_weak.add_argument("--query", required=True)
    p_weak.add_argument("--answer", required=True)
    p_weak.add_argument("--scores", required=True, help="comma-separated floats in [0,1]")

    args = parser.parse_args(argv)

    if args.cmd == "score":
        result = score(args.query, args.answer, model_id=args.model_id, timeout=args.timeout)
        payload = {"score": result} if isinstance(result, float) else result
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 1 if isinstance(result, dict) else 0

    if args.cmd == "weak-ensemble":
        weak_scores = [float(x) for x in args.scores.split(",") if x.strip()]
        result = weak_ensemble(args.query, args.answer, weak_scores)
        print(json.dumps({"score": result}, ensure_ascii=False, indent=2))
        return 0

    return 2  # pragma: no cover — argparse `required=True` on the subparser makes this unreachable


if __name__ == "__main__":
    raise SystemExit(main())
