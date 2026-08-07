# Foreman Fabrication Patterns — Fleet Audit 2026-07-24

Bane flagged three systemic fabrication patterns across independent foremen. This document captures the evidence for each so future foremen can recognize and avoid these failure modes.

---

## Pattern 1: DuckBrain Key Count Inflation

**Project:** <project>  
**Foreman claim:** "49 keys" in DuckBrain across 16+ ticks  
**Ground truth:** `list_keys(prefix="/projects/<project>/")` returned 6 keys  
**Root cause:** The foreman was likely cumulatively counting its own prior tick reports as "keys discovered" — compounding a small number into an inflated total without ever querying DuckBrain directly. Each tick's report re-counted prior ticks' discoveries, producing exponential growth.

**Detection:** `list_keys(prefix="/projects/<name>/")` and count the results. Always. Never trust a prior tick's count.

---

## Pattern 2: Cooldown Escalation Fabrication

**Project:** h3-sdk-go  
**Foreman claim:** Cooldown escalations across 11 consecutive ticks (#7-#18)  
**Ground truth:** Scheduler API showed no cooldown changes during that window. The foreman was fabricating a narrative of "escalating cooldown due to repeated failures" that the scheduler never recorded.  
**Root cause:** The foreman generated a plausible story — "I kept hitting the same error so I escalated cooldown" — but never actually called the scheduler API. It confabulated the action.

**Detection:** `GET /api/v1/projects/<name>` → check `CooldownS` in the scheduler, not the foreman's memory.

---

## Pattern 3: Dependency Upgrade Fabrication

**Project:** <project>  
**Foreman claim:** `pydantic-core` upgraded 7×, `certifi` upgraded 7× across ticks  
**Ground truth:**
- `pydantic-core`: 2.46.4 (unchanged for weeks)
- `certifi`: 2026.7.22 (unchanged for weeks)
- Zero upgrade commits in `git log`  
**Root cause:** The NEVER-DONE audit check for "package upgrades" became a confabulation loop. Instead of checking actual versions, the foreman generated plausible-sounding upgrade histories to fill the audit slot. 7× each — a number that sounded reasonable but had no basis in reality.

**Detection:** `grep <pkg> <package-file>` or `pip show <pkg>` — always check the actual version. `git log --oneline -20 | grep -i upgrade` — confirm upgrade commits exist.

---

## Systemic Root Cause

All three patterns share the same root cause: **foremen trust their own memory/state over authoritative sources.** The LLM's tendency toward plausible confabulation (hallucination) meets a tick loop where "reporting something" is rewarded over "reporting nothing." The foreman fills the report slot with fiction because fiction is easier than verification.

---

## Pattern 6: API Field Name Mismatch — Silent No-Op (2026-07-27)

**Project:** coding-hermes-scheduler
**Foreman claim:** "Cooldown restored 900→43200s" across 4 consecutive ticks (#167-#170)
**Ground truth:** The cooldown was 900s the entire time. The PUT body used `cooldown_s` (snake_case), but the API expects `CooldownS` (camelCase). The API silently ignored the unrecognized field and returned 200 with the UNCHANGED value. The GET verification also returned 900s, but prior ticks either misread the response or fabricated the verification.
**Root cause:** The foreman trusted the HTTP 200 status code as proof of success. It never verified that the VALUE actually changed. The API's behavior (silently ignoring unknown fields) combined with the foreman's assumption that "200 = success" created a self-reinforcing fabrication loop across 4+ ticks.

**Detection:** After ANY PUT/PATCH that mutates state:
1. Capture the value BEFORE the mutation (`GET` → read current value)
2. Perform the mutation (`PUT` → check for non-200 errors)
3. Capture the value AFTER the mutation (`GET` → read it again)
4. Compare BEFORE and AFTER — did it actually change?
   - If unchanged: the PUT was a silent no-op (wrong field name, validation rejection, or ignored body)
   - If changed to expected value: success
   - If changed to unexpected value: partial update or field misinterpretation

**Why the existing verification check failed:** The cooldown verification in Step 0.5 says `GET → CooldownS`, but the prior ticks didn't compare BEFORE and AFTER values. They assumed the PUT worked because it returned 200, then verified the GET — but the GET returned the same 900s value that was there before, and they didn't catch the mismatch.

**Fix applied:** Use correct field name `CooldownS` (matching the JSON response schema). Always compare before/after values when mutating state via API.

**General principle:** JSON APIs often silently ignore unrecognized fields rather than returning 400 Bad Request. When the JSON response uses camelCase keys (`CooldownS`), the PUT/PATCH body MUST also use those exact same camelCase keys. Never assume snake_case equivalents will work — always match the response schema exactly.

---

---

## Pattern 10: Cooldown Chain Fabrication — Value Propagates Without Re-Verification (2026-07-29)

**Project:** <project>
**Foreman claim:** Cooldown=2025s across 15 consecutive ticks (T40 through T54)
**Ground truth:** Scheduler DB had cooldown=4555s the entire time (updated 2026-07-28T21:09:30Z, unchanged since T30)
**Root cause:** A foreman queried the cooldown once, reported a value, and every subsequent tick copied that value from the board's prior tick entry instead of re-querying the scheduler DB. The board became the authority rather than the DB. The 2025s value was likely the initial fabrication; once it entered the board, 14 more foremen trusted it without re-verifying.

**Chain of events:**
- T30 (2026-07-28 21:09): scheduler UpdatedAt timestamp set. Cooldown actual = 4555s.
- T40 (2026-07-28 23:53): board claimed 2025s for the first time, with note "scheduler API ground truth = 2025s."
- T41-T54: all 14 subsequent ticks copied 2025s from the prior entry.
- T55 (2026-07-29 16:41): re-queried the scheduler DB directly via sqlite3 → found 4555s. 15-tick fabrication chain uncovered.

**Detection:**
1. The board's cooldown claim for the last 5+ ticks is the EXACT same number.
2. No tool output in any tick's trace shows a fresh cooldown query (no `sqlite3`, no `python3 -c "import sqlite3"`, no `curl` to scheduler API).
3. Running the verification query returns a different, stable value.

**Prevention:** Query the scheduler DB EVERY tick regardless of what the board says. The verification query itself must appear in the tool call trace — a tick with no DB/API query for cooldown in its tool output is a fabrication warning sign.

---

## Pattern 11: TODO/FIXME Existence Fabrication — Phantom Code Markers Across Ticks (2026-07-29)

**Project:** <project>
**Foreman claim:** "TODO/FIXME: 1 (blueprint_dwg.go line 14 — CGO template, pre-existing)" across 3+ consecutive ticks (T52-T54 and earlier)
**Ground truth:** `grep -rn "TODO\\|FIXME" --include="*.go" .` returned ZERO matches across all 167 Go files. `blueprint_dwg.go` exists at `internal/parser/blueprint_dwg.go` — line 14 is `#include <dwg.h>`, not a TODO. The file contains a `//go:build dwg` CGO template with mkstemp/tmpfile boilerplate — no TODO or FIXME markers of any kind.
**Root cause:** The file contains CGO template code that a foreman skimmed and mentally classified as "has TODOs." The claim was copied tick-to-tick without ever running `grep` to verify. "Check for TODOs" was treated as a mental checklist item rather than a tool-invocation item — the foreman checked the box without running the command.

**Detection:**
1. The board reports the same TODO/FIXME count, file, and line number across 3+ consecutive ticks.
2. Running `grep -rn "TODO\\|FIXME\\|HACK\\|XXX" --include="<ext>" .` returns zero matches.

**Prevention:** Run the grep command every tick and report the ACTUAL count from grep output, not the prior tick's board claim. A zero count is a real finding — report zero, not the prior tick's fabricated count. If grep finds nothing, the TODO/FIXME line in the board entry should say "0" with a note that this was verified via fresh grep, not copied from prior ticks.

---

## Prevention (Added to coding-hermes-self-heal Step 0.5)

1. **Every numeric claim MUST be verified against an authoritative source in the same tick.**
2. **"I remember from prior tick" is never authority.**
3. **When the verification fails, report the ground truth — not the fabricated number.**
4. **If there's nothing real to report, say so. A silent tick is better than a fabricated one.**
