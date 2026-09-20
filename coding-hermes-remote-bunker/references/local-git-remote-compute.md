# Worked example: local git + remote compute, measured end to end

The loop this walks through, and what each step actually proves. Every number
below came from one real run against a fresh agent; reproduce it rather than
trusting it.

## The loop

```
scaffold/edit  ->  through the mount      (the files ARE the agent's)
git add/commit ->  locally, via the mount (your identity, your hooks)
build/run/test ->  on the agent           (`bunker exec` — its CPU)
<change again>
```

## What was measured

**Mount → scaffold through it.** Files created through the mount appear natively
on the agent; nothing was copied in.

**Local commit is a real commit on the agent.** A commit made on the control side
(`git init` + `git add` + `git commit`, using the local git binary) produced
`f4aa90d`, and asking the **agent** for its HEAD returned the same `f4aa90d`. The
mount is the agent's disk, so there is one repository, not two — no sync step, and
no divergence to reconcile.

**Build and run remotely.** `bunker exec <agent-id> -- sh -c '... build ...'`
executed on the agent (`hostname` confirmed the far side; `id -un` confirmed the
agent's own identity) and produced an artifact on the agent. Nothing was
transferred in either direction: inputs were already there because the mount *is*
the working tree, and the output was created there too.

**`.gitignore` is what makes it safe.** With `bin/` ignored, `git status` through
the mount stayed **CLEAN** even though a freshly built artifact existed on the
agent at that moment. This is the whole point: you can build remotely, repeatedly,
and never see build output as something to commit. Without the ignore rule, the
same run would have offered a binary for commit.

**The local side holds the credential.** `git ls-remote git@github.com:<org>/<repo>`
run on the control side returned real refs — so the side that performs the commit
is also the side that authenticates to the forge. That is why this loop needs no
credential on the agent and no second credential path to maintain.

## The precondition nobody expects: the agent needs the toolchain

**Measured on a fresh agent:** `go` ABSENT, `gcc` ABSENT, `make` ABSENT, `node`
ABSENT, `cargo` ABSENT — only `python3` present.

This is the constraint that decides whether the loop is useful for your project:
**offloading the compute requires the toolchain to exist on the far side.** The
mount gives you a native tree and your own credentials; it does not give you a
compiler. If the agent cannot build the project, "the bunker does the building"
is not yet true for that project, no matter how well the transport works.

So before adopting the loop for a repo, check the far side:

```
bunker exec <agent-id> -- sh -c 'for t in go python3 gcc make node cargo; do
  printf "%-8s %s\n" "$t" "$(command -v $t || echo ABSENT)"; done'
```

Then either provision what is missing (toolchain packages belong to the agent's
provisioning path — see the deployment's tool-delivery rows, and note that a
registry-distributed toolchain belongs to the image/package path rather than to a
copied binary) or keep that project's build local and offload only what the agent
can actually run.

**Run the interpreter/compiler the project needs, not the one you happen to have.**
A loop proven with `python3` says nothing about a Go or Rust project.

## Reproducing the loop

```bash
bunker mount <agent-id> ~/remote-tree
cd ~/remote-tree/<repo>

git status                      # clean BEFORE you start (the baseline)
<edit>
git commit -am "…"              # local identity, local hooks, local credentials

bunker exec <agent-id> -- sh -c 'cd <repo> && <build command>'
bunker exec <agent-id> -- sh -c 'cd <repo> && <test command>'

git status                      # MUST be clean — the artifact is ignored
```

If the final `git status` is dirty, stop and fix `.gitignore` before committing
anything else. Everything after that point inherits the mistake.
