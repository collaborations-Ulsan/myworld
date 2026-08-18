#!/usr/bin/env python3
"""aios.model_registry.v1 — the model catalogue, ingested from live sources and diffable.

Founder: find where the community keeps model usage written down, record it in AIOS, and
have it update when they update.

The answer is that nobody needs to maintain a document, because four catalogues are
already maintained by other people AND are machine-readable (probed 2026-08-18, all 200):

  litellm    model_prices_and_context_window.json  1.7MB  pricing, context, modality
  openrouter /api/v1/models                        675KB  context, pricing, top_provider
  ollama     /library                              801KB  what we can actually pull
  huggingface/api/models                           JSON   trending, downloads

So this fetches rather than writes, stores a snapshot with its fetch time, and — the part
that matters — DIFFS against the previous snapshot. A catalogue that cannot say what
changed is a catalogue you have to read in full every time, which means you never do.

The registry in aios_substrate.py stays hand-curated and small: it holds the handful we
have MEASURED. This holds the thousands we merely know about. Conflating those two is how
a registry starts lying.
"""
from __future__ import annotations
import argparse, json, os, re, sqlite3, sys, time, urllib.request
from pathlib import Path

DB = Path(os.environ.get("AIOS_GRAPH_DEST", "/data/jaewon/aios")) / "index" / "aios.db"
UA = {"User-Agent": "aios-model-registry/1.0 (+cjw0076/myworld)"}

SOURCES = {
    "litellm": "https://raw.githubusercontent.com/BerriAI/litellm/main/"
               "model_prices_and_context_window.json",
    "openrouter": "https://openrouter.ai/api/v1/models",
    "ollama": "https://ollama.com/library",
    "huggingface": "https://huggingface.co/api/models?sort=trendingScore&limit=200",
}


def fetch(url: str, timeout: int = 90) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except Exception as e:
        print(f"  FETCH FAILED {url[:60]}: {type(e).__name__}", file=sys.stderr)
        return None


def parse_litellm(b: bytes) -> list[dict]:
    d = json.loads(b)
    out = []
    for name, m in d.items():
        if not isinstance(m, dict) or name == "sample_spec":
            continue
        out.append({"id": name, "source": "litellm", "provider": m.get("litellm_provider", ""),
                    "context": m.get("max_input_tokens") or m.get("max_tokens"),
                    "max_out": m.get("max_output_tokens"),
                    "in_cost": m.get("input_cost_per_token"),
                    "out_cost": m.get("output_cost_per_token"),
                    "mode": m.get("mode", ""),
                    "caps": ",".join(sorted(k[10:] for k in m
                                            if k.startswith("supports_") and m[k] is True))})
    return out


def parse_openrouter(b: bytes) -> list[dict]:
    d = json.loads(b)
    out = []
    for m in d.get("data", []):
        p = m.get("pricing") or {}
        arch = m.get("architecture") or {}
        out.append({"id": m["id"], "source": "openrouter",
                    "provider": m["id"].split("/")[0],
                    "context": m.get("context_length"),
                    "max_out": (m.get("top_provider") or {}).get("max_completion_tokens"),
                    "in_cost": float(p.get("prompt") or 0) or None,
                    "out_cost": float(p.get("completion") or 0) or None,
                    "mode": arch.get("modality", ""),
                    "caps": ",".join(arch.get("input_modalities") or [])})
    return out


def parse_ollama(b: bytes) -> list[dict]:
    """HTML, so this is a scrape and says so. Names only — the pullable surface."""
    names = sorted(set(re.findall(rb'href="/library/([a-z0-9][\w\.\-]{1,40})"', b)))
    return [{"id": n.decode(), "source": "ollama", "provider": "ollama",
             "context": None, "max_out": None, "in_cost": 0.0, "out_cost": 0.0,
             "mode": "local", "caps": ""} for n in names]


def parse_hf(b: bytes) -> list[dict]:
    d = json.loads(b)
    return [{"id": m["id"], "source": "huggingface", "provider": m["id"].split("/")[0],
             "context": None, "max_out": None, "in_cost": None, "out_cost": None,
             "mode": m.get("pipeline_tag", ""),
             "caps": f"downloads={m.get('downloads',0)}"} for m in d]


