# Standing up a project dev box

A checklist for turning a fresh agent into the thing the loop actually needs: a
provisioned box you mount and drive, the way a LAMP developer treats a server
they log into — except the environment is provisioned deliberately and verified
rather than assumed.

Order matters. Each step is cheap; discovering a missing step *after* you have
written code is expensive.

## 1. Decide the lifetime before you spawn

Agents expire by default and are destroyed at expiry. A dev box is kept, so spawn
with an explicit, generous TTL and extend it while the work is live.

- Spawn with the life you want: `bunker spawn <agent-id> --ttl 24h`.
- Extend while working: `bunker heartbeat <agent-id>`.
- An existing longer expiry is never shortened, so extending is safe — but a
  default TTL applied to a box you meant to keep is a box that vanishes mid-work.

Write down the lifetime you chose. A box that expires during a test run looks
exactly like a flaky test.

## 2. Ask the box what it is (the doctor step)

Do this **every session**, before trusting it. Never inherit an assumption about
what is installed.

```
bunker exec <agent-id> -- sh -c 'for t in go python3 node gcc make cargo; do
  printf "%-8s %s\n" "$t" "$(command -v $t || echo ABSENT)"; done'
bunker agent-tools <agent-id>     # the editing verbs' own dependencies, named
```

Both should return **named** answers. An absent tool is a finding you act on, not
a surprise you discover later. If the project's toolchain is not there, either
provision it or do not adopt this box for that project — do not "try and see".

## 3. Provision the box

The box owns its environment. That means the toolchain the project needs, the
services it talks to, and the credentials *the box* requires for outbound work.

- **Toolchains and interpreters** belong to the box's provisioning path (registry
  packages, version-pinned), not to a binary you copied in.
- **Repositories the box manages itself** can be cloned by the box, with whatever
  identity the box was given.
- **Anything the box authenticates to** needs an identity the box actually holds.
  Which side holds which credential is the decision covered in the main skill —
  settle it here rather than debugging a `Permission denied` later.

## 4. Clone and mount

Decide whether the tree is cloned **by the box** (native, survives a remount, and
is the shape the loop assumes) or **by you through the mount**. Prefer the box:
the loop's whole premise is that the code is native to the side that builds it.

Then mount it, and treat the mount as a window rather than a copy:

```
bunker mount <agent-id> <local-dir>
cd <local-dir>/<repo> && git status      # must be clean at the start
```

One mount per project, and the local directory should **name the project** — two
mounted trees that look alike is how you commit to the wrong one.

## 5. Confirm the loop works before writing real code

A throwaway file is enough:

```
<edit a file through the mount>
git commit -am "loop check"                       # local identity
bunker exec <agent-id> -- sh -c 'cd <repo> && <build>'
git status                                        # must still be clean
```

If the last `git status` is dirty, your `.gitignore` is incomplete. Fix it now,
while the cost is one throwaway commit instead of a history full of binaries.

## 6. Record it

Write down, where the next agent will look: the agent id, what the box is for,
which toolchain it carries, where the tree lives, how long the lifetime is, and
anything that surprised you. A dev box that only the person who built it
understands is a dev box that gets rebuilt from scratch.

## What this checklist deliberately does NOT cover

- **Isolation.** The box runs as one user; project code running as that user can
  reach everything that user can reach. Provision accordingly.
- **Secrets management.** This checklist says *which side* holds an identity; how
  that identity is stored and rotated is its own concern.
- **Backups.** A dev box is disposable in principle and precious in practice;
  whatever is not cloned or committed is not backed up by this workflow.
