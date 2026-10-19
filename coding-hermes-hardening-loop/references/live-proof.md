# Live proof — writing a proof that can fail

A live proof is a script that boots the real artifact, drives the real path, and
prints measurements you can quote. It becomes evidence only when the same script
(or the same test) demonstrates failure on the pre-change code.

## Shape

```
boot(env) -> wait health -> set up the minimum real state -> act -> read back what
changed -> print each observation with the exact code/string
```

Rules that make it evidence rather than a demo:

- **Real artifact, real transport.** The built binary, the container, two instances,
  a browser. Not an in-process stub of the thing under test, and not a reimplementation
  of the client logic in the script.
- **Assert the negative.** Every security/authority claim needs the refused case:
  no token → named refusal and *nothing written*; wrong key → named refusal; unknown
  row → refused, not silently accepted.
- **Assert nothing was written** where the claim is "refused": count the rows/bubbles/
  files after the call. "Refused" with a side effect is not refused.
- **Print the numbers you will quote.** Counts of hook calls, attempts, budget in
  seconds, chain depth, byte sizes. Prose summaries drift; the printed number is what
  goes into the row.
- **Clean up deterministically.** Delete state files before each boot, kill by pid from
  `$!`/Popen, never `pkill -f <pattern you also appear in>`. A leftover process on a
  fixed port turns the next run into a false failure.
- **Two boots beat one.** Durability claims need: boot → write → SIGTERM → fresh
  process on the same store → read back. Same-process survival proves nothing.

## The control

The control is the part reviewers skip and then get burned by. Choose the strongest
one available:

1. **Run the same test against pre-change code.** Copy the new test file onto the base
   commit and run it. Expect failure — often failure of the "positive" case, because
   the old code never sent the credential at all.
2. **Neuter proof.** A copy of the checker with the verdict call forced to success must
   *accept* the fixture the real checker rejects.
3. **Fabricate the claim.** Feed the system the evidence it is supposed to distrust
   (a canned body, a replayed nonce, a self-asserted identity) and show it refuses.

If none of those is possible, the proof is not evidence yet — say so in the row rather
than dressing a happy path as a control.

## What to record

In the row's summary: the boot configuration (backends, knobs, defaults), each case as
`input → status + named code → recorded state`, the control's failure, and the one
thing you could not measure by hand (name it, e.g. "requires a two-sided handshake —
rests on the branch's 12-case matrix, not my run").
