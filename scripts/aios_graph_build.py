#!/usr/bin/env python3
"""aios.graph.v1 — the knowledge graph of what AIOS actually knows and made.

Mirrors the layout the robot-side subagent used for the paper graph
(/data/jaewon/robotics: index/*.db + ontology/ontology.jsonl + honest failures table)
so the two sit side by side and can be queried the same way.

Why this and not another brick: the standing audit finding is that every artifact we
build is an ORPHAN — nothing references it, nothing depends on it, it changes no
behaviour. That is a statement about EDGES, so it was never checkable while the
artifacts sat in a directory. A graph makes "is this an organism or a pile?" a query:

    orphans      = nodes with degree 0
    organism     = size of the largest connected component / N
    dead ends    = nodes cited BY things but citing nothing (consumed, never composed)

Edges are EXTRACTED, never invented. A `cites` edge exists only when a document names a
path that actually resolves on disk. An unresolvable reference is not an edge — it is
recorded in `failures`, because a doc citing a file that does not exist is exactly the
rot this graph is meant to surface.

PRIVACY: _from_desktop / dain / minyoung / .vault / .env are excluded at the walker,
not at the writer. They never enter the process.
"""
from __future__ import annotations
import argparse, json, os, re, sqlite3, subprocess, sys, time
from collections import Counter, defaultdict
from pathlib import Path

WS = Path("/home/user/workspaces/jaewon")
DEST = Path(os.environ.get("AIOS_GRAPH_DEST", "/data/jaewon/aios"))

# HARD exclusions — privacy boundary + vendored code. Checked on every path part.
DENY_PARTS = {"_from_desktop", "dain", "minyoung", ".vault", "node_modules", ".venv",
              "venv", "site-packages", "__pycache__", ".git", ".mypy_cache", "dist",
              "build", ".pytest_cache", "lost+found"}
DENY_RE = re.compile(r"\.vault|\.env($|\.)|secrets?\.(json|ya?ml|txt)|credentials")

TEXT_EXT = {".md": "doc", ".py": "code", ".sh": "code", ".json": "data",
            ".jsonl": "data", ".toml": "config", ".yaml": "config", ".yml": "config"}

# a path-shaped reference inside prose or code
# leading dot must be kept: .aios/ and .claude/ are real directories, and stripping the dot
# silently turned every reference to them into a false "dangling" (measured: 85,802 of them).
PATH_RE = re.compile(r"(?<![A-Za-z0-9_.\-])[./]?[A-Za-z0-9_][A-Za-z0-9_./\-]{2,120}\.(?:md|py|sh|jsonl|json|toml|ya?ml)\b")
URL_RE = re.compile(r"^[A-Za-z0-9\-]+\.(?:com|org|io|net|dev|ai|co|gov|edu|sh)/")
SUPERSEDE_RE = re.compile(r"(?i)\b(supersede[sd]?|deprecat\w+|철회|폐기|무효|대체)\b")
# A Python import IS a dependency, and the path regex never saw one — `from .local_workers
# import ...` contains no ".py". That blind spot made memoryOS/memoryos/local_workers.py
# read as a graph orphan, the legacy triage archived it on four agreeing signals, and
# memoryOS's CLI stopped importing. Measured the hard way on 2026-08-19.
IMPORT_RE = re.compile(r"(?m)^\s*(?:from\s+(\.*[\w\.]+)\s+import|import\s+([\w\.]+))")
ERRATA_RE = re.compile(r"(?im)^#{1,4}\s*errata|^\*\*E\d+\s*[·.]")
STOP = set("""the a an and or of to in for on with is are was were be been by as at from that this it
its not no if then than so such can may will would should could we our us you your i me my they them
their he she his her but do does did done have has had here there what which who whom when where how
all any both each few more most other some only own same too very just also into over under again
further once out up down off above below between during before after while about against because
있다 있는 하는 하고 해서 이것 그것 저것 때문 위해 통해 대한 대해 에서 으로 로서 하며 되는 된다 한다 없다 같은 등의 및 또는 그리고 그러나""".split())
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{2,}|[가-힣]{2,}")


def denied(p: Path) -> bool:
    parts = set(p.parts)
    return bool(parts & DENY_PARTS) or bool(DENY_RE.search(str(p)))


def node_kind(rel: str, ext_kind: str) -> str:
    if "/docs/contracts/" in rel or re.search(r"ASC-\d{4}", rel):
        return "contract"
    if "/experiments/" in rel:
        return "experiment"
    if rel.endswith("_test.py") or "/tests/" in rel or "/test_" in rel:
        return "test"
    if "/.aios/" in rel:
        return "receipt"
    if "/memory/" in rel or "/drafts/" in rel:
        return "memory"
    if "/spec/" in rel:
        return "spec"
    return ext_kind


