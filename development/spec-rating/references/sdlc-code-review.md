# SDLC: code review & merge process

## What a complete review section documents
- **What needs review**: every change (the floor), with the exception classes
  (the owner's own repos may merge directly — but that is a stated policy,
  not an accident).
- **The reviewer's checklist**: what a reviewer is trusted to verify (the ACs
  are met; the failure paths are handled; the tests prove it) vs what
  machines verify first (lint, types, secrets) — humans review design,
  machines review style.
- **The evidence rule**: a PR claims what it does and SHOWS it (test output,
  live verification); claims without evidence bounce. 'It works on my
  machine' is not evidence; the CI verdict and the logged probe are.
- **Merge mechanics**: squash vs merge-commit policy, the commit message
  convention (trailers, co-author), and the landing discipline (rebase/
  merge-by default, the broken-window rules for red main).
- **The return path**: how reviewed-off findings get fixed (new commits vs
  rebase), and the stale-PR policy.

## Rating checks
- FAIL if merge authority is undefined (who may merge what).
- FAIL if review claims aren't evidence-backed (the rubber-stamp failure). 
- FAIL if the process cannot answer 'the review is silent for a week' —
  every gate needs a timeout and an escalation.
