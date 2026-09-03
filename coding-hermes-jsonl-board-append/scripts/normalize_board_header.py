#!/usr/bin/env python3
"""Normalize a pretty-printed board.jsonl header + rebuild board.db caches + parity probe.

Board-storage-canonical doctrine (Bane 08-07) mandates STRICT single-line JSONL
headers. ANY writer other than the stock append script — a hand-rolled agent
script, a sibling/orphan foreman chain, a bootstrap — can re-pretty-print the
header (indent=2, \\uXXXX escapes) and churn the diff. This script restores the
canonical shape and re-syncs the rebuildable caches in one shot.

Usage:
    python3 normalize_board_header.py <repo-dir>

Proven: ai-plays-poke T101 (2026-08-07) — an orphan worker chain's board commit
re-pretty-printed board.jsonl to 24 lines (\\u00e9 escapes) + left board.db
diverged (jsonl 57 rows vs db 54); this recipe restored 1 line + parity MATCH.
"""
import json
import subprocess
import sys

repo = sys.argv[1] if len(sys.argv) > 1 else "."
BOARD = f"{repo}/.coding-hermes/board"
VENV_PY = "~/.hermes/venvs/board/bin/python3"
REBUILD = "~/.hermes/skills/database/coding-hermes-jsonl-board-append/scripts/rebuild_board_caches.py"
PROBE = "~/.hermes/skills/coding-hermes-foreman/scripts/board_jsonl_parity_probe.py"


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"FAILED: {' '.join(cmd)}\n{r.stderr[-600:]}")
    return r.stdout


# 1. Rebuild board.db + parquet caches from JSONL (authoritative tracked store)
run([VENV_PY, REBUILD, repo])

# 2. Normalize header: parse whole file (tolerant of pretty), write strict single-line
path = f"{BOARD}/board.jsonl"
raw = open(path, encoding="utf-8").read()
hdr = json.loads(raw)
hdr.setdefault("updated_at", hdr.get("last_tick_at"))
line = json.dumps(hdr, ensure_ascii=False, separators=(",", ":")) + "\n"
open(path, "w", encoding="utf-8").write(line)
print(f"header: {len(raw.splitlines())} lines -> 1")

# 3. Parity probe must MATCH
print(run([VENV_PY, PROBE, BOARD]).strip().splitlines()[-2:])
print("OK — commit the board files (board.jsonl may be the only tracked change)")