def layer_of(rel: str) -> str:
    """Which organ does this belong to — the analogue of the paper graph's layer field."""
    for repo in ("hivemind", "memoryOS", "CapabilityOS", "GenesisOS", "uri"):
        if f"/{repo}/" in f"/{rel}":
            return repo
    for d in ("docs", "scripts", "experiments", "spec", "tests", ".aios", ".claude", "gpt_sessions"):
        if rel.startswith(f"myworld/{d}/") or rel.startswith(f"{d}/"):
            return d
    return "other"


def walk(roots: list[Path], max_bytes: int) -> dict[str, dict]:
    nodes: dict[str, dict] = {}
    for root in roots:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dp = Path(dirpath)
            dirnames[:] = [d for d in dirnames if d not in DENY_PARTS and not DENY_RE.search(d)]
            if denied(dp):
                continue
            for fn in filenames:
                p = dp / fn
                ext = p.suffix.lower()
                if ext not in TEXT_EXT or denied(p):
                    continue
                try:
                    st = p.stat()
                except OSError:
                    continue
                if st.st_size > max_bytes or st.st_size == 0:
                    continue
                rel = str(p.relative_to(WS))
                nodes[rel] = {"rel": rel, "kind": node_kind(rel, TEXT_EXT[ext]),
                              "layer": layer_of(rel), "size": st.st_size,
                              "mtime": int(st.st_mtime), "abs": str(p)}
    return nodes


def resolve(ref: str, src_rel: str, index: dict[str, str]) -> str | None:
    """A reference becomes an edge only if it lands on a node we actually hold."""
    ref = ref.strip().strip("`'\"()[]<>,;:")
    if ref.startswith(str(WS) + "/"):            # absolute paths into the workspace are ours
        ref = ref[len(str(WS)) + 1:]
    elif ref.startswith("/"):                    # absolute path outside the workspace
        return None
    if ref in index:
        return index[ref]
    src_dir = str(Path(src_rel).parent)
    for cand in (f"{src_dir}/{ref}", f"myworld/{ref}",
                 f"{src_rel.split('/')[0]}/{ref}"):
        cand = str(Path(cand)) if ".." not in cand else None
        if cand and cand in index:
            return index[cand]
    hit = index.get("::base::" + Path(ref).name)
    return hit