PARSERS = {"litellm": parse_litellm, "openrouter": parse_openrouter,
           "ollama": parse_ollama, "huggingface": parse_hf}


def ensure(con) -> None:
    con.executescript("""
      create table if not exists models(
        id text, source text, provider text, context int, max_out int,
        in_cost real, out_cost real, mode text, caps text, fetched_at int,
        primary key (source, id));
      create table if not exists model_snapshots(
        source text, fetched_at int, n int, primary key (source, fetched_at));
      create index if not exists idx_models_src on models(source);
    """)


def refresh(only: str | None = None) -> dict:
    con = sqlite3.connect(DB)
    ensure(con)
    now = int(time.time())
    report = {}
    for name, url in SOURCES.items():
        if only and name != only:
            continue
        print(f"fetching {name} …", flush=True)
        raw = fetch(url)
        if raw is None:
            report[name] = {"status": "fetch_failed"}       # never silently zero
            continue
        try:
            rows = PARSERS[name](raw)
        except Exception as e:
            report[name] = {"status": f"parse_failed: {type(e).__name__}"}
            continue
        before = {r for (r,) in con.execute(
            "select id from models where source = ?", (name,))}
        now_ids = {r["id"] for r in rows}
        con.executemany(
            "insert or replace into models values (?,?,?,?,?,?,?,?,?,?)",
            [(r["id"], r["source"], r["provider"], r["context"], r["max_out"],
              r["in_cost"], r["out_cost"], r["mode"], r["caps"], now) for r in rows])
        con.execute("insert or replace into model_snapshots values (?,?,?)",
                    (name, now, len(rows)))
        con.commit()
        report[name] = {"status": "ok", "n": len(rows),
                        "new": sorted(now_ids - before)[:40],
                        "n_new": len(now_ids - before),
                        "gone": len(before - now_ids)}
        print(f"  {len(rows)} models, {len(now_ids - before)} new", flush=True)
    con.close()
    return report


def find(term: str, limit: int = 25) -> list[tuple]:
    con = sqlite3.connect(DB)
    ensure(con)
    q = f"%{term.lower()}%"
    return list(con.execute(
        "select id, source, context, in_cost, mode, caps from models "
        "where lower(id) like ? or lower(caps) like ? or lower(mode) like ? "
        "order by (context is null), context desc limit ?", (q, q, q, limit)))


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="subcmd", required=True)   # not "cmd" — collides with --cmd
    r = sub.add_parser("refresh"); r.add_argument("--source", choices=sorted(SOURCES))
    f = sub.add_parser("find"); f.add_argument("term"); f.add_argument("--limit", type=int, default=25)
    sub.add_parser("stats")
    a = ap.parse_args()

    if a.subcmd == "refresh":
        rep = refresh(a.source)
        print()
        for k, v in rep.items():
            if v["status"] != "ok":
                print(f"  {k:<13}{v['status']}")
                continue
            print(f"  {k:<13}{v['n']:>6} models   +{v['n_new']} new   -{v['gone']} gone")
            for n in v["new"][:8]:
                print(f"                  NEW {n}")
    elif a.subcmd == "find":
        rows = find(a.term, a.limit)
        print(f"{'model':<52}{'src':<12}{'ctx':>9}{'$/tok in':>12}  mode")
        for i, s, c, ic, mo, _ in rows:
            print(f"{i[:50]:<52}{s:<12}{(c or 0):>9}{(ic if ic is not None else -1):>12.8f}  {mo[:24]}")
    elif a.subcmd == "stats":
        con = sqlite3.connect(DB); ensure(con)
        for s, n, t in con.execute(
                "select source, count(*), max(fetched_at) from models group by source"):
            age = (time.time() - t) / 3600
            print(f"  {s:<13}{n:>6} models   fetched {age:.1f}h ago")
    return 0


if __name__ == "__main__":
    sys.exit(main())
