# Parallel Tick Sibling Signals — Detection & Recovery

When foreman intervals are 30m or less, parallel ticks firing within seconds of
each other will write to the same files. This reference catalogs the EXACT
signals to recognize and the recovery flow.

## Detection Signals

### 1. write_file sibling modification warning

```
"_warning": "/path/to/file.go was modified by sibling subagent '<uuid>' at HH:MM:SS — after this agent's last read at HH:MM:SS. Re-read the file before writing."
```

**This appears in the write_file/patch tool result.** It means: another foreman tick wrote
to this file between when you last read it and when you tried to write to it. If you
proceed without re-reading, you will overwrite the sibling's changes.

**Response:** re-read the file immediately. Compare against your intended change.
If sibling's version is correct (exported types, better patterns, cleaner code),
accept it — do NOT re-write. Only write the delta that's still needed.

### 2. Repeated sibling warnings (3+ consecutive tool calls)

When the same file shows sibling modification warnings on 3+ consecutive tool calls,
the sibling is **actively iterating** on that file. Continuing to write will produce
syntax errors from interleaved edits (mangled indentation, duplicate statements).

**Response:** stop writing to that file. Switch to read-only verification. Let the
sibling finish — they started first and have more context.

### 3. git log shows fresh sibling commits

```bash
git log --oneline -5
```

If commits appear during your tick with the same Phase prefix and correct
authorship (`totalwindupflightsystems`), the sibling is already completing
the work.

**Response:** pull, verify sibling's commits (build+vet+test), mark tasks done
on the board. Do NOT re-do work the sibling already did.

### 4. git diff --cached --stat shows fewer files than expected

When `git add <files>` silently skips files already in HEAD (committed by sibling),
your commit scope is smaller than intended.

**Response:** verify the skipped files are in the sibling's commit. Don't
re-stage them.

## Recovery Flow

```
1. Detect   → write_file warning OR git log shows sibling commits
2. Read     → re-read the file(s) the sibling modified
3. Compare  → diff sibling's version vs your intent
4. Accept   → keep sibling's changes when correct
5. Delta    → write ONLY files the sibling didn't touch
6. Build    → go build ./... (may need import fixes)
7. Test     → go test ./... (may need test fixes if sibling renamed types)
8. Commit   → git add <delta files only> + commit + push
9. Board    → mark tasks done with sibling's commit hash
10. DuckBrain → note the overlap for supervisor awareness
```

### 5. Test file API mismatch (compilation failure, not test failure)

When a sibling writes a test file that references types/methods your
implementation doesn't export (different constructor names, field names like
`PID` vs `AgentPID`, status constants like `Complete` vs `Completed`), the
test file will fail at **compilation** level — `go build` passes but
`go test ./internal/<pkg>/...` fails with `undefined:` errors.

**Response:** do NOT accept the sibling's test file as-is. Either:
- Rewrite the test to match YOUR implementation's API, OR
- Rewrite YOUR implementation to match the sibling's test API (if their
  API is better — wider, more complete, covers more features)

**Decision heuristic:** prefer the test's API when it covers more use cases
than your implementation. But always fix type mismatches against the ACTUAL
types package — the test may reference non-existent type constants. Run
`go doc <pkg>` on the types package to verify which constants exist.

**Proven:** Rabbit-Hole P7-01 (2026-07-13) — sibling wrote attach_test.go
with `New()`, `AttachManager.Attach()`, `types.FlowPhaseExecution`,
`types.Time`, `session.PID` (should be `AgentPID`), `SessionStatusComplete`
(should be `SessionStatusCompleted`). Rewrote test to match actual
Pipeline/SessionManager API with correct type constants.

## Proven Instances

- **Rabbit-Hole P1 (2026-07-12):** sibling committed P1-01 through P1-06 while foreman
  was writing the same files. Foreman verified, committed only P1-07/P1-08.

- **Rabbit-Hole P3 (2026-07-12):** 3+ parallel ticks wrote conflicting ebpf.go
  (duplicate types), renamed ringBuffer→RingBuffer, and deleted/recreated C files.
  Sibling ultimately produced 5 clean commits covering P3-01 through P3-07 with
  exported types and graceful eBPF degradation. Yielding to the sibling was correct.

- **coding-hermes-scheduler FEAT-API duplicate (2026-07-19):** Foreman tick #16 found
  sibling commit `fde287d` had already implemented queue/openapi/status-filter handlers.
  Foreman re-implemented the same handlers in `90f8130` before detecting the duplication.
  Only net-new value was tests + listQueue SQL fix. Git log check would have caught this.

## Signal 6: Patch tool corruption after partial read_file

When `read_file(path, offset=N, limit=M)` returns a paginated view, the patch tool's
internal buffer contains only that partial window. The patch tool warns:

```
"_warning": "/path/to/file was last read with offset/limit pagination (partial view).
Re-read the whole file before overwriting it."
```

**This is NOT advisory — proceeding WILL corrupt the file.** Writing via `patch()` or
`write_file()` after a partial read can:
- Duplicate code blocks (same function body appears twice)
- Drop sections entirely (content between the paginated window and end of file lost)
- Leave orphaned code fragments (lines shifted, partial function bodies at wrong offsets)
- Mix content from different versions (the partial-read buffer + the patch diff merge)

**Response:** before ANY `patch()` or `write_file()` on a file that was last read with
offset/limit pagination, re-read the full file:
```
read_file(path)   # no offset/limit — get the complete file
```
Then apply the patch against the full content.

**Recovery if already corrupted:** `git checkout -- <file>` restores the committed
version. Discard the corrupted copy — the partial-read buffer and the patch diff
are both suspect.

**Proven:** coding-hermes-scheduler 2026-07-19 — `read_file(server_test.go, offset=540, limit=40)`
followed by `patch()` inserted `mustInsertTick` but also duplicated the function body
after the `// --- health ---` comment. Subsequent reads showed the file at different
line counts (545→556→545→647) on successive access. Required `git checkout` to recover.
Three separate corruption events in a single foreman tick.
