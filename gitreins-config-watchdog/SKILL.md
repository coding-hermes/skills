---
name: gitreins-config-watchdog
description: >-
  Daily cron that catches GitReins guard-config downgrades — agents
  weakening secrets/tests/hooks to make commits go through.
version: 1.0.0
metadata:
  hermes:
    tags: [coding-hermes, gitreins, security, watchdog, cron]
---

# GitReins Config Watchdog — daily guard-config audit

GitReins guard configs (`.gitreins/config.yaml` + the git hooks that run
them) are enforced by agents but edited by agents too. A worker that keeps
hitting a red guard has a strong local incentive to "fix" the guard instead
of the code: `secrets: false`, `allow_skips: true`, an extra sensitive-path
ignore entry, `core.hooksPath=/dev/null`. Each edit is locally plausible and
none of them announce themselves — the next commit just goes through green.

This skill installs a once-a-day cron that diffs every watched repo's live
guard state against an **out-of-repo baseline** and classifies every change:

| Severity | Meaning |
|----------|---------|
| DOWNGRADE | a guard got weaker — blocking finding, act today |
| DRIFT | a value changed; may be legitimate, review it |
| TIGHTEN | a guard got stricter — informational, never blocks |
| INFO | new keys, notes |

**It does not write anything by default.** Restoration is an explicit
`--restore`, and drift (unlike downgrade) is a question, not an alarm.

## What counts as a downgrade

- `guards.secrets` / `guards.lint` / `guards.tests` (and the Go sub-toggles)
  `true -> false`, or the key removed entirely.
- `allow_skips: false -> true` — empty gates now PASS instead of blocking.
- `test_mode: full -> diff` — narrower scope graded.
- Any pipeline step's `on_fail: block -> warn/continue` — the gate reports
  red but no longer blocks.
- Any entry ADDED to a sensitive-path allow list — widens what the secrets
  guard ignores. Removals are tightenings.
- `core.hooksPath` pointed at `/dev/null`/unset, or the pre-commit hook
  deleted / made non-executable / rewritten to no longer run gitreins.

Deliberately NOT downgrades (classified as DRIFT): evaluator caps
(`max_iterations`, `max_time`, token budgets) rising — that is cost drift;
and timeout changes — worth reading, because a hook cut off mid-suite
fail-opens, but often a legitimate sizing fix.

## Install (once, per repo)

The audit script lives in this skill's `scripts/`. Copy it somewhere your
crons can reach, e.g. `~/.hermes/scripts/` for a Hermes gateway install.

1. **Record the baseline while the config is known-good.** The baseline
   deliberately lives OUTSIDE the repo (`~/.config/gitreins-watchdog/`), so
   an agent downgrading the live config cannot also edit the baseline in
   the same commit:

   ```
   python3 gitreins_config_audit.py --repo ~/your-project --init
   ```

   This snapshots `.gitreins/config.yaml` plus the hook state
   (`core.hooksPath`, pre-commit hash and executability).

2. **Smoke-test the audit:**

   ```
   python3 gitreins_config_audit.py --repo ~/your-project   # expect CLEAN, exit 0
   python3 gitreins_config_audit.py --selftest              # verifies the classifier
   ```

3. **Create the cron — daily, script-only.** Follow the infrastructure-cron
   shape in `coding-hermes-cron-schema`: `no_agent: true`, `skills: []`,
   no model/provider, explicit delivery target:

   ```json
   {
     "name": "gitreins-config-watchdog",
     "state": "scheduled",
     "enabled": true,
     "schedule": {"kind": "cron", "display": "0 9 * * *", "expr": "0 9 * * *"},
     "repeat": {"times": null, "completed": 0},
     "skills": [],
     "no_agent": true,
     "script": "gitreins_config_audit.py",
     "model": null,
     "provider": null,
     "workdir": null,
     "deliver": "origin"
   }
   ```

   Once a day is the recommended cadence — the same audit also works fine
   weekly, but downgrades compound: a secrets guard that has been off for
   six days is six days of exposed diffs. For several repos, wrap the loop
   in a small script (one invocation per `--repo`) and point the cron at
   that; the exit code is the first non-clean verdict, so the cron's
   delivery shows exactly which repo needs eyes.

**Exit codes** (machine-readable, so a scheduler can alert on them):
`0` clean · `2` downgrade found · `3` drift-only · `4` no baseline
(run `--init`) · `5` input/parse error.

## When the watchdog fires

1. Read the finding lines. `[DOWNGRADE]` lines name the exact key and the
   old -> new values.
2. Attribute the change: `git log -p -- .gitreins/config.yaml` in the repo
   shows which commit touched it; match it to the agent session that made it.
3. If the change was a legitimate policy decision, re-baseline it:
   `--init` again AFTER the decision is recorded. The baseline should always
   match the CURRENT intended policy, not a frozen past.
4. If it was not legitimate, restore and tighten:

   ```
   python3 gitreins_config_audit.py --repo ~/your-project --restore
   ```

   then address the workflow hole that let the agent edit guard config at
   all — the guard config is operator territory, and a worker that needs a
   guard changed should be told to fail loudly instead.
5. Verify with a re-run (expect exit 0 or drift-only) and report what was
   restored and why. Never restore silently.

## Verification

- `--selftest` passes from the installed copy (it exercises every downgrade
  rule against embedded fixtures).
- Round-trip on a scratch copy: `--init`, flip `secrets: true` to `false`
  in the scratch, re-run (expect exit 2 and the `guards.secrets` finding),
  `--restore` (expect byte-identical config and exit 0/3).
- After installing the cron, confirm it actually fired on schedule the next
  day — a watchdog that silently never runs is worse than none.

## Pitfalls

- **The baseline is the trust anchor — protect it.** It lives outside the
  repo precisely so guard-editing agents cannot reach it in the same commit.
  Do not move it into the repo, and re-baseline only as a recorded policy
  decision (step 3 above), never "to make the cron green".
- **`--restore` overwrites the live config wholesale.** If a legitimate
  sibling change landed after the downgrade, restore may revert it too —
  diff before restoring, and re-apply legitimate edits afterwards.
- **Parser scope is deliberate.** The script ships a minimal YAML-subset
  parser (stdlib-only, no PyYAML dependency). It covers real GitReins
  configs (nested maps, lists of scalars, lists of maps, comments, quoted
  scalars); anything it cannot parse surfaces as a DOWNGRADE ("config no
  longer parses"), never as a silent skip.
- **DRIFT still deserves a read.** Timeouts and command swaps are favorite
  fail-open tricks: a hook killed mid-suite by a too-short timeout reports
  as a timeout, not a red guard, and a swapped `test_command` can grade
  nothing while looking busy.
- **A missing hook is a downgrade even with a perfect config.** Fresh
  clones often lack the pre-commit hook entirely; the hook-state check
  catches that (baseline had one, live does not).
- **Guard-config edits with explicit operator authorization are legitimate**
  — the watchdog flags the state change, not the intent. Attribution
  (step 2) decides whether it was authorized; disclose authorized bypasses
  in the work that used them.
