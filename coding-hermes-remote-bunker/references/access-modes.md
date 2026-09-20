# Access modes, side by side

Worked through the task that exposes the difference fastest: **clone, edit, push.**

## The three modes

| | SSHFS mount | Socket-served tool surface | Plain remote exec |
|---|---|---|---|
| **Where commands run** | Your machine (mount is I/O) | The agent | The agent |
| **Whose HOME/PATH** | Yours | The agent's | The agent's |
| **Whose SSH credentials** | Yours | The agent's | The agent's |
| **Advanced edit verbs** (strict patch, atomic apply, diff3, leases) | No — those are toolkit verbs | Yes | Yes |
| **Per-file I/O cost** | Round-trip per operation | n/a | n/a |
| **Bulk build / full index** | Slow (all traffic crosses the link) | Fast (local to the agent) | Fast |
| **Confinement** | The tree you aimed at | `--root` on each verb | The agent's own context |
| **Best for** | Editing, diffing, your toolchain | The tool pool's guarantees | One-shot commands, scripts |

## "Clone, edit, push" in each mode

### Via the mount — the mode that keeps your credentials

```
bunker mount <agent-id> ~/remote-tree
cd ~/remote-tree
git clone git@github.com:<org>/<repo>.git work
cd work && <your editor> src/
git commit -am "…" && git push
```

Every one of those commands runs **on your machine**. Your SSH key, your Git
identity and your forge CLI are the local ones, so `git push` works with the
credentials you already have. **Nothing was provisioned on the agent.** This is
the reason to reach for a mount first: the remote holds the files, your side
holds the identity.

Cost: every read and write crosses the link. Fine for editing and diffing;
painful for `git status` on a huge tree or a full build.

### Via the socket / exec — the mode that gets the tool guarantees

```
bunker exec <agent-id> -- git clone <repo> work
toolsd patch --root <agent-home>/work < change.diff
toolsd apply --root <agent-home>/work edits.json
```

Here the work happens **in the agent's context**, so the agent's identity is what
counts. A fresh agent typically holds **no** git credentials, so the `clone` above
fails unless you either:

- forward your key to it, or
- give it a credential it owns (a deploy key), or
- keep the VCS operation on your side and only run the *edit* verbs remotely.

What you gain is the part a mount cannot give you: strict patch application that
refuses rather than fuzzes, atomic multi-file apply, three-way merge, and edit
leases. Reach for this mode when **the verb is the point**.

### Via plain exec — the mode for one-shots

```
bunker exec <agent-id> -- sh -c 'cd <agent-home>/work && make test'
```

Right when you want a single fact or a scripted check and do not want to own a
mountpoint. Wrong when you want to iterate interactively — you pay a round trip
per command and you are re-establishing context every time.

## How to decide in one pass

1. Does the command authenticate to GitHub or another SSH-keyed resource?
   → Prefer the side that already holds a working identity, usually **yours**.
2. Must the command run inside the agent's confinement?
   → exec or the socket.
3. Do you need refusal-not-fuzz patches, atomic multi-file apply, or leases?
   → the socket / exec path with the toolkit verbs.
4. Are you navigating, diffing, or building in a directory?
   → the mount, unless the tree is large enough that the round trips dominate.
5. Still tied? Choose the mode that puts **no new credential** on the remote and
   whose failure would be **loud**.
