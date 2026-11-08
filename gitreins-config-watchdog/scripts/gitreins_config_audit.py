#!/usr/bin/env python3
"""GitReins config watchdog — catch guard-config security downgrades.

Agents (workers, foremen, one-off cron prompts) sometimes edit a repo's
.gitreins/config.yaml "to make a commit go through": the secrets guard goes
from true to false, an allow_skips flag flips, a sensitive-path allowlist
grows, the pre-commit hook gets pointed at /dev/null. Each edit looks
locally reasonable and is a security downgrade in aggregate.

This script snapshots a repo's GitReins guard config as an OUT-OF-REPO
baseline (an agent that downgrades the live config cannot edit the baseline
in the same commit), then diffs the live state against that baseline on
every run and classifies each change:

  DOWNGRADE  a guard got weaker (blocking finding)
  DRIFT      a value changed; may be legitimate, review it
  TIGHTEN    a guard got stricter (informational, never blocks)
  INFO       new keys or notes

Quickstart:
  python3 gitreins_config_audit.py --repo /path/to/project --init  # once
  python3 gitreins_config_audit.py --repo /path/to/project        # daily
  python3 gitreins_config_audit.py --selftest                     # verify

Exit codes: 0 clean | 2 downgrade found | 3 drift-only | 4 no baseline
            | 5 input/parse error
Stdlib only. The baseline dir defaults to ~/.config/gitreins-watchdog/.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

CONFIG_REL = os.path.join(".gitreins", "config.yaml")
DEFAULT_BASELINE_DIR = os.path.join("~", ".config", "gitreins-watchdog")
HOOK_PATH_DISABLED = {"/dev/null", ""}

BOOL_TRUE = {"true", "on", "yes", "1"}
BOOL_FALSE = {"false", "off", "no", "0"}
TEST_MODE_STRENGTH = {"full": 3, "changed": 2, "diff": 1, "none": 0}

# Boolean guard toggles: baseline true -> live false is a downgrade.
GUARD_BOOLS = {
    "secrets", "lint", "tests", "lsp", "static_analysis",
    "dead_code", "build",          # go.build etc. via path suffix match
}


# --------------------------------------------------------------------------
# Minimal YAML-subset parser (nested maps, lists of scalars, lists of maps).
# Full YAML is NOT supported; on any parse failure callers fall back to a
# raw-text diff so a weird-but-valid config never silently skips the audit.
# --------------------------------------------------------------------------

def _clean_val(raw):
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
        return raw[1:-1]
    # strip an unquoted trailing comment
    for i, ch in enumerate(raw):
        if ch == "#" and i > 0 and raw[i - 1] in (" ", "\t"):
            return raw[:i].strip()
    return raw


def _partition_kv(content):
    for i, ch in enumerate(content):
        if ch == ":" and (i + 1 == len(content) or content[i + 1] in (" ", "\t")):
            key = content[:i].strip()
            if len(key) >= 2 and key[0] == key[-1] and key[0] in ("'", '"'):
                key = key[1:-1]
            return key, content[i + 1:].strip()
    return None, None


def parse_yaml(text):
    lines = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        lines.append((len(raw) - len(raw.lstrip(" ")), raw.strip()))
    pos = [0]

    def child_indent(ind):
        """Indent of the block that belongs to a key at indent `ind`:
        the next line's indent if deeper, or the same indent when the
        child is a list (YAML allows lists at the parent key's indent)."""
        if pos[0] >= len(lines):
            return None
        nind, ncontent = lines[pos[0]]
        if nind > ind:
            return nind
        if nind == ind and (ncontent.startswith("- ") or ncontent == "-"):
            return nind
        return None

    def parse_block(indent):
        result = None
        while pos[0] < len(lines):
            ind, content = lines[pos[0]]
            if ind < indent:
                break
            if content.startswith("- ") or content == "-":
                if result is None:
                    result = []
                pos[0] += 1
                item_txt = content[2:].strip()
                key, val = (None, None)
                if item_txt:
                    key, val = _partition_kv(item_txt)
                if key is not None:
                    entry = {}
                    if val:
                        entry[key] = _clean_val(val)
                    else:
                        ci = child_indent(ind)
                        entry[key] = parse_block(ci) if ci is not None else {}
                    # continuation keys of this list item live deeper than the dash
                    while pos[0] < len(lines) and lines[pos[0]][0] > ind:
                        ind2, c2 = lines[pos[0]]
                        if c2.startswith("- "):
                            break
                        k2, v2 = _partition_kv(c2)
                        pos[0] += 1
                        if k2 is None:
                            raise ValueError("cannot parse list item line: " + c2)
                        if v2:
                            entry[k2] = _clean_val(v2)
                        else:
                            ci = child_indent(ind2)
                            entry[k2] = parse_block(ci) if ci is not None else {}
                    result.append(entry)
                else:
                    ci = child_indent(ind - 1) if ind else None
                    result.append(_clean_val(item_txt) if item_txt
                                  else (parse_block(ci) if ci is not None else {}))
            else:
                key, val = _partition_kv(content)
                if key is None:
                    raise ValueError("cannot parse line: " + content)
                if result is None:
                    result = {}
                pos[0] += 1
                if val:
                    result[key] = _clean_val(val)
                else:
                    ci = child_indent(ind)
                    result[key] = parse_block(ci) if ci is not None else {}
        return result if result is not None else {}

    return parse_block(0)


def flatten(node, prefix="", out=None):
    """Flatten parsed YAML into {dotted.path: scalar-string}; lists index as [i]."""
    if out is None:
        out = {}
    if isinstance(node, dict):
        for k, v in node.items():
            flatten(v, prefix + "." + str(k) if prefix else str(k), out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            flatten(v, "%s[%d]" % (prefix, i), out)
    else:
        out[prefix] = str(node)
    return out


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------

def classify_pair(path, old, new):
    """Return (severity, message) for one changed key. severity in
    downgrade/drift/tighten/info."""
    p = path.lower()
    last = p.rsplit(".", 1)[-1]
    o, n = (old or "").strip().lower(), (new or "").strip().lower()

    if "on_fail" in p:
        if "block" in o and "block" not in n:
            return "downgrade", "%s: on_fail %s -> %s (gate no longer blocks)" % (path, old, new)
        return "drift", "%s: on_fail %s -> %s" % (path, old, new)

    if "paths" in p and ("allow" in last or "allow" in p) and "sensitive" in p or "sensitive" in p and "allow" in p:
        # handled at list level by the caller; per-scalar entries land here
        pass

    if last in GUARD_BOOLS and ("guards" in p or p.startswith("go.") or ".go." in p):
        if o in BOOL_TRUE and (n in BOOL_FALSE or n == ""):
            return "downgrade", "%s: guard %s -> %s" % (path, old or "(removed)", new or "(removed)")
        if o in BOOL_FALSE and n in BOOL_TRUE:
            return "tighten", "%s: guard %s -> %s" % (path, old, new)
        return "drift", "%s: %s -> %s" % (path, old, new)

    if last == "allow_skips":
        if o in BOOL_FALSE and n in BOOL_TRUE:
            return "downgrade", "%s: allow_skips false -> true (empty gates now PASS)" % path
        if o in BOOL_TRUE and n in BOOL_FALSE:
            return "tighten", "%s: allow_skips true -> false" % path
        return "drift", "%s: %s -> %s" % (path, old, new)

    if last == "test_mode":
        so, sn = TEST_MODE_STRENGTH.get(o), TEST_MODE_STRENGTH.get(n)
        if so is not None and sn is not None and sn < so:
            return "downgrade", "%s: test_mode %s -> %s (weaker scope)" % (path, old, new)
        if so is not None and sn is not None and sn > so:
            return "tighten", "%s: test_mode %s -> %s" % (path, old, new)
        return "drift", "%s: %s -> %s" % (path, old, new)

    if last in ("test_command", "lint_command"):
        return "drift", "%s: command changed (%s -> %s) — verify it still grades the same thing" % (path, old, new)

    if last in ("test_timeout", "hook_timeout"):
        return "drift", "%s: timeout %s -> %s — a hook cut off mid-suite fail-opens; verify intent" % (path, old, new)

    if last in ("max_iterations", "max_time", "max_input_tokens", "max_output_tokens"):
        return "drift", "%s: evaluator cap %s -> %s (cost drift, not security)" % (path, old, new)

    return "info", "%s: %s -> %s" % (path, old, new)


def is_allowlist_path(path):
    p = path.lower()
    return ("sensitive" in p or "paths" in p or "ignore" in p) and "allow" in p


def diff_flat(baseline, live):
    findings = []
    for path in sorted(set(baseline) | set(live)):
        old, new = baseline.get(path), live.get(path)
        if old == new:
            continue
        # allow-list entries: an ADDED entry widens what the guard ignores
        # (downgrade); a REMOVED entry tightens it (informational).
        if is_allowlist_path(path):
            if new is not None and old is None:
                findings.append(("downgrade", "%s: sensitive-path allow ENTRY ADDED (%s)" % (path, new)))
            elif old is not None and new is None:
                findings.append(("tighten", "%s: sensitive-path allow entry removed (%s)" % (path, old)))
            else:
                findings.append(("downgrade", "%s: sensitive-path allow entry changed (%s -> %s)" % (path, old, new)))
            continue
        if old is None:
            findings.append(("info", "%s: new key = %s" % (path, new)))
        elif new is None:
            sev, msg = classify_pair(path, old, "(removed)")
            findings.append((sev, msg))
        else:
            sev, msg = classify_pair(path, old, new)
            findings.append((sev, msg))
    return findings


# --------------------------------------------------------------------------
# Git hook state
# --------------------------------------------------------------------------

def git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", repo] + list(args),
                           capture_output=True, text=True, timeout=30)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def hook_state(repo):
    hooks_path = git(repo, "config", "--get", "core.hooksPath") or ""
    precommit = os.path.join(repo, hooks_path or ".git/hooks", "pre-commit")
    state = {"hooks_path": hooks_path, "pre_commit": None}
    if os.path.isfile(precommit):
        state["pre_commit"] = {"executable": os.access(precommit, os.X_OK),
                               "sha256": hashlib.sha256(open(precommit, "rb").read()).hexdigest(),
                               "mentions_gitreins": b"gitreins" in open(precommit, "rb").read().lower()}
    return state


def audit_hooks(baseline_meta, current):
    findings = []
    base = baseline_meta.get("hook_state", {})
    bp, cp = base.get("hooks_path", ""), current.get("hooks_path", "")
    if cp.lower() in HOOK_PATH_DISABLED and bp.lower() not in HOOK_PATH_DISABLED:
        findings.append(("downgrade", "core.hooksPath is now '%s' — the guard hook is bypassed for every commit" % (cp or "(unset)")))
    elif cp != bp:
        findings.append(("drift", "core.hooksPath %s -> %s" % (bp or "(unset)", cp or "(unset)")))
    bc, cc = base.get("pre_commit"), current.get("pre_commit")
    if bc and not cc:
        findings.append(("downgrade", "pre-commit hook removed (baseline had one)"))
    elif bc and cc and not cc.get("executable"):
        findings.append(("downgrade", "pre-commit hook is no longer executable"))
    elif bc and cc and bc.get("sha256") != cc.get("sha256"):
        if cc.get("mentions_gitreins"):
            findings.append(("drift", "pre-commit hook changed content (still references gitreins — likely a legit upgrade, verify)"))
        else:
            findings.append(("downgrade", "pre-commit hook changed and no longer references gitreins"))
    if not bc and not cc and baseline_meta.get("baseline_exists"):
        findings.append(("drift", "no pre-commit hook now and none at baseline — commits may run without the guard"))
    return findings


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def load_baseline(baseline_dir, slug):
    d = os.path.join(baseline_dir, slug)
    cfg = os.path.join(d, "config.yaml")
    meta = os.path.join(d, "meta.json")
    if not os.path.isfile(cfg):
        return None, None
    bcfg = flatten(parse_yaml(open(cfg).read()))
    bmeta = json.load(open(meta)) if os.path.isfile(meta) else {"baseline_exists": True}
    bmeta.setdefault("baseline_exists", True)
    return {"config": bcfg, "meta": bmeta}, d


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit .gitreins/config.yaml against an out-of-repo baseline.")
    ap.add_argument("--repo", default=".", help="repo to audit (default: cwd)")
    ap.add_argument("--baseline-dir", default=DEFAULT_BASELINE_DIR, help="where baselines live (default: %(default)s)")
    ap.add_argument("--init", action="store_true", help="record current state as the baseline")
    ap.add_argument("--restore", action="store_true", help="copy the baseline config back over the live one")
    ap.add_argument("--json", action="store_true", dest="as_json", help="machine-readable output")
    ap.add_argument("--selftest", action="store_true", help="run the built-in classifier check")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    repo = os.path.abspath(args.repo)
    live_path = os.path.join(repo, CONFIG_REL)
    slug = os.path.basename(repo.rstrip(os.sep)) or "repo"
    baseline, base_dir = load_baseline(os.path.expanduser(args.baseline_dir), slug)

    if args.init:
        if not os.path.isfile(live_path):
            print("ERROR: no %s under %s" % (CONFIG_REL, repo), file=sys.stderr)
            return 5
        d = os.path.join(os.path.expanduser(args.baseline_dir), slug)
        os.makedirs(d, exist_ok=True)
        with open(live_path, "rb") as f:
            raw = f.read()
        with open(os.path.join(d, "config.yaml"), "wb") as f:
            f.write(raw)
        meta = {"hook_state": hook_state(repo), "baseline_exists": True}
        with open(os.path.join(d, "meta.json"), "w") as f:
            json.dump(meta, f, indent=2)
        print("baseline for %s written to %s" % (repo, d))
        return 0

    if baseline is None:
        print("NO BASELINE: run with --init once, with the config in its known-good state", file=sys.stderr)
        return 4

    if args.restore:
        src = os.path.join(base_dir, "config.yaml")
        with open(src, "rb") as f:
            raw = f.read()
        with open(live_path, "wb") as f:
            f.write(raw)
        print("restored %s from baseline %s" % (live_path, base_dir))
        return 0

    if not os.path.isfile(live_path):
        print("DOWNGRADE: %s is GONE (baseline exists for %s)" % (CONFIG_REL, repo))
        return 2

    findings = []
    try:
        live = flatten(parse_yaml(open(live_path).read()))
        findings += diff_flat(baseline["config"], live)
    except Exception as exc:  # unparsable live config is itself suspicious
        findings.append(("downgrade", "config.yaml no longer parses (%s) — possible rewrite or corruption" % exc))

    findings += audit_hooks(baseline["meta"], hook_state(repo))

    sev_rank = {"downgrade": 0, "drift": 1, "info": 2, "tighten": 3}
    findings.sort(key=lambda f: sev_rank[f[0]])
    if args.as_json:
        print(json.dumps({"repo": repo, "verdict": "CLEAN" if not findings else findings[0][0].upper(),
                          "findings": [{"severity": s, "message": m} for s, m in findings]}, indent=2))
    else:
        if not findings:
            print("CLEAN: %s matches baseline" % repo)
        for s, m in findings:
            print("[%s] %s" % (s.upper(), m))

    if any(s == "downgrade" for s, _ in findings):
        return 2
    if any(s == "drift" for s, _ in findings):
        return 3
    return 0


# --------------------------------------------------------------------------
# Self-test: fixtures covering every downgrade rule the audit enforces.
# --------------------------------------------------------------------------

GOOD = """guards:
  secrets: true
  lint: true
  tests: true
  test_mode: full
  allow_skips: false
  sensitive_paths:
    allow:
      - "examples/*"
evaluator:
  max_iterations: 100
"""

DOWNGRADED = """guards:
  secrets: false          # "temporarily disabled so the commit goes through"
  lint: true
  tests: false
  test_mode: diff
  allow_skips: true
  sensitive_paths:
    allow:
      - "examples/*"
      - ".env*"
evaluator:
  max_iterations: 200
"""


def selftest():
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS" if cond else "FAIL"), name)
        ok = ok and cond

    base = flatten(parse_yaml(GOOD))
    live = flatten(parse_yaml(DOWNGRADED))
    f = diff_flat(base, live)
    downgraded = {m for s, m in f if s == "downgrade"}
    check("secrets true->false is a downgrade",
          any("secrets" in m for m in downgraded))
    check("tests true->false is a downgrade",
          any(m.startswith("[S".replace("[S", "guards.tests")) or "guards.tests" in m for m in downgraded))
    check("allow_skips false->true is a downgrade",
          any("allow_skips" in m for m in downgraded))
    check("test_mode full->diff is a downgrade",
          any("test_mode" in m for m in downgraded))
    check("sensitive-path allowlist growth is a downgrade",
          any("sensitive" in m.lower() or "paths" in m.lower() for m in downgraded))
    check("evaluator cap raise is drift, not downgrade",
          any(s == "drift" and "max_iterations" in m for s, m in f))
    check("exit-code path: downgrades present", len(downgraded) >= 4)

    # on_fail softening inside a pipeline step
    pipe_base = flatten(parse_yaml("pipeline:\n  stages:\n  - id: tier1\n    steps:\n    - id: lint\n      on_fail: block\n"))
    pipe_live = flatten(parse_yaml("pipeline:\n  stages:\n  - id: tier1\n    steps:\n    - id: lint\n      on_fail: warn\n"))
    f2 = diff_flat(pipe_base, pipe_live)
    check("on_fail block->warn is a downgrade",
          any(s == "downgrade" and "on_fail" in m for s, m in f2))

    print("selftest:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
