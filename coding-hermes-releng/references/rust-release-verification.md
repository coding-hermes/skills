# Rust/Cargo release verification

Use this reference when the repository ships a Rust binary or library through Cargo.

## Candidate and version chain

Run all checks in a clean detached worktree at the fetched candidate SHA, never in a shared or deployed checkout.

```bash
cargo metadata --format-version 1 --no-deps
cargo tree --workspace --locked
rg '^version\s*=' Cargo.toml '**/Cargo.toml'
rg '^## \[v?[0-9]+\.[0-9]+\.[0-9]+\]' CHANGELOG.md CHANGELOG.*
```

Reconcile the workspace/package versions, changelog heading, proposed tag, and any runtime version command. A matching manifest and changelog do not prove that the binary was built or published from that tree. Inventory version surfaces by searching for the LITERAL current version string across the tree, not only for `^version =`: a workspace root using `[workspace.package] version` plus members that `version.workspace = true` needs one edit, while a member carrying a hard-pinned literal needs its own — and the release script usually derives the tag from ONE of them, so a half-promoted workspace builds a tag whose binary reports the previous number. Record the full list of files holding the literal and cite each in the version-hygiene row.

## Repository-owned artifact path

Inspect the Makefile, build scripts, Cargo workspace metadata, and release documentation first. Prefer the repository-owned release target, but verify what it actually does: build profile, package selection, stripping, packaging, checksums, and publication. A target that only leaves a bare binary in `target/release` is a build step, not a complete release artifact pipeline.

Run format/check/test/build as separate bounded commands and save complete logs. For the release build, use the repository's declared flags and lockfile policy; use `cargo build --release --locked -p <package>` only when the repository's contract supports `--locked`. Native dependencies such as bundled database or C/C++ builds can make Cargo appear idle for a long time; do not infer success from process existence, partial output, or a previously built binary. If the bounded command ends without an exit receipt and a completed artifact, mark the artifact gate UNVERIFIED and do not retry the same side effect through another wrapper in the same tick.

After a completed build, verify the artifact from the candidate worktree:

```bash
file target/release/<binary>
target/release/<binary> --version
git describe --tags --always --dirty
sha256sum target/release/<binary>
mkdir -p <fresh-package-dir>/bin
cp target/release/<binary> <fresh-package-dir>/bin/
tar -C <fresh-package-dir> -czf <package>.tar.gz bin/<binary>
sha256sum <package>.tar.gz > <package>.tar.gz.sha256
```

The runtime version must name the intended release rather than `dev` or an unrelated prior tag. Check `git status --short` before and after the build; generated files or a dirty provenance stamp narrow the evidence. Preserve executable mode inside the tarball and verify the checksum from a fresh download or copied package before publication.

## Multi-hour native builds: put them in a unit, resume them, stamp them

A bundled C/C++ dependency (DuckDB, SQLite, LLVM, wasmtime) can hold one release build far past
an hour. Launch the repository's build script under a transient user unit from the start instead
of the harness background terminal:

```bash
WT=<carrier-worktree>
systemd-run --user --collect --unit=<repo>-relbuild-<ver> \
  --property=WorkingDirectory=$WT \
  --setenv=CARGO_HOME=<cargo-home> --setenv=CARGO_TARGET_DIR=$WT/target \
  --setenv=PATH=$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin \
  /bin/bash -lc 'scripts/<repo-build>.sh -p <pkg>; echo BUILD_RC=$?; ./target/release/<bin> --version'
```

Why: a harness-tracked background process can be terminated mid-build (`exit 143`) with no
kernel OOM record, no guard log, and a still-growing target dir — nothing in the environment
explains it, and re-running the same way loses the whole build. A unit survives the session and
logs `BUILD_RC` plus the version stamp into the journal, which is the receipt.

Resumability makes the retry cheap. The `cc` crate keeps its objects in
`target/release/build/<sys-crate>-<hash>/out/*.o`, so a second run of the same target dir skips
them: a build killed after ~2 h in the C++ batch can finish in ~15 min, and a later forced
re-run of just the version-stamp crate takes seconds. Do not `cargo clean` to "start fresh".

Monitoring, because the naive probe lies: during the C++ phase `pgrep -c rustc` is 0 while cargo
is alive-but-idle, and `du` growth is dominated by link churn. Poll the compiler fan-out and the
object count, and only call it stalled when the count stops moving across several minutes:

```bash
pgrep -c cc1plus
ls <target>/release/build/<sys-crate>-*/out/*.o | wc -l
journalctl --user -u <unit> -n 5 --no-pager
```

## Stamping the exact tagged SHA

A build script that emits provenance from `git describe --tags --always --dirty` is only as fresh
as its rerun trigger. In a LINKED WORKTREE `.git` is a file, so
`cargo:rerun-if-changed=.git/HEAD` does not track the worktree's HEAD — a build that spans your
prep commit keeps the previous describe, usually with a `-dirty` suffix from the uncommitted
edit. Force the stamp and prove it before packaging:

```bash
touch <pkg-with-build.rs>/build.rs        # or `cargo clean -p <that crate>`
<scripts/build>.sh -p <pkg>               # seconds once deps are compiled
./target/release/<bin> --version          # must be: <ver>, build: v<prev-tag>-<n>-g<EXACT-SHA>, no -dirty
```

