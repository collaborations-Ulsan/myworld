#!/bin/sh
# A conforming participant in ~60 lines of POSIX shell.
#
# The seam spec claims a foreign implementation, linking none of our code, can
# produce artifacts that pass `scripts/aios_conform.py`. A claim like that is
# worth nothing until something cashes it, so this is the cheapest possible
# cash: /bin/sh and sha256sum, no Python, no imports, no library.
#
# It matters for a reason beyond tidiness. If passing our checker required our
# code, then "conformance" would mean "runs our stack" and nobody outside would
# ever adopt it. Every clause below was re-derived from the written rule, and
# the Merkle root it computes has to agree with the one our Python producer
# computes over the same lines — byte for byte, or the spec is underspecified.
#
#   sh spec/examples/producer.sh /tmp/demo
#   python3 scripts/aios_conform.py /tmp/demo/receipts.jsonl --ledger /tmp/demo/ledger.jsonl
#
# Exit 0 on success. The two artifacts land in $1 (default: ./demo-participant).

set -eu

OUT="${1:-./demo-participant}"
mkdir -p "$OUT"
LEDGER="$OUT/ledger.jsonl"
RECEIPTS="$OUT/receipts.jsonl"
: > "$LEDGER"
: > "$RECEIPTS"

sha() { sha256sum | cut -d' ' -f1; }

# spec 1: leaf(i, line) = sha256( decimal(i) || 0x00 || line ).
# The NUL goes straight down the pipe — a shell variable cannot hold one, which
# is exactly why it is written to the hasher rather than assembled first.
leaf() { printf '%s\000%s' "$1" "$2" | sha; }

# spec 1: sort the leaves, fold pairs, an odd tail element pairs with ITSELF.
# `a` and `b` are the leaf strings INCLUDING their sha256: prefix, concatenated
# as text — re-hashing raw digests instead would silently diverge from Python.
root() {
    if [ ! -s "$1" ]; then printf 'sha256:%s' "$(printf '' | sha)"; return; fi
    layer=$(i=0; while IFS= read -r line; do
                printf 'sha256:%s\n' "$(leaf "$i" "$line")"; i=$((i + 1))
            done < "$1" | sort)
    while [ "$(printf '%s\n' "$layer" | wc -l)" -gt 1 ]; do
        layer=$(printf '%s\n' "$layer" | {
            while IFS= read -r a; do
                IFS= read -r b || b="$a"
                printf 'sha256:%s\n' "$(printf '%s%s' "$a" "$b" | sha)"
            done; })
    done
    printf '%s' "$layer"
}

emit() {                       # emit <verdict> <outcome> <claim>
    before=$(root "$LEDGER")
    printf '{"claim":"%s","verdict":"%s"}\n' "$3" "$2" >> "$LEDGER"
    after=$(root "$LEDGER")
    # spec 2: every clause is present because dropping it admits a fake. A
    # foreign producer that cannot honestly set model_consulted=false and
    # invoked_by=host has not done the cycle and should not claim it.
    printf '{"schema":"aios.minimal_operation.v1",'
    printf '"sense":{"predicate":"source_newer_than_cursor","evaluated_by":"policy",'
    printf '"input_digest":"sha256:%s","model_consulted":false},' \
        "$(printf '%s' "$3" | sha)"
    printf '"act":{"operator":"sh-demo-producer","invoked_by":"host",'
    printf '"model_offered_choice":false,"executes_code":false},'
    printf '"verify":{"oracle_cmd_digest":"sha256:%s","verdict":"%s",' \
        "$(printf 'grep -qF' | sha)" "$1"
    printf '"verifier_identity":"grep(1)","isolation":"separate_process"},'
    printf '"settle":{"outcome":"%s","root_before":"%s","root_after":"%s"}}\n' \
        "$2" "$before" "$after"
}

# Two cycles, and the second one is the point: a producer that only emits
# receipts when it succeeds has not demonstrated a verified cycle, so the
# rejection path is exercised here too and lands on the ledger.
emit pass committed  "the quoted span was found in the source"   >> "$RECEIPTS"
emit fail reverted   "the quoted span was NOT found in the source" >> "$RECEIPTS"

printf 'wrote %s and %s\n' "$LEDGER" "$RECEIPTS"
printf 'final root: %s\n' "$(root "$LEDGER")"
