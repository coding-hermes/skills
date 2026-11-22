#!/usr/bin/env python3
"""acceptance_gate.py - deterministic check that a board row's acceptance criteria
are re-runnable by a foreman who has no context.

Usage:
  acceptance_gate.py validate <repo> <row-json-file-or-inline-json>
  acceptance_gate.py audit    <repo>            # report pass/fail for every open row

Exit codes: 0 = all valid, 1 = at least one failure.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

# Phrases that mean nothing to a worker who has no context.
FILLER = [
    'tests pass', 'tests are green', 'it works', 'works correctly', 'no errors',
    'as expected', 'looks good', 'is implemented', 'behaves properly',
    'functions correctly', 'is working', 'satisfies the requirement',
]

COMMAND_HINTS = (
    '`', 'cargo ', 'go test', 'go build', 'go vet', 'pytest', 'python3 ', 'npm ',
    'npx ', 'make ', 'bash ', 'sh ', 'curl ', 'sqlite3 ', 'git ', 'grep ', 'jq ',
    'bunker ', 'gitreins ', 'router ', 'boardctl ', 'hermes ',
)

OPEN_STATUS = {'pending', 'open', 'in_progress', 'ready', 'todo', 'blocked'}

# Flags documented by external CLIs that no repo consuming them can mention in
# source. Exempted only when the criterion actually invokes that CLI (see check()).
_BOARDCTL_FLAGS = {'--type', '--acceptance-criteria', '--meta', '--commit-hash',
                   '--evidence-fingerprint'}
# `boardctl update --evidence-fingerprint FP` is a real boardctl flag (verified live
# 2026-11-22 PM tick: `boardctl update --help` usage line prints
# "[--evidence-run-id RUN] [--evidence-fingerprint FP]"). JUDGE-DUCKBRAIN-002's
# evidence-attachment arm cites it; boardctl ships from coding-hermes-tools, so no
# consuming repo file can spell it. Same external-tool class as --evidence-run-id;
# scoped via the boardctl branch below, so an invented flag beside boardctl
# (--evidence-sha) still FAILs (red-proved 2026-11-22).
# `boardctl update --commit-hash <sha>` is a real boardctl flag (verified live
# 2026-11-22 PM tick: `boardctl update --help` usage line prints
# "[--commit-hash SHA]"), and boardctl ships from coding-hermes-tools, so no
# file in a consuming repo can ever mention it. DF-DIGEST-068's re-point arm
# cites it (verified live 2026-11-21 on the repo's own scratch probe: the flag
# exists but the update is refused for a DIFFERENT reason — duplicate
# completion — so the refusal the arm asserts is real). Same external-tool
# class as --evidence-run-id; scoped via the boardctl branch below, so an
# invented flag on any other tool still fails (red-proved: --frobnicate
# beside boardctl still FAILs).
# `boardctl create --meta k=v` is a real flag (verified live 2026-11-22 PM tick:
# `boardctl create --help` usage line prints "[--meta k=v]"). terminal-jail
# INT-CI-020-R2 legitimately cites it inside a PROHIBITION — "no --meta flags"
# on the fixed default path — and the mirror of the curl/-k class: a negation
# read as a demanded flag fails the row forever. Scoped to a criterion that
# names boardctl, so an invented flag on any other tool still fails (red-proved:
# --frobnicate beside boardctl still FAILs; gate_fixtures must stay ALL-GREEN).
# `gh run view --log-failed` is real GitHub CLI (verified live 2026-11-21 PM tick:
# `gh run view --help` prints "--log-failed  View the log for any failed steps in a
# run or specific job"), and the CLI is host-installed, so no file in a consuming
# repo can mention it. Same external-tool class as --evidence-run-id.
_GH_FLAGS = {'--log-failed'}
# `gitreins guard --quality-async` is a real gitreins flag (verified live 2026-11-21
# PM tick: `gitreins guard --help` on the pipx-installed 0.21.1 prints
# "[--quality-async]" in the usage line and "  --quality-async       Run the
# repo-owned quality producer in the background" in the option list). gitreins
# ships from pipx, so no file in a consuming repo can ever mention it. Verified
# against BOTH verbs before exempting: `gitreins task complete --help` does NOT
# print it (its flags are --scan-root/--force/--skip-tier2), which is why the
# exemption is scoped to a criterion that invokes `gitreins guard`.
_GITREINS_GUARD_FLAGS = {'--quality-async'}
# bunker-qa.sh flags — the QA foreman's fleet harness lives OUTSIDE every consuming
# repo (~/.hermes/scripts/bunker-qa.sh), so no tracked file can ever mention them and
# the repo-grep can only read them as invented. Verified live 2026-11-22 PM tick
# against the harness's own Usage block and argument parser, not against a guessed
# interface: usage lines 'collect --evidence <path>' (bunker-qa.sh:28) and
# 'verify-evidence <dir|evidence.jsonl> [--expect <hex>] [--event <json>]'
# (bunker-qa.sh:40) plus 'run <repo-dir> [--server X] [--ttl 4h] [--keep]'
# (bunker-qa.sh:17-18); the --expect parser is real code at bunker-qa.sh:300-303
# ('--expect)' -> refuses a missing digest, '--expect=*)' -> strips the prefix) and
# an unknown flag there exits 2 with 'unknown verify-evidence flag' (line 311).
# Scoped to a criterion that names the harness, so an invented flag on any other
# tool still fails (red-proved in the fixtures run).
_BUNKER_QA_FLAGS = {'--expect', '--evidence', '--event', '--keep', '--ttl', '--server'}



def _is_absence_subject(text: str, token: str) -> bool:
    """True when `token` is named in `text` as a path that must NOT exist.

    Two sanctioned shapes, both requiring an EXACT path match on the subject:
      * `test ! -e|! -f <token>`         — negation test
      * `git log|show ... -- <token>`    — history query proving zero commits
    A prefix such as `~/<repo>/` is not equal to the bare relative token, so
    an exemption granted to one arm can never silence another arm's citation.
    """
    want = os.path.normpath(token.lstrip('./'))
    for m in re.finditer(r'test\s+!\s+-[ef]\s+[`\'"]?([^\s`\'";|)]+)', text):
        if os.path.normpath(m.group(1).lstrip('./')) == want:
            return True
    for m in re.finditer(r'\bgit\b[^\n]*?\b(?:log|show)\b[^\n]*?\s--\s+([^\n]+)', text):
        for word in m.group(1).split():
            word = word.strip('`\'";|)')
            if word and os.path.normpath(word.lstrip('./')) == want:
                return True
    return False


def as_text(value) -> str:
    if value is None:
        return ''
    if isinstance(value, (list, tuple)):
        return '\n'.join(as_text(v) for v in value)
    if isinstance(value, dict):
        return '\n'.join(f'{k}: {as_text(v)}' for k, v in value.items())
    return str(value)


def repo_paths(repo: str) -> set[str]:
    """Tracked files, so a criterion naming a path can be checked for existence."""
    try:
        out = subprocess.run(['git', '-C', repo, 'ls-files'], capture_output=True,
                             text=True, timeout=30).stdout
        return set(out.split('\n'))
    except Exception:                                          # noqa: BLE001
        return set()


_GREP_CACHE: dict[tuple[str, str], int] = {}


def _greps(repo: str, name: str) -> int:
    """How many tracked files mention `name`, EXCLUDING the board itself.

    The exclusion is load-bearing: a criterion's own text lives in tasks.jsonl, so an
    unexcluded `git grep` matches the criterion and every fabrication verifies as real.
    """
    key = (repo, name)
    if key in _GREP_CACHE:
        return _GREP_CACHE[key]
    try:
        # `-e <name>` so a pattern that itself starts with `--` (a CLI flag token
        # cited by a criterion, e.g. `--frozen-lockfile`) is parsed as a PATTERN,
        # not as a git option — without it, every flag citation rc=129s and
        # reads as "flag that does not exist" (proven 2026-10-22 PM tick).
        # `-i`: a `-run` fragment like 'SCHEDGAP214' or a flag token may differ
        # in case from the real symbol it cites (TestSchedGap214_...); existence
        # is case-insensitive (proven 2026-11-21 PM tick: SCHED-SHUTDOWN-001's
        # red-arm -run fragment read as "test that does not exist" while
        # TestSchedGap214_OperatorRestartAbortKeepsWaiver exists and passes).
        out = subprocess.run(['git', '-C', repo, 'grep', '-l', '-i', '-F', '-e', name,
                              '--', ':(exclude).coding-hermes/*', ':(exclude)*.jsonl',
                              ':(exclude)data/*', ':(exclude)site/*'],
                             capture_output=True, text=True, timeout=30).stdout
        n = len([l for l in out.split('\n') if l.strip()])
    except Exception:                                          # noqa: BLE001
        n = 1          # a failed probe must not manufacture a failure
    _GREP_CACHE[key] = n
    return n


def check(criteria: str, repo: str, files: set[str]) -> list[str]:
    problems = []
    text = criteria.strip()
    low = text.lower()

    # A criterion may name a FOREIGN repo ("in the <name> repo"). Path and
    # test-symbol existence then resolve against that checkout, not the audited
    # repo — otherwise a real cross-repo arm reads as an invented path/test.
    # Proven 2026-11-21: BOARDCTL-HOOK-001's `cmd/boardctl/main.go` and
    # `TestBT083` live in ~/coding-hermes-boardctl (verified on disk), and the
    # gate read both as absent from the crier repo. Fail CLOSED: the foreign
    # checkout must exist AND be a git work tree, or alt_repo stays None and
    # the audited repo is used (so a typo'd repo name cannot disarm the arm).
    alt_repo = None
    m = re.search(r'in the ([A-Za-z0-9_.-]+) repo', text)
    if m:
        cand = os.path.expanduser('~/' + m.group(1))
        if os.path.isdir(os.path.join(cand, '.git')):
            alt_repo = cand

    if not text:
        return ['empty']
    if len(text) < 40:
        problems.append(f'too short ({len(text)} chars) - cannot specify done')
    if low.strip().rstrip('.') in FILLER or any(f == low.strip().rstrip('.') for f in FILLER):
        problems.append('pure filler phrase')
    if not any(hint in low for hint in COMMAND_HINTS):
        problems.append('names no runnable command')
    if any(f in low for f in FILLER) and not any(hint in low for hint in COMMAND_HINTS):
        problems.append('filler without a command')

    # A path-shaped token must exist in the repo (or be a dotfile/board path).
    # Longest extensions first: 'js' before 'json' truncates 'edges.jsonl' to 'edges.js'.
    # Context classes that are NOT invented references (proven 2026-11-21 PM tick):
    #   - runtime data the repo's own writers create untracked
    #     (data/state/outcomes.jsonl is ~490MB on this host, gitignored) —
    #     exists-on-disk == real;
    #   - a PROPOSED deliverable: "a new docs/data-refresh.md", "(e.g. tests/...py:";
    #   - a git-plumbing citation `HEAD:<path>` whose arm asserts it may be absent;
    #   - an OR-resolution: "<path>` (or the suite file that owns ...)".
    for m in re.finditer(
            r'[A-Za-z0-9_./-]+/[A-Za-z0-9_./-]+\.(?:jsonl|json|go|py|rs|md|tsx|ts|js|toml|yaml|yml|sh)',
            text):
        token = m.group(0)
        if token.startswith(('.coding-hermes', '~', '/')) or token.startswith('http'):
            continue
        if alt_repo and os.path.exists(os.path.join(alt_repo, token)):
            continue
        if files and token not in files and not any(f.endswith('/' + token) for f in files):
            if os.path.exists(os.path.join(repo, token)):
                continue
            # One contextually-exempt occurrence exempts the TOKEN: a criterion can
            # cite the same path 3x (proposed / HEAD: / absence-check) and one
            # exempt shape proves the path is not an invented reference.
            # (proven 2026-11-21 PM tick: DOC-24's docs/README.md is proposed once
            # and cited twice more; DOC-36's docs/drivers.md is `HEAD:`-quoted and
            # the subject of a ZERO-hits arm.)
            token_exempt = False
            positions = [mm for mm in re.finditer(re.escape(token), text)]
            for pm in positions:
                before = text[max(0, pm.start() - 6):pm.start()].lower()
                after = text[pm.end():pm.end() + 8].lower()
                if before.rstrip().endswith(('new', 'e.g.')):
                    token_exempt = True
                    break
                if after.lstrip('` ').startswith('(or') or before.endswith('head:'):
                    token_exempt = True
                    break
            if token_exempt:
                continue
            # ABSENCE assertion: an arm may name a path precisely to prove it is
            # GONE (`test ! -e <path>`, or a zero-hits `git log --all -- <path>`).
            # Such a path can never be in git ls-files, so the existence check
            # failed those arms forever (proven 2026-11-21 PM tick: TRBL-049
            # forbids the repo from carrying an in-repo AGENTS.md and the gate read
            # the forbidden path as an invented one).
            # EXACT subject match only. An earlier version let any prefix sit
            # before the token, so `test ! -e ~/<repo>/specs/AGENTS.md` exempted
            # the UNRELATED `specs/AGENTS.md` cited in the next arm — the audit
            # went green on an arm that still fails standalone (skip-guard trap).
            if _is_absence_subject(text, token):
                continue
            problems.append(f'path not in repo: {token}')

    # Expected outcome must be stated.
    # 'Expected outcome' / 'exits 0' are the standard phrasings in criteria; the
    # bare keywords fail the trailing \b on the suffix ('expected', 'exits').
    # (proven 2026-11-21 PM tick: RELEASE-061 etc. carry a literal 'Expected
    # outcome:' paragraph and still read as outcome-less.)
    # Broadened 2026-11-21 PM tick: substantive criteria also state the outcome as
    # a result STATE — "completes the fresh-install cell", "byte-identical",
    # "is <= 3", "no more than", "concludes success", "verified with the exact
    # evidence path" — the original verb list read those as outcome-less and
    # failed 12 live task-router rows whose criteria name commands and thresholds.
    if not (re.search(r'\b(expect(?:ed(?:ly)?)?|exit(?:s|ed|ing)?|returns?|prints?|outputs?|PASS|FAIL|must (?:show|print|return)|completes?|equals?|resolves?|passes?|green|keeps?|stays?|remains?|byte-identical|recorded|no more than|at least|success|verif(?:y|ied)|reports?|produc(?:es|e|ed)|never)\b',
                     text, re.I)
            or re.search(r'[<>]=?\s*[0-9]', text)):
        problems.append('does not state the expected outcome')

    # A blind worker cannot substitute a placeholder for anything. Restored 2026-11-22
    # PM tick: the 2026-11-21 gate revision dropped this arm silently, so rows carrying
    # `make version-check VERSION_TAG=<current release>` or an unexpanded
    # `<skills>/...` path audited green — measured: 5 boardctl README rows whose arms
    # cite a placeholder token went FAIL -> PASS on the install alone.
    for ph in re.findall(r'<([a-zA-Z][a-zA-Z0-9 _-]{1,30})>', text):
        if ph.lower() not in ('br', 'date', 'sources', 'sources checked'):
            problems.append(f'unexpanded placeholder <{ph}> — a context-free worker cannot fill it')

    # A NAMED symbol must exist. A path check alone passes a criterion naming a test
    # function or CLI flag that was invented: the file is real, the name is not.
    named = set()
    for pat in (r"-run\s+['\"]?([A-Za-z_][\w/.-]*)", r"-k\s+['\"]?([A-Za-z_]\w*)",
                r'\bTest[A-Z]\w{3,}', r'::(Test\w+)'):
        named.update(re.findall(pat, text))
    for name in list(named)[:6]:
        if alt_repo and _greps(alt_repo, name):
            continue
        if files and not _greps(repo, name):
            problems.append(f'names a test that does not exist: {name}')

    flags = {f for f in re.findall(r'(?<![\w-])(--[a-z][a-z0-9-]{2,}(?:\.[a-z][a-z0-9-]*)+|--[a-z][a-z0-9-]{2,})', text)
             if f not in ('--help', '--version', '--dry-run', '--json', '--format',
                          # External-scanner scan-mode flag: `gitleaks detect --no-git`
                          # recurs in board criteria but lives only in the gitleaks
                          # binary, so no tracked repo file can ever mention it
                          # (proven 2026-10-30 BT-83: flag ran live, gate read it
                          # as invented). Exempt like the generic flags above.
                          '--no-git',
                          # Generic git plumbing flag (proven 2026-11-03 guard PM
                          # tick: `git rev-parse --show-toplevel` ran live, gate
                          # read it as invented) and the bunker-qa.sh collect
                          # evidence-path flag, which recurs in QA criteria but
                          # lives only in ~/.hermes/scripts/bunker-qa.sh — same
                          # external-tool class as --no-git.
                          '--show-toplevel', '--evidence',
                          # External-CLI flag: `gh run list -c/--commit <sha>` is a
                          # real gh flag (verified live 2026-11-07: `gh run list
                          # --help` on gh 2.46.0 prints `-c, --commit SHA  Filter
                          # runs by the SHA of the commit`), but no tracked repo
                          # file mentions it, so the RELEASE-045 arm read as
                          # invented. Same external-tool class as --no-git.
                          '--commit',
                          # External-CLI flag: `act --concurrent-jobs N` is a real
                          # nektos/act flag (verified live 2026-11-17: `act
                          # --help` on the host act prints "--concurrent-jobs int
                          # Maximum number of concurrent jobs to run"), but it
                          # lives only in the act binary, so QA-CHIMERA-V2-46's
                          # serial-mode arm read as invented. Same external-tool
                          # class as --no-git.
                          '--concurrent-jobs',
                          # External-CLI flag: `git status --ignored[=<mode>]` is real git
                          # plumbing (verified live 2026-11-21 PM tick: `git status --help`
                          # prints "--ignored[=<mode>]" and `git status --ignored --porcelain`
                          # exits 0 in this repo), but DAGGER-1089's criterion is the only place
                          # in the tree that spells the long form, so the gate read it as
                          # invented. Same external-tool class as --no-git / --commit.
                          '--ignored',
                          # Cobra/pflag flags are registered with the BARE name, so a
                          # criterion that cites the runtime form finds nothing in
                          # source: internal/builtin/extended.go:961 reads
                          # `verifyCmd.Flags().StringVar(&verifySink, "sink", ...)`
                          # (verified 2026-11-20 PM tick: `openapi-cli audit verify
                          # --sink <path>` documented in docs/guides/commands.md,
                          # runtime flag real, literal `--sink` absent from the tree).
                          # This is the documented-form class, not an invented flag:
                          # DOC-25's whole point is that the runtime flag exists and
                          # the docs omit it.
                          '--sink',
                          # External-CLI flag: `bunker list --server <alias>` is real
                          # (verified live 2026-11-20: `bunker list --help` prints
                          # "      --server string      Server alias (default: active
                          # server)") but lives only in the bunker binary, so
                          # QA-MUSTER-046's harness arm read as invented. Same
                          # external-tool class as --no-git / --commit.
                          '--server',
                          # External-CLI flag: `hyperfine --export-json <FILE>` is a
                          # real sharkdp/hyperfine flag (verified live 2026-11-21 PM
                          # tick: `hyperfine --help` on the host hyperfine 1.20.0
                          # prints "      --export-json <FILE>", and the sibling
                          # -w/--warmup and -r/--runs flags in the same criterion
                          # print on the same help), but it lives only in the
                          # hyperfine binary, so PERF-017's A/B arm read as invented.
                          # Same external-tool class as --no-git / --commit.
                          '--export-json',
                          # NEGATIVE citation: QA-MUSTER-041 quotes the pre-fix
                          # failure `Error: unknown flag: --email` as proof that the
                          # form-encoded property flags did NOT exist. A flag named
                          # for its own absence can never appear in a tracked file
                          # before the fix, and after the fix the name derives from
                          # spec properties, not source text (verified 2026-11-20 PM
                          # tick: gate re-read the quote as an invented flag).
                          # External-CLI flag: `boardctl update --evidence-run-id <run>` is a
                          # real boardctl flag (verified live 2026-11-21: `boardctl update
                          # --help` on the host binary at ~/.local/bin/boardctl prints
                          # "--evidence-run-id RUN"), and boardctl ships from
                          # coding-hermes-tools, so no file in a consuming repo can ever
                          # mention it. Same external-tool class as --no-git / --commit.
                          '--evidence-run-id',
                          # NEGATIVE citation: SCHED-GAP-17021 forbids --no-verify
                          # ("a guard refusal ... never worked around") and
                          # SCHED-GAP-17033 requires a commit to land WITHOUT
                          # --no-verify. The flag is real git plumbing (verified
                          # live 2026-11-21: `git commit --help` lists it), no
                          # tracked file in a consumer repo need mention it.
                          '--no-verify',
                          # External-CLI flag: `git merge --ff-only` is real git
                          # plumbing (verified live 2026-11-21 PM tick: `git merge
                          # --help` prints "--ff, --no-ff, --ff-only" and "With
                          # --ff-only, resolve the merge as a fast-forward when
                          # possible"), and HARDEN-LOOP-001's contract arm cites
                          # it, so the gate read it as invented. Same
                          # external-tool class as --no-git / --commit.
                          '--ff-only',
                          '--email')}
    # Tool-scoped flag exemptions: a flag documented by an external CLI counts as
    # real only inside a criterion that actually invokes that CLI, so an invented
    # flag on any other tool is still caught in the same repo.
    # boardctl create --type SLUG / --acceptance-criteria TEXT — verified live
    # 2026-11-21 (`boardctl create --help` prints both, boardctl ships from
    # coding-hermes-tools so no consuming repo file can mention them).
    if 'boardctl' in text:
        flags -= _BOARDCTL_FLAGS
    # bunker-qa.sh launch/collect/verify-evidence — verified live 2026-11-22 PM tick
    # against the harness file itself (Usage block lines 17-18/28/40 and the
    # --expect parser at 300-311). Scoped to a criterion that names the harness, so
    # an invented flag on any other tool still fails (red-proved: --frobnicate
    # beside bunker-qa.sh still FAILs).
    if 'bunker-qa.sh' in text:
        flags -= _BUNKER_QA_FLAGS
    # gh run view --log-failed — verified live 2026-11-21; scoped to a criterion
    # that actually invokes `gh`, so an invented flag on any other tool still fails.
    if 'gh ' in text:
        flags -= _GH_FLAGS
    # gitreins guard --quality-async — verified live 2026-11-21. Scoped twice: the
    # criterion must name gitreins at all, AND cite the flag on the verb that owns
    # it (`guard --quality-async`). A criterion that names the flag on another
    # tool, or on another gitreins verb, still fails (red-proved in fixtures E/G).
    if re.search(r'gitreins\b', text) and re.search(r'\bguard\s+[`\'"]?' + '--quality-async', text):
        flags -= _GITREINS_GUARD_FLAGS
    # gitreins task complete / judge --skip-tier2 — verified live 2026-11-22 PM tick:
    # BOTH `gitreins task complete --help` and `gitreins judge --help` on the
    # pipx-installed 0.21.1 print "[--skip-tier2]  Skip Tier 2 LLM evaluation;
    # Tier 1 guards only". gitreins ships from pipx, so no file in a consuming
    # repo can mention it. Scoped to a criterion that invokes one of those verbs
    # AND cites the flag, so an invented flag on any other tool, or on another
    # gitreins verb, still fails (red-proved: --skip-tier3 beside the same verbs
    # still FAILs; the stale pre-fix copy FAILs the real-flag fixture).
    if re.search(r'\bgitreins\s+(task\s+complete|judge)\b', text) and '--skip-tier2' in text:
        flags -= {'--skip-tier2'}
    # ruff --select / --statistics are real ruff flags (verified live 2026-11-21:
    # `ruff check --help` prints both, ruff 0.15.22) scoped to a criterion that
    # invokes ruff — TR-CMPLX-001's statistics arm read as invented otherwise.
    if 'ruff' in text:
        flags -= {'--select', '--statistics'}
    # journalctl --since <date|time> is a real systemd-journald time filter
    # (verified live 2026-11-21 PM tick: `journalctl --help` prints --since and
    # `journalctl --user -u h3-digest.service --since 2026-11-18` exits 0 printing
    # the unit's Nov 20 entries). journalctl is a host binary, so no consuming
    # repo file can spell the flag and the repo-grep can never learn it from the
    # tree — the extractor read DF-DIGEST-058's evidence arm as invented. Scoped
    # to a criterion that invokes journalctl, so an invented flag on any other
    # tool still fails (red-proved in the fixtures run below).
    if re.search(r'\bjournalctl\b', text):
        flags -= {'--since'}
    # node_exporter DOTTED flag: `--collector.textfile.directory` is a real
    # node_exporter collector flag, but it is spelled with a dot, so the old
    # `--[a-z][a-z0-9-]{2,}` extractor truncated it to `--collector` and then
    # grepped the repo for a token nobody writes. Proven live 2026-11-21 PM tick:
    # OBS-GITREINS-4 §3 read as "names a flag that does not exist: --collector".
    # Provenance: the fleet's real node-exporter stack mounts the textfile dir
    # (`/root/fleet-monitoring/docker-compose.yml.bak-20261004-loopback:203`
    # -> /var/lib/node_exporter/textfile, and
    # scripts/build-inventory.py:149 keys on `node_textfile_scrape_error`), so the
    # collector class is live in this fleet. Scoped to a criterion that names
    # node-exporter, mirroring the gh/ruff/boardctl tool-scoped blocks: the same
    # dotted flag on any other tool still fails, and an invented dotted flag on
    # node-exporter still fails (red-proved in the fixtures run below).
    if re.search(r'node[-_]exporter', text):
        flags -= {'--collector.textfile.directory'}
    # git diff --stat / --numstat are real git flags (verified live 2026-11-21:
    # `git diff --stat HEAD` and `git diff --numstat HEAD` both exit 0 in
    # dexdat-core, printing a diffstat / numstat line per changed file). The
    # extractor cannot know them from repo files. Scoped twice: the criterion
    # must invoke a git subcommand that owns the flag AND name the flag itself,
    # so `go test ./... --stat` and an invented git flag still fail
    # (red-proved in fixtures run below).
    if re.search(r'\bgit\s+(?:diff|log|show|status)\b', text) and re.search(r'--(?:num)?stat\b', text):
        flags -= {'--stat', '--numstat'}
    # git tag --sort=<key> is real git plumbing (verified live 2026-11-22 PM tick,
    # boardctl repo: `git tag --sort=-creatordate` exits 0 printing v0.5.0/v0.4.0/
    # v0.3.0, and `git tag --help` documents "-n, --sort=<key>"). QA-BOARDCTL-009's
    # ground-truth arm cites it; the gate read it as invented because no tracked
    # file in a consuming repo spells it. Scoped twice like the git diff block:
    # the criterion must invoke `git tag` AND cite the flag, so an invented --sort
    # on any other tool (or on another git verb) still fails (red-proved in the
    # fixtures run below).
    if re.search(r'\bgit\s+tag\b', text) and re.search(r'--sort\b', text):
        flags -= {'--sort'}
    # git log --all / git rev-list --all — verified live 2026-11-21 PM tick
    # (`git log --help` documents --all, "pretend as if all the refs ... are
    # listed on the command line", and `git log --all --oneline --no-walk`
    # exits 0 in digest printing commits). Negative-existence arms legitimately
    # cite it — the negative-log-arm fixture's `git log --all -- docs/Invented-
    # Gone.md` absence proof read as an invented flag since d67559c added the
    # fixtures. Scoped: the criterion must invoke git log/rev-list AND name
    # --all, so an invented git flag still fails (red-proved in fixtures).
    if re.search(r'\bgit\s+(?:log|rev-list)\b', text) and re.search(r'--all\b', text):
        flags -= {'--all'}
    # git rev-list --objects / git cat-file --batch-check / git clone --mirror are
    # real git plumbing (verified live 2026-11-21 PM tick in off-by-one, rc=0 for
    # every one: `git rev-list --objects --all | head -2` printed blob ids,
    # `git rev-parse HEAD | git cat-file --batch-check` printed
    # "<sha> commit 3144", and `git clone --mirror . <scratch>.git` built a 52M
    # bare mirror). A history-purge criterion legitimately cites all three as the
    # inventory/size proof, so OBS-OB-010's arm read as three invented flags. No
    # tracked repo file spells them, so the repo-grep can never learn them.
    # Scoped per owning subcommand: the criterion must invoke that subcommand AND
    # name the flag on it, so `go test ./... --objects` or an invented git flag
    # still fails.
    if re.search(r'\bgit\s+rev-list\b', text) and re.search(r'--objects\b', text):
        flags -= {'--objects'}
    if re.search(r'\bgit\s+cat-file\b', text) and re.search(r'--batch-check\b', text):
        flags -= {'--batch-check'}
    if re.search(r'\bgit\s+clone\b', text) and re.search(r'--mirror\b', text):
        flags -= {'--mirror'}
    # curl -k/--insecure is real curl plumbing (verified live 2026-11-21 PM tick:
    # `curl --help all` prints " -k, --insecure    Allow insecure server connections"),
    # but the extractor only knows flags some tracked file spells. Criteria legitimately
    # cite it as a PROHIBITION -- "with verification ENABLED (no `-k`, no `--insecure`)"
    # -- because a proof that disables certificate verification proves nothing about the
    # LAN trust store; the gate read the negation as a demanded flag and failed the row
    # forever (proven: voice-mode VOICE-8). Scoped to a criterion that actually invokes
    # curl, so an invented flag on another tool still fails and an invented curl-ish
    # flag still fails (red-proved in fixtures run below).
    if re.search(r'\bcurl\b', text):
        flags -= {'--insecure'}
    # A flag inside an "(or ...)" parenthetical is a PROPOSED ALTERNATIVE the work
    # may add, not an existing flag to verify (proven 2026-11-21 PM tick:
    # TR-1000976681059262's "Provide --all (or --chain-limit N)" — --chain-limit
    # does not exist yet and is not required to). An invented flag outside such a
    # parenthetical still fails.
    flags = {f for f in flags
             if not re.search(r'\(or\s+' + re.escape(f) + r'\b', text)}

    for flag in list(flags)[:5]:
        if files and not _greps(repo, flag):
            problems.append(f'names a flag that does not exist: {flag}')
    return problems


def load_board(repo: str) -> tuple[str, list[dict]]:
    path = os.path.join(repo, '.coding-hermes/board/tasks.jsonl')
    if not os.path.exists(path):
        sys.exit(f'no board at {path}')
    rows = [json.loads(l) for l in open(path) if l.strip()]
    return path, rows


def cmd_audit(repo: str) -> int:
    _, rows = load_board(repo)
    files = repo_paths(repo)
    bad = 0
    total = 0
    for row in rows:
        if str(row.get('status', '')).lower() not in OPEN_STATUS:
            continue
        total += 1
        ac = row.get('acceptance') or row.get('acceptance_criteria')
        problems = check(as_text(ac), repo, files)
        if problems:
            bad += 1
            print(f"FAIL {row.get('id')}: {'; '.join(problems)}")
    print(f'\naudit: {total} open rows, {bad} failing, {total - bad} passing')
    return 0 if bad == 0 else 1


def cmd_validate(repo: str, payload: str) -> int:
    files = repo_paths(repo)
    if os.path.exists(payload):
        data = json.load(open(payload))
    else:
        data = json.loads(payload)
    # Acceptance first, canon fallback — same read path as cmd_audit, so a
    # criteria-only row is never falsely REJECTed as 'empty'.
    problems = check(as_text(data.get('acceptance') or data.get('acceptance_criteria')), repo, files)
    if problems:
        print('REJECT: ' + '; '.join(problems))
        return 1
    print('PASS')
    return 0


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    action = sys.argv[1]
    repo = sys.argv[2]
    if action == 'audit':
        sys.exit(cmd_audit(repo))
    if action == 'validate' and len(sys.argv) == 4:
        sys.exit(cmd_validate(repo, sys.argv[3]))
    sys.exit(__doc__)
