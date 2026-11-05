# Module section field contract

What a single module section of a master document must contain, in order, and the failure each
field prevents. The governing rule: **a required field that cannot be filled is not
"incomplete" — it is RED, and the empty field is the finding.** A document whose sections are
all comfortably full has stopped measuring and started describing.

Status vocabulary per section: `VERIFIED` / `UNVERIFIED` / `FAILING`. Never blank, never "done".

## 1. Identity

| field | rule |
|---|---|
| name | the file or service as named on disk, not a nickname |
| path | absolute, at the stamped revision |
| revision | the commit the section was derived from; ONE revision per document issue |
| runtime | measured, not assumed (`python3.11`, `bash 5.x`, `go1.26`) |
| owner lane | who is permitted to change it |
| status | the three-value vocabulary above |

## 2. Purpose — what breaks, twice

Two paragraphs maximum, and never a description of behaviour:

- **what breaks if it is absent** — the downstream failure, named.
- **what breaks if it lies** — every component that reports on itself has a mode where it
  reports success. Name that mode here or it will be discovered by an incident.

## 3. Dependencies and library contracts — three tables, because they fail differently

**Runtime** — what must exist on the host:

| dependency | version constraint | required location | how absence is DETECTED |
|---|---|---|---|

A dependency whose absence produces a confusing error instead of a refusal is a defect in this
module, not a host problem. Name the detector: exit 127, a logged line, a typed error.

**Library** — the calls relied on:

| import | provider | the specific call/field relied on | if it changes |
|---|---|---|---|

"Uses requests" is not a contract. "Relies on `client.retrieve` returning a dict or a JSON
string" is one, and it tells the next reader what breaks on an upstream rename.

**Service** — the wire to other modules:

| peer | direction | transport | payload shape | compatibility rule |
|---|---|---|---|---|

Every wire contract names **both sides' file and function**. A contract with one side named is
a rumour, and a rumour is what a worker implements wrongly.

## 4. Verification

| check | command | expected | last run (date) | result |
|---|---|---|---|---|

- Runnable by someone who did not write the module, or it is not a check.
- Prefer a command that fails LOUDLY over one that prints PASS.
- A check that cannot fail is decoration.
- Passed three revisions ago = `UNVERIFIED` today. The date and the revision belong in the row.

## 5. Metrics it emits

| metric | type | labels | what question it answers | where scraped |
|---|---|---|---|---|

**If the module emits none, write `none` and mark the section RED.** An unobservable critical
component means every question about it is answered by reading code or by guessing — and the
absence of liveness data is usually discovered during an incident, at the worst moment.

## 6. Log lines it can generate

| level | line (verbatim, placeholders intact) | emitted when | descriptive / evidentiary |
|---|---|---|---|

- **descriptive**: reports that something happened. Useful for an operator, worthless as proof.
- **evidentiary**: can be cited as proof in a closeout, a verdict or a post-mortem.

A line that announces a state is not evidence of that state — the module that reported
"failed" and the scheduler that read it as a pass is the canonical shape of this defect. When a
line is the only record of an outcome, say whether it is proof or narration.

## 7. Failure modes

| failure | how it presents | how an operator distinguishes it from the row above | recovery |
|---|---|---|---|

Row order matters: two failures that present identically are one row that has not been
diagnosed. The "distinguishes it" column is what makes the table usable at 3am.

## 8. Evidence of record

Board rows, verdict files, job directories, log excerpts with timestamps — whatever makes the
status checkable by a third party. A status with no evidence pointer is an opinion.

---

## Worked shape (abbreviated)

```
### MOD-nn — <module>
path /home/<user>/<area>/<file>   rev <sha>   python 3.11   owner <lane>   status VERIFIED

Purpose: absent, <downstream flow> never starts. If it lies, <outcome> is recorded as success
that never happened.

Runtime: <binary> (>= x.y) at /abs/path — absence logged as exit 127.
Library: relies on <call> returning <shape>; a rename stops <behaviour> silently.
Service: <peer> | out | <transport> | <payload keys> | <compat rule> (implemented at <file>:<fn>).

Verification: `python3 tests/test_<x>.py` → <expected>, last run <date> @ <rev>, PASS.
Metrics: NONE (RED).
Logs: info `job %s finished rc=%s after %.0fs` — evidentiary.
Failure modes: overrun → rc=124; network → no job dir; silent success → OPEN.
Evidence: board row <id>, job dir <path>.
```
