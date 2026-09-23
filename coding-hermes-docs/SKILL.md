---
name: coding-hermes-docs
description: Use when auditing a project for documentation gaps, or when a weekly documentation-health lane runs. Files each gap as an actionable row for the owning foreman and its worker; never writes the docs itself.
version: 1.0.0
metadata:
  hermes:
    tags: [coding-hermes, docs, audit, weekly, foreman, worker]
    related_skills:
      - coding-hermes-readme
      - coding-hermes-foreman
      - coding-hermes-prd-to-contracts
      - coding-hermes-jsonl-board-append
---

# coding-hermes-docs — documentation gap audit

You find what is **not written**, and you file it so it gets written. You do not write it.
The README lane guards the front door; this lane guards everything behind it — the
reference, the operator's path, the integrator's path, and the runbooks that only matter
during an incident.

The target standard: **a thing that shipped has somewhere to have been described**, and a
reader can find it from the repo without asking a human.

## The weekly sweep

Work the surface outward. Derive everything from the code and the board — never from your
memory of the project, and never from the docs themselves (the docs are the thing under
audit).

1. **Derive the real surface.**
   - Public entry points: exported functions/types, CLI verbs and flags, HTTP routes, MCP tools.
   - Configuration: every config key and environment variable the code actually reads.
   - Error and exit paths a caller must handle.
   - Build the list from source, with file:line, so every claim below is anchored.

2. **Diff the surface against the docs.** For each item, ask: *where is this described, and
   can a reader find it from the repo root in one hop?*
   - Undocumented item → a gap.
   - Documented but **wrong** (signature, flag, default, return, status code) → a gap, higher severity.
   - Documented only in a changelog or a row title, never in reference → a gap; a changelog is not documentation.

3. **Diff the board against the docs.** Closed rows naming user-visible behaviour with no
   corresponding doc page are gaps. The board is the record of what exists; if the board
   says it shipped and the docs do not, one of the two is lying.

4. **Audience coverage.** For each project, name the reader and check each has a home:
   - **Developer** — how to build, test, extend.
   - **Operator** — how to run, configure, monitor, recover, and what to do at 3am.
   - **Integrator** — the contract: shapes, errors, limits, versioning.
   - **End user** — what it does for them, and what it will not do.
   A missing audience is one gap per audience, not one gap called "docs".

5. **Rot.** Docs referencing a removed file, flag, endpoint or service; examples whose
   output no longer matches; diagrams and counts that have drifted. Rot is cheaper to fix
   than a gap and more damaging, because it is confidently wrong.

6. **Gaps the repo admits.** Deferred rows, `TODO`/`FIXME` markers describing missing
   documentation, and incident post-mortems whose action item was "document this" — turn
   each into a row instead of letting it stay a promise.

## What you file

One row per gap, on the **owning project's board**, sized so the foreman can hand it
straight to a worker.

```
id:      DOC-<n>
title:   "document <what> for <which reader>" — a deliverable, not a complaint
type:    missing-reference | wrong-reference | missing-audience | rot | operator-path
severity: P1 if an operator or integrator cannot act without it; P2 otherwise
surface: the code anchor proving the thing exists   (file:line)
artifact: the file the documentation belongs in       (path, or the path to create)
reader:  who it is for
accept:  what makes it done — the falsifiable test a reviewer will apply
```

Sizing rule: **the row names the artifact and the acceptance test.** "Improve the docs" is
not a row. "Document the retry and backoff semantics of `<verb>` for an integrator, in
`docs/reference/<area>.md`, accepted when every state in the retry ladder appears with its
trigger" is a row a worker can finish without asking a question.

## Discipline

- **Never write the documentation in this lane.** File; the foreman dispatches; the worker
  writes. An audit lane that quietly patches produces no durable record of the gap class,
  and the same holes reopen.
- **Anchor every gap to code.** A gap you cannot point at in the source is a preference.
  State the file:line of the surface that exists undocumented.
- **One gap, one row.** Bundling nine missing pages into one row guarantees eight are never
  done, and it makes completion unmeasurable.
- **Do not file taste.** Tone, layout, tooling choices and page ordering are not gaps.
  Missing, wrong, rotten, or unreachable are.
- **A quiet week is a valid result.** If the surface is documented and the references are
  true, file nothing and say so plainly. A lane that manufactures findings teaches the
  fleet to ignore it.
- **Report coverage, not a score.** Say which surface items have no home, with anchors. Do
  not grade the documentation.

## Failure modes to hunt by name

- **The reference that documents the old signature** — it compiles in the reader's head and fails in their terminal.
- **The operator path that only exists in a chat thread** — the knowledge is real and nowhere a 3am reader can find it.
- **The config key documented nowhere but required** — the code reads it, the docs never mention it, and the failure is a silent default.
- **The example whose output stopped matching** two versions ago; nothing executes it, so nothing catches it.
- **The audience that has no home at all** — an integrator reading developer prose, guessing at error semantics.
- **The gap that is only ever a promise**: an incident action item, a deferred row, or a comment asking someone to document it later.
