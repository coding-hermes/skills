---
name: coding-hermes-remote-bunker
description: >-
  Working on a REMOTE bunker agent from your own machine — choosing between the
  SSHFS mount, the socket-served toolsd surface, and plain remote exec, and why
  that choice decides which credentials can reach GitHub and other SSH resources.
version: 1.0.0
author: Bane + Hermes
platforms: [linux]
metadata:
  hermes:
    tags: [coding-hermes, bunker, remote, sshfs, mount, credentials, toolsd, ssh]
    related_skills:
      - coding-hermes-tools-usage
      - coding-hermes-config
      - coding-hermes-map
---

# Remote Bunker — Work Against a Remote Agent Without Losing Your Credentials

> See [coding-hermes-map] for the full skill hierarchy and when to use each skill.

## Why This Skill Exists

A bunker agent is a **separate machine with a separate identity**. That single
fact causes most of the confusion: files can be reached several ways, the ways
look interchangeable, and they are not — because they differ in **where the
command actually runs**, and therefore in **which credentials are available to
it**. Choose the mode carelessly and a `git push` that works in one mode fails
with `Permission denied (publickey)` in another, with nothing about the files
themselves having changed.

This skill answers: *how do I work on a remote agent's tree, and which access
mode gives me the credentials and the safety properties I need?*

## The Credential Rule (the load-bearing idea)

> **Work executes where the tool runs, not where the files live.**

A mount is **I/O**, not execution. Mounting a remote directory does not move the
work to the remote: your commands still run on *your* machine, reading and
writing through the mount. Your shell, your Git config, your SSH keys, and your
`gh`/`glab` authentication are all still the local ones — so **every SSH-based
resource you already have (GitHub and anything else keyed to your identity)
keeps working unchanged**, with nothing to provision on the agent.

The opposite is true the moment execution moves to the agent: exec and the
socket-served tool surface run verbs **in the agent's own context**, so they
carry the agent's credentials, its PATH, and its HOME — which are not yours.

**Verified shape of a fresh agent** (re-measure per deployment rather than
trusting this line):

| Where the command runs | Who authenticates to GitHub |
|---|---|
| Your control box, through a mount | **You** — your existing SSH identity |
| The agent, via exec or the socket | **The agent** — which by default holds NO git credentials (`~/.ssh` may contain only `authorized_keys`: no private keys, no `gh`), so outbound `git@github.com` fails with `Permission denied (publickey)` |

That asymmetry is the whole reason to reach for a mount first.

## Choosing an Access Mode

**Question:** given a task on a remote agent, which access mode should I use?

**Criteria (ranked):**

1. **Where must the command run?** If the work is *your* tooling (your editor,
   your `git`, your linters) it belongs on your side → mount. If the work must
   happen *inside* the agent's confinement → exec or the socket.
2. **Which credentials does it need?** If it authenticates to GitHub or another
   SSH-keyed resource, prefer the side that already holds a working identity —
   usually yours. See the Credential Rule.
3. **Is a persistent directory view needed, or a one-shot command?** A directory
   you navigate, diff, and build in → mount. A single verb or a scripted check →
   exec.
4. **Do you need the tool surface's advanced verbs** (strict patch, atomic
   multi-file apply, diff3, leases)? Those live in the toolkit → the socket or
   exec path, not the mount.
5. **How much data and how often?** Mounts carry per-operation round-trip cost;
   a full index or build over a mount is slow. Bulk work belongs on the far side.

**Live source of truth:**
- Agent identity and where it actually lives: `bunker info <agent-id>` — read the
  `SSHFS Mount` / `Docker Tunnel` lines. **The daemon host is frequently NOT the
  agent host; never infer the agent host from your client config.**
- What an agent's user is: `bunker exec <agent-id> -- id -un` (the agent's own
  answer; host-side user lookup is unreliable).
- Available verbs and their contracts: `toolsd describe --json`.

**Tie-breakers (in order):**
1. Credentials beat convenience — pick the mode whose side holds the identity.
2. Prefer the mode that leaves **no** new credential on the remote.
3. Prefer the mode whose failure is **loud** (a mount that did not happen is
   visible; a permission denial deep inside a script is not).
4. When both work, prefer the one with the smaller blast radius.

## The Recommended Loop: code native on the remote, compute on the remote, git on your side

The rule above composes into one workflow that gives the best of both sides. The
agent owns the code natively; you own the identity; the agent owns the compute.

```
scaffold/edit  ->  through the mount (files ARE the agent's, natively)
git add/commit ->  locally, through the mount (your credentials, your config)
build/run/test ->  on the agent, via `bunker exec` (its CPU, not yours)
change again   ->  through the mount
```

Why this is the shape to reach for:

- **Code is 100% native to the agent.** Nothing is copied in, so nothing drifts.
  The agent modifies the tree it actually runs.
- **Your commit path never changes.** `git` runs on your side, so your identity,
  your hooks and your forge auth apply — see the Credential Rule. There is no
  second credential path to keep in sync.
- **Build/run/test cost you no local compute.** The heavy work happens on the
  agent, so a laptop can drive many projects at once, limited by its *memory*
  for the mounts and its own Hermes loop, not by compile and test load.
