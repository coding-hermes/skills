# Troubleshooting — the failures actually seen

Each entry: the symptom, what it means, and the fix. Read the *meaning* line — most
of these are the system working correctly and being misread.

## `Permission denied (publickey)` on a git command

**Symptom:** a `git clone`/`push` that works in one mode fails in another with
`git@github.com: Permission denied (publickey)`, exit 255.

**Means:** the command ran on the wrong side of the boundary. If it executes on
the agent (via exec or the socket), it uses the **agent's** identity, and a fresh
agent usually holds no git credential at all — its `~/.ssh` may contain only
`authorized_keys`.

**Fix:** run the VCS operation where the credentials are (usually the client,
through a mount), or deliberately give the far side an identity — forward your
key, or place a deploy key. Choose on purpose; do not assume credentials travel
with the files.

**Check:** `bunker exec <agent-id> -- sh -c 'ls -a ~/.ssh; ssh -T git@github.com'`.

## The mount is empty, or does not exist

**Symptom:** `ls` on the mountpoint returns nothing, or the operations land in a
local directory instead.

**Means:** the mount did not happen. A local directory at the same path looks
similar from a distance and is the dangerous case: writes "succeed" into the
wrong place.

**Fix:** confirm the mount is real before trusting it — check the mount table, and
confirm the file you write is visible **from the agent** (`bunker exec <agent-id>
-- ls -l <file>`). A write that appears locally but not remotely was never a
mount.

## `path outside root` on a file verb

**Symptom:** `toolsd: read: fsops: path outside root`, exit 1 — including for a
path that looks relative and harmless (`../../etc/passwd`).

**Means:** confinement working exactly as designed. The verb refuses to escape the
`--root` it was given. This is the correct outcome, not a bug.

**Fix:** none — narrow the path. If you expected the file to be inside the root,
your root is wrong, not the check.

## `lstat <dir>: no such file or directory` on a file verb

**Symptom:** `toolsd: write: fsops: open root <dir>: lstat <dir>: no such file or directory`.

**Means:** the `--root` does not exist. A root that does not exist cannot be a
confinement boundary, so the verb refuses rather than creating one implicitly —
which would silently widen the boundary.

**Fix:** create the workspace root first (`mkdir -p`), then run the verb. Note
this means "the verbs are unusable" usually means "the workspace is not set up",
not "the tools are broken".

## Mountpoint not empty / refuses to mount

**Symptom:** the mount fails complaining the mountpoint is not empty.

**Means:** the tool will not silently shadow files that are already there.

**Fix:** use an empty directory, or unmount/clean the intended one. Prefer a fresh
directory per agent so two agents can never be confused for each other.

## Stale mountpoint, or `umount` says it is busy

**Symptom:** the directory appears mounted but hangs, or unmount refuses.

**Means:** the transport died underneath the kernel mount (network blip, agent
destroyed, host rebuilt) and the mountpoint is a ghost. Processes with a working
directory, or open files, inside it also hold it busy.

**Fix:** leave the tree (no shell `cd`'d inside), close files, then unmount. If it
still hangs it is a dead transport, not a busy one — unmount lazily and re-mount.
Treat a ghost mountpoint as a real failure: it is the case that silently writes to
the wrong place.

## A mounted tree that does not match the agent

**Symptom:** files you see through the mount do not correspond to what the agent
sees, or a mount from an earlier agent is still up.

**Means:** more than one agent exists and you mounted the wrong one's home, or an
old mount survived a spawn/destroy cycle.

**Fix:** mount into a path that **names the agent**, one directory per agent, and
unmount before re-spawning. When in doubt, ask the agent (`bunker exec <agent-id>
-- ls -l <path>`) rather than trusting the mount.

## The agent host is not the host you expected

**Symptom:** host-side checks contradict what the agent reports — a socket or file
"not visible from the host", users whose names differ between sides.

**Means:** you are looking at a different machine. A daemon can provision onto a
host other than its own, and a client config's address is where you *talk to the
daemon*, not where the agent runs.

**Fix:** resolve the agent host from the agent record (`bunker info <agent-id>` →
the mount lines), and ask the agent for its own identity
(`bunker exec <agent-id> -- id -un`). Never infer either from the client config.
