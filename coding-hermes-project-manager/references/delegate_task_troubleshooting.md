# Delegate Task Troubleshooting

## Common Issues

### "tasks must be a JSON array of task objects" Error

This error occurs when the `tasks` parameter passed to `delegate_task` is not properly formatted as a JSON array.

#### Causes:
- Passing a string instead of an array
- Malformed JSON (trailing commas, missing quotes)
- Incorrect nesting

#### Solution:
Ensure `tasks` is a JSON array where each element is an object with:
```json
[
  {
    "goal": "Clear description of what the subagent should accomplish",
    "context": "Background information the subagent needs",
    "output_schema": {
      "type": "object",
      "properties": {
        "findings": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "id_candidate": {"type": "string"},
              "problem": {"type": "string"},
              "how_user_hits_it": {"type": "string"},
              "fix_direction": {"type": "string"},
              "observable_pass_criteria": {"type": "string"}
            },
            "required": ["id_candidate", "problem", "how_user_hits_it", "fix_direction", "observable_pass_criteria"]
          }
        }
      }
    }
  }
]
```

#### Common Mistakes to Avoid
- **Missing commas between objects**: `[ { "goal": "..." } { "goal": "..." } ]` → add comma: `[ { "goal": "..." }, { "goal": "..." } ]`
- **Trailing comma after last object**: `[ { "goal": "..." }, ]` → remove trailing comma
- **Using single quotes instead of double quotes**: `[ { 'goal': '...' } ]` → use double quotes for JSON
- **Passing a string instead of array**: `"[{ \"goal\": \"...\" }]"` → remove outer quotes to pass actual array
- **Incorrect nesting**: ensure `output_schema` is a valid JSON object as shown above

#### Best Practices:
1. Start with minimal tasks to verify formatting
2. Use `write_file` to create a test JSON file first
3. Validate JSON structure before passing to delegate_task
4. Remember that each subagent gets isolated context - repeat shared background

### Transport double-encoding on unattended surfaces (api_server, cron)

On unattended surfaces every tool-call argument is serialized into a JSON string
before transport. A runtime double-encoding layer can deliver your WELL-FORMED
array as a string, so the tool rejects it with the identical error even though
the authoring was correct. Signature: the same argument fails repeatedly
(4+ identical failures in one cycle) while a minimal two-field call
(`[{"goal": "Say hello", "context": "test"}]`) succeeds in the same session.

- After ONE retry of the full payload, test with the minimal payload. Minimal
  passes + full fails with identical JSON semantics = transport encoding, not
  authoring error. Stop rearranging the JSON (re-ordering fields, changing
  quoting, adding whitespace) — no authoring variation fixes the transport.
- Fallback: run the hunt yourself with direct read tools (read_file, terminal,
  search_files) and note the delegation failure in the cycle report. A cycle
  with hand-run hunts is a valid cycle; a cycle aborted for tooling is not.
- **Do not persist with failing delegate_task calls**: If JSON validation passes
  but delegation fails on unattended surfaces, fall back to manual gap hunting
  immediately rather than retrying delegate_task. Continued attempts waste
  cycle time and delay issue resolution.

### output_schema must be a BARE JSON Schema object, not wrapped

The `output_schema` field is itself validated against the JSON Schema meta-schema
before dispatch: `{"type": "object", "properties": {...}, "required": [...]}` at the TOP level.
Two authoring mistakes both fail with a meta-schema error naming a `properties` path —
read the error's `On schema['properties']['type']` line to tell them apart:
- WRAPPED schema: `{"properties": {"type": "object", "verdicts": {...}}}` (the `type` key
  landed INSIDE `properties`) → 'object' is not of type 'object'. Fix: pull `type: "object"`
  and `required` back to the top level next to `properties`.
- INVERTED key/value: a property name written as the `type` VALUE inside a definition
  (`"type": "object"` where the property key should be) → same metaschema failure, a
  different offending line. Fix: re-read the schema as name→definition mappings.
When both errors fire in one tick (e.g. after a JSON re-serialization pass), fix the
STRUCTURE first (bare top-level type/properties/required), then re-check each
property definition — one reserialize-and-resend usually clears both.