- **Nothing is transferred back and forth.** No syncing a tree to the remote to
  build it, and no pulling artifacts back. The mount already shows you the
  result.

**The load-bearing precondition: a correct `.gitignore`.** Build outputs land in
the tree you also commit from, so anything not ignored shows up as a change you
might commit by accident — binaries, object files, caches, and test output:

```gitignore
/bin/
*.o
*.test
__pycache__/
node_modules/
```

This is not tidiness; it is what makes "build remotely" safe. An artifact that is
not ignored turns into a 40 MB binary in your history, and every future clone pays
for it. Prefer build output in an ignored directory (`bin/`, `dist/`) rather than
next to the sources.

**The precondition nobody expects: the agent needs the TOOLCHAIN.** Offloading the
compute requires the compiler to exist on the far side. A mount gives you a native
tree and your own credentials; it does not give you a toolchain, and a fresh agent
may have almost nothing installed. Check before you commit a project to this loop:

```
bunker exec <agent-id> -- sh -c 'for t in go python3 gcc make node cargo; do
  printf "%-8s %s\n" "$t" "$(command -v $t || echo ABSENT)"; done'
```

If the agent cannot build the project, "the remote does the building" is not yet
true for that project however well the transport works — provision what is missing
through the agent's tool-provisioning path, or keep that project's build local.
And prove the loop with the toolchain the project actually uses, not the one you
happen to have.

Prove the loop is real rather than assumed, in one pass:

```
bunker mount <agent-id> ~/remote-tree
cd ~/remote-tree/<repo> && git status          # clean before you start
<edit files>
git commit -am "…"                             # local commit, your identity
bunker exec <agent-id> -- sh -c 'cd <repo> && <build> && <test>'
git status                                     # MUST still be clean
```

If that last `git status` is not clean, your `.gitignore` is incomplete — fix it
before committing anything else.

**Worked example:** `references/local-git-remote-compute.md` walks this through a
real scaffold → commit → remote build → clean-status cycle, including what each
step proves.

## Operating a Mount

```
bunker mount <agent-id> <local-dir>      # mount the agent's home
bunker umount <local-dir>                # unmount cleanly
bunker exec <agent-id> -- <command>      # run something IN the agent's context
```

Procedures and properties worth knowing:

- **Mount, then work locally.** Standard tools, your Git, your editor — all with
  your existing credentials, because execution stays on your side.
- **The mountpoint is private (`0700`).** A deployment may deliberately drop
  `allow_other` from the generated command; that option would expose the agent's
  files to other local users in exchange for nothing on a private mountpoint.
- **Confinement still comes from the tree, not the transport.** The mount gives
  you a directory; the security boundary you care about is which tree the work is
  aimed at.
- **Check the client's `sshfs` against the current advisory before trusting it
  with untrusted code.** The mount runs locally, so a vulnerable client is *your*
  exposure — a symlink planted by untrusted code on the far side can redirect
  local writes. A deployment may have no fixed package; a patched build is then
  something you build, not something you install. See the deployment's mount
  security rows.

## Operating the Socket / Exec Path

The socket-served tool surface gives the toolkit's **advanced** verbs (strict
patch, atomic multi-file apply, diff3, leases) against the agent's tree, running
**as the agent**. Prefer it when the verb — not the directory — is the point.

- **Same confinement rule, different executor.** The verbs run on the far side,
  so they obey the agent's identity and its HOME/PATH.
- **A workspace root that does not exist is refused, by design.** A root that
  does not exist cannot be a confinement boundary. Create it first; the error
  names the problem.
- **Any operation that authenticates outbound needs the agent to hold an
  identity** — either forwarding your key to it, or a credential it owns. Do not
  assume the mount's credential story carries over; it does not.
- **Never treat this transport as isolation.** The service runs as the agent
  user, so anything running as that user — including untrusted repository code
  the agent executes — can call every verb.

## Recording

Record what you chose and why, so the next agent inherits the decision rather
than rediscovering it:

```
duckbrain remember --namespace <project> --key /remote-bunker/<agent-class>/access-mode \
  --domain event --content "<mode>, <why>, <date>, revisit when <trigger>"
```

Record the **mode and the reason**, never a credential and never a credential's
location.

## Anti-Patterns

- **Assuming a mount moves execution.** It does not. If a command needs the
  agent's environment, a mount will not give it to you — and if it needs *your*
  credentials, the socket path will not give you those.
- **Provisioning a credential on the agent when the mount would have avoided it.**
  The cheapest credential is the one you did not have to place.
- **Hardcoding the agent host.** Resolve it from the agent record. A daemon can
  provision onto a host other than its own.
- **Trusting host-side user lookup for an agent's identity.** Ask the agent.
- **Leaving an untrusted tree mounted while doing unrelated work.** The exposure
  is local.
- **Documenting this transport as a security boundary.** It is not one.

## references/

- `references/access-modes.md` — the side-by-side comparison, worked through a
  concrete "clone, edit, push" task.
- `references/local-git-remote-compute.md` — the recommended loop measured end to
  end: local git through the mount, remote build, and the `.gitignore` rule that
  keeps remote artifacts out of your history.
- `references/troubleshooting.md` — the failures seen in practice (permission
  denied after a copy, empty mount, stale mountpoint, credential confusion) and
  what each one actually means.
