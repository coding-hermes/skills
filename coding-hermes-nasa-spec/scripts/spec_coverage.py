#!/usr/bin/env python3
"""Structural coverage gate for a design spec tree.

Usage:
    python3 spec_coverage.py <specs_dir> [--json] [--strict] [--quiet]

The spec tree is a directory of markdown files. IDs are declared in headings:

    ### FLOW-01 — Mint a session token
    ### MOD-03 — Token broker
    #### SUB-03.2 — Signature verifier
    ### CT-07 — POST /v1/tokens

and in tables:

    | FACT-12 | claim | how measured | when | confidence |
    | R-014  | statement | module: MOD-03 | test: TestX | fact: FACT-12 |

Metadata lives in `key: value` lines inside the declaration block:

    flow: FLOW-01          (required on MOD)
    module: MOD-03         (required on SUB)
    producer: MOD-03       (>=1 required on CT)
    consumer: MOD-05       (>=1 required on CT)
    leaf: yes              (MOD with no SUB needs this)
    trigger: ...           (required on FLOW)
    exit: ...              (required on FLOW)

Exit codes: 0 clean, 1 errors (or warnings with --strict), 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

DECL = {
    "flow": re.compile(r"^#{1,6}\s+(FLOW-\d+)\b"),
    "mod": re.compile(r"^#{1,6}\s+(MOD-\d+)\b"),
    "sub": re.compile(r"^#{1,6}\s+(SUB-\d+(?:\.\d+)?)\b"),
    "ct": re.compile(r"^#{1,6}\s+(CT-\d+)\b"),
}
FACT_ROW = re.compile(r"^\|\s*(FACT-\d+)\s*\|")
REQ_ROW = re.compile(r"^\|\s*(R-\d+)\s*\|")
META_LINE = re.compile(
    r"^\s*(flow|module|producer|consumer|leaf|trigger|exit|owns|does-not-own)\s*:\s*(.+?)\s*$"
)
FACT_REF = re.compile(r"\bFACT-\d+\b")
ID_IN_META = {
    "flow": re.compile(r"FLOW-\d+"),
    "module": re.compile(r"MOD-\d+"),
    "producer": re.compile(r"MOD-\d+"),
    "consumer": re.compile(r"MOD-\d+"),
}
ASSERTION = re.compile(r"\b(test|check)\s*:\s*(\S.*)$")
# A runnable assertion names a test, a script, or a grep-able marker — never a
# phrase. Prose that merely contains "check:" used to satisfy the gate.
ASSERTION_TARGET = re.compile(r"^[A-Za-z0-9_./:@<>+=-]+$")


def row_cells(row: str) -> list[str]:
    """Split a markdown table row into stripped cells, honouring `\\|` escapes."""
    body = row.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    return [cell.strip() for cell in re.split(r"(?<!\\)\|", body)]


@dataclass
class Decl:
    kind: str
    ident: str
    file: str
    line: int
    meta: dict[str, list[str]] = field(default_factory=dict)

    def get(self, key: str) -> list[str]:
        return self.meta.get(key, [])


@dataclass
class Req:
    ident: str
    file: str
    line: int
    text: str


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def parse(specs: Path) -> tuple[dict[str, list[Decl]], list[Req], dict[str, list[str]]]:
    decls: dict[str, list[Decl]] = {"flow": [], "mod": [], "sub": [], "ct": []}
    facts: dict[str, list[str]] = {}
    reqs: list[Req] = []

    files = sorted(p for p in specs.rglob("*.md") if p.is_file())
    if not files:
        raise SystemExit(f"no markdown files under {specs}")

    for path in files:
        rel = str(path.relative_to(specs))
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError as exc:  # pragma: no cover - unreadable file
            raise SystemExit(f"cannot read {path}: {exc}") from exc

        # index declaration lines so a block ends at the next declaration
        decl_at: list[tuple[int, str, str]] = []
        for i, line in enumerate(lines):
            for kind, rx in DECL.items():
                m = rx.match(line)
                if m:
                    decl_at.append((i, kind, m.group(1)))
                    break
        decl_at.sort()

        for n, (i, kind, ident) in enumerate(decl_at):
            end = decl_at[n + 1][0] if n + 1 < len(decl_at) else len(lines)
            d = Decl(kind, ident, rel, i + 1)
            for line in lines[i + 1 : end]:
                m = META_LINE.match(line)
                if m:
                    d.meta.setdefault(m.group(1), []).append(m.group(2))
            decls[kind].append(d)

        for i, line in enumerate(lines):
            m = FACT_ROW.match(line)
            if m:
                facts.setdefault(m.group(1), []).append(f"{rel}:{i + 1}")
            m = REQ_ROW.match(line)
            if m:
                reqs.append(Req(m.group(1), rel, i + 1, line))
    return decls, reqs, facts


def check(specs: Path) -> Report:
    rep = Report()
    decls, reqs, facts = parse(specs)

    # --- unique ids -----------------------------------------------------
    seen: dict[str, Decl] = {}
    for kind in ("flow", "mod", "sub", "ct"):
        for d in decls[kind]:
            if d.ident in seen:
                first = seen[d.ident]
                rep.err(
                    f"duplicate id {d.ident}: declared at {first.file}:{first.line} "
                    f"and {d.file}:{d.line}"
                )
            else:
                seen[d.ident] = d

    flows = {d.ident: d for d in decls["flow"]}
    mods = {d.ident: d for d in decls["mod"]}
    subs = {d.ident: d for d in decls["sub"]}
    cts = {d.ident: d for d in decls["ct"]}

    # --- flows declare trigger + exit ------------------------------------
    for f in flows.values():
        if not f.get("trigger"):
            rep.err(f"{f.ident} ({f.file}:{f.line}) has no `trigger:` line")
        if not f.get("exit"):
            rep.err(f"{f.ident} ({f.file}:{f.line}) has no `exit:` line")

    # --- modules attach to a real flow -----------------------------------
    modules_per_flow: dict[str, int] = {f: 0 for f in flows}
    modules_per_ct: dict[str, int] = {c: 0 for c in cts}
    for m in mods.values():
        flow_ids = ID_IN_META["flow"].findall(" ".join(m.get("flow")))
        if not flow_ids:
            rep.err(f"{m.ident} ({m.file}:{m.line}) has no `flow:` line")
        for fid in flow_ids:
            if fid not in flows:
                rep.err(f"{m.ident} ({m.file}:{m.line}) names unknown {fid}")
            else:
                modules_per_flow[fid] += 1
        if not m.get("owns"):
            rep.warn(f"{m.ident} ({m.file}:{m.line}) has no `owns:` line")

    for fid, count in modules_per_flow.items():
        if count == 0:
            rep.warn(f"{fid} ({flows[fid].file}:{flows[fid].line}) has no modules")

    # --- submodules attach to a real module ------------------------------
    subs_per_mod: dict[str, int] = {m: 0 for m in mods}
    for s in subs.values():
        mod_ids = ID_IN_META["module"].findall(" ".join(s.get("module")))
        if not mod_ids:
            rep.err(f"{s.ident} ({s.file}:{s.line}) has no `module:` line")
        for mid in mod_ids:
            if mid not in mods:
                rep.err(f"{s.ident} ({s.file}:{s.line}) names unknown {mid}")
            else:
                subs_per_mod[mid] += 1

    for mid, count in subs_per_mod.items():
        if count:
            continue
        leaf = " ".join(mods[mid].get("leaf")).strip().lower()
        if leaf not in {"yes", "true", "1"}:
            rep.warn(
                f"{mid} ({mods[mid].file}:{mods[mid].line}) has no submodules and "
                "no `leaf: yes`"
            )

    # --- contracts have producer and consumer ----------------------------
    for c in cts.values():
        prods = ID_IN_META["producer"].findall(" ".join(c.get("producer")))
        cons = ID_IN_META["consumer"].findall(" ".join(c.get("consumer")))
        if not prods:
            rep.err(f"{c.ident} ({c.file}:{c.line}) has no `producer:` line")
        if not cons:
            rep.err(f"{c.ident} ({c.file}:{c.line}) has no `consumer:` line")
        for pid in prods + cons:
            if pid not in mods:
                rep.err(f"{c.ident} ({c.file}:{c.line}) names unknown {pid}")
            else:
                modules_per_ct[c.ident] += 1

    # --- requirements ----------------------------------------------------
    req_seen: dict[str, Req] = {}
    for r in reqs:
        if r.ident in req_seen:
            first = req_seen[r.ident]
            rep.err(
                f"duplicate id {r.ident}: declared at {first.file}:{first.line} "
                f"and {r.file}:{r.line}"
            )
            continue
        req_seen[r.ident] = r

        # Column layout is part of the contract: the assertion must be the 4th
        # cell and the evidence the 5th. Counting `test:`/`check:` anywhere in
        # the row lets prose satisfy the gate — regression: "prose assertion"
        # in scripts/test_spec_coverage.py.
        cells = row_cells(r.text)
        if len(cells) != 5:
            rep.err(
                f"{r.ident} ({r.file}:{r.line}) has {len(cells)} columns; a requirement "
                "row needs exactly 5: `| id | statement-or-module | flow | assertion | evidence |`"
            )
            continue

        attach, assertion_cell, evidence_cell = cells[1:3], cells[3], cells[4]
        attach_text = " ".join(attach)

        module_ids = ID_IN_META["module"].findall(attach_text)
        if not module_ids:
            rep.err(f"{r.ident} ({r.file}:{r.line}) has no `module: MOD-nn` in its attach column")
        for mid in module_ids:
            if mid not in mods:
                rep.err(f"{r.ident} ({r.file}:{r.line}) names unknown {mid}")

        stray = re.findall(r"\b(?:test|check)\s*:", " ".join([*attach, evidence_cell]))
        if stray:
            rep.err(
                f"{r.ident} ({r.file}:{r.line}) names an assertion outside the assertion "
                "column; prose does not satisfy the gate"
            )

        assertions = re.findall(r"\b(?:test|check)\s*:", assertion_cell)
        if len(assertions) != 1:
            rep.err(
                f"{r.ident} ({r.file}:{r.line}) has {len(assertions)} assertions "
                "(exactly one `test:` or `check:` is required)"
            )
        else:
            target = re.sub(r"^\s*(?:test|check)\s*:\s*", "", assertion_cell).strip()
            if not target:
                rep.err(f"{r.ident} ({r.file}:{r.line}) has an empty assertion")
            elif not ASSERTION_TARGET.match(target):
                rep.err(
                    f"{r.ident} ({r.file}:{r.line}) assertion target {target!r} is not "
                    "runnable; name a test or a check, not a description"
                )

        if not re.search(r"\b(?:fact|decision)\s*:\s*\S", evidence_cell):
            rep.err(
                f"{r.ident} ({r.file}:{r.line}) has no `fact: FACT-nn` or "
                "`decision:` evidence in its evidence column"
            )

        for fid in re.findall(r"\bfact\s*:\s*(FACT-\d+)", evidence_cell):
            if fid not in facts:
                rep.err(f"{r.ident} ({r.file}:{r.line}) cites missing {fid}")

    if not reqs:
        rep.err("no requirements found (expected a table of `| R-nnn | ... |` rows)")

    # --- advisory: facts nobody cites ------------------------------------
    corpus = "\n".join(
        p.read_text(encoding="utf-8", errors="replace")
        for p in sorted(specs.rglob("*.md"))
    )
    for fid, where in facts.items():
        if len(FACT_REF.findall(corpus)) and len(re.findall(rf"\bfact\s*:\s*{fid}\b", corpus)) == 0:
            rep.warn(f"{fid} ({where[0]}) is declared but cited by no requirement")

    return rep


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="design-spec coverage gate")
    ap.add_argument("specs_dir", type=Path)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true", help="warnings fail the run")
    ap.add_argument("--quiet", action="store_true", help="only the summary line")
    args = ap.parse_args(argv)

    if not args.specs_dir.is_dir():
        print(f"error: {args.specs_dir} is not a directory", file=sys.stderr)
        return 2

    rep = check(args.specs_dir)
    failed = bool(rep.errors) or (args.strict and bool(rep.warnings))

    if args.json:
        print(
            json.dumps(
                {
                    "specs_dir": str(args.specs_dir),
                    "errors": rep.errors,
                    "warnings": rep.warnings,
                    "ok": not failed,
                },
                indent=2,
            )
        )
    else:
        if not args.quiet:
            for msg in rep.errors:
                print(f"ERROR   {msg}")
            for msg in rep.warnings:
                print(f"WARN    {msg}")
        verdict = "FAIL" if failed else "PASS"
        print(
            f"{verdict}  {len(rep.errors)} error(s), {len(rep.warnings)} warning(s) "
            f"— {args.specs_dir}"
        )

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
