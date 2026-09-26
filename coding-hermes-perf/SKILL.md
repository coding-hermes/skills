---
name: coding-hermes-perf
description: "Use when profiling or speeding up any project — measure first, profile where the numbers point, change ONE thing, re-measure; PERF-* rows on the owning board."
version: 1.0.0
author: totalwindupflightsystems
license: MIT
metadata:
  hermes:
    tags: [performance, profiling, flamegraph, benchmarking, verification, 計測]
    related_skills:
      - coding-hermes-worker
      - coding-hermes-quorum
      - coding-hermes-retrospective-self-improvement
---

# 計測 KEISOKU — the perf lane

**計測 (keisoku)** is measurement — 計 (to measure, as in 計画 a plan) + 測 (to fathom, as in
観測 observation). The name is the law: this lane exists to **measure**, not to optimize. An
optimization without a number is an opinion, and this skill exists because opinions about
performance are wrong more often than they are right.

> **The law, in one line:** no optimization without a measurement, no claim without a
> re-measurement, and **one change at a time** — measured with the SAME command, on the SAME
> build profile, at the SAME input scale.

## What this lane is

You are the per-project **performance** lane. One target project per lane, named in your prompt
(`<target>-perf`). Your work is a hunt, not a refactor: you find where the time goes, you prove
it, and you hand the fix to the owning foreman.

**You never edit the target project's code.** The foreman implements. You produce:
a **PERF-&lt;n&gt; row on the target's own board** via `boardctl`, carrying the exact command,
the before/after numbers, the profile evidence, and the `file:line` hot path.

## The hunt, in order

### 1. Measure before you profile

Pick a workload that matters (a test, a CLI invocation, a hot endpoint) and get a **number**
with `hyperfine` (installed) or `time -p`:

```
hyperfine --warmup 3 --runs 10 './bin/schedulerd --help'
hyperfine --warmup 3 --runs 10 'python3 -m pytest -q tests/test_x.py'
```

Fix the three things that must not move: **command**, **build profile** (debug vs release —
they are not comparable), and **input scale**. Write them into your report before you change
anything. If the workload is not worth optimizing, STOP HERE and say so — a quiet tick is a
success (see the closing rule).

### 2. Profile only where the numbers justify it

Do not profile everything. Profile the thing the measurement said was slow. Pick the tool for
the target's language:

| Language | Profile with | Flame graph from |
|---|---|---|
| **Python** | `py-spy record -o prof.svg -- python3 ...` (installed; sampling, **no code change**) | the SVG py-spy writes; `--format=speedscope` for a portable one |
| **Python (memory)** | `python3 -m tracemalloc`, `memray run` (install), `-X importtime` | memray's report |
| **Go** | built-in: `go test -bench . -cpuprofile cpu.out`, `runtime/trace` | `go tool pprof -http=:0 cpu.out` → Flame Graph |
| **Rust** | `samply record ./target/release/bin` (installed), `cargo flamegraph` (installed) | samply's own UI (live), or its profile output |
| **Node / TS** | `node --cpu-prof`, `0x`, `clinic flame` (install) | 0x / clinic |
| **JVM** | `async-profiler` (install), JFR | async-profiler → flamegraph HTML |
| **C / C++** | `perf record -g` (installed), `valgrind --tool=callgrind` | `perf script` + FlameGraph, or KCachegrind |
| **C# / .NET** | `dotnet-trace` (install), PerfView | Speedscope |
| **Anything, whole host** | the **Pyroscope stack** (see below) | Grafana flame-graph panel |

`perf` is installed and works for anything with symbols, including native extensions.

### 3. Read the flame graph NUMERICALLY

**Do not eyeball the picture and pick the widest bar.** Parse the profile:

```
# py-spy's own text output is already a ranked list — use it
py-spy record -o prof.svg --format=raw -- python3 ... > raw.txt
py-spy top -- python3 ...          # live, ranked by own-time
# then, from a folded-stack file:
sort -t' ' -k2 -rn raw.txt | head -20
```

For `pprof`-style profiles, `-top` and `-list <function>` give per-function and per-line
numbers. A frame that owns 40% *inclusive* but 2% *self* is a caller — the cost is downstream,
and optimizing the caller is the classic mistake this step exists to prevent.

### 4. Change ONE thing, then re-measure with the same command

One change. Same command. Same build profile. Same input scale. Record before/after side by
side — the row is written from those two numbers, not from the change's description.

If the change did not move the number, **say so and revert it**. A measured "this did not help"
is a real finding; a kept unproven change is a regression waiting for a release.

### 5. File the row, and hand over

```
boardctl -C <target-workdir> create --id PERF-<n> \
  --title "<what got faster>: <before> -> <after> on <workload>" \
  --priority P2 --complexity <n> \
  --evidence-run-id "<stable-key-for-this-finding>" \
  --reasoning "$(cat /tmp/perf-row.md)"
```

`--evidence-run-id` is the dedupe: a re-detected finding is REFUSED (exit 2). A refusal is the
system working — never rename an id to force a row through. The row must carry: the exact
command, before/after numbers, the profile evidence (with the file path to it), and the
`file:line` of the hot path. **A row that says "improved performance" with no command and no
numbers is not a finding and must not be filed.**

## Continuous profiling — the Pyroscope stack

Ad-hoc profiling answers "why is this slow right now". The **Pyroscope stack** answers "what has
been slow for the last week", continuously and across every process, with no code changes:
Alloy's `pyroscope.ebpf` reads stacks from the kernel and Grafana renders flame graphs. When it
is deployed (see the observability stack), it becomes the lane's first stop:

- **Grafana → Explore → Pyroscope → `service_name` → Flame Graph** for a live flame graph
- `curl -s 'http://<pyroscope>:4040/pyroscope/api/v1/labels'` to confirm profiles are arriving
- **Honest limit:** eBPF loses frames where a runtime keeps its own stack — **CPython built
  without frame pointers comes out thin**. When a Python profile looks hollow, that is why, and
  the fix is `py-spy` (which reads the interpreter's own stack) feeding the same store. Report a
  thin profile as thin; do not present it as the truth.

## The closing rule

**A tick where nothing is slow enough to be worth a row is a SUCCESS — say so.** Fabricating a
finding to look busy is the failure mode of an audit lane, and it pollutes the board the owning
foreman has to read. Report terse: first line one of `OK` / `FINDINGS` / `NOTHING-TO-DO` /
`BLOCKED <why>`, then each finding with its row id, numbers and what you left **UNVERIFIED**.

## Pitfalls

- **Comparing across builds.** Debug vs release, or a cold vs warm cache, is not a measurement.
- **Optimizing the caller of the hot leaf.** Check *self* time, not just inclusive.
- **Keeping the change that did not help.** Revert it and record that it did not help.
- **Filing a row from a profile with no baseline.** The row needs before *and* after.
- **Trusting a thin eBPF profile for an interpreter.** Say it is thin; use that language's
  profiler.
- **Editing the target's code.** You hand over; the foreman implements. This is what keeps one
  lane from silently rewriting another project while that project is mid-release.
