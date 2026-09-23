# Remote exec semantics — measured, not assumed

Measured 2026-09 on a Hetzner box (64 cores) with `--image-spec` agents while driving
three real repositories through a remote loop. Every item here cost a run to discover.

## 1. `exec` is not your HOME

`bunker exec` runs as **root** with `HOME=/root`, and its working directory is the
agent's home. So `cd $HOME/<repo>` silently looks in the wrong place.

**Rule:** never use `$HOME` or `~` in a remote command. Spell the absolute agent path
(`/home/bunker-<agent>/<repo>`).

## 2. Every exec starts a FRESH container

Two consecutive execs reported different hostnames; markers written to `/tmp` and
`/root` vanished; **only the workspace bind survived**. Consequences:

- **Caches evaporate.** Go's defaults live under `/root`, so export them into the
  workspace in *every* exec or every build is cold:
  `export GOMODCACHE=/home/bunker-<agent>/go/pkg/mod` and
  `export GOCACHE=/home/bunker-<agent>/.cache/go-build`. With GOMODCACHE in the
  workspace the auto-downloaded toolchain persists too (downloaded once).
- **A backgrounded process dies with its exec.** Never run a build with `&` and poll
  it. Run it in the foreground of one exec.
- **Runtime installs evaporate.** `apt-get install` is undone on the next call, so a
  project needing a C compiler pays the install on *every* building exec. The image
  spec is the only durable place for tooling.

## 3. `--timeout` defaults to 30 seconds

Any build longer than 30s dies with `deadline_exceeded: context deadline exceeded`,
which reads like a failure rather than a missing flag. Real builds take minutes.
Always pass `--timeout` (e.g. `--timeout 1800`).

## 4. Bulk transfer belongs on `bunker cp`, never the mount

Measured: writing a 637M repo through the sshfs mount reached ~0.05 MB/s and wedged in
uninterruptible `D` state; the same payload via `bunker cp` moved at ~7.3 MB/s — about
150x. Disk was not the limit (890 MB/s to the workspace).

**The mount is an edit channel.** Also note `bunker cp` writes to the **host** path
while exec sees the **container** path — copy into the workspace, not `/tmp`.

And remember the agent cannot clone a private repo at all (no credentials): seeding a
real tree is a control-side job.

## 5. Read-only git goes on the agent

A whole-tree `git status` over the mount can block in `D` state, and a killed git
leaves a stale zero-byte `index.lock` that then blocks the next commit. Take read-only
git state via exec; keep writes (commit/push) on your side through the mount.

## 6. The image may be bare

Seen missing: `python3`, `rg`, any C compiler (`CGO_ENABLED=0`), so a cgo module fails
with `undefined: Conn` and agent-side scripting is shell/Go only. Check with a quick
`command -v` sweep before writing a brief that assumes a tool.

## 7. Provenance: a seed mirrors the CONTROL checkout

Seeding via a local bundle copies the control side's state, **including commits that
were never pushed**. Fetch first if freshness matters, and record the base sha so the
branch you push has a known ancestor.
