# Process: the spec is the ONLY memory (the doctrine)

"Humans naturally find ways to store things, communicate, and improve them.
You don't have that ability, so you need to document how everything needs to
actually work. If you don't document it in the specifications, where would
you document it?"

## The doctrine
A human team has hallway conversations, shared assumptions, manager
hand-waving, and a culture that carries unwritten knowledge. Agents have
NONE of that. For an agent fleet, the specification tree is the TOTAL
collective memory:

- **Undocumented = nonexistent.** A requirement that isn't in a spec file
doesn't exist. A decision made in a conversation and not written into the
owning file evaporates at session end. A fact learned by one agent dies
with its context window unless it lands in the tree.
- **Everything owns a file.** Every requirement, decision, integration,
and invariant lives in exactly ONE owning file (the file that answers
'what happens if this breaks?'). The ownership registry is part of the
spec set. Orphan knowledge — true, written down nowhere that owns it —
is a defect of the same severity as a missing test.
- **The session discipline**: any workhorse session that LEARNS something
(along a probe, a correction from the operator, a discovered constraint)
writes it into the owning spec file BEFORE the session ends. Learning
that doesn't reach a file didn't happen.
- **No informal channel is assumed**: no tribal knowledge, no 'everyone
knows', no 'see the chat history'. If a builder needs it, the spec has it.

## What this changes about rating
A spec set is rated not only per-domain but on MEMORY COMPLETENESS:
- Does every file in the repo that encodes a decision trace to a spec
section that owns it?
- Does every operator answer given during planning land in the tree?
- Are there statements true only in conversations (the invisible spec)?

## Rating checks
- FAIL if a load-bearing fact exists only in a person's head or a chat log.
- FAIL if two files disagree about the same fact with no ownership rule
  (one file owns the fact; others link).
- FAIL if a session's discoveries are not recoverable from the spec tree
  by a fresh agent.
