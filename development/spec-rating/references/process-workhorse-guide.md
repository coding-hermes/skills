# Process: how a WORKHORSE model uses this set (the core reframe)

Frontier models can plan. Workhorse models (cheap, fast, good at following
process) cannot reliably plan — but they can ANSWER questions. This skill set
exists to convert that: the resource files are question ladders, and the
answers, written down in order, ARE the spec.

## The workhorse loop
**First, pick the files:** run `process-file-routing.md` — the project shape
gives the minimum set, signals add files, and every family you skip gets a
written reason. Do not choose files by name proximity.
For each resource file in that set:
1. **Load the file.** Read its three sections: what a complete spec documents,
   the questions it must answer, the FAIL checks.
2. **Answer every question, one at a time.** Answers come from: the operator
   (ask, don't invent), the existing codebase (read, cite file:line), or a
   decision record (write one if the answer doesn't exist). An unanswered
   question is NEVER silently skipped — it is either answered, marked
   OPEN with an owner, or marked NOT-APPLICABLE with a reason.
3. **Write the spec section.** The answers become prose + artifacts in the
   spec's section for this domain, using the file's required-artifact list.
4. **Self-rate against the FAIL checks.** Any FAIL = the section is not done.
5. Move to the next file. When no file applies unresolved, the spec is done,
   and the same files become the RATING rubric for a second agent to verify.

## Rules that make workhorse output trustworthy
- **Never let the model plan freeform.** Every design decision must land in a
  resource-file section; if no file covers it, ADD A FILE (that is how the set
  grows) instead of letting the decision live in chat history.
- **Citations over recall.** Answers cite a source (operator statement, code
  location, prior decision id). Uncited claims are drafts.
- **One decision, one place.** Cross-references, not restatements — restated
  decisions drift.
- **The failure path is part of every answer.** A decision without its
  failure answer is half a decision.

## Why this works
A workhorse model walking ~50 question ladders answers ~500 concrete
questions. Nobody — frontier model or human — reliably holds 500 open
decisions in mind at once; the ladder means nothing is held, everything is
written. The spec stops being a memory test and becomes a checklist
execution, which is exactly what workhorse models are good at.