Never upload an asset whose stamp names another commit or carries `-dirty`; it is the one field a
downloader uses to check what they have, and a correct binary with a wrong stamp is still wrong
evidence. Strip AFTER the rebuild (`strip --strip-debug --strip-unneeded`) and re-run the version
and `--help` smoke on the stripped copy, not the unstripped one.

## Cross-target publish leg (prove it before the first tag)

Most Rust release workflows build more than the host target, and a never-tagged repo has zero runs of that workflow — so the first tag push is the first time the non-host leg compiles, at the moment the tag is already public and immutable. Convert that into measured evidence at the candidate, using the workflow's OWN environment rather than an invented one:

```bash
rustup target add aarch64-unknown-linux-gnu
CARGO_TARGET_DIR=<scratch>/arm64-target \
CARGO_TARGET_AARCH64_UNKNOWN_LINUX_GNU_LINKER=aarch64-linux-gnu-gcc \
CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc \
AR_aarch64_unknown_linux_gnu=aarch64-linux-gnu-ar \
cargo build --release --locked --target aarch64-unknown-linux-gnu \
  --bin <binary> --bin <second-binary>
file <scratch>/arm64-target/aarch64-unknown-linux-gnu/release/<binary>
```

Copy the variable names out of the workflow file instead of guessing: Cargo reads the linker from `CARGO_TARGET_<TRIPLE_UPPER>_LINKER`, while the `cc` crate reads `CC_<triple_with_underscores>` / `AR_<triple_with_underscores>`, and bundled-C dependencies (`rusqlite`'s `bundled` SQLite, `openssl`) fail to link when one of the pair is missing or the triple spelling drifts. Give the cross leg its own `CARGO_TARGET_DIR` so its artifacts can never be mistaken for host output, and record binary sizes plus the `file` line (`ELF 64-bit LSB pie executable, ARM aarch64`) as the receipt.

Classify these correctly: they are artifact-STRATEGY evidence, not publishable assets. They retire the toolchain half of the risk and leave the workflow wiring (tag/version/CHANGELOG preflight, artifact naming, checksum assembly, release creation) unproven — which is what the publish-path RELEASE-* row owns.

## Stale deployed binary

Inspect deployed or PATH copies separately from the candidate artifact:

```bash
<path-to-binary> --version
git status --short
stat -c '%y %s %n' <path-to-binary>
```

Treat an older build provenance, older modification time, or a version that does not name the candidate as stale-install evidence. Never rebuild or replace the deployed copy during a readiness sweep merely to make the freshness check pass.

A binary whose `build.rs` stamps `git describe --tags --always --dirty` hands you a free provenance receipt — decode it, do not eyeball it. `build: v0.4.0-50-g4216c7f` reads "commit 4216c7f, 50 commits past v0.4.0", so settle containment mechanically with `git merge-base --is-ancestor 4216c7f <candidate>`: true means the installed copy contains that commit, false means it predates it. A stamp naming the latest published tag while the candidate has advanced is the plainest staleness receipt available, and it stays stale even though the self-reported semver string (`0.4.1`) is byte-identical to the release — manifests are only promoted at cut time, so the version string alone can never distinguish a release install from a pre-release build. Report the stamp verbatim beside the tag peel and the candidate SHA.

## A cold release build that dies at -9 is the host's memory guard, not a code failure

A bounded `cargo build --release` can end with `exit_code: -9` and NOTHING in
`dmesg`/`journalctl -k`. The kill usually came from the harness's own I/O-thrash guard,
not the kernel OOM killer, so empty kernel logs do not clear the build — and relaunching
the same unbounded command just gets killed again. Confirm from the guard's own logs:

```bash
journalctl --since -40min | grep -E 'hermes-worker-proc|scope.*(stop|kill)|Killing'
ls -t ~/.hermes/logs/*reaper* ~/.hermes/logs/*scope* 2>/dev/null | head
```

A multi-GB swap peak driven by one native dependency (bundled DuckDB/SQLite, LLVM,
`cc1plus` fan-out) is the signature. Retry capped, in a transient user unit:

```bash
systemd-run --user --unit=<repo>-relbuild-<ver> \
  --property=MemoryMax=10G --property=MemorySwapMax=2G \
  --setenv=CARGO_BUILD_JOBS=6 --setenv=CARGO_TARGET_DIR=<scratch-target> \
  --setenv=PATH=$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin \
  --setenv=CARGO_HOME=$HOME/.cargo --setenv=RUSTUP_HOME=$HOME/.rustup \
  /bin/bash -lc 'cd <worktree> && <repo build script or cargo build --release -p <pkg>>'
```

Pass `PATH`/`CARGO_HOME`/`RUSTUP_HOME` explicitly — a bare unit has no login shell and
fails to find cargo before compiling anything. Poll coarsely (hundreds of seconds apart):

```bash
systemctl --user is-active <unit>; pgrep -c rustc; pgrep -c cc1plus
du -sh <scratch-target>; ls -l <scratch-target>/release/<binary>
```

Zero compilers with a still-growing target directory is link/compile churn, not a stall —
wait for the unit to terminalise before calling it dead. The build is evidence only when
`--version` reports the candidate version triple, `file` reports the host target, and a
`--help` smoke test exits 0.