### Hunter Final Report Truncated (output length limit)

A hunter can spend its entire output budget on per-probe tool chatter and lose its final findings report: the result returns with `error: "Response truncated due to output length limit"` and a `live_transcript` path. Treat that as NO REPORT — the hunt ran, the conclusions never landed.

- Salvage by grepping the transcript for emitted findings, but a truncated transcript carries NO verified claims: only act on a salvage thread you independently re-verify yourself (run the cited command against the repo first). Never file a conclusion read straight off a dead transcript.
- Prevention is in the brief: require "AT MOST N findings, one line each (`[P0-P3] title — command + key output`), no per-probe commentary". Deep multi-command hunts on big repos are the exposure — the terse-report rule is what survives the output cap.

### Subagent Timing Out

If a subagent returns status: `timeout` (1200s leaf cap on api_server):
- Salvage before re-hunting: read the live transcript tail
  (`~/.hermes/cache/delegation/live/<deleg_id>/task-<n>.log`, last ~60 lines)
  to see which commands the hunter ran and what they returned. A dead hunter
  whose probes were all GREEN (build/vet/test clean, spec selfcheck 0 errors)
  is a valid empty-cycle result with evidence — record those green probes in
  the cycle report instead of spawning a replacement hunter that repeats the
  same 20-minute sweep.
- Only re-hunt if the transcript shows the hunter died before covering the
  brief's main lens, or a probe actually FAILED (that failed probe is itself a
  candidate finding — re-verify it yourself before filing).
- Otherwise treat as no findings; consider manual gap-finding as fallback.
- Check if the task description is too broad — broad "hunt the whole repo"
  briefs are the main timeout cause; a lens + specific entry points fits the
  budget.

### Empty Results

An empty cycle with 0 rows gated-in is VALID when:
- Backlog is already deep (dozen+ pending rows)
- Foreman is actively consuming it (recent ticks completing)
- The cycle's value is in verification, ledger hygiene, and escalation

## Verification

After fixing delegate_task calls:
1. Test with a simple "say hello" task
2. Verify the subagent completes successfully
3. Check that summaries are returned in the expected format
4. Ensure no concurrent board edits from hunters (they should only READ)

## Related Tools

- Use `terminal` for executing helper scripts when `execute_code` is restricted
- Use `write_file` to create JSON templates for delegate_task
- Use `read_file` to verify file contents before processing

## Real-Session Example

On 2026-09-27 during a digest-pm PM tick on api_server:
- Delegate_task failed repeatedly with "tasks must be a JSON array of task objects" error
- JSON was validated via `echo '$TASKS' | jq empty` and `echo '$TASKS' | python3 -m json.tool` (both passed)
- WAVE_BUDGET was unset (manual gap hunting was correct approach)
- Fallback involved: checking for missing documentation (API.md, INTEGRATION.md), verifying test suite, checking board status manually
- Lesson: On unattended surfaces, validate JSON first, then if delegation fails, immediately fall back to manual gap hunting using local tools rather than persisting with delegate_task attempts.

## Real-Session Example (logsey-pm)

On 2026-09-27 during a logsey-pm PM tick on api_server:
- Delegate_task failed with "tasks must be a JSON array of task objects; received a string that could not be parsed as JSON" error despite valid JSON construction
- JSON validation passed via `echo '$TASKS' | jq empty` and `echo '$TASKS' | python3 -m json.tool`
- WAVE_BUDGET was unset (confirmed via `printenv WAVE_BUDGET` returning empty)
- Manual gap hunting performed: checked project workdir, README, board status, and verified ledger items
- Found 6 ledger items (GAP-209 through GAP-214) with status 'added' that corresponded to existing board rows
- Verified completion status with real commands: `test -f CONTRIBUTING.md && echo "PASS" || echo "FAIL: missing"` for GAP-209
- Ledger items remained in 'added' status as work was not completed
- Lesson: On unattended surfaces, even with valid JSON, delegate_task can fail due to transport-layer encoding; always validate JSON first, then if delegation fails, immediately fall back to manual gap hunting using local tools rather than persisting with delegate_task attempts.