def build(args) -> int:
    t0 = time.time()
    roots = [WS / r for r in args.roots]
    print(f"walking {len(roots)} roots …", flush=True)
    nodes = walk(roots, args.max_bytes)
    print(f"  {len(nodes)} nodes", flush=True)

    index = {rel: rel for rel in nodes}
    basename: dict[str, list[str]] = defaultdict(list)
    for rel in nodes:
        basename[Path(rel).name].append(rel)
    for name, rels in basename.items():
        if len(rels) == 1:                       # unambiguous basenames only
            index["::base::" + name] = rels[0]

    edges: set[tuple[str, str, str]] = set()
    failures: list[tuple[str, str]] = []
    concept_df: Counter = Counter()
    concept_layers: dict[str, Counter] = defaultdict(Counter)
    concept_top: dict[str, list[str]] = defaultdict(list)
    texts: dict[str, str] = {}

    for i, (rel, meta) in enumerate(nodes.items()):
        if i % 2000 == 0:
            print(f"  parsing {i}/{len(nodes)}", flush=True)
        try:
            text = Path(meta["abs"]).read_text(errors="replace")
        except OSError as e:
            failures.append((rel, f"read: {type(e).__name__}"))
            continue
        if meta["kind"] in ("doc", "spec", "contract", "experiment"):
            texts[rel] = text[:400_000]
        # --- cites -------------------------------------------------------------
        seen_refs = set()
        for m in PATH_RE.finditer(text):
            ref = m.group(0)
            if ref in seen_refs:
                continue
            seen_refs.add(ref)
            if URL_RE.match(ref) or "://" in text[max(0, m.start() - 3):m.start() + 3]:
                continue                         # a URL is not a path reference
            dst = resolve(ref, rel, index)
            if dst is None:
                if "/" in ref:                   # bare filenames are too noisy to call rot
                    # a transcript proposing an architecture is not rot; a doc of ours citing a
                    # file of ours that does not exist is. Keep them apart or the number lies.
                    kindf = "proposed_ref" if "gpt_sessions" in rel or "ChatGPT" in rel else "dangling_ref"
                    failures.append((rel, f"{kindf}: {ref[:100]}"))
                continue
            if dst != rel:
                kind = "supersedes" if SUPERSEDE_RE.search(
                    text[max(0, m.start() - 160):m.start()]) else "cites"
                edges.add((rel, dst, kind))
        # --- python imports as edges -------------------------------------------
        if meta["kind"] in ("code", "test"):
            pkg_dir = str(Path(rel).parent)
            for m in IMPORT_RE.finditer(text):
                mod = (m.group(1) or m.group(2) or "").strip()
                if not mod:
                    continue
                leaf = mod.lstrip(".").split(".")[-1]
                if not leaf:
                    continue
                for cand in (f"{pkg_dir}/{leaf}.py", f"{pkg_dir}/{leaf}/__init__.py"):
                    if cand in index and cand != rel:
                        edges.add((rel, cand, "imports"))
                        break
                else:
                    hit = index.get("::base::" + leaf + ".py")
                    if hit and hit != rel:
                        edges.add((rel, hit, "imports"))

        # --- concepts ----------------------------------------------------------
        if rel in texts:
            # phrases, not tokens. Single tokens rank generic vocabulary ("run", "status",
            # "use") at the top and say nothing; the peer paper graph keys on phrases
            # ("robotic manipulation") for exactly this reason.
            seq = [t.lower() for t in TOKEN_RE.findall(texts[rel])]
            grams = set()
            for n in (2, 3):
                for i in range(len(seq) - n + 1):
                    g = seq[i:i + n]
                    if g[0] in STOP or g[-1] in STOP:
                        continue          # phrases must not start or end on a stopword
                    if any(x.isdigit() for x in g):
                        continue
                    grams.add(" ".join(g))
            # keep a unigram only when it is not ordinary vocabulary
            for t in set(seq):
                if t not in STOP and not t.isdigit() and len(t) > 3 and (
                        "_" in t or t.endswith("os") or re.match(r"^[a-z]+\d", t)):
                    grams.add(t)
            for t in grams:
                concept_df[t] += 1
                concept_layers[t][meta["layer"]] += 1
                if len(concept_top[t]) < 5:
                    concept_top[t].append(rel)

    print(f"  {len(edges)} path edges, {len(failures)} dangling", flush=True)

    # --- git provenance: commit -> file ----------------------------------------
    commits = 0
    for repo in args.roots:
        rp = WS / repo
        if not (rp / ".git").exists():
            continue
        try:
            log = subprocess.run(
                ["git", "-C", str(rp), "log", f"--max-count={args.commits}",
                 "--pretty=format:@@%H|%at|%s", "--name-only"],
                capture_output=True, text=True, timeout=180).stdout
        except Exception as e:
            failures.append((repo, f"git: {type(e).__name__}"))
            continue
        cur = None
        for line in log.splitlines():
            if line.startswith("@@"):
                h, at, subj = line[2:].split("|", 2)
                cur = f"commit:{h[:12]}"
                nodes[cur] = {"rel": cur, "kind": "commit", "layer": "git",
                              "size": 0, "mtime": int(at), "abs": "", "title": subj[:200]}
                commits += 1
            elif line.strip() and cur:
                cand = f"{repo}/{line.strip()}"
                if cand in nodes:
                    edges.add((cur, cand, "produces"))
    print(f"  {commits} commits", flush=True)

    # --- write, mirroring the robotics layout ----------------------------------
    (DEST / "index").mkdir(parents=True, exist_ok=True)
    (DEST / "ontology").mkdir(parents=True, exist_ok=True)
    db = DEST / "index" / "aios.db"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.executescript("""
        create table nodes(id text primary key, kind text, layer text, size int,
                           mtime int, title text);
        create table edges(src text, dst text, kind text);
        create table fulltext(id text primary key, text text, n_chars int);
        create table failures(id text, reason text, at int);
        create index idx_e_src on edges(src);
        create index idx_e_dst on edges(dst);
        create index idx_n_kind on nodes(kind);
        create index idx_n_layer on nodes(layer);
    """)
    con.executemany("insert or replace into nodes values (?,?,?,?,?,?)",
                    [(r, m["kind"], m["layer"], m["size"], m["mtime"], m.get("title", ""))
                     for r, m in nodes.items()])
    con.executemany("insert into edges values (?,?,?)", sorted(edges))
    con.executemany("insert or replace into fulltext values (?,?,?)",
                    [(r, t, len(t)) for r, t in texts.items()])
    now = int(time.time())
    con.executemany("insert into failures values (?,?,?)",
                    [(a, b, now) for a, b in failures])
    con.commit()

    onto = DEST / "ontology" / "ontology.jsonl"
    with onto.open("w") as fh:
        for name, df in concept_df.most_common():
            if df < args.min_df:
                break
            fh.write(json.dumps({"type": "concept", "name": name, "df": df,
                                 "layers": dict(concept_layers[name]),
                                 "top_nodes": concept_top[name]}, ensure_ascii=False) + "\n")
    con.close()
    print(f"\nwrote {db} ({db.stat().st_size/1e6:.1f} MB) and {onto}")
    print(f"elapsed {time.time()-t0:.0f}s")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="*", default=["myworld"])
    ap.add_argument("--max-bytes", type=int, default=2_000_000)
    ap.add_argument("--commits", type=int, default=4000)
    ap.add_argument("--min-df", type=int, default=3)
    return build(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())